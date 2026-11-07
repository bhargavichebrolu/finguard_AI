"""SHAP explanations for the saved model.

SHAP describes how this model reacted to its inputs. It says nothing about what causes fraud.
Several features are near duplicates of each other (amount and its logarithm, three encodings of
the hour), and SHAP splits credit among duplicates, so results are also reported by group.
"""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

TREE_FAMILIES = {"decision_tree", "random_forest", "xgboost", "lightgbm", "catboost"}
_MARGIN_FAMILIES = {"xgboost", "lightgbm", "catboost", "logistic_regression"}
_LINEAR_BACKGROUND_ROWS = 1_000
LIMITATIONS: tuple[str, ...] = (
    "SHAP explains this model's output. It does not establish that a feature causes fraud.",
    "Credit is split among correlated features, so groups are more reliable than single features.",
    "Fraud labels come from a simulator, so patterns may reflect how it was programmed.",
    "Local explanations describe one score and do not carry over to other transactions.",
)


def feature_group(name: str) -> str:
    """Map one model input column to the underlying thing it measures."""
    if name.startswith("amount"):
        return "amount"
    if name.startswith("hour"):
        return "hour"
    return "transaction_type_and_destination"


def explain_rows(pipeline: Pipeline, features: pd.DataFrame, family: str) -> dict[str, Any]:
    """Return SHAP values for rows, with base value, column names and output scale.

    Raises ValueError for a family with no supported explainer, rather than approximating.
    """
    import shap

    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    matrix = preprocess.transform(features)
    names = [str(name) for name in preprocess.get_feature_names_out()]

    if family in TREE_FAMILIES:
        explainer = shap.TreeExplainer(model)
    elif family == "logistic_regression":
        explainer = shap.LinearExplainer(
            model, shap.maskers.Independent(matrix[:_LINEAR_BACKGROUND_ROWS])
        )
    else:
        raise ValueError(f"No SHAP explainer is supported for {family}")

    values = np.asarray(explainer.shap_values(matrix))
    base = np.ravel(explainer.expected_value)
    if values.ndim == 3:  # sklearn trees return one set of values per class.
        values = values[:, :, 1]
    return {
        "values": values,
        "base_value": float(base[-1]),
        "feature_names": names,
        "output_scale": "log_odds" if family in _MARGIN_FAMILIES else "probability",
    }


def additivity_error(explanation: dict[str, Any], scores: np.ndarray) -> float:
    """Return the largest gap between base value plus SHAP values and the model's real output."""
    reconstructed = explanation["base_value"] + explanation["values"].sum(axis=1)
    if explanation["output_scale"] == "log_odds":
        reconstructed = 1.0 / (1.0 + np.exp(-reconstructed))
    return float(np.max(np.abs(reconstructed - scores)))


def _weighted_absolute_mean(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.average(np.abs(values), axis=0, weights=weights)


def summarise_explanations(
    explanation: dict[str, Any],
    labels: np.ndarray,
    weights: np.ndarray,
    slices: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Return global importance per feature and per group, overall, by class and by slice.

    Weights restore the natural class mix when legitimate rows were sampled. Without them,
    every statistic would be dominated by the over-represented fraud rows.
    """
    values, names = explanation["values"], explanation["feature_names"]
    groups = sorted({feature_group(name) for name in names})
    group_values = np.column_stack(
        [
            values[
                :, [index for index, name in enumerate(names) if feature_group(name) == group]
            ].sum(axis=1)
            for group in groups
        ]
    )

    def describe(mask: np.ndarray) -> dict[str, Any]:
        if not mask.any():
            return {"rows": 0}
        feature_mean = _weighted_absolute_mean(values[mask], weights[mask])
        group_mean = _weighted_absolute_mean(group_values[mask], weights[mask])
        signed = np.average(group_values[mask], axis=0, weights=weights[mask])
        return {
            "rows": int(mask.sum()),
            "mean_absolute_by_feature": dict(zip(names, map(float, feature_mean), strict=True)),
            "mean_absolute_by_group": dict(zip(groups, map(float, group_mean), strict=True)),
            "mean_signed_by_group": dict(zip(groups, map(float, signed), strict=True)),
        }

    everything = np.ones(labels.size, dtype=bool)
    return {
        "all_rows": describe(everything),
        "fraud": describe(labels == 1),
        "legitimate": describe(labels != 1),
        "slices": {name: describe(mask) for name, mask in slices.items()},
    }


def local_explanation(
    explanation: dict[str, Any], position: int, score: float, threshold: float
) -> dict[str, Any]:
    """Describe one row: contributions ordered by size, split into positive and negative."""
    contributions = sorted(
        zip(
            explanation["feature_names"],
            map(float, explanation["values"][position]),
            strict=True,
        ),
        key=lambda item: -abs(item[1]),
    )
    return {
        "score": float(score),
        "alert": bool(score >= threshold),
        "base_value": explanation["base_value"],
        "output_scale": explanation["output_scale"],
        "positive_contributions": [
            {"feature": name, "shap_value": value} for name, value in contributions if value > 0
        ],
        "negative_contributions": [
            {"feature": name, "shap_value": value} for name, value in contributions if value < 0
        ],
    }


def sample_for_explanation(
    labels: np.ndarray, legitimate_rows: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return row positions and weights: all fraud rows, plus a random sample of the others."""
    fraud = np.flatnonzero(labels == 1)
    legitimate = np.flatnonzero(labels != 1)
    chosen = np.random.default_rng(seed).choice(
        legitimate, size=min(legitimate_rows, legitimate.size), replace=False
    )
    positions = np.sort(np.r_[fraud, chosen])
    weights = np.where(labels[positions] == 1, 1.0, legitimate.size / chosen.size)
    return positions, weights


def explain_validation_rows(
    pipeline: Pipeline,
    family: str,
    features: pd.DataFrame,
    labels: np.ndarray,
    scores: np.ndarray,
    slices: dict[str, np.ndarray],
    threshold: float,
    legitimate_rows: int,
    seed: int,
) -> dict[str, Any]:
    """Build the saved SHAP report, and return the raw values for charts."""
    positions, weights = sample_for_explanation(labels, legitimate_rows, seed)
    sample = features.iloc[positions]
    sample_labels, sample_scores = labels[positions], scores[positions]
    explanation = explain_rows(pipeline, sample, family)
    sample_slices = {name: mask[positions] for name, mask in slices.items()}

    def example(condition: np.ndarray, highest: bool) -> dict[str, Any] | None:
        candidates = np.flatnonzero(condition)
        if candidates.size == 0:
            return None
        order = np.argsort(sample_scores[candidates])
        position = int(candidates[order[-1] if highest else order[0]])
        row = sample.iloc[position]
        return {
            "inputs": {
                "amount": float(row["amount"]),
                "transaction_type": str(row["transaction_type"]),
                "hour_of_day": int(row["hour_of_day"]),
                "destination_category": str(row["destination_category"]),
            },
            "true_label": int(sample_labels[position]),
            **local_explanation(explanation, position, sample_scores[position], threshold),
        }

    alerts = sample_scores >= threshold
    is_fraud = sample_labels == 1
    return {
        "report": {
            "scope": "Validation rows: all fraud, plus a reweighted sample of legitimate rows",
            "rows_explained": int(positions.size),
            "fraud_rows_explained": int(is_fraud.sum()),
            "family": family,
            "output_scale": explanation["output_scale"],
            "base_value": explanation["base_value"],
            "additivity_max_error": additivity_error(explanation, sample_scores),
            "limitations": list(LIMITATIONS),
            "summary": summarise_explanations(explanation, sample_labels, weights, sample_slices),
            "local_examples": {
                "strongest_true_alert": example(alerts & is_fraud, highest=True),
                "strongest_false_alert": example(alerts & ~is_fraud, highest=True),
                "most_missed_fraud": example(~alerts & is_fraud, highest=False),
            },
        },
        "values": explanation["values"],
        "feature_names": explanation["feature_names"],
        "sample": sample,
        "sample_labels": sample_labels,
    }
