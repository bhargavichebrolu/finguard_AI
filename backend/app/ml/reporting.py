"""Charts and tables built only from saved results, so reports can never drift from the evidence.

Nothing here fits or scores a model. Every number in a generated table is read from a results
file, which is what keeps figures in the documentation traceable to an executed run.
"""

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Render to files; no display exists in scripts or CI.
import matplotlib.pyplot as plt
import numpy as np

from app.ml.candidates import IMBALANCE_STRATEGIES, MODEL_FAMILIES
from app.ml.explainability import feature_group

# Fixed family order and colours from the validated reference palette, so a family keeps its
# colour on every chart. Passes colour-vision-deficiency checks for adjacent pairs on white.
FAMILY_COLORS = {
    "logistic_regression": "#2a78d6",
    "decision_tree": "#eb6834",
    "random_forest": "#1baf7a",
    "xgboost": "#eda100",
    "lightgbm": "#e87ba4",
    "catboost": "#008300",
}
FAMILY_LABELS = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
}
STRATEGY_LABELS = {
    "original": "Original",
    "class_weight": "Class weight",
    "smote": "SMOTE",
    "adasyn": "ADASYN",
}
GROUP_LABELS = {
    "amount": "Amount",
    "hour": "Hour of day",
    "transaction_type_and_destination": "Type and destination",
}
_PRIMARY = "#2a78d6"
_SECONDARY = "#eb6834"
_TERTIARY = "#1baf7a"
_SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
_INK = "#0b0b0b"
_MUTED = "#52514e"
_GRID = "#e1e0d9"
_AXIS = "#c3c2b7"
_LOGIT_MARGIN = 1e-6
_RESULTS_BEGIN = "<!-- BEGIN GENERATED RESULTS -->"
_RESULTS_END = "<!-- END GENERATED RESULTS -->"
_CSV_THRESHOLD_FIELDS = (
    "threshold",
    "true_positives",
    "false_positives",
    "true_negatives",
    "false_negatives",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "balanced_accuracy",
    "false_positive_rate",
    "false_negative_rate",
)


def _style_axis(axis: plt.Axes, ylabel: str, xlabel: str = "") -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(_AXIS)
    axis.grid(axis="y", color=_GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(colors=_MUTED, length=0, labelsize=8)
    axis.set_ylabel(ylabel, color=_MUTED, fontsize=9)
    axis.set_xlabel(xlabel, color=_MUTED, fontsize=9)


def _save(figure: plt.Figure, title: str, path: Path) -> Path:
    figure.suptitle(title, x=0.01, ha="left", color=_INK, fontsize=12, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return path


def _search_runs(runs: dict[str, dict[str, Any]], stage: str) -> dict[tuple[str, str], Any]:
    return {
        (run["spec"]["family"], run["spec"]["strategy"]): run
        for run in runs.values()
        if run["stage"] == stage
    }


def _matrix_values(runs: dict[str, dict[str, Any]]) -> np.ndarray:
    """Return validation PR-AUC by family and strategy, with NaN marking a failed run."""
    cells = _search_runs(runs, "matrix")
    values = np.full((len(MODEL_FAMILIES), len(IMBALANCE_STRATEGIES)), np.nan)
    for row, family in enumerate(MODEL_FAMILIES):
        for column, strategy in enumerate(IMBALANCE_STRATEGIES):
            run = cells.get((family, strategy))
            if run is not None and run["status"] == "ok":
                values[row, column] = run["evaluation"]["ranking"]["pr_auc"]
    return values


def plot_imbalance_matrix(runs: dict[str, dict[str, Any]], out_dir: Path) -> Path:
    """Draw a heatmap of validation PR-AUC for all 24 family and strategy combinations."""
    values = _matrix_values(runs)
    colormap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", _SEQUENTIAL)
    figure, axis = plt.subplots(figsize=(8.5, 4))
    image = axis.imshow(values, cmap=colormap, aspect="auto")
    axis.set_xticks(range(len(IMBALANCE_STRATEGIES)))
    axis.set_xticklabels([STRATEGY_LABELS[name] for name in IMBALANCE_STRATEGIES], fontsize=9)
    axis.set_yticks(range(len(MODEL_FAMILIES)))
    axis.set_yticklabels([FAMILY_LABELS[name] for name in MODEL_FAMILIES], fontsize=9)
    axis.tick_params(length=0, colors=_MUTED)
    axis.spines[:].set_visible(False)
    finite = values[np.isfinite(values)]
    midpoint = (finite.min() + finite.max()) / 2 if finite.size else 0.0
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            label = "failed" if np.isnan(value) else f"{value:.4f}"
            color = "white" if np.isfinite(value) and value > midpoint else _INK
            axis.text(column, row, label, ha="center", va="center", color=color, fontsize=9)
    bar = figure.colorbar(image, ax=axis, fraction=0.025, pad=0.02)
    bar.ax.tick_params(labelsize=8, colors=_MUTED, length=0)
    bar.outline.set_visible(False)
    bar.set_label("Validation PR-AUC", color=_MUTED, fontsize=9)
    figure.subplots_adjust(top=0.88)
    return _save(
        figure,
        "Validation PR-AUC by model and imbalance strategy, at baseline settings",
        out_dir / "imbalance_matrix.png",
    )


def plot_family_curves(selection: dict[str, Any], out_dir: Path) -> Path:
    """Draw PR and ROC curves for each family's best run, on validation."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.4))
    for candidate in selection["candidates"]:
        family = candidate["family"]
        curves = selection["candidate_curves"][family]
        style = {"color": FAMILY_COLORS[family], "linewidth": 1.6, "label": FAMILY_LABELS[family]}
        left.plot(curves["pr_recall"], curves["pr_precision"], **style)
        right.plot(curves["roc_fpr"], curves["roc_tpr"], **style)
    _style_axis(left, "Precision (log scale)", "Recall")
    _style_axis(right, "Recall", "False positive rate (log scale)")
    left.set_yscale("log")
    right.set_xscale("log")
    right.set_xlim(left=1e-5, right=1)
    handles, labels = left.get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="lower center", ncol=6, frameon=False, fontsize=8, labelcolor=_INK
    )
    figure.subplots_adjust(top=0.88, bottom=0.2, wspace=0.22)
    return _save(figure, "Each family's best run on validation", out_dir / "family_curves.png")


def plot_threshold_behaviour(thresholds: dict[str, Any], out_dir: Path) -> Path:
    """Draw how precision, recall and false positive rate respond to the threshold."""
    sweep = [item for item in thresholds["sweep"] if _LOGIT_MARGIN <= item["threshold"] <= 1 - 1e-6]
    x = [item["threshold"] for item in sweep]
    precision = [item["precision"] if item["precision"] is not None else np.nan for item in sweep]
    recall = [item["recall"] for item in sweep]
    fpr = [item["false_positive_rate"] for item in sweep]
    selected = thresholds["selected_threshold"]

    figure, (upper, lower) = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True)
    upper.plot(x, recall, color=_PRIMARY, linewidth=2, label="Recall")
    upper.plot(x, precision, color=_SECONDARY, linewidth=2, label="Precision")
    lower.plot(x, fpr, color=_PRIMARY, linewidth=2)
    _style_axis(upper, "Share")
    _style_axis(lower, "False positive rate (log scale)", "Threshold (logit scale)")
    lower.set_yscale("log")
    lower.set_xscale("logit")
    for axis in (upper, lower):
        axis.axvline(selected, color=_MUTED, linewidth=1, linestyle="--")
    upper.text(
        selected,
        1.02,
        f" selected {selected:.4g}",
        transform=upper.get_xaxis_transform(),
        color=_INK,
        fontsize=8,
    )
    upper.legend(frameon=False, fontsize=9, labelcolor=_INK, loc="center left")
    figure.subplots_adjust(top=0.9, hspace=0.1)
    return _save(
        figure,
        "Threshold behaviour of the selected model on validation",
        out_dir / "threshold_behaviour.png",
    )


def plot_confusion_matrix(metrics: dict[str, Any], title: str, path: Path) -> Path:
    """Draw one confusion matrix, with counts labelled in every cell."""
    cells = np.array(
        [
            [metrics["true_negatives"], metrics["false_positives"]],
            [metrics["false_negatives"], metrics["true_positives"]],
        ]
    )
    colormap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", _SEQUENTIAL)
    figure, axis = plt.subplots(figsize=(5, 3.6))
    axis.imshow(np.log10(cells + 1), cmap=colormap, aspect="auto")
    limit = np.log10(cells.max() + 1) / 2
    for row in range(2):
        for column in range(2):
            count = cells[row, column]
            color = "white" if np.log10(count + 1) > limit else _INK
            axis.text(column, row, f"{count:,}", ha="center", va="center", color=color, fontsize=12)
    axis.set_xticks([0, 1], ["Predicted legitimate", "Predicted fraud"], fontsize=9)
    axis.set_yticks([0, 1], ["Actual legitimate", "Actual fraud"], fontsize=9)
    axis.tick_params(length=0, colors=_MUTED)
    axis.spines[:].set_visible(False)
    figure.subplots_adjust(top=0.86)
    return _save(figure, title, path)


def plot_regime_comparison(selection: dict[str, Any], out_dir: Path) -> Path:
    """Compare each family's sparse and normal step results on validation."""
    candidates = selection["candidates"]
    names = [FAMILY_LABELS[item["family"]] for item in candidates]
    positions = np.arange(len(candidates))
    width = 0.38
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
    for offset, regime, color, label in (
        (-width / 2, "regime_sparse", _SECONDARY, "Sparse steps"),
        (width / 2, "regime_normal", _PRIMARY, "Normal steps"),
    ):
        lift = [item["slices"][regime]["ranking"]["pr_auc_lift"] or 0.0 for item in candidates]
        recall = [item["slices"][regime]["at_fpr_cap"]["recall"] or 0.0 for item in candidates]
        left.bar(positions + offset, lift, width * 0.92, color=color, label=label)
        right.bar(positions + offset, recall, width * 0.92, color=color, label=label)
    _style_axis(left, "PR-AUC divided by the regime's fraud rate")
    _style_axis(right, "Recall at the shared capped threshold")
    for axis in (left, right):
        axis.set_xticks(positions, names, rotation=20, ha="right", fontsize=8)
    left.legend(
        frameon=False,
        fontsize=9,
        labelcolor=_INK,
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        ncol=2,
    )
    figure.subplots_adjust(top=0.84, wspace=0.2)
    return _save(
        figure,
        "Sparse and normal steps on validation, by family",
        out_dir / "regime_comparison.png",
    )


def plot_compute_cost(selection: dict[str, Any], out_dir: Path) -> Path:
    """Compare training time and single-row prediction time for each family's best run."""
    candidates = selection["candidates"]
    names = [FAMILY_LABELS[item["family"]] for item in candidates]
    colors = [FAMILY_COLORS[item["family"]] for item in candidates]
    positions = np.arange(len(candidates))
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 3.6))
    left.barh(positions, [item["training_seconds"] for item in candidates], color=colors)
    right.barh(positions, [item["single_row_ms"] for item in candidates], color=colors)
    _style_axis(left, "", "Training time (seconds)")
    _style_axis(right, "", "Median single-row prediction (ms)")
    left.set_yticks(positions, names, fontsize=8)
    right.set_yticks(positions, [""] * len(names))
    for axis in (left, right):
        axis.grid(axis="y", visible=False)
        axis.grid(axis="x", color=_GRID, linewidth=0.8)
        axis.invert_yaxis()
    figure.subplots_adjust(top=0.86, wspace=0.08)
    return _save(
        figure, "Computational cost of each family's best run", out_dir / "compute_cost.png"
    )


def _chronological(partitions: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Order partitions by time, because saved JSON stores its keys alphabetically."""
    return sorted(partitions.items(), key=lambda item: item[1]["first_step"])


def plot_temporal_drift(drift: dict[str, Any], out_dir: Path) -> Path:
    """Draw daily volume and prevalence across the whole simulation, by partition."""
    profile = drift["daily_profile"]
    days = [item["day"] for item in profile]
    rows = [item["rows"] for item in profile]
    prevalence = [100 * item["prevalence"] for item in profile]
    figure, (upper, lower) = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True)
    upper.plot(days, rows, color=_PRIMARY, linewidth=1.6)
    lower.plot(days, prevalence, color=_SECONDARY, linewidth=1.6)
    _style_axis(upper, "Rows per day (log scale)")
    _style_axis(lower, "Fraud rate, % (log scale)", "Simulated day")
    upper.set_yscale("log")
    lower.set_yscale("log")
    # Validation is short, so its label would overprint the next one on the same line.
    for position, (name, summary) in enumerate(_chronological(drift["partitions"])):
        first = next(item["day"] for item in profile if item["last_step"] >= summary["first_step"])
        if summary["first_step"] > profile[0]["first_step"]:
            for axis in (upper, lower):
                axis.axvline(first, color=_MUTED, linewidth=0.8, linestyle="--")
        upper.text(
            first,
            1.02 + 0.09 * (position % 2),
            f"{name}: {summary['prevalence']:.3%} fraud",
            transform=upper.get_xaxis_transform(),
            color=_INK,
            fontsize=8,
        )
    figure.subplots_adjust(top=0.84, hspace=0.1)
    return _save(
        figure,
        "Fraud rate rises late in the simulation because legitimate volume collapses",
        out_dir / "temporal_drift.png",
    )


def plot_sparse_by_hour(drift: dict[str, Any], out_dir: Path) -> Path:
    """Draw how often each hour's steps are sparse, per partition."""
    hours = np.arange(24)
    colors = {"train": _PRIMARY, "validation": _SECONDARY, "test": _TERTIARY}
    figure, axis = plt.subplots(figsize=(10, 3.6))
    for name, color in colors.items():
        shares = drift["sparse_share_by_hour"][name]
        values = [100 * share if share is not None else np.nan for share in shares]
        axis.plot(hours, values, color=color, linewidth=2, marker="o", ms=4, label=name)
    _style_axis(axis, "Steps that are sparse (%)", "hour_of_day (step modulo 24)")
    axis.set_xticks(hours[::2])
    axis.legend(frameon=False, fontsize=9, labelcolor=_INK)
    figure.subplots_adjust(top=0.88)
    return _save(figure, "When sparse steps occur, by partition", out_dir / "sparse_by_hour.png")


def plot_shap_summary(shap_report: dict[str, Any], out_dir: Path) -> Path:
    """Draw global SHAP importance by underlying group and by individual column."""
    summary = shap_report["summary"]
    groups = sorted(
        summary["all_rows"]["mean_absolute_by_group"],
        key=lambda name: -summary["fraud"]["mean_absolute_by_group"][name],
    )
    features = sorted(
        summary["all_rows"]["mean_absolute_by_feature"],
        key=lambda name: -summary["all_rows"]["mean_absolute_by_feature"][name],
    )
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    positions = np.arange(len(groups))
    width = 0.38
    left.barh(
        positions - width / 2,
        [summary["fraud"]["mean_absolute_by_group"][name] for name in groups],
        width * 0.92,
        color=_SECONDARY,
        label="Fraud rows",
    )
    left.barh(
        positions + width / 2,
        [summary["legitimate"]["mean_absolute_by_group"][name] for name in groups],
        width * 0.92,
        color=_PRIMARY,
        label="Legitimate rows",
    )
    left.set_yticks(positions, [GROUP_LABELS[name] for name in groups], fontsize=9)
    left.legend(
        frameon=False,
        fontsize=9,
        labelcolor=_INK,
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        ncol=2,
    )
    right.barh(
        np.arange(len(features)),
        [summary["all_rows"]["mean_absolute_by_feature"][name] for name in features],
        color=_PRIMARY,
    )
    right.set_yticks(np.arange(len(features)), features, fontsize=8)
    scale = shap_report["output_scale"].replace("_", "-")
    for axis, label in (
        (left, f"Mean |SHAP| ({scale}), summed within group"),
        (right, f"Mean |SHAP| ({scale}), all rows, reweighted"),
    ):
        _style_axis(axis, "", label)
        axis.grid(axis="y", visible=False)
        axis.grid(axis="x", color=_GRID, linewidth=0.8)
        axis.invert_yaxis()
    figure.subplots_adjust(top=0.84, wspace=0.62)
    return _save(
        figure, "What the selected model relies on (validation)", out_dir / "shap_global.png"
    )


def plot_shap_dependence(sample_path: Path, shap_report: dict[str, Any], out_dir: Path) -> Path:
    """Draw how the amount and hour contributions change with their values."""
    sample = np.load(sample_path, allow_pickle=False)
    names = [str(name) for name in sample["feature_names"]]
    values, labels = sample["values"], sample["labels"]

    def group_values(group: str) -> np.ndarray:
        columns = [index for index, name in enumerate(names) if feature_group(name) == group]
        return values[:, columns].sum(axis=1)

    scale = shap_report["output_scale"].replace("_", "-")
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
    for mask, color, label, size in (
        (labels != 1, _PRIMARY, "Legitimate (sample)", 3),
        (labels == 1, _SECONDARY, "Fraud", 8),
    ):
        left.scatter(
            np.maximum(sample["amount"][mask], 1.0),
            group_values("amount")[mask],
            s=size,
            color=color,
            alpha=0.5,
            label=label,
            linewidths=0,
        )
        right.scatter(
            sample["hour_of_day"][mask],
            group_values("hour")[mask],
            s=size,
            color=color,
            alpha=0.5,
            linewidths=0,
        )
    left.set_xscale("log")
    _style_axis(left, f"Amount contribution ({scale})", "Amount (log scale)")
    _style_axis(right, f"Hour contribution ({scale})", "hour_of_day")
    right.set_xticks(np.arange(0, 24, 2))
    left.legend(frameon=False, fontsize=9, labelcolor=_INK, markerscale=2)
    figure.subplots_adjust(top=0.88, wspace=0.22)
    return _save(
        figure,
        "How amount and hour change the selected model's score (validation)",
        out_dir / "shap_dependence.png",
    )


def plot_test_results(test: dict[str, Any], out_dir: Path) -> list[Path]:
    """Draw the frozen model's test curves against validation, plus its confusion matrix."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    for curves, color, label in (
        (test["validation_curves"], _PRIMARY, "Validation"),
        (test["curves"], _SECONDARY, "Test"),
    ):
        left.plot(
            curves["pr_recall"], curves["pr_precision"], color=color, linewidth=2, label=label
        )
        right.plot(curves["roc_fpr"], curves["roc_tpr"], color=color, linewidth=2, label=label)
    _style_axis(left, "Precision (log scale)", "Recall")
    _style_axis(right, "Recall", "False positive rate (log scale)")
    left.set_yscale("log")
    right.set_xscale("log")
    right.set_xlim(left=1e-5, right=1)
    left.legend(frameon=False, fontsize=9, labelcolor=_INK)
    figure.subplots_adjust(top=0.88, wspace=0.22)
    curves_path = _save(
        figure,
        "The frozen model on test and validation (prevalence differs, so PR is not comparable)",
        out_dir / "test_curves.png",
    )
    matrix_path = plot_confusion_matrix(
        test["overall"]["at_frozen_threshold"],
        "Test, at the frozen threshold",
        out_dir / "test_confusion_matrix.png",
    )
    return [curves_path, matrix_path]


def _fmt(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _pct(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{100 * value:.{digits}f}%"


def _count(value: int | None) -> str:
    return "n/a" if value is None else f"{value:,}"


def _table(header: list[str], rows: list[list[str]], align: str = "") -> str:
    markers = list(align) + ["-"] * (len(header) - len(align))
    separator = ["---:" if mark == "r" else "---" for mark in markers]
    lines = [header, separator, *rows]
    return "\n".join("| " + " | ".join(line) + " |" for line in lines)


def write_runs_csv(runs: dict[str, dict[str, Any]], path: Path) -> Path:
    """Write every run, including failures, as one spreadsheet row with all recorded metrics."""
    header = [
        "run_id",
        "stage",
        "status",
        "family",
        "strategy",
        "seed",
        "target_ratio",
        "dropped_features",
        "hyperparameters",
        "rows_evaluated",
        "fraud_rows_evaluated",
        "prevalence",
        "pr_auc",
        "pr_auc_lift",
        "roc_auc",
        "brier",
    ]
    for prefix in ("default_0_50", "fpr_cap", "max_f1"):
        header.extend(f"{prefix}_{field}" for field in _CSV_THRESHOLD_FIELDS)
    header.extend(
        [
            "rows_fitted",
            "fraud_rows_fitted",
            "resample_seconds",
            "fit_seconds",
            "total_training_seconds",
            "batch_inference_seconds",
            "batch_microseconds_per_row",
            "single_row_ms_median",
            "single_row_ms_p95",
            "error",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for run_id, run in sorted(runs.items()):
            spec = run["spec"]
            row: dict[str, Any] = {
                "run_id": run_id,
                "stage": run["stage"],
                "status": run["status"],
                "family": spec["family"],
                "strategy": spec["strategy"],
                "seed": spec["seed"],
                "target_ratio": spec["target_ratio"],
                "dropped_features": " ".join(spec["dropped_features"]),
                "hyperparameters": repr(dict(sorted(spec["hyperparameters"].items()))),
                "error": run.get("error", ""),
            }
            if run["status"] == "ok":
                ranking = run["evaluation"]["ranking"]
                row.update(
                    rows_evaluated=ranking["rows"],
                    fraud_rows_evaluated=ranking["fraud_rows"],
                    prevalence=ranking["prevalence"],
                    pr_auc=ranking["pr_auc"],
                    pr_auc_lift=ranking["pr_auc_lift"],
                    roc_auc=ranking["roc_auc"],
                    brier=ranking["brier"],
                    rows_fitted=run["training"]["rows_fitted"],
                    fraud_rows_fitted=run["training"]["fraud_rows_fitted"],
                    resample_seconds=run["training"]["resample_seconds"],
                    fit_seconds=run["training"]["fit_seconds"],
                    total_training_seconds=run["training"]["total_seconds"],
                    batch_inference_seconds=run["inference"]["batch_seconds"],
                    batch_microseconds_per_row=run["inference"]["batch_microseconds_per_row"],
                    single_row_ms_median=run["inference"]["single_row_ms_median"],
                    single_row_ms_p95=run["inference"]["single_row_ms_p95"],
                )
                evaluation = run["evaluation"]
                for prefix, metrics in (
                    ("default_0_50", evaluation["at_prd_candidates"]["0.50"]),
                    ("fpr_cap", evaluation["at_fpr_cap"]),
                    ("max_f1", evaluation["at_max_f1"]),
                ):
                    row.update(
                        {f"{prefix}_{name}": metrics[name] for name in _CSV_THRESHOLD_FIELDS}
                    )
            writer.writerow([row.get(name, "") for name in header])
    return path


def render_drift_tables(drift: dict[str, Any]) -> str:
    """Render the prevalence, decomposition and regime tables."""
    rows, regime_rows = [], []
    for name, item in _chronological(drift["partitions"]):
        rows.append(
            [
                name,
                _count(item["steps"]),
                _count(item["rows"]),
                _count(item["fraud_rows"]),
                _pct(item["prevalence"]),
                _fmt(item["fraud_per_step"], 2),
                _fmt(item["legitimate_per_step"], 0),
            ]
        )
        for regime in ("sparse", "normal"):
            part = item["regimes"][regime]
            regime_rows.append(
                [
                    name,
                    regime,
                    _count(part["steps"]),
                    _count(part["rows"]),
                    _count(part["fraud_rows"]),
                    _pct(part["prevalence"]),
                    _pct(part["share_of_partition_rows"], 2),
                    _pct(part["share_of_partition_fraud"], 1),
                ]
            )
    decomposition = [
        [
            name.replace("_", " "),
            _pct(item["total_change"]),
            _pct(item["regime_mix_effect"]),
            _pct(item["within_regime_rate_effect"]),
        ]
        for name, item in drift["decomposition"].items()
    ]
    counterfactual = drift["test_prevalence_at_reference_volume"]
    feature = drift["feature_drift_train_to_validation"]
    psi = [
        [
            name,
            _fmt(feature[name]["amount_log1p"]),
            _fmt(feature[name]["transaction_type"]),
            _fmt(feature[name]["hour_of_day"]),
        ]
        for name in ("all_rows", "legitimate", "fraud")
    ]
    return "\n\n".join(
        [
            "#### Prevalence by partition\n\n"
            + _table(
                ["Partition", "Steps", "Rows", "Fraud", "Fraud rate", "Fraud/step", "Legit/step"],
                rows,
                "lrrrrrr",
            ),
            "#### Sparse and normal steps\n\n"
            + _table(
                [
                    "Partition",
                    "Regime",
                    "Steps",
                    "Rows",
                    "Fraud",
                    "Fraud rate",
                    "% rows",
                    "% fraud",
                ],
                regime_rows,
                "llrrrrrr",
            ),
            "#### What drives the prevalence change\n\n"
            + _table(
                ["Change", "Total", "Regime mix effect", "Within-regime rate effect"],
                decomposition,
                "lrrr",
            ),
            "Test prevalence if its fraud per step stayed the same but legitimate volume matched "
            f"training: **{_pct(counterfactual['at_train_legitimate_volume'])}**; validation: "
            f"**{_pct(counterfactual['at_validation_legitimate_volume'])}**.",
            "#### Feature drift, train to validation (PSI)\n\n"
            + _table(["Rows", "Amount", "Type", "Hour"], psi, "lrrr"),
        ]
    )


def render_matrix_tables(runs: dict[str, dict[str, Any]], baselines: dict[str, Any]) -> str:
    """Render the baselines, and the matrix by family and strategy on two measures."""
    cells = _search_runs(runs, "matrix")
    random_baseline = baselines["prevalence_of_random_ranking"]
    type_rate = baselines["transaction_type_rate"]
    rule = baselines["existing_rule_is_flagged_fraud"]["at_rule_flag"]
    baseline_rows = [
        ["Random ranking", _fmt(random_baseline["prevalence"], 5), "0.5000", "n/a", "n/a"],
        [
            "Transaction type rate",
            _fmt(type_rate["ranking"]["pr_auc"], 5),
            _fmt(type_rate["ranking"]["roc_auc"]),
            _fmt(type_rate["at_fpr_cap"]["recall"]),
            _fmt(type_rate["at_fpr_cap"]["precision"]),
        ],
        [
            "Existing rule (`isFlaggedFraud`)",
            "n/a",
            "n/a",
            _fmt(rule["recall"]),
            _fmt(rule["precision"]),
        ],
    ]

    def pivot(read: Callable[[dict[str, Any]], float | None], digits: int = 4) -> str:
        rows = []
        for family in MODEL_FAMILIES:
            row = [FAMILY_LABELS[family]]
            for strategy in IMBALANCE_STRATEGIES:
                run = cells.get((family, strategy))
                if run is None:
                    row.append("not run")
                elif run["status"] != "ok":
                    row.append("failed")
                else:
                    row.append(_fmt(read(run), digits))
            rows.append(row)
        header = ["Model", *[STRATEGY_LABELS[name] for name in IMBALANCE_STRATEGIES]]
        return _table(header, rows, "lrrrr")

    return "\n\n".join(
        [
            "#### Baselines on validation\n\n"
            + _table(
                ["Baseline", "PR-AUC", "ROC-AUC", "Recall", "Precision"], baseline_rows, "lrrrr"
            ),
            "#### Validation PR-AUC, baseline settings\n\n"
            + pivot(lambda run: run["evaluation"]["ranking"]["pr_auc"]),
            "#### Validation recall at a 0.1% false positive rate\n\n"
            + pivot(lambda run: run["evaluation"]["at_fpr_cap"]["recall"]),
            "#### Training time in seconds, including resampling\n\n"
            + pivot(lambda run: run["training"]["total_seconds"], 1),
        ]
    )


def _sensitivity_reference(
    run: dict[str, Any], runs: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Find the run a sensitivity run should be compared with: the same spec, unchanged."""
    spec = run["spec"]
    for other in runs.values():
        candidate = other["spec"]
        same_model = (candidate["family"], candidate["strategy"], candidate["seed"]) == (
            spec["family"],
            spec["strategy"],
            spec["seed"],
        )
        if not same_model or other["status"] != "ok":
            continue
        if run["stage"] == "sensitivity_ratio" and other["stage"] == "matrix":
            return other
        if (
            run["stage"] == "sensitivity_features"
            and other["stage"] in ("matrix", "tuning")
            and not candidate["dropped_features"]
            and candidate["hyperparameters"] == spec["hyperparameters"]
        ):
            return other
    return None


def render_search_tables(runs: dict[str, dict[str, Any]]) -> str:
    """Render the range of the hyperparameter search, and every sensitivity run."""
    search = []
    for family in MODEL_FAMILIES:
        tried = [
            run
            for run in runs.values()
            if run["spec"]["family"] == family and run["stage"] == "tuning"
        ]
        ok = [run["evaluation"]["ranking"]["pr_auc"] for run in tried if run["status"] == "ok"]
        search.append(
            [
                FAMILY_LABELS[family],
                STRATEGY_LABELS[tried[0]["spec"]["strategy"]] if tried else "not run",
                _count(len(tried)),
                _count(len(tried) - len(ok)),
                _fmt(min(ok)) if ok else "n/a",
                _fmt(max(ok)) if ok else "n/a",
            ]
        )
    sensitivity = []
    for run in runs.values():
        if run["stage"] not in ("sensitivity_ratio", "sensitivity_features"):
            continue
        spec = run["spec"]
        change = (
            f"Oversampling ratio {spec['target_ratio']}"
            if run["stage"] == "sensitivity_ratio"
            else "Without " + ", ".join(spec["dropped_features"])
        )
        reference = _sensitivity_reference(run, runs)
        ok = run["status"] == "ok"
        sensitivity.append(
            [
                change,
                FAMILY_LABELS[spec["family"]],
                STRATEGY_LABELS[spec["strategy"]],
                _fmt(reference["evaluation"]["ranking"]["pr_auc"]) if reference else "n/a",
                _fmt(run["evaluation"]["ranking"]["pr_auc"]) if ok else "failed",
                _fmt(run["evaluation"]["ranking"]["roc_auc"]) if ok else "failed",
                _fmt(run["evaluation"]["at_fpr_cap"]["recall"]) if ok else "failed",
            ]
        )
    sensitivity.sort(key=lambda row: (row[1], row[2], row[0]))
    return "\n\n".join(
        [
            "#### Hyperparameter search on validation\n\n"
            + _table(
                [
                    "Model",
                    "Strategy",
                    "Settings tried",
                    "Failed",
                    "Lowest PR-AUC",
                    "Highest PR-AUC",
                ],
                search,
                "llrrrr",
            ),
            "#### Sensitivity runs on validation\n\n"
            + _table(
                [
                    "Change",
                    "Model",
                    "Strategy",
                    "PR-AUC before",
                    "PR-AUC after",
                    "ROC-AUC after",
                    "Recall at 0.1% FPR after",
                ],
                sensitivity,
                "lllrrrr",
            ),
        ]
    )


def render_lightgbm_diagnostic(diagnostic: dict[str, Any]) -> str:
    """Render the diagnostic of LightGBM's collapse, marked as outside selection."""
    rows = []
    for cell in diagnostic["cells"]:
        strategy, settings = STRATEGY_LABELS[cell["strategy"]], cell["settings"]
        if cell["status"] != "ok":
            rows.append([strategy, settings, f"failed: {cell['error']}", "", "", "", "", ""])
            continue
        rows.append(
            [
                strategy,
                settings,
                f"{cell['trees_built']} of {cell['trees_requested']}",
                f"{cell['largest_split_gain']:.2e}",
                _count(cell["distinct_scores"]),
                _fmt(cell["pr_auc"]),
                _fmt(cell["roc_auc"]),
                _fmt(cell["recall_at_fpr_cap"]),
            ]
        )
    return (
        "#### LightGBM diagnostic on validation\n\n"
        "These fits ran after selection and were not eligible for it.\n\n"
        + _table(
            [
                "Strategy",
                "Settings",
                "Trees built",
                "Largest split gain",
                "Distinct scores",
                "PR-AUC",
                "ROC-AUC",
                "Recall at 0.1% FPR",
            ],
            rows,
            "llrrrrrr",
        )
    )


def render_comparison_table(selection: dict[str, Any]) -> str:
    """Render each family's best run, with all requested metrics at the capped threshold."""
    intervals = selection["pr_auc_intervals"]
    rows, confusion = [], []
    for item in sorted(selection["candidates"], key=lambda entry: -entry["pr_auc_mean"]):
        family = item["family"]
        at_cap = item["at_fpr_cap"]
        interval = intervals[family]
        rows.append(
            [
                FAMILY_LABELS[family],
                STRATEGY_LABELS[item["spec"]["strategy"]],
                _fmt(item["pr_auc"]),
                f"{_fmt(interval['ci_low'])} to {_fmt(interval['ci_high'])}",
                _fmt(item["roc_auc"]),
                _fmt(at_cap["precision"]),
                _fmt(at_cap["recall"]),
                _fmt(at_cap["f1"]),
                _fmt(at_cap["balanced_accuracy"]),
            ]
        )
        confusion.append(
            [
                FAMILY_LABELS[family],
                _count(at_cap["true_positives"]),
                _count(at_cap["false_positives"]),
                _count(at_cap["false_negatives"]),
                _count(at_cap["true_negatives"]),
                _pct(at_cap["false_positive_rate"]),
                _pct(at_cap["false_negative_rate"], 1),
                _fmt(item["training_seconds"], 1),
                _fmt(item["batch_microseconds_per_row"], 2),
                _fmt(item["single_row_ms"], 2),
            ]
        )
    return "\n\n".join(
        [
            "#### Best run per family on validation\n\n"
            + _table(
                [
                    "Model",
                    "Strategy",
                    "PR-AUC",
                    "95% interval (steps resampled)",
                    "ROC-AUC",
                    "Precision",
                    "Recall",
                    "F1",
                    "Balanced acc.",
                ],
                rows,
                "llrlrrrrr",
            ),
            "#### Confusion matrices, error rates and cost\n\n"
            + _table(
                [
                    "Model",
                    "TP",
                    "FP",
                    "FN",
                    "TN",
                    "FPR",
                    "FNR",
                    "Train (s)",
                    "Batch (us/row)",
                    "Single row (ms)",
                ],
                confusion,
                "lrrrrrrrrr",
            ),
        ]
    )


def render_stability_table(selection: dict[str, Any]) -> str:
    """Render seed and rolling fold results, and each candidate's outcome at the gates."""
    rejected = {item["family"]: item["reasons"] for item in selection["gates"]["rejected"]}
    rows = []
    for item in selection["candidates"]:
        folds = ", ".join(_fmt(fold["pr_auc"], 4) for fold in item["folds"])
        baselines = ", ".join(_fmt(fold["type_rate_baseline_pr_auc"], 4) for fold in item["folds"])
        difference = selection["paired_difference_from_top"].get(item["family"])
        rows.append(
            [
                FAMILY_LABELS[item["family"]],
                _fmt(item["pr_auc_mean"]),
                _pct(item["pr_auc_seed_cv"], 1),
                folds,
                baselines,
                "top"
                if difference is None
                else f"{_fmt(difference['ci_low'])} to {_fmt(difference['ci_high'])}",
                "passed" if item["family"] not in rejected else "; ".join(rejected[item["family"]]),
            ]
        )
    return _table(
        [
            "Model",
            "Mean PR-AUC across seeds",
            "Seed variation",
            "Rolling fold PR-AUC",
            "Type baseline per fold",
            "PR-AUC gap to top (95%)",
            "Gates",
        ],
        rows,
        "lrrlll",
    )


def render_threshold_tables(thresholds: dict[str, Any]) -> str:
    """Render the threshold candidates and rules, and how the chosen threshold holds up."""

    def row(name: str, item: dict[str, Any]) -> list[str]:
        sparse = item["slices"].get("regime_sparse", {})
        normal = item["slices"].get("regime_normal", {})
        return [
            name,
            f"{item['threshold']:.6g}",
            _fmt(item["precision"]),
            _fmt(item["recall"]),
            _fmt(item["f1"]),
            _pct(item["false_positive_rate"]),
            _count(item["alerts"]),
            _fmt(sparse.get("recall")),
            _fmt(normal.get("recall")),
        ]

    rows = [row("**Selected (FPR at most 0.1%)**", thresholds["selected"])]
    rows += [
        row(f"PRD candidate {name}", item) for name, item in thresholds["prd_candidates"].items()
    ]
    rows += [
        row(name.replace("_", " "), item) for name, item in thresholds["rule_alternatives"].items()
    ]
    check = thresholds["temporal_check"]
    out_of_bag = thresholds["out_of_bag"]
    held = [
        [
            "Set on early steps, measured on late",
            _fmt(check["set_on_early_measured_on_late"]["recall"]),
            _pct(check["set_on_early_measured_on_late"]["false_positive_rate"]),
            _fmt(check["set_on_early_measured_on_late"]["precision"]),
        ],
        [
            "Set on late steps, measured on early",
            _fmt(check["set_on_late_measured_on_early"]["recall"]),
            _pct(check["set_on_late_measured_on_early"]["false_positive_rate"]),
            _fmt(check["set_on_late_measured_on_early"]["precision"]),
        ],
        [
            "Out-of-bag steps, mean (95% interval)",
            f"{_fmt(out_of_bag['out_of_bag_recall']['mean'])} "
            f"({_fmt(out_of_bag['out_of_bag_recall']['ci_low'])} to "
            f"{_fmt(out_of_bag['out_of_bag_recall']['ci_high'])})",
            f"{_pct(out_of_bag['out_of_bag_false_positive_rate']['mean'])} "
            f"({_pct(out_of_bag['out_of_bag_false_positive_rate']['ci_low'])} to "
            f"{_pct(out_of_bag['out_of_bag_false_positive_rate']['ci_high'])})",
            _fmt(out_of_bag["out_of_bag_precision"]["mean"]),
        ],
    ]
    reliability = [
        [
            f"{item['score_low']:.1f} to {item['score_high']:.1f}",
            _count(item["rows"]),
            _count(item["fraud_rows"]),
            _fmt(item["mean_score"]),
            _fmt(item["observed_fraud_rate"]),
        ]
        for item in thresholds["reliability"]
    ]
    return "\n\n".join(
        [
            "#### Thresholds on validation\n\n"
            + _table(
                [
                    "Rule",
                    "Threshold",
                    "Precision",
                    "Recall",
                    "F1",
                    "FPR",
                    "Alerts",
                    "Recall (sparse)",
                    "Recall (normal)",
                ],
                rows,
                "lrrrrrrrr",
            ),
            "#### Does the rule hold on steps it did not see?\n\n"
            + _table(["Check", "Recall", "FPR", "Precision"], held, "lrrr"),
            "#### Do scores behave like probabilities?\n\n"
            + _table(
                ["Score bin", "Rows", "Fraud", "Mean score", "Observed fraud rate"],
                reliability,
                "lrrrr",
            ),
        ]
    )


def render_shap_tables(shap_report: dict[str, Any]) -> str:
    """Render SHAP importance by group, and the three explained examples."""
    summary = shap_report["summary"]
    columns = [
        ("All rows (reweighted)", summary["all_rows"]),
        ("Fraud rows", summary["fraud"]),
        ("Legitimate rows", summary["legitimate"]),
        ("Sparse steps", summary["slices"]["regime_sparse"]),
        ("Normal steps", summary["slices"]["regime_normal"]),
    ]
    groups = sorted(
        summary["all_rows"]["mean_absolute_by_group"],
        key=lambda name: -summary["all_rows"]["mean_absolute_by_group"][name],
    )
    rows = [
        [GROUP_LABELS[name]]
        + [_fmt(column.get("mean_absolute_by_group", {}).get(name)) for _, column in columns]
        for name in groups
    ]
    examples = []
    for name, example in shap_report["local_examples"].items():
        if example is None:
            continue
        inputs = example["inputs"]
        positive = ", ".join(
            f"{item['feature']} +{item['shap_value']:.2f}"
            for item in example["positive_contributions"][:3]
        )
        negative = ", ".join(
            f"{item['feature']} {item['shap_value']:.2f}"
            for item in example["negative_contributions"][:3]
        )
        examples.append(
            [
                name.replace("_", " "),
                f"{inputs['transaction_type']}, {inputs['amount']:,.2f}, "
                f"hour {inputs['hour_of_day']}",
                f"{example['score']:.4g}",
                positive or "none",
                negative or "none",
            ]
        )
    scale = shap_report["output_scale"].replace("_", "-")
    return "\n\n".join(
        [
            f"#### Mean absolute SHAP value by group ({scale})\n\n"
            + _table(["Group", *[name for name, _ in columns]], rows, "lrrrrr"),
            "#### Explained examples\n\n"
            + _table(
                ["Example", "Transaction", "Score", "Pushed score up", "Pushed score down"],
                examples,
            ),
            f"Largest additivity error across explained rows: "
            f"{shap_report['additivity_max_error']:.2e}.",
        ]
    )


def render_test_tables(test: dict[str, Any]) -> str:
    """Render the single test evaluation, always next to its baselines and validation."""
    overall = test["overall"]
    ranking = overall["ranking"]
    interval = overall["pr_auc_interval"]
    at_threshold = overall["at_frozen_threshold"]
    baselines = test["baselines"]
    shift = test["prior_shift_check"]
    headline = [
        ["Rows / fraud", f"{_count(ranking['rows'])} / {_count(ranking['fraud_rows'])}"],
        ["Fraud rate (random ranking PR-AUC)", _pct(ranking["prevalence"])],
        [
            "PR-AUC (95% interval, steps resampled)",
            f"{_fmt(ranking['pr_auc'])} "
            f"({_fmt(interval['ci_low'])} to {_fmt(interval['ci_high'])})",
        ],
        [
            "PR-AUC of the transaction type baseline",
            _fmt(baselines["transaction_type_rate"]["pr_auc"]),
        ],
        ["ROC-AUC", _fmt(ranking["roc_auc"])],
        ["Accuracy (not a useful measure here)", _fmt(at_threshold["accuracy"])],
        ["Precision", _fmt(at_threshold["precision"])],
        ["Recall", _fmt(at_threshold["recall"])],
        ["F1", _fmt(at_threshold["f1"])],
        ["Balanced accuracy", _fmt(at_threshold["balanced_accuracy"])],
        ["False positive rate", _pct(at_threshold["false_positive_rate"])],
        ["False negative rate", _pct(at_threshold["false_negative_rate"], 1)],
        [
            "TP / FP / FN / TN",
            " / ".join(
                _count(at_threshold[name])
                for name in (
                    "true_positives",
                    "false_positives",
                    "false_negatives",
                    "true_negatives",
                )
            ),
        ],
        [
            "Existing rule: recall / precision",
            f"{_fmt(baselines['existing_rule_is_flagged_fraud']['recall'])} / "
            f"{_fmt(baselines['existing_rule_is_flagged_fraud']['precision'])}",
        ],
    ]
    regimes = []
    for name, item in test["regimes"].items():
        for window, ranking_key, threshold_key in (
            ("validation", "validation_ranking", "validation_at_frozen_threshold"),
            ("test", "ranking", "at_frozen_threshold"),
        ):
            regimes.append(
                [
                    name,
                    window,
                    _count(item[ranking_key]["rows"]),
                    _count(item[ranking_key]["fraud_rows"]),
                    _pct(item[ranking_key]["prevalence"]),
                    _fmt(item[ranking_key]["pr_auc"]),
                    _fmt(item[ranking_key]["roc_auc"]),
                    _fmt(item[threshold_key]["precision"]),
                    _fmt(item[threshold_key]["recall"]),
                    _pct(item[threshold_key]["false_positive_rate"]),
                ]
            )
    slices = [
        [
            name.replace("_", " "),
            _count(item["ranking"]["rows"]),
            _count(item["ranking"]["fraud_rows"]),
            _fmt(item["ranking"]["pr_auc"]),
            _fmt(item["at_frozen_threshold"]["precision"]),
            _fmt(item["at_frozen_threshold"]["recall"]),
        ]
        for name, item in test["slices"].items()
    ]
    shift_rows = [
        ["Fraud rate", _pct(shift["validation_prevalence"]), _pct(shift["test_prevalence"]), ""],
        [
            "Recall",
            _fmt(shift["validation_recall"]),
            _fmt(shift["test_recall"]),
            "same as validation",
        ],
        [
            "False positive rate",
            _pct(shift["validation_false_positive_rate"]),
            _pct(shift["test_false_positive_rate"]),
            "same as validation",
        ],
        [
            "Precision",
            _fmt(shift["validation_precision"]),
            _fmt(shift["test_precision"]),
            _fmt(shift["test_precision_expected_from_prior_shift_alone"]),
        ],
        [
            "PR-AUC",
            _fmt(shift["validation_pr_auc"]),
            f"{_fmt(ranking['pr_auc'])} ({_fmt(shift['test_pr_auc_at_validation_prevalence'])} at "
            "validation's fraud rate)",
            "",
        ],
    ]
    drift = test["feature_drift_train_to_test"]
    psi = [
        [
            name,
            _fmt(drift[name]["amount_log1p"]),
            _fmt(drift[name]["transaction_type"]),
            _fmt(drift[name]["hour_of_day"]),
        ]
        for name in ("all_rows", "legitimate", "fraud")
    ]
    return "\n\n".join(
        [
            _table(["Measure", "Test, frozen threshold"], headline, "lr"),
            "#### Sparse and normal steps, frozen threshold\n\n"
            + _table(
                [
                    "Regime",
                    "Window",
                    "Rows",
                    "Fraud",
                    "Fraud rate",
                    "PR-AUC",
                    "ROC-AUC",
                    "Precision",
                    "Recall",
                    "FPR",
                ],
                regimes,
                "llrrrrrrrr",
            ),
            "#### Prior shift check\n\n"
            + _table(
                ["Measure", "Validation", "Test", "Expected if only the fraud rate changed"],
                shift_rows,
                "lrrr",
            ),
            "#### Test slices\n\n"
            + _table(["Slice", "Rows", "Fraud", "PR-AUC", "Precision", "Recall"], slices, "lrrrrr"),
            "#### Feature drift, train to test (PSI)\n\n"
            + _table(["Rows", "Amount", "Type", "Hour"], psi, "lrrr"),
        ]
    )


def render_results_markdown(sections: dict[str, str]) -> str:
    """Join generated sections, in the order given, under their headings."""
    return "\n\n".join(f"### {title}\n\n{body}" for title, body in sections.items())


def inject_generated_results(document: Path, generated: str) -> None:
    """Replace the generated block in a document, and leave all other text unchanged."""
    text = document.read_text(encoding="utf-8")
    if _RESULTS_BEGIN not in text or _RESULTS_END not in text:
        raise ValueError(f"{document} has no generated results block")
    before, rest = text.split(_RESULTS_BEGIN, 1)
    _, after = rest.split(_RESULTS_END, 1)
    updated = f"{before}{_RESULTS_BEGIN}\n\n{generated}\n\n{_RESULTS_END}{after}"
    document.write_text(updated, encoding="utf-8", newline="\n")
