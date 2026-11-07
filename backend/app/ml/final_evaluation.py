"""The single evaluation of the frozen model on the test partition.

This is the only module allowed to read the test partition. It refuses to run unless a frozen
model exists, and refuses to run twice. It takes the model and threshold as given: it has no
way to change either, and nothing downstream of it feeds back into selection.
"""

from pathlib import Path
from typing import Any

import numpy as np

from app.ml.dataset_preparation import PartitionData, load_partition, partition_path
from app.ml.drift import feature_drift
from app.ml.evaluation import (
    PRD_THRESHOLD_CANDIDATES,
    bootstrap_pr_auc,
    build_slices,
    decimated_curves,
    expected_precision,
    prevalence_adjusted_pr_auc,
    ranking_metrics,
    threshold_metrics,
)
from app.ml.experiment_stages import type_rate_scores
from app.ml.model_artifacts import LoadedModel
from app.ml.pipeline_io import write_json
from app.ml.preprocessing import compact_features
from app.ml.regimes import NORMAL, SPARSE

_REGIME_SLICES = {SPARSE: f"regime_{SPARSE}", NORMAL: f"regime_{NORMAL}"}
_STEPS_PER_DAY = 24


class TestAlreadyEvaluatedError(RuntimeError):
    """Raised when a test evaluation already exists, because the test set is used only once."""

    __test__ = False


class ModelNotFrozenError(RuntimeError):
    """Raised when the model metadata does not record a completed freeze."""


def assert_ready_for_test(metadata: dict[str, Any], output_path: Path) -> None:
    """Stop unless the model is frozen and this evaluation has not already happened."""
    if metadata.get("status") != "frozen":
        raise ModelNotFrozenError("The model metadata is not marked frozen")
    if output_path.exists():
        raise TestAlreadyEvaluatedError(
            f"{output_path} already exists. The test set is evaluated once; "
            "a new evaluation would need a new model version and a new untouched window."
        )


def _score_partition(model: LoadedModel, partition: PartitionData) -> np.ndarray:
    features = compact_features(partition.features)
    return model.pipeline.predict_proba(features)[:, 1].astype("float64")


def _regime_comparison(
    labels: np.ndarray,
    scores: np.ndarray,
    slices: dict[str, np.ndarray],
    threshold: float,
    reference_labels: np.ndarray,
    reference_scores: np.ndarray,
    reference_slices: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Report each regime on test, with validation beside it at the same threshold."""
    report: dict[str, Any] = {}
    for regime, name in _REGIME_SLICES.items():
        test_mask = slices[name]
        reference_mask = reference_slices[name]
        reference = threshold_metrics(
            reference_labels[reference_mask], reference_scores[reference_mask], threshold
        )
        observed = threshold_metrics(labels[test_mask], scores[test_mask], threshold)
        ranking = ranking_metrics(labels[test_mask], scores[test_mask])
        report[regime] = {
            "ranking": ranking,
            "at_frozen_threshold": observed,
            "validation_ranking": ranking_metrics(
                reference_labels[reference_mask], reference_scores[reference_mask]
            ),
            "validation_at_frozen_threshold": reference,
        }
    return report


def _prior_shift_check(
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    reference_labels: np.ndarray,
    reference_scores: np.ndarray,
) -> dict[str, Any]:
    """Compare observed test precision with what prevalence alone predicts.

    If only prevalence changed, validation's recall and false positive rate should still hold,
    and Bayes' rule gives the expected precision. A gap means score behaviour changed too.
    """
    reference = threshold_metrics(reference_labels, reference_scores, threshold)
    observed = threshold_metrics(labels, scores, threshold)
    prevalence = float(np.mean(labels))
    reference_prevalence = float(np.mean(reference_labels))
    return {
        "validation_prevalence": reference_prevalence,
        "test_prevalence": prevalence,
        "validation_recall": reference["recall"],
        "test_recall": observed["recall"],
        "validation_false_positive_rate": reference["false_positive_rate"],
        "test_false_positive_rate": observed["false_positive_rate"],
        "validation_precision": reference["precision"],
        "test_precision": observed["precision"],
        "test_precision_expected_from_prior_shift_alone": expected_precision(
            reference["recall"], reference["false_positive_rate"], prevalence
        ),
        "test_pr_auc_at_validation_prevalence": prevalence_adjusted_pr_auc(
            labels, scores, reference_prevalence
        ),
        "validation_pr_auc": ranking_metrics(reference_labels, reference_scores)["pr_auc"],
    }


def _alerts_by_day(
    labels: np.ndarray, scores: np.ndarray, steps: np.ndarray, threshold: float
) -> list[dict[str, Any]]:
    days = (steps - 1) // _STEPS_PER_DAY
    profile = []
    for day in np.unique(days):
        selected = days == day
        result = threshold_metrics(labels[selected], scores[selected], threshold)
        profile.append(
            {
                "day": int(day),
                "rows": int(selected.sum()),
                "fraud_rows": int(labels[selected].sum()),
                "alerts": result["alerts"],
                "true_positives": result["true_positives"],
                "recall": result["recall"],
                "false_positive_rate": result["false_positive_rate"],
            }
        )
    return profile


def evaluate_frozen_model(
    model: LoadedModel,
    processed_dir: Path,
    output_path: Path,
    config: dict[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    """Run the one test evaluation and save it. The threshold comes from the frozen metadata."""
    assert_ready_for_test(model.metadata, output_path)

    train = load_partition(partition_path(processed_dir, "train"))
    validation = load_partition(partition_path(processed_dir, "validation"))
    test = load_partition(partition_path(processed_dir, "test"))

    cutoff = config["regimes"]["sparse_step_max_rows"]
    threshold = model.threshold
    labels = test.labels.to_numpy()
    steps = test.steps.to_numpy()
    scores = _score_partition(model, test)
    slices = build_slices(test.features, test.steps, cutoff)

    validation_labels = validation.labels.to_numpy()
    validation_scores = _score_partition(model, validation)
    validation_slices = build_slices(validation.features, validation.steps, cutoff)

    type_scores = type_rate_scores(train.features, train.labels.to_numpy(), test.features)
    rule_flags = test.rule_flags.to_numpy().astype("float64")
    bootstrap = config["bootstrap"]

    report = {
        "scope": "Test partition. Evaluated once, after the model and threshold were frozen.",
        "evaluated_at_commit": source_commit,
        "model_fitted_at_commit": model.metadata["source_commit"],
        "model_version": model.metadata["model_version"],
        "model_sha256": model.metadata["model_sha256"],
        "family": model.metadata["family"],
        "frozen_threshold": threshold,
        "overall": {
            "ranking": ranking_metrics(labels, scores),
            "pr_auc_interval": bootstrap_pr_auc(
                labels, scores, steps, bootstrap["replicates"], bootstrap["seed"]
            ),
            "at_frozen_threshold": threshold_metrics(labels, scores, threshold),
            "at_prd_candidates_report_only": {
                f"{value:.2f}": threshold_metrics(labels, scores, value)
                for value in PRD_THRESHOLD_CANDIDATES
            },
        },
        "regimes": _regime_comparison(
            labels,
            scores,
            slices,
            threshold,
            validation_labels,
            validation_scores,
            validation_slices,
        ),
        "regime_cutoff_sensitivity": {
            str(other): {
                name: {
                    "ranking": ranking_metrics(labels[mask], scores[mask]),
                    "at_frozen_threshold": threshold_metrics(labels[mask], scores[mask], threshold),
                }
                for name, mask in build_slices(test.features, test.steps, other).items()
                if name.startswith("regime_")
            }
            for other in config["regimes"]["sensitivity_cutoffs"]
        },
        "slices": {
            name: {
                "ranking": ranking_metrics(labels[mask], scores[mask]),
                "at_frozen_threshold": threshold_metrics(labels[mask], scores[mask], threshold),
            }
            for name, mask in slices.items()
        },
        "baselines": {
            "random_ranking_pr_auc": float(np.mean(labels)),
            "transaction_type_rate": ranking_metrics(labels, type_scores),
            "existing_rule_is_flagged_fraud": threshold_metrics(labels, rule_flags, 1.0),
        },
        "prior_shift_check": _prior_shift_check(
            labels, scores, threshold, validation_labels, validation_scores
        ),
        "feature_drift_train_to_test": feature_drift(
            train.features, train.labels.to_numpy(), test.features, labels
        ),
        "alerts_by_day": _alerts_by_day(labels, scores, steps, threshold),
        "curves": decimated_curves(labels, scores),
        "validation_curves": decimated_curves(validation_labels, validation_scores),
    }
    write_json(output_path, report)
    return report
