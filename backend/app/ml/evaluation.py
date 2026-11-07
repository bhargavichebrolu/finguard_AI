"""Metrics, threshold rules and step-level uncertainty for every experiment.

All model comparisons go through this module, so each one is calculated the same way. Nothing
here knows which partition it is given: the callers enforce which data may be used.
"""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from app.ml.regimes import NORMAL, SPARSE, SPARSE_STEP_MAX_ROWS, row_regime_masks
from app.ml.schema import SIMULATOR_AMOUNT_CAP

PRD_THRESHOLD_CANDIDATES: tuple[float, ...] = (0.30, 0.40, 0.50, 0.60, 0.70)
_CURVE_POINTS = 200
_MINIMUM_FPR_ON_CURVE = 1e-6


def _ratio(numerator: float, denominator: float) -> float | None:
    """Divide, returning None when the metric is undefined, so it is never reported as zero."""
    return float(numerator / denominator) if denominator else None


def threshold_metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    """Return the confusion matrix and threshold metrics. A score at the threshold alerts."""
    predicted = scores >= threshold
    positive = labels == 1
    true_positives = int(np.count_nonzero(predicted & positive))
    false_positives = int(np.count_nonzero(predicted & ~positive))
    false_negatives = int(np.count_nonzero(~predicted & positive))
    true_negatives = int(np.count_nonzero(~predicted & ~positive))
    rows = labels.size

    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)
    specificity = _ratio(true_negatives, true_negatives + false_positives)
    false_positive_rate = _ratio(false_positives, false_positives + true_negatives)
    false_negative_rate = _ratio(false_negatives, false_negatives + true_positives)
    has_both = recall is not None and specificity is not None
    return {
        "threshold": float(threshold),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "accuracy": _ratio(true_positives + true_negatives, rows),
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * true_positives, 2 * true_positives + false_positives + false_negatives),
        "balanced_accuracy": (recall + specificity) / 2 if has_both else None,
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
        "alerts": true_positives + false_positives,
        "alert_rate": _ratio(true_positives + false_positives, rows),
    }


def ranking_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    """Return threshold-free metrics, with PR-AUC beside the baseline it must be read against."""
    rows = int(labels.size)
    fraud_rows = int(np.count_nonzero(labels == 1))
    prevalence = _ratio(fraud_rows, rows)
    result: dict[str, Any] = {
        "rows": rows,
        "fraud_rows": fraud_rows,
        "prevalence": prevalence,
        "roc_auc": None,
        "pr_auc": None,
        "pr_auc_lift": None,
        "brier": float(np.mean((scores - labels) ** 2)) if rows else None,
    }
    if 0 < fraud_rows < rows:
        pr_auc = float(average_precision_score(labels, scores))
        result["roc_auc"] = float(roc_auc_score(labels, scores))
        result["pr_auc"] = pr_auc
        result["pr_auc_lift"] = pr_auc / prevalence
    return result


def threshold_for_fpr_cap(labels: np.ndarray, scores: np.ndarray, cap: float) -> float:
    """Return the lowest threshold whose false positive rate does not exceed the cap.

    The lowest such threshold has the highest recall, because recall can only fall as the
    threshold rises. Tied scores cannot be separated, so a tie that would cross the cap is
    excluded as a whole.
    """
    if not 0 < cap < 1:
        raise ValueError(f"cap must be between 0 and 1, got {cap}")
    negatives = np.sort(scores[labels != 1])[::-1]
    if negatives.size == 0:
        raise ValueError("Cannot set a false positive rate without negative rows")
    allowed = int(np.floor(cap * negatives.size + 1e-9))
    if allowed == 0:
        return float(np.nextafter(negatives[0], np.inf))
    if allowed >= negatives.size:
        return float(negatives[-1])
    last_allowed = negatives[allowed - 1]
    if negatives[allowed] == last_allowed:
        return float(np.nextafter(last_allowed, np.inf))
    return float(last_allowed)


def threshold_for_max_fbeta(labels: np.ndarray, scores: np.ndarray, beta: float = 1.0) -> float:
    """Return the threshold that maximises F-beta on the rows given."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    weight = beta**2
    denominator = weight * precision[:-1] + recall[:-1]
    fbeta = np.divide(
        (1 + weight) * precision[:-1] * recall[:-1],
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )
    return float(thresholds[int(np.argmax(fbeta))])


def prevalence_adjusted_pr_auc(
    labels: np.ndarray, scores: np.ndarray, target_prevalence: float
) -> float | None:
    """Return PR-AUC as if the rows had target_prevalence, by reweighting negative rows.

    This lets windows with different base rates be compared on skill. It assumes the score
    distribution within each class would be unchanged, which is an assumption, not a fact.
    """
    is_fraud = labels == 1
    fraud_rows = int(np.count_nonzero(is_fraud))
    negative_rows = labels.size - fraud_rows
    if fraud_rows == 0 or negative_rows == 0:
        return None
    current_odds = fraud_rows / negative_rows
    target_odds = target_prevalence / (1 - target_prevalence)
    weights = np.where(is_fraud, 1.0, current_odds / target_odds)
    return float(average_precision_score(labels, scores, sample_weight=weights))


def expected_precision(
    recall: float, false_positive_rate: float, prevalence: float
) -> float | None:
    """Return the precision implied by a recall and false positive rate at a given prevalence."""
    alerts_from_fraud = recall * prevalence
    alerts_from_legitimate = false_positive_rate * (1 - prevalence)
    return _ratio(alerts_from_fraud, alerts_from_fraud + alerts_from_legitimate)


def decimated_curves(labels: np.ndarray, scores: np.ndarray) -> dict[str, list[float]]:
    """Return PR and ROC curves thinned to a few hundred points, small enough to commit."""
    precision, recall, _ = precision_recall_curve(labels, scores)
    fpr, tpr, _ = roc_curve(labels, scores, drop_intermediate=True)

    # Points are spread evenly along recall, and evenly on a log scale along false positive
    # rate, because the low false positive region is the one that matters here.
    pr_order = np.argsort(recall)
    pr_index = np.searchsorted(recall[pr_order], np.linspace(0, 1, _CURVE_POINTS))
    pr_index = np.unique(np.clip(pr_index, 0, recall.size - 1))
    roc_grid = np.r_[0.0, np.geomspace(_MINIMUM_FPR_ON_CURVE, 1.0, _CURVE_POINTS)]
    roc_index = np.unique(np.clip(np.searchsorted(fpr, roc_grid), 0, fpr.size - 1))
    return {
        "pr_recall": [round(float(x), 6) for x in recall[pr_order][pr_index]],
        "pr_precision": [round(float(x), 6) for x in precision[pr_order][pr_index]],
        "roc_fpr": [round(float(x), 8) for x in fpr[roc_index]],
        "roc_tpr": [round(float(x), 6) for x in tpr[roc_index]],
    }


def build_slices(
    features: pd.DataFrame, steps: pd.Series, cutoff: int = SPARSE_STEP_MAX_ROWS
) -> dict[str, np.ndarray]:
    """Return the row masks every result is broken down by."""
    regimes = row_regime_masks(steps, cutoff)
    transaction_type = features["transaction_type"].astype(object).to_numpy()
    at_cap = features["amount"].to_numpy() == SIMULATOR_AMOUNT_CAP
    return {
        f"regime_{SPARSE}": regimes[SPARSE],
        f"regime_{NORMAL}": regimes[NORMAL],
        "type_cash_out": transaction_type == "CASH_OUT",
        "type_transfer": transaction_type == "TRANSFER",
        "amount_at_simulator_cap": at_cap,
        "amount_below_simulator_cap": ~at_cap,
    }


def evaluate_scores(
    labels: np.ndarray,
    scores: np.ndarray,
    slices: dict[str, np.ndarray],
    fpr_cap: float,
) -> dict[str, Any]:
    """Evaluate one set of scores overall, at standard thresholds, and on every slice.

    A threshold is set on all rows and then applied unchanged to each slice, as it would be in
    use. Rows are never reweighted or resampled here.
    """
    cap_threshold = threshold_for_fpr_cap(labels, scores, fpr_cap)
    f1_threshold = threshold_for_max_fbeta(labels, scores)
    return {
        "ranking": ranking_metrics(labels, scores),
        "at_prd_candidates": {
            f"{value:.2f}": threshold_metrics(labels, scores, value)
            for value in PRD_THRESHOLD_CANDIDATES
        },
        "at_fpr_cap": threshold_metrics(labels, scores, cap_threshold),
        "at_max_f1": threshold_metrics(labels, scores, f1_threshold),
        "slices": {
            name: {
                "ranking": ranking_metrics(labels[mask], scores[mask]),
                "at_fpr_cap": threshold_metrics(labels[mask], scores[mask], cap_threshold),
            }
            for name, mask in slices.items()
        },
    }


class StepBootstrap:
    """Resamples whole simulation steps, because rows within a step are not independent.

    A window with 55 steps carries far less independent evidence than its row count suggests.
    The same seed gives the same draws, which makes comparisons between models paired.
    """

    def __init__(self, steps: np.ndarray, seed: int) -> None:
        self.unique_steps, self.row_step_index = np.unique(steps, return_inverse=True)
        self.generator = np.random.default_rng(seed)

    def draw_step_counts(self) -> np.ndarray:
        """Return how many times each unique step appears in one resample."""
        size = self.unique_steps.size
        return np.bincount(self.generator.integers(0, size, size), minlength=size)

    def row_weights(self, step_counts: np.ndarray) -> np.ndarray:
        """Convert step counts into one weight per row."""
        return step_counts[self.row_step_index]


def _prepare_ranking(labels: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sort rows by descending score and locate where each group of tied scores ends."""
    order = np.argsort(-scores, kind="stable")
    ends = np.r_[np.flatnonzero(np.diff(scores[order])), scores.size - 1]
    return order, ends


def _weighted_average_precision(
    sorted_labels: np.ndarray, sorted_weights: np.ndarray, ends: np.ndarray
) -> float:
    """Compute average precision from presorted rows, without sorting again for each resample."""
    true_positives = np.cumsum(sorted_labels * sorted_weights)[ends]
    alerts = np.cumsum(sorted_weights)[ends]
    if true_positives[-1] == 0:
        return float("nan")
    precision = np.divide(
        true_positives, alerts, out=np.zeros_like(true_positives), where=alerts > 0
    )
    recall_gain = np.diff(np.r_[0.0, true_positives]) / true_positives[-1]
    return float(np.sum(recall_gain * precision))


def _interval(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"mean": None, "ci_low": None, "ci_high": None}
    low, high = np.percentile(finite, [2.5, 97.5])
    return {"mean": float(finite.mean()), "ci_low": float(low), "ci_high": float(high)}


def bootstrap_pr_auc(
    labels: np.ndarray, scores: np.ndarray, steps: np.ndarray, replicates: int, seed: int
) -> dict[str, float | None]:
    """Return a percentile 95% interval for PR-AUC by resampling steps."""
    bootstrap = StepBootstrap(steps, seed)
    order, ends = _prepare_ranking(labels, scores)
    sorted_labels = labels[order].astype("float64")
    sorted_steps = bootstrap.row_step_index[order]
    values = np.empty(replicates)
    for index in range(replicates):
        weights = bootstrap.draw_step_counts()[sorted_steps].astype("float64")
        values[index] = _weighted_average_precision(sorted_labels, weights, ends)
    return _interval(values)


def paired_bootstrap_difference(
    labels: np.ndarray,
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    steps: np.ndarray,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Return an interval for PR-AUC(a) minus PR-AUC(b), drawing the same steps for both."""
    bootstrap = StepBootstrap(steps, seed)
    order_a, ends_a = _prepare_ranking(labels, scores_a)
    order_b, ends_b = _prepare_ranking(labels, scores_b)
    labels_a = labels[order_a].astype("float64")
    labels_b = labels[order_b].astype("float64")
    steps_a = bootstrap.row_step_index[order_a]
    steps_b = bootstrap.row_step_index[order_b]
    differences = np.empty(replicates)
    for index in range(replicates):
        counts = bootstrap.draw_step_counts()
        differences[index] = _weighted_average_precision(
            labels_a, counts[steps_a].astype("float64"), ends_a
        ) - _weighted_average_precision(labels_b, counts[steps_b].astype("float64"), ends_b)
    interval = _interval(differences)
    interval["includes_zero"] = (
        interval["ci_low"] is not None and interval["ci_low"] <= 0 <= interval["ci_high"]
    )
    return interval


def out_of_bag_threshold_behaviour(
    labels: np.ndarray,
    scores: np.ndarray,
    steps: np.ndarray,
    cap: float,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Estimate how a capped threshold behaves on steps it was not chosen from.

    Each replicate sets the threshold on the steps drawn and measures the rows of the steps not
    drawn, which gives a less optimistic view than measuring on the rows that set it.
    """
    bootstrap = StepBootstrap(steps, seed)
    thresholds, recalls, fprs, precisions = [], [], [], []
    for _ in range(replicates):
        in_bag = bootstrap.row_weights(bootstrap.draw_step_counts()) > 0
        if not (labels[in_bag] != 1).any() or in_bag.all():
            continue
        threshold = threshold_for_fpr_cap(labels[in_bag], scores[in_bag], cap)
        result = threshold_metrics(labels[~in_bag], scores[~in_bag], threshold)
        thresholds.append(threshold)
        if result["recall"] is not None:
            recalls.append(result["recall"])
        if result["false_positive_rate"] is not None:
            fprs.append(result["false_positive_rate"])
        if result["precision"] is not None:
            precisions.append(result["precision"])
    return {
        "replicates_used": len(thresholds),
        "threshold": _interval(np.array(thresholds)),
        "out_of_bag_recall": _interval(np.array(recalls)),
        "out_of_bag_false_positive_rate": _interval(np.array(fprs)),
        "out_of_bag_precision": _interval(np.array(precisions)),
    }
