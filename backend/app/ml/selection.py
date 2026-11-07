"""Choose the model and threshold from validation evidence, under a rule fixed in advance.

The rule is written in docs/decisions/0002-phase-2-decisions.md and was committed before any
candidate was scored. Every step's outcome is saved, including rejected candidates. Nothing
here can read the test partition.
"""

import json
import platform
import statistics
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.candidates import MODEL_FAMILIES, CandidateSpec
from app.ml.evaluation import (
    PRD_THRESHOLD_CANDIDATES,
    bootstrap_pr_auc,
    decimated_curves,
    out_of_bag_threshold_behaviour,
    paired_bootstrap_difference,
    ranking_metrics,
    threshold_for_fpr_cap,
    threshold_for_max_fbeta,
    threshold_metrics,
)
from app.ml.experiment_stages import ExperimentData, best_run
from app.ml.experiments import RunStore, fit_candidate, score_rows, scores_digest
from app.ml.model_artifacts import save_model_artifact
from app.ml.pipeline_io import sha256_file, write_json
from app.ml.schema import FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION

_FINE_GRID_POINTS = 99
_TAIL_GRID_POINTS = 13
_RELIABILITY_BINS = 10
_F2_BETA = 2.0
_FAMILY_PACKAGES = {
    "logistic_regression": "scikit-learn",
    "decision_tree": "scikit-learn",
    "random_forest": "scikit-learn",
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "catboost": "catboost",
}
MODEL_VERSION = "fraud_detector_v1"


def _same_settings(spec_a: dict[str, Any], spec_b: dict[str, Any]) -> bool:
    """Return True if two specs differ at most in their seed."""
    keys = ("family", "strategy", "hyperparameters", "target_ratio", "dropped_features")
    return all(spec_a[key] == spec_b[key] for key in keys)


def summarise_family(
    family: str,
    runs: dict[str, dict[str, Any]],
    fold_reports: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Collect everything the rule needs about one family's best run."""
    found = best_run(runs, family)
    if found is None:
        return None
    run_id, run = found

    seed_runs = [
        other
        for other in runs.values()
        if other["stage"] in ("matrix", "tuning", "stability_seed")
        and _same_settings(other["spec"], run["spec"])
    ]
    seed_values = [
        other["evaluation"]["ranking"]["pr_auc"] for other in seed_runs if other["status"] == "ok"
    ]
    mean = statistics.fmean(seed_values)
    deviation = statistics.pstdev(seed_values) if len(seed_values) > 1 else 0.0

    fold_results = []
    for index, fold in enumerate(fold_reports):
        fold_run = runs.get(f"{run_id}-fold{index}")
        baseline = fold["transaction_type_rate"]["pr_auc"]
        ok = fold_run is not None and fold_run["status"] == "ok"
        value = fold_run["evaluation"]["ranking"]["pr_auc"] if ok else None
        fold_results.append({"fold": index, "pr_auc": value, "type_rate_baseline_pr_auc": baseline})

    evaluation = run["evaluation"]
    return {
        "family": family,
        "run_id": run_id,
        "stage": run["stage"],
        "spec": run["spec"],
        "pr_auc": evaluation["ranking"]["pr_auc"],
        "roc_auc": evaluation["ranking"]["roc_auc"],
        "seed_pr_aucs": seed_values,
        "seed_runs_failed": sum(other["status"] != "ok" for other in seed_runs),
        "pr_auc_mean": mean,
        "pr_auc_seed_cv": deviation / mean if mean else None,
        "folds": fold_results,
        "at_fpr_cap": evaluation["at_fpr_cap"],
        "at_max_f1": evaluation["at_max_f1"],
        "slices": evaluation["slices"],
        "training_seconds": run["training"]["total_seconds"],
        "single_row_ms": run["inference"]["single_row_ms_median"],
        "batch_microseconds_per_row": run["inference"]["batch_microseconds_per_row"],
    }


def apply_gates(
    candidates: list[dict[str, Any]], type_rate_pr_auc: float, rule: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reject candidates that fail a stability or minimum-skill requirement, stating why."""
    passed, rejected = [], []
    for candidate in candidates:
        reasons = []
        if candidate["pr_auc_mean"] <= type_rate_pr_auc:
            reasons.append("does not beat the transaction-type baseline on validation")
        if candidate["seed_runs_failed"]:
            reasons.append("a seed run failed")
        cv = candidate["pr_auc_seed_cv"]
        if cv is None or cv > rule["max_seed_coefficient_of_variation"]:
            reasons.append(f"seed variation {cv} exceeds the limit")
        for fold in candidate["folds"]:
            if fold["pr_auc"] is None:
                reasons.append(f"rolling fold {fold['fold']} failed")
            elif fold["pr_auc"] <= fold["type_rate_baseline_pr_auc"]:
                reasons.append(f"does not beat the type baseline in rolling fold {fold['fold']}")
        if reasons:
            rejected.append({"family": candidate["family"], "reasons": reasons})
        else:
            passed.append(candidate)
    return passed, rejected


def choose_candidate(
    passed: list[dict[str, Any]],
    differences: dict[str, dict[str, Any]],
    rule: dict[str, Any],
) -> dict[str, Any]:
    """Apply the three ranking steps and return the selected family with each step's result.

    1. Keep candidates whose PR-AUC is not distinguishable from the top candidate's.
    2. Among those, keep the highest recall at the operational false positive cap, within a margin.
    3. Among those, choose the lowest single-row prediction time.
    """
    if not passed:
        raise ValueError("choose_candidate needs at least one candidate")
    top = max(passed, key=lambda candidate: candidate["pr_auc_mean"])
    indistinguishable = [
        candidate
        for candidate in passed
        if candidate["family"] == top["family"] or differences[candidate["family"]]["includes_zero"]
    ]
    best_recall = max(candidate["at_fpr_cap"]["recall"] for candidate in indistinguishable)
    near_best_recall = [
        candidate
        for candidate in indistinguishable
        if candidate["at_fpr_cap"]["recall"] >= best_recall - rule["recall_tie_margin"]
    ]
    selected = min(near_best_recall, key=lambda candidate: candidate["single_row_ms"])
    return {
        "top_by_pr_auc": top["family"],
        "statistically_indistinguishable": [c["family"] for c in indistinguishable],
        "best_recall_at_fpr_cap": best_recall,
        "tied_on_recall": [c["family"] for c in near_best_recall],
        "selected_family": selected["family"],
    }


def _threshold_grid() -> np.ndarray:
    """Return thresholds covering very low, ordinary and very high scores."""
    return np.unique(
        np.r_[
            np.logspace(-6, -2, _TAIL_GRID_POINTS),
            np.linspace(0.01, 0.99, _FINE_GRID_POINTS),
            1 - np.logspace(-2, -6, _TAIL_GRID_POINTS),
            np.array(PRD_THRESHOLD_CANDIDATES),
        ]
    )


def reliability_table(labels: np.ndarray, scores: np.ndarray) -> list[dict[str, Any]]:
    """Compare mean score with the observed fraud rate in equal-width score bins."""
    edges = np.linspace(0, 1, _RELIABILITY_BINS + 1)
    bins = np.clip(np.digitize(scores, edges) - 1, 0, _RELIABILITY_BINS - 1)
    table = []
    for index in range(_RELIABILITY_BINS):
        selected = bins == index
        count = int(selected.sum())
        table.append(
            {
                "score_low": float(edges[index]),
                "score_high": float(edges[index + 1]),
                "rows": count,
                "fraud_rows": int(labels[selected].sum()),
                "mean_score": float(scores[selected].mean()) if count else None,
                "observed_fraud_rate": float(labels[selected].mean()) if count else None,
            }
        )
    return table


def _with_slices(
    labels: np.ndarray, scores: np.ndarray, threshold: float, slices: dict[str, np.ndarray]
) -> dict[str, Any]:
    return {
        **threshold_metrics(labels, scores, threshold),
        "slices": {
            name: threshold_metrics(labels[mask], scores[mask], threshold)
            for name, mask in slices.items()
        },
    }


def analyse_thresholds(
    labels: np.ndarray,
    scores: np.ndarray,
    steps: np.ndarray,
    slices: dict[str, np.ndarray],
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Study threshold behaviour on validation and choose by the fixed operational objective."""
    threshold_settings = settings["threshold"]
    bootstrap = settings["bootstrap"]
    cap = threshold_settings["operational_fpr_cap"]
    selected = threshold_for_fpr_cap(labels, scores, cap)
    step_count = int(np.unique(steps).size)

    middle = (int(steps.min()) + int(steps.max())) // 2
    early, late = steps <= middle, steps > middle
    early_threshold = threshold_for_fpr_cap(labels[early], scores[early], cap)
    late_threshold = threshold_for_fpr_cap(labels[late], scores[late], cap)

    rules = {
        f"fpr_cap_{value}": threshold_for_fpr_cap(labels, scores, value)
        for value in sorted({cap, *threshold_settings["alternative_fpr_caps"]})
    }
    rules["max_f1"] = threshold_for_max_fbeta(labels, scores)
    rules["max_f2"] = threshold_for_max_fbeta(labels, scores, _F2_BETA)

    return {
        "objective": (
            f"Highest recall with a false positive rate of at most {cap} on validation. "
            "A false positive rate does not depend on prevalence, whereas precision and F1 do."
        ),
        "selected_threshold": selected,
        "validation_steps": step_count,
        "selected": {
            **_with_slices(labels, scores, selected, slices),
            "alerts_per_step": threshold_metrics(labels, scores, selected)["alerts"] / step_count,
        },
        "prd_candidates": {
            f"{value:.2f}": _with_slices(labels, scores, value, slices)
            for value in PRD_THRESHOLD_CANDIDATES
        },
        "rule_alternatives": {
            name: _with_slices(labels, scores, value, slices) for name, value in rules.items()
        },
        "sweep": [threshold_metrics(labels, scores, value) for value in _threshold_grid()],
        "temporal_check": {
            "split_after_step": middle,
            "set_on_early_measured_on_late": threshold_metrics(
                labels[late], scores[late], early_threshold
            ),
            "set_on_late_measured_on_early": threshold_metrics(
                labels[early], scores[early], late_threshold
            ),
        },
        "out_of_bag": out_of_bag_threshold_behaviour(
            labels, scores, steps, cap, bootstrap["threshold_replicates"], bootstrap["seed"]
        ),
        "reliability": reliability_table(labels, scores),
        "ranking": ranking_metrics(labels, scores),
        "curves": decimated_curves(labels, scores),
    }


def compare_with_top(
    candidates: list[dict[str, Any]],
    scores_by_family: dict[str, np.ndarray],
    labels: np.ndarray,
    steps: np.ndarray,
    bootstrap: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return each candidate's paired PR-AUC difference from the top candidate."""
    top = max(candidates, key=lambda candidate: candidate["pr_auc_mean"])
    return {
        candidate["family"]: paired_bootstrap_difference(
            labels,
            scores_by_family[top["family"]],
            scores_by_family[candidate["family"]],
            steps,
            bootstrap["replicates"],
            bootstrap["seed"],
        )
        for candidate in candidates
        if candidate["family"] != top["family"]
    }


def family_summaries(
    runs: dict[str, dict[str, Any]], fold_reports: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Summarise every family, and list any that have no successful run."""
    summaries, missing = [], []
    for family in MODEL_FAMILIES:
        summary = summarise_family(family, runs, fold_reports)
        if summary is None:
            missing.append(family)
        else:
            summaries.append(summary)
    return summaries, missing


def spec_from_summary(summary: dict[str, Any]) -> CandidateSpec:
    """Rebuild the exact spec of a summarised run."""
    fields = summary["spec"]
    return CandidateSpec(
        family=fields["family"],
        strategy=fields["strategy"],
        hyperparameters=fields["hyperparameters"],
        seed=fields["seed"],
        target_ratio=fields["target_ratio"],
        dropped_features=tuple(fields["dropped_features"]),
    )


def score_semantics(strategy: str) -> str:
    """Describe what the saved model's score means, for the API and interface."""
    if strategy == "original":
        return (
            "Model output trained on the natural class distribution. It is estimated on the "
            "training period's fraud rate, so it is not a calibrated probability for other periods."
        )
    return (
        f"Risk score from a model trained with {strategy}, which inflates scores above the true "
        "fraud rate. It ranks transactions but must not be presented as a probability of fraud."
    )


def _library_versions(family: str) -> dict[str, str]:
    names = {"numpy", "pandas", "scikit-learn", "joblib", _FAMILY_PACKAGES[family]}
    return {
        "python": platform.python_version(),
        **{name: package_version(name) for name in sorted(names)},
    }


def freeze_selected_model(
    data: ExperimentData,
    config: dict[str, Any],
    store: RunStore,
    results_dir: Path,
    models_dir: Path,
    metadata_path: Path,
    preprocessing_metadata_path: Path,
    source_commit: str,
) -> dict[str, Any]:
    """Apply the selection rule, refit the winner, set its threshold and save everything.

    The refit uses training rows only. Its scores are compared with the recorded run, so the
    saved model is shown to be the run that was selected, not merely a similar one.
    """
    folds = json.loads((results_dir / "rolling_folds.json").read_text(encoding="utf-8"))["folds"]
    baselines = json.loads((results_dir / "baselines.json").read_text(encoding="utf-8"))
    type_rate_pr_auc = baselines["transaction_type_rate"]["ranking"]["pr_auc"]
    rule = config["selection"]

    summaries, missing = family_summaries(store.runs, folds)
    passed, rejected = apply_gates(summaries, type_rate_pr_auc, rule)
    no_candidate_passed = not passed
    eligible = passed or summaries

    labels = data.validation.labels.to_numpy()
    steps = data.validation.steps.to_numpy()
    scores_by_family = {
        summary["family"]: store.load_scores(summary["run_id"]).astype("float64")
        for summary in summaries
    }
    differences = compare_with_top(eligible, scores_by_family, labels, steps, config["bootstrap"])
    decision = choose_candidate(eligible, differences, rule)
    selected = next(item for item in summaries if item["family"] == decision["selected_family"])

    spec = spec_from_summary(selected)
    fitted = fit_candidate(
        spec,
        data.train.features,
        data.train.labels.to_numpy(),
        config["threads"],
        config["oversampling"]["k_neighbors"],
    )
    scores = score_rows(fitted.pipeline, data.validation.features)
    recorded = store.runs[selected["run_id"]]["scores_sha256"]
    refit_matches = scores_digest(scores) == recorded

    thresholds = analyse_thresholds(labels, scores, steps, data.validation_slices, config)
    write_json(results_dir / "threshold_analysis.json", thresholds)

    report = {
        "rule_source": "docs/decisions/0002-phase-2-decisions.md",
        "scope": "training rows for fitting; validation rows for every comparison",
        "families_without_a_successful_run": missing,
        "type_rate_baseline_pr_auc": type_rate_pr_auc,
        "candidates": summaries,
        "gates": {
            "passed": [item["family"] for item in passed],
            "rejected": rejected,
            "no_candidate_passed": no_candidate_passed,
        },
        "paired_difference_from_top": differences,
        "decision": decision,
        "pr_auc_intervals": {
            family: bootstrap_pr_auc(
                labels,
                family_scores,
                steps,
                config["bootstrap"]["replicates"],
                config["bootstrap"]["seed"],
            )
            for family, family_scores in scores_by_family.items()
        },
        "candidate_curves": {
            family: decimated_curves(labels, family_scores)
            for family, family_scores in scores_by_family.items()
        },
        "refit_matches_recorded_run": refit_matches,
        "selected_threshold": thresholds["selected_threshold"],
    }
    write_json(results_dir / "selection.json", report)

    names = fitted.pipeline.named_steps["preprocess"].get_feature_names_out()
    metadata = {
        "model_version": MODEL_VERSION,
        "status": "frozen",
        "family": spec.family,
        "spec": spec.identity(),
        "run_id": selected["run_id"],
        "trained_on": "train partition only",
        "training_report": fitted.report,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "model_input_columns": [str(name) for name in names],
        "preprocessing_metadata_sha256": sha256_file(preprocessing_metadata_path),
        "experiment_config_version": config["version"],
        "threshold": {
            "value": thresholds["selected_threshold"],
            "chosen_on": "validation partition",
            "objective": thresholds["objective"],
            "operational_fpr_cap": config["threshold"]["operational_fpr_cap"],
        },
        "score_semantics": score_semantics(spec.strategy),
        "validation_summary": {
            "ranking": thresholds["ranking"],
            "at_threshold": {
                key: value for key, value in thresholds["selected"].items() if key != "slices"
            },
        },
        "refit_matches_recorded_run": refit_matches,
        "source_commit": source_commit,
        "library_versions": _library_versions(spec.family),
    }
    save_model_artifact(fitted.pipeline, metadata, models_dir, metadata_path)
    return report
