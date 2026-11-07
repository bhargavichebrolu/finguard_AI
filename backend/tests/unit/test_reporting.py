"""Reports must show exactly what the results contain, including failures."""

import csv

import numpy as np
import pytest

from app.ml.reporting import (
    _fmt,
    _matrix_values,
    _table,
    inject_generated_results,
    plot_confusion_matrix,
    plot_imbalance_matrix,
    render_results_markdown,
    write_runs_csv,
)


def _metrics():
    return {
        "threshold": 0.5,
        "true_positives": 3,
        "false_positives": 2,
        "true_negatives": 90,
        "false_negatives": 5,
        "accuracy": 0.93,
        "precision": 0.6,
        "recall": 0.375,
        "f1": 0.46,
        "balanced_accuracy": 0.68,
        "false_positive_rate": 0.02,
        "false_negative_rate": 0.625,
    }


def _run(family="xgboost", strategy="original", status="ok", pr_auc=0.1234):
    spec = {
        "family": family,
        "strategy": strategy,
        "seed": 42,
        "target_ratio": None,
        "dropped_features": [],
        "hyperparameters": {"a": 1},
    }
    if status != "ok":
        return {"status": status, "stage": "matrix", "spec": spec, "error": "ValueError: boom"}
    return {
        "status": "ok",
        "stage": "matrix",
        "spec": spec,
        "training": {
            "rows_fitted": 100,
            "fraud_rows_fitted": 8,
            "resample_seconds": 0.0,
            "fit_seconds": 1.0,
            "total_seconds": 1.0,
        },
        "inference": {
            "batch_seconds": 0.5,
            "batch_microseconds_per_row": 5.0,
            "single_row_ms_median": 3.0,
            "single_row_ms_p95": 4.0,
        },
        "evaluation": {
            "ranking": {
                "rows": 100,
                "fraud_rows": 8,
                "prevalence": 0.08,
                "pr_auc": pr_auc,
                "pr_auc_lift": pr_auc / 0.08,
                "roc_auc": 0.9,
                "brier": 0.05,
            },
            "at_prd_candidates": {"0.50": _metrics()},
            "at_fpr_cap": _metrics(),
            "at_max_f1": _metrics(),
        },
    }


def test_matrix_values_mark_a_failed_run_as_missing():
    runs = {"a": _run(pr_auc=0.2), "b": _run(strategy="smote", status="failed")}
    values = _matrix_values(runs)
    assert np.nanmax(values) == pytest.approx(0.2)
    assert np.isnan(values).sum() == 23


def test_all_runs_csv_keeps_failures_and_exact_values(tmp_path):
    path = write_runs_csv(
        {"ok-run": _run(pr_auc=0.1234), "bad-run": _run(status="failed")}, tmp_path / "runs.csv"
    )
    rows = {row["run_id"]: row for row in csv.DictReader(path.open(encoding="utf-8"))}
    assert float(rows["ok-run"]["pr_auc"]) == 0.1234
    assert int(rows["ok-run"]["fpr_cap_true_positives"]) == 3
    assert float(rows["ok-run"]["single_row_ms_median"]) == 3.0
    assert rows["bad-run"]["status"] == "failed"
    assert rows["bad-run"]["pr_auc"] == ""
    assert "boom" in rows["bad-run"]["error"]


def test_undefined_values_show_as_not_available_not_zero():
    assert _fmt(None) == "n/a"
    assert _fmt(0.0) == "0.0000"


def test_table_aligns_columns_and_has_a_separator():
    text = _table(["a", "b"], [["1", "2"]], "lr")
    assert text.splitlines()[1] == "| --- | ---: |"
    assert text.splitlines()[2] == "| 1 | 2 |"


def test_injection_replaces_only_the_generated_block(tmp_path):
    document = tmp_path / "doc.md"
    document.write_text(
        "written\n<!-- BEGIN GENERATED RESULTS -->\nold\n<!-- END GENERATED RESULTS -->\nkept\n",
        encoding="utf-8",
    )
    inject_generated_results(document, "new")
    text = document.read_text(encoding="utf-8")
    assert "old" not in text and "new" in text
    assert text.startswith("written\n") and text.endswith("kept\n")


def test_injection_is_repeatable(tmp_path):
    document = tmp_path / "doc.md"
    document.write_text(
        "<!-- BEGIN GENERATED RESULTS -->\n<!-- END GENERATED RESULTS -->\n", encoding="utf-8"
    )
    inject_generated_results(document, "first")
    inject_generated_results(document, "second")
    assert document.read_text(encoding="utf-8").count("BEGIN GENERATED") == 1
    assert "first" not in document.read_text(encoding="utf-8")


def test_injection_without_markers_is_refused(tmp_path):
    document = tmp_path / "doc.md"
    document.write_text("no markers", encoding="utf-8")
    with pytest.raises(ValueError):
        inject_generated_results(document, "new")


def test_sections_render_under_headings():
    assert render_results_markdown({"A": "x", "B": "y"}) == "### A\n\nx\n\n### B\n\ny"


def test_charts_are_written(tmp_path):
    assert plot_imbalance_matrix({"a": _run()}, tmp_path).stat().st_size > 0
    path = plot_confusion_matrix(_metrics(), "Title", tmp_path / "matrix.png")
    assert path.stat().st_size > 0
