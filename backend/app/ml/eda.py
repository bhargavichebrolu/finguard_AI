"""Exploratory data analysis, computed in chunks, respecting the untouched test set.

Row and fraud counts per step cover the whole file because they are needed to understand
the split. Everything that could influence feature choices, such as class behaviour by
hour, type or amount, is computed from training rows only.
"""

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Render to files; no display exists in scripts or CI.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.ml.features import HOURS_PER_DAY
from app.ml.pipeline_io import DEFAULT_CHUNK_SIZE
from app.ml.schema import TARGET_COLUMN, TRANSACTION_TYPES
from app.ml.splitting import PARTITIONS, SplitBoundaries, partition_masks

_FRAUD_ELIGIBLE_TYPES = ("TRANSFER", "CASH_OUT")
_SIMULATOR_AMOUNT_CAP = 10_000_000.0
_LOG10_AMOUNT_EDGES = np.linspace(-1.0, 8.5, 77)
# Descriptive cut-off for "sparse" steps. It is reported only and never used by a model.
_LOW_VOLUME_ROWS_PER_STEP = 1_000

# Primary blue is from PRD section 7.2. The orange is chart-only so that the PRD's reserved
# status colours keep their meaning. The pair passes colour-vision-deficiency separation checks.
_COLOR_LEGITIMATE = "#2563EB"
_COLOR_FRAUD = "#C2410C"
_COLOR_TEXT = "#172033"
_COLOR_MUTED = "#64748B"
_COLOR_GRID = "#E2E8F0"


def compute_eda(
    raw_path: Path, boundaries: SplitBoundaries, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> dict[str, Any]:
    """Stream the raw file once and return a JSON-ready EDA summary."""
    rows_per_step: pd.Series | None = None
    fraud_per_step: pd.Series | None = None
    type_rows = pd.Series(0, index=TRANSACTION_TYPES, dtype="int64")
    type_fraud = pd.Series(0, index=TRANSACTION_TYPES, dtype="int64")
    hour_rows = np.zeros((2, HOURS_PER_DAY), dtype="int64")
    amount_histogram = np.zeros((2, len(_LOG10_AMOUNT_EDGES) - 1), dtype="int64")
    at_cap = np.zeros(2, dtype="int64")
    whole_number = np.zeros(2, dtype="int64")
    eligible_rows = np.zeros(2, dtype="int64")
    train_zero_amounts = 0

    columns = ["step", "type", "amount", TARGET_COLUMN]
    for chunk in pd.read_csv(raw_path, usecols=columns, chunksize=chunk_size):
        grouped = chunk.groupby("step")[TARGET_COLUMN].agg(["size", "sum"])
        rows_per_step = _add_counts(rows_per_step, grouped["size"])
        fraud_per_step = _add_counts(fraud_per_step, grouped["sum"])

        train = chunk.loc[partition_masks(chunk["step"], boundaries)["train"]]
        if train.empty:
            continue
        train_zero_amounts += int((train["amount"] == 0).sum())
        by_type = train.groupby("type")[TARGET_COLUMN].agg(["size", "sum"])
        type_rows = type_rows.add(by_type["size"], fill_value=0).astype("int64")
        type_fraud = type_fraud.add(by_type["sum"], fill_value=0).astype("int64")

        hours = train["step"].to_numpy() % HOURS_PER_DAY
        eligible = train.loc[train["type"].isin(_FRAUD_ELIGIBLE_TYPES)]
        for label in (0, 1):
            is_class = train[TARGET_COLUMN].to_numpy() == label
            hour_rows[label] += np.bincount(hours[is_class], minlength=HOURS_PER_DAY)

            class_amounts = eligible.loc[eligible[TARGET_COLUMN] == label, "amount"].to_numpy()
            positive = class_amounts[class_amounts > 0]
            amount_histogram[label] += np.histogram(np.log10(positive), _LOG10_AMOUNT_EDGES)[0]
            at_cap[label] += int((class_amounts == _SIMULATOR_AMOUNT_CAP).sum())
            whole_number[label] += int((class_amounts == np.round(class_amounts)).sum())
            eligible_rows[label] += class_amounts.size

    if rows_per_step is None or fraud_per_step is None:
        raise ValueError(f"No rows found in {raw_path}")

    return {
        "whole_dataset": {
            "scope": "all rows; volume and label counts only",
            "steps": [int(step) for step in rows_per_step.index],
            "rows_per_step": [int(value) for value in rows_per_step],
            "fraud_per_step": [int(value) for value in fraud_per_step],
            "partitions": _partition_summary(rows_per_step, fraud_per_step, boundaries),
        },
        "training_partition": {
            "scope": "training rows only",
            "rows_by_type": {name: int(type_rows[name]) for name in TRANSACTION_TYPES},
            "fraud_by_type": {name: int(type_fraud[name]) for name in TRANSACTION_TYPES},
            "rows_by_hour": {
                "legitimate": hour_rows[0].tolist(),
                "fraud": hour_rows[1].tolist(),
            },
            "zero_amount_rows": train_zero_amounts,
            "fraud_eligible_types": list(_FRAUD_ELIGIBLE_TYPES),
            "amount_log10_histogram": {
                "bin_edges": [round(float(edge), 6) for edge in _LOG10_AMOUNT_EDGES],
                "legitimate": amount_histogram[0].tolist(),
                "fraud": amount_histogram[1].tolist(),
            },
            "eligible_rows": {"legitimate": int(eligible_rows[0]), "fraud": int(eligible_rows[1])},
            "amount_at_simulator_cap": {"legitimate": int(at_cap[0]), "fraud": int(at_cap[1])},
            "amount_is_whole_number": {
                "legitimate": int(whole_number[0]),
                "fraud": int(whole_number[1]),
            },
        },
    }


def _add_counts(total: pd.Series | None, counts: pd.Series) -> pd.Series:
    if total is None:
        return counts
    return total.add(counts, fill_value=0).astype("int64")


def _partition_summary(
    rows_per_step: pd.Series, fraud_per_step: pd.Series, boundaries: SplitBoundaries
) -> dict[str, dict[str, Any]]:
    steps = rows_per_step.index.to_series()
    masks = partition_masks(steps, boundaries)
    summary: dict[str, dict[str, Any]] = {}
    for name in PARTITIONS:
        rows = int(rows_per_step[masks[name]].sum())
        fraud = int(fraud_per_step[masks[name]].sum())
        selected = steps[masks[name]]
        is_low_volume = masks[name] & (rows_per_step < _LOW_VOLUME_ROWS_PER_STEP)
        low_volume_rows = int(rows_per_step[is_low_volume].sum())
        low_volume_fraud = int(fraud_per_step[is_low_volume].sum())
        summary[name] = {
            "first_step": int(selected.min()),
            "last_step": int(selected.max()),
            "steps": len(selected),
            "rows": rows,
            "fraud_rows": fraud,
            "fraud_rate": fraud / rows,
            "mean_rows_per_step": rows / len(selected),
            "mean_fraud_per_step": fraud / len(selected),
            "low_volume_steps": int(is_low_volume.sum()),
            "low_volume_rows": low_volume_rows,
            "low_volume_fraud_rows": low_volume_fraud,
        }
    return summary


def _style_axis(axis: plt.Axes, ylabel: str) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(_COLOR_GRID)
    axis.grid(axis="y", color=_COLOR_GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(colors=_COLOR_MUTED, length=0)
    axis.set_ylabel(ylabel, color=_COLOR_MUTED)


def _save(figure: plt.Figure, title: str, path: Path) -> None:
    figure.suptitle(title, x=0.01, ha="left", color=_COLOR_TEXT, fontsize=13, fontweight="bold")
    figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _plot_volume_and_fraud(summary: dict[str, Any], out_dir: Path) -> Path:
    whole = summary["whole_dataset"]
    steps = whole["steps"]
    figure, (upper, lower) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    upper.plot(steps, whole["rows_per_step"], color=_COLOR_LEGITIMATE, linewidth=1.2)
    lower.plot(steps, whole["fraud_per_step"], color=_COLOR_FRAUD, linewidth=1.2)
    _style_axis(upper, "All rows per step")
    _style_axis(lower, "Fraud rows per step")
    lower.set_xlabel("Simulation step (hours)", color=_COLOR_MUTED)

    for name in PARTITIONS:
        info = whole["partitions"][name]
        if name != PARTITIONS[-1]:
            for axis in (upper, lower):
                axis.axvline(
                    info["last_step"] + 0.5, color=_COLOR_MUTED, linewidth=0.8, linestyle="--"
                )
        middle = (info["first_step"] + info["last_step"]) / 2
        label = f"{name}\n{info['fraud_rate'] * 100:.3f}% fraud"
        upper.text(
            middle,
            1.02,
            label,
            transform=upper.get_xaxis_transform(),
            ha="center",
            va="bottom",
            color=_COLOR_TEXT,
            fontsize=9,
        )
    path = out_dir / "volume_and_fraud_by_step.png"
    figure.subplots_adjust(top=0.82, hspace=0.12)
    _save(figure, "Row volume swings by orders of magnitude while fraud counts stay steady", path)
    return path


def _plot_types(summary: dict[str, Any], out_dir: Path) -> Path:
    train = summary["training_partition"]
    names = list(TRANSACTION_TYPES)
    rows = np.array([train["rows_by_type"][name] for name in names])
    fraud = np.array([train["fraud_by_type"][name] for name in names])
    rates = 100.0 * fraud / np.maximum(rows, 1)

    figure, (left, right) = plt.subplots(1, 2, figsize=(10, 3.6))
    left.bar(names, rows / 1e6, color=_COLOR_LEGITIMATE, width=0.6)
    right.bar(names, rates, color=_COLOR_FRAUD, width=0.6)
    _style_axis(left, "Rows (millions)")
    _style_axis(right, "Fraud rate (%)")
    left.tick_params(axis="x", labelsize=8)
    right.tick_params(axis="x", labelsize=8)
    for position, rate in enumerate(rates):
        right.text(
            position, rate, f"{rate:.3f}%", ha="center", va="bottom", color=_COLOR_TEXT, fontsize=9
        )
    path = out_dir / "training_type_distribution.png"
    figure.subplots_adjust(top=0.86, wspace=0.25)
    _save(figure, "Training partition: labelled fraud occurs in two transaction types", path)
    return path


def _plot_hours(summary: dict[str, Any], out_dir: Path) -> Path:
    train = summary["training_partition"]["rows_by_hour"]
    legitimate = np.array(train["legitimate"], dtype="float64")
    fraud = np.array(train["fraud"], dtype="float64")
    hours = np.arange(HOURS_PER_DAY)

    figure, axis = plt.subplots(figsize=(10, 3.8))
    axis.plot(
        hours,
        100 * legitimate / legitimate.sum(),
        color=_COLOR_LEGITIMATE,
        linewidth=2,
        label="Legitimate",
    )
    axis.plot(hours, 100 * fraud / fraud.sum(), color=_COLOR_FRAUD, linewidth=2, label="Fraud")
    _style_axis(axis, "Share of the class (%)")
    axis.set_xlabel("hour_of_day (step modulo 24)", color=_COLOR_MUTED)
    axis.set_xticks(hours[::2])
    axis.legend(frameon=False, loc="upper left", labelcolor=_COLOR_TEXT)
    path = out_dir / "training_hour_of_day.png"
    figure.subplots_adjust(top=0.88)
    _save(figure, "Training partition: legitimate activity is daily, fraud is not", path)
    return path


def _plot_amounts(summary: dict[str, Any], out_dir: Path) -> Path:
    histogram = summary["training_partition"]["amount_log10_histogram"]
    edges = np.array(histogram["bin_edges"])
    centers = 10 ** ((edges[:-1] + edges[1:]) / 2)
    legitimate = np.array(histogram["legitimate"], dtype="float64")
    fraud = np.array(histogram["fraud"], dtype="float64")

    figure, axis = plt.subplots(figsize=(10, 3.8))
    axis.plot(
        centers,
        100 * legitimate / legitimate.sum(),
        color=_COLOR_LEGITIMATE,
        linewidth=2,
        label="Legitimate",
    )
    axis.plot(centers, 100 * fraud / fraud.sum(), color=_COLOR_FRAUD, linewidth=2, label="Fraud")
    axis.set_xscale("log")
    axis.set_xlim(left=10)  # Bins below this are empty for both classes.
    _style_axis(axis, "Share of the class per bin (%)")
    axis.set_xlabel("Transaction amount (log scale), TRANSFER and CASH_OUT", color=_COLOR_MUTED)
    axis.legend(frameon=False, loc="upper left", labelcolor=_COLOR_TEXT)
    path = out_dir / "training_amount_by_class.png"
    figure.subplots_adjust(top=0.88)
    _save(figure, "Training partition: fraud amounts overlap legitimate ones but skew higher", path)
    return path


def render_eda_figures(summary: dict[str, Any], out_dir: Path) -> list[Path]:
    """Write all EDA charts and return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        _plot_volume_and_fraud(summary, out_dir),
        _plot_types(summary, out_dir),
        _plot_hours(summary, out_dir),
        _plot_amounts(summary, out_dir),
    ]
