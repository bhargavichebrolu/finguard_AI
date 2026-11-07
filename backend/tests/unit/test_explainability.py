"""SHAP support: values must add up to the model's output, for every family."""

import numpy as np
import pytest
from tests.conftest import small_experiment_config

from app.ml.candidates import MODEL_FAMILIES, CandidateSpec
from app.ml.experiments import fit_candidate, score_rows
from app.ml.explainability import (
    LIMITATIONS,
    additivity_error,
    explain_rows,
    explain_validation_rows,
    feature_group,
    local_explanation,
    sample_for_explanation,
    summarise_explanations,
)

HYPERPARAMETERS = small_experiment_config()["baseline_hyperparameters"]


def fit_family(family, partition):
    spec = CandidateSpec(family, "original", HYPERPARAMETERS[family], 42)
    return fit_candidate(spec, partition.features, partition.labels.to_numpy(), 1, 3).pipeline


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_explanations_add_up_to_the_score(family, model_partition, later_partition):
    pipeline = fit_family(family, model_partition)
    sample = later_partition.features.iloc[:100]
    explanation = explain_rows(pipeline, sample, family)
    assert explanation["values"].shape == (100, 12)
    assert additivity_error(explanation, score_rows(pipeline, sample)) < 1e-2


def test_unsupported_family_is_refused(model_partition):
    pipeline = fit_family("decision_tree", model_partition)
    with pytest.raises(ValueError):
        explain_rows(pipeline, model_partition.features.iloc[:5], "kernel_machine")


@pytest.mark.parametrize(
    ("name", "group"),
    [
        ("amount", "amount"),
        ("amount_log1p", "amount"),
        ("hour_of_day", "hour"),
        ("hour_sin", "hour"),
        ("transaction_type_TRANSFER", "transaction_type_and_destination"),
        ("destination_category_customer", "transaction_type_and_destination"),
    ],
)
def test_feature_groups(name, group):
    assert feature_group(name) == group


def test_sampling_keeps_all_fraud_and_restores_natural_weights():
    labels = np.array([1] * 5 + [0] * 95)
    positions, weights = sample_for_explanation(labels, legitimate_rows=19, seed=1)
    assert labels[positions].sum() == 5
    assert positions.size == 24
    assert weights[labels[positions] == 1].tolist() == [1.0] * 5
    # Each sampled legitimate row stands for 5 rows, so weights add back up to 100.
    assert weights.sum() == pytest.approx(100.0)


def test_sampling_is_capped_at_the_available_rows():
    labels = np.array([1, 0, 0])
    positions, weights = sample_for_explanation(labels, legitimate_rows=99, seed=1)
    assert positions.size == 3
    assert weights.tolist() == [1.0, 1.0, 1.0]


def test_group_importance_adds_values_within_the_group():
    explanation = {
        "values": np.array([[1.0, 1.0, -2.0], [1.0, 1.0, -2.0]]),
        "feature_names": ["amount", "amount_log1p", "hour_sin"],
    }
    summary = summarise_explanations(explanation, np.array([1, 0]), np.ones(2), {})
    groups = summary["all_rows"]["mean_absolute_by_group"]
    assert groups["amount"] == pytest.approx(2.0)
    assert groups["hour"] == pytest.approx(2.0)
    assert summary["all_rows"]["mean_absolute_by_feature"]["amount"] == pytest.approx(1.0)
    assert summary["all_rows"]["mean_signed_by_group"]["hour"] == pytest.approx(-2.0)


def test_weights_are_applied_in_importance():
    explanation = {"values": np.array([[1.0], [3.0]]), "feature_names": ["amount"]}
    summary = summarise_explanations(explanation, np.array([1, 0]), np.array([1.0, 3.0]), {})
    assert summary["all_rows"]["mean_absolute_by_feature"]["amount"] == pytest.approx(2.5)


def test_empty_slice_is_reported_as_empty():
    explanation = {"values": np.array([[1.0]]), "feature_names": ["amount"]}
    summary = summarise_explanations(
        explanation, np.array([1]), np.ones(1), {"nothing": np.array([False])}
    )
    assert summary["slices"]["nothing"] == {"rows": 0}


def test_local_explanation_separates_and_orders_contributions():
    explanation = {
        "values": np.array([[0.5, -2.0, 1.0, 0.0]]),
        "feature_names": ["a", "b", "c", "d"],
        "base_value": -3.0,
        "output_scale": "log_odds",
    }
    result = local_explanation(explanation, 0, 0.8, threshold=0.5)
    assert result["alert"] is True
    assert [item["feature"] for item in result["positive_contributions"]] == ["c", "a"]
    assert [item["feature"] for item in result["negative_contributions"]] == ["b"]


def test_report_has_examples_limitations_and_a_causality_warning(model_partition, later_partition):
    pipeline = fit_family("lightgbm", model_partition)
    features, labels = later_partition.features, later_partition.labels.to_numpy()
    scores = score_rows(pipeline, features)
    result = explain_validation_rows(
        pipeline, "lightgbm", features, labels, scores, {}, float(np.median(scores)), 100, 1
    )
    report = result["report"]
    assert report["fraud_rows_explained"] == int(labels.sum())
    assert report["additivity_max_error"] < 1e-2
    assert report["local_examples"]["strongest_true_alert"]["true_label"] == 1
    assert any("does not establish" in text for text in report["limitations"])
    assert list(LIMITATIONS) == report["limitations"]
