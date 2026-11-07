"""Temporal drift: how prevalence, volume and features change across the simulation.

Prevalence analysis reads per-step row and label counts already published by Phase 1 EDA, so
it covers all three partitions without opening the test file. Feature drift compares feature
values, so before the freeze it may only be given training and validation rows.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.ml.features import HOURS_PER_DAY
from app.ml.regimes import NORMAL, REGIMES, SPARSE, classify_steps
from app.ml.schema import TRANSACTION_TYPES
from app.ml.splitting import PARTITIONS, SplitBoundaries, partition_masks

STEPS_PER_DAY = HOURS_PER_DAY
_PSI_BINS = 10
_PSI_FLOOR = 1e-6
_AMOUNT_COLUMN = "amount_log1p"


def step_table_from_eda(eda_summary: dict[str, Any], boundaries: SplitBoundaries) -> pd.DataFrame:
    """Build a table of rows, fraud and partition per step from the EDA report."""
    whole = eda_summary["whole_dataset"]
    table = pd.DataFrame(
        {"rows": whole["rows_per_step"], "fraud": whole["fraud_per_step"]},
        index=pd.Index(whole["steps"], name="step"),
    )
    masks = partition_masks(table.index.to_series(), boundaries)
    table["partition"] = np.select(
        [masks[name].to_numpy() for name in PARTITIONS], list(PARTITIONS), default=""
    )
    return table


def _group_summary(group: pd.DataFrame) -> dict[str, Any]:
    rows = int(group["rows"].sum())
    fraud = int(group["fraud"].sum())
    steps = len(group)
    return {
        "steps": steps,
        "first_step": int(group.index.min()) if steps else None,
        "last_step": int(group.index.max()) if steps else None,
        "rows": rows,
        "fraud_rows": fraud,
        "legitimate_rows": rows - fraud,
        "prevalence": fraud / rows if rows else None,
        "fraud_per_step": fraud / steps if steps else None,
        "legitimate_per_step": (rows - fraud) / steps if steps else None,
    }


def partition_prevalence(table: pd.DataFrame, cutoff: int) -> dict[str, Any]:
    """Summarise each partition overall and for each regime."""
    regimes = classify_steps(table["rows"], cutoff)
    report: dict[str, Any] = {}
    for name in PARTITIONS:
        rows = table[table["partition"] == name]
        summary = _group_summary(rows)
        summary["regimes"] = {}
        for regime in REGIMES:
            part = rows[regimes.loc[rows.index] == regime]
            entry = _group_summary(part)
            entry["share_of_partition_rows"] = (
                entry["rows"] / summary["rows"] if summary["rows"] else None
            )
            entry["share_of_partition_fraud"] = (
                entry["fraud_rows"] / summary["fraud_rows"] if summary["fraud_rows"] else None
            )
            summary["regimes"][regime] = entry
        report[name] = summary
    return report


def decompose_prevalence_change(
    reference: dict[str, Any], target: dict[str, Any]
) -> dict[str, float]:
    """Split a prevalence change into a regime mix effect and a within-regime rate effect.

    Each effect uses the average of the other quantity across the two windows, so the two
    effects add up to the total change exactly (the Kitagawa decomposition).
    """
    mix_effect = 0.0
    rate_effect = 0.0
    for regime in REGIMES:
        ref, tgt = reference["regimes"][regime], target["regimes"][regime]
        ref_share, tgt_share = ref["share_of_partition_rows"], tgt["share_of_partition_rows"]
        ref_rate, tgt_rate = ref["prevalence"] or 0.0, tgt["prevalence"] or 0.0
        mix_effect += (tgt_share - ref_share) * (tgt_rate + ref_rate) / 2
        rate_effect += (tgt_rate - ref_rate) * (tgt_share + ref_share) / 2
    return {
        "total_change": target["prevalence"] - reference["prevalence"],
        "regime_mix_effect": mix_effect,
        "within_regime_rate_effect": rate_effect,
    }


def prevalence_at_reference_volume(reference: dict[str, Any], target: dict[str, Any]) -> float:
    """Return the target's prevalence if its legitimate volume per step matched the reference."""
    fraud = target["fraud_per_step"]
    return fraud / (fraud + reference["legitimate_per_step"])


def daily_profile(table: pd.DataFrame) -> list[dict[str, Any]]:
    """Group steps into simulated days, for charting drift over time."""
    days = (table.index.to_numpy() - 1) // STEPS_PER_DAY
    profile = []
    for day, group in table.groupby(days):
        rows = int(group["rows"].sum())
        fraud = int(group["fraud"].sum())
        profile.append(
            {
                "day": int(day),
                "first_step": int(group.index.min()),
                "last_step": int(group.index.max()),
                "rows": rows,
                "fraud_rows": fraud,
                "prevalence": fraud / rows if rows else None,
            }
        )
    return profile


def regime_by_hour(table: pd.DataFrame, cutoff: int) -> dict[str, list[float | None]]:
    """Return, per partition, the share of each hour's steps that are sparse.

    If sparse steps fall in overnight hours only, then hour features can act as a proxy for the
    regime, which would not hold in a window where sparse steps happen at any hour.
    """
    regimes = classify_steps(table["rows"], cutoff)
    hours = table.index.to_numpy() % HOURS_PER_DAY
    report: dict[str, list[float | None]] = {}
    for name in PARTITIONS:
        in_partition = table["partition"].to_numpy() == name
        shares: list[float | None] = []
        for hour in range(HOURS_PER_DAY):
            selected = in_partition & (hours == hour)
            count = int(selected.sum())
            sparse = int((regimes.to_numpy()[selected] == SPARSE).sum())
            shares.append(sparse / count if count else None)
        report[name] = shares
    return report


def cutoff_sensitivity(table: pd.DataFrame, cutoffs: list[int]) -> dict[str, Any]:
    """Repeat the regime summary at other cut-offs, to test dependence on the chosen value."""
    report: dict[str, Any] = {}
    for cutoff in cutoffs:
        result = partition_prevalence(table, cutoff)
        report[str(cutoff)] = {
            name: {
                regime: {
                    "steps": result[name]["regimes"][regime]["steps"],
                    "prevalence": result[name]["regimes"][regime]["prevalence"],
                    "share_of_partition_fraud": result[name]["regimes"][regime][
                        "share_of_partition_fraud"
                    ],
                }
                for regime in REGIMES
            }
            for name in PARTITIONS
        }
    return report


def population_stability_index(reference: np.ndarray, target: np.ndarray) -> float:
    """Return PSI for a numeric column, using quantile bins from the reference."""
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, _PSI_BINS + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    expected = np.histogram(reference, edges)[0] / reference.size
    actual = np.histogram(target, edges)[0] / target.size
    return _psi(expected, actual)


def categorical_stability_index(
    reference: np.ndarray, target: np.ndarray, categories: list[Any]
) -> float:
    """Return PSI for a categorical column with known categories."""
    expected = np.array([np.mean(reference == value) for value in categories])
    actual = np.array([np.mean(target == value) for value in categories])
    return _psi(expected, actual)


def _psi(expected: np.ndarray, actual: np.ndarray) -> float:
    expected = np.clip(expected, _PSI_FLOOR, None)
    actual = np.clip(actual, _PSI_FLOOR, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def _frame_drift(reference: pd.DataFrame, target: pd.DataFrame) -> dict[str, float]:
    return {
        "amount_log1p": population_stability_index(
            reference[_AMOUNT_COLUMN].to_numpy(), target[_AMOUNT_COLUMN].to_numpy()
        ),
        "transaction_type": categorical_stability_index(
            reference["transaction_type"].astype(object).to_numpy(),
            target["transaction_type"].astype(object).to_numpy(),
            list(TRANSACTION_TYPES),
        ),
        "hour_of_day": categorical_stability_index(
            reference["hour_of_day"].to_numpy(),
            target["hour_of_day"].to_numpy(),
            list(range(HOURS_PER_DAY)),
        ),
    }


def feature_drift(
    reference: pd.DataFrame,
    reference_labels: np.ndarray,
    target: pd.DataFrame,
    target_labels: np.ndarray,
) -> dict[str, Any]:
    """Compare feature distributions across two windows, overall and within each class."""
    report: dict[str, Any] = {"all_rows": _frame_drift(reference, target)}
    for label, name in ((0, "legitimate"), (1, "fraud")):
        report[name] = _frame_drift(
            reference[reference_labels == label], target[target_labels == label]
        )
    return report


def build_prevalence_report(
    eda_summary: dict[str, Any],
    boundaries: SplitBoundaries,
    cutoff: int,
    sensitivity_cutoffs: list[int],
) -> dict[str, Any]:
    """Assemble the drift analysis that needs only published per-step counts."""
    table = step_table_from_eda(eda_summary, boundaries)
    partitions = partition_prevalence(table, cutoff)
    return {
        "scope": (
            "Per-step row and label counts from the Phase 1 EDA report. No feature value from the "
            "test partition was read, and no model has seen it."
        ),
        "regime_definition": {
            "rule": f"A step is {SPARSE} if it has fewer than {cutoff} rows; else {NORMAL}.",
            "uses_labels": False,
            "available_at_serving": False,
            "note": "Analysis slice only. Never a model feature.",
        },
        "partitions": partitions,
        "decomposition": {
            "train_to_validation": decompose_prevalence_change(
                partitions["train"], partitions["validation"]
            ),
            "train_to_test": decompose_prevalence_change(partitions["train"], partitions["test"]),
            "validation_to_test": decompose_prevalence_change(
                partitions["validation"], partitions["test"]
            ),
        },
        "test_prevalence_at_reference_volume": {
            "at_train_legitimate_volume": prevalence_at_reference_volume(
                partitions["train"], partitions["test"]
            ),
            "at_validation_legitimate_volume": prevalence_at_reference_volume(
                partitions["validation"], partitions["test"]
            ),
        },
        "sparse_share_by_hour": regime_by_hour(table, cutoff),
        "cutoff_sensitivity": cutoff_sensitivity(table, sensitivity_cutoffs),
        "daily_profile": daily_profile(table),
    }
