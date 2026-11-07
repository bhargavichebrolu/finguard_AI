"""Metric formulas, threshold rules and bootstrap behaviour, checked against hand calculations."""

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from app.ml.evaluation import (
    StepBootstrap,
    _prepare_ranking,
    _weighted_average_precision,
    bootstrap_pr_auc,
    build_slices,
    decimated_curves,
    evaluate_scores,
    expected_precision,
    out_of_bag_threshold_behaviour,
    paired_bootstrap_difference,
    prevalence_adjusted_pr_auc,
    ranking_metrics,
    threshold_for_fpr_cap,
    threshold_for_max_fbeta,
    threshold_metrics,
)

LABELS = np.array([1, 1, 0, 0, 0, 0, 1, 0])
SCORES = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1, 0.4, 0.6])


def test_threshold_metrics_by_hand():
    # At 0.5: alerts are rows 0, 1, 2 and 7, so TP=2, FP=2, FN=1 (row 6), TN=3.
    result = threshold_metrics(LABELS, SCORES, 0.5)
    assert (result["true_positives"], result["false_positives"]) == (2, 2)
    assert (result["false_negatives"], result["true_negatives"]) == (1, 3)
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(2 / 3)
    assert result["f1"] == pytest.approx(4 / 7)
    assert result["accuracy"] == pytest.approx(5 / 8)
    assert result["false_positive_rate"] == pytest.approx(0.4)
    assert result["false_negative_rate"] == pytest.approx(1 / 3)
    assert result["balanced_accuracy"] == pytest.approx((2 / 3 + 0.6) / 2)
    assert result["alerts"] == 4


def test_a_score_equal_to_the_threshold_alerts():
    assert threshold_metrics(np.array([1]), np.array([0.5]), 0.5)["true_positives"] == 1


def test_higher_threshold_cannot_raise_recall_or_alerts():
    previous = None
    for threshold in np.linspace(0, 1, 21):
        result = threshold_metrics(LABELS, SCORES, threshold)
        if previous is not None:
            assert result["recall"] <= previous["recall"]
            assert result["alerts"] <= previous["alerts"]
        previous = result


def test_undefined_metrics_are_none_not_zero():
    no_alerts = threshold_metrics(LABELS, SCORES, 2.0)
    assert no_alerts["precision"] is None
    assert no_alerts["recall"] == 0.0
    no_fraud = threshold_metrics(np.zeros(3, dtype=int), np.array([0.1, 0.2, 0.3]), 0.5)
    assert no_fraud["recall"] is None
    assert no_fraud["balanced_accuracy"] is None


def test_ranking_metrics_report_baseline_and_lift():
    result = ranking_metrics(LABELS, SCORES)
    assert result["prevalence"] == pytest.approx(3 / 8)
    assert result["pr_auc"] == pytest.approx(average_precision_score(LABELS, SCORES))
    assert result["pr_auc_lift"] == pytest.approx(result["pr_auc"] / (3 / 8))


def test_ranking_metrics_with_one_class_are_none():
    result = ranking_metrics(np.zeros(4, dtype=int), np.arange(4.0))
    assert result["pr_auc"] is None and result["roc_auc"] is None


def test_fpr_cap_gives_highest_recall_within_the_cap():
    labels = np.r_[np.ones(5, dtype=int), np.zeros(1000, dtype=int)]
    generator = np.random.default_rng(0)
    scores = generator.random(labels.size)
    threshold = threshold_for_fpr_cap(labels, scores, 0.01)
    within = threshold_metrics(labels, scores, threshold)
    assert within["false_positive_rate"] <= 0.01
    # The negative just below the threshold would break the cap, so this is the lowest allowed.
    below = np.sort(scores[labels == 0])[::-1][10]
    assert threshold_metrics(labels, scores, below)["false_positive_rate"] > 0.01


def test_fpr_cap_excludes_a_tie_that_would_cross_it():
    labels = np.zeros(1000, dtype=int)
    labels[0] = 1
    scores = np.zeros(1000)
    scores[0] = 0.9
    scores[1:51] = 0.5  # 50 tied negatives is 5%, which is over a 1% cap.
    threshold = threshold_for_fpr_cap(labels, scores, 0.01)
    assert threshold > 0.5
    assert threshold_metrics(labels, scores, threshold)["false_positives"] == 0
    assert threshold_metrics(labels, scores, threshold)["true_positives"] == 1


def test_fpr_cap_too_small_for_any_alert_on_negatives():
    threshold = threshold_for_fpr_cap(np.array([0, 0, 1]), np.array([0.1, 0.2, 0.9]), 0.1)
    assert (
        threshold_metrics(np.array([0, 0, 1]), np.array([0.1, 0.2, 0.9]), threshold)[
            "false_positives"
        ]
        == 0
    )


@pytest.mark.parametrize("cap", [0.0, 1.0, -0.1])
def test_invalid_fpr_cap_is_rejected(cap):
    with pytest.raises(ValueError):
        threshold_for_fpr_cap(LABELS, SCORES, cap)


def test_max_f1_threshold_is_the_best_among_all_scores():
    best = threshold_for_max_fbeta(LABELS, SCORES)
    best_f1 = threshold_metrics(LABELS, SCORES, best)["f1"]
    assert all(
        threshold_metrics(LABELS, SCORES, value)["f1"] <= best_f1 + 1e-12 for value in SCORES
    )


def test_f2_favours_recall_over_f1():
    labels = np.array([1, 0, 0, 1, 0, 0, 0, 1])
    scores = np.array([0.9, 0.1, 0.2, 0.8, 0.3, 0.4, 0.5, 0.45])
    f1_threshold = threshold_for_max_fbeta(labels, scores)
    f2_threshold = threshold_for_max_fbeta(labels, scores, beta=2.0)
    assert f2_threshold <= f1_threshold


def test_prevalence_adjustment_at_same_prevalence_changes_nothing():
    prevalence = float(LABELS.mean())
    assert prevalence_adjusted_pr_auc(LABELS, SCORES, prevalence) == pytest.approx(
        average_precision_score(LABELS, SCORES)
    )


def test_prevalence_adjustment_lowers_pr_auc_at_lower_prevalence():
    assert prevalence_adjusted_pr_auc(LABELS, SCORES, 0.01) < average_precision_score(
        LABELS, SCORES
    )


def test_expected_precision_by_hand():
    # 0.5 x 0.01 = 0.005 true alerts; 0.01 x 0.99 = 0.0099 false alerts.
    assert expected_precision(0.5, 0.01, 0.01) == pytest.approx(0.005 / 0.0149)


def test_expected_precision_with_no_alerts_is_none():
    assert expected_precision(0.0, 0.0, 0.5) is None


def test_weighted_average_precision_matches_sklearn_with_ties():
    generator = np.random.default_rng(3)
    labels = generator.integers(0, 2, 500)
    scores = np.round(generator.random(500), 2)  # Rounding creates many ties.
    order, ends = _prepare_ranking(labels, scores)
    weights = generator.integers(0, 4, 500).astype("float64")
    ours = _weighted_average_precision(labels[order].astype("float64"), weights[order], ends)
    theirs = average_precision_score(labels, scores, sample_weight=weights)
    assert ours == pytest.approx(theirs)


def test_bootstrap_draws_whole_steps():
    steps = np.array([5, 5, 7, 7, 7, 9])
    bootstrap = StepBootstrap(steps, seed=0)
    counts = bootstrap.draw_step_counts()
    assert counts.sum() == 3
    weights = bootstrap.row_weights(counts)
    # Rows of one step always share a weight.
    assert weights[0] == weights[1]
    assert weights[2] == weights[3] == weights[4]


def _block_data(seed=0):
    generator = np.random.default_rng(seed)
    steps = np.repeat(np.arange(40), 50)
    labels = (generator.random(steps.size) < 0.1).astype(int)
    scores = labels * generator.normal(1.0, 1.0, steps.size) + generator.normal(0, 1, steps.size)
    return labels, scores, steps


def test_bootstrap_is_reproducible_and_brackets_the_estimate():
    labels, scores, steps = _block_data()
    first = bootstrap_pr_auc(labels, scores, steps, 200, seed=1)
    second = bootstrap_pr_auc(labels, scores, steps, 200, seed=1)
    assert first == second
    point = average_precision_score(labels, scores)
    assert first["ci_low"] <= point <= first["ci_high"]


def test_paired_difference_of_a_model_with_itself_is_exactly_zero():
    labels, scores, steps = _block_data()
    result = paired_bootstrap_difference(labels, scores, scores, steps, 50, seed=1)
    assert result["mean"] == 0.0 and result["includes_zero"] is True


def test_paired_difference_detects_a_clearly_better_model():
    labels, scores, steps = _block_data()
    noise = np.random.default_rng(9).normal(size=scores.size)
    result = paired_bootstrap_difference(labels, scores, noise, steps, 200, seed=1)
    assert result["ci_low"] > 0 and result["includes_zero"] is False


def test_out_of_bag_behaviour_reports_how_many_replicates_were_used():
    labels, scores, steps = _block_data()
    result = out_of_bag_threshold_behaviour(labels, scores, steps, 0.01, 30, seed=1)
    assert 0 < result["replicates_used"] <= 30
    assert result["out_of_bag_false_positive_rate"]["mean"] < 0.05


def test_slices_describe_regime_type_and_cap():
    features = pd.DataFrame(
        {
            "transaction_type": pd.Categorical(["TRANSFER", "CASH_OUT", "PAYMENT"]),
            "amount": np.array([10_000_000.0, 5.0, 5.0], dtype="float32"),
        }
    )
    slices = build_slices(features, pd.Series([1, 2, 2]), cutoff=2)
    assert slices["regime_sparse"].tolist() == [True, False, False]
    assert slices["type_transfer"].tolist() == [True, False, False]
    assert slices["type_cash_out"].tolist() == [False, True, False]
    assert slices["amount_at_simulator_cap"].tolist() == [True, False, False]


def test_evaluate_scores_keeps_natural_distribution_and_applies_one_threshold():
    labels, scores, _ = _block_data()
    mask = np.arange(labels.size) % 2 == 0
    result = evaluate_scores(labels, scores, {"half": mask}, 0.01)
    assert result["ranking"]["rows"] == labels.size
    assert result["ranking"]["fraud_rows"] == int(labels.sum())
    threshold = result["at_fpr_cap"]["threshold"]
    assert result["slices"]["half"]["at_fpr_cap"]["threshold"] == threshold
    assert set(result["at_prd_candidates"]) == {"0.30", "0.40", "0.50", "0.60", "0.70"}


def test_curves_are_small_and_within_range():
    labels, scores, _ = _block_data()
    curves = decimated_curves(labels, scores)
    assert len(curves["pr_recall"]) <= 201
    assert len(curves["pr_recall"]) == len(curves["pr_precision"])
    assert len(curves["roc_fpr"]) == len(curves["roc_tpr"])
    assert all(0 <= value <= 1 for value in curves["roc_tpr"])
