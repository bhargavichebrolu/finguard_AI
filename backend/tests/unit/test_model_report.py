"""Tests that the model report is copied faithfully from saved Phase 2 outputs and nothing else."""

import ast
import csv
import json
from pathlib import Path

import pytest

from app.core.frozen_model import MODEL_REPORT_SHA256
from app.ml.pipeline_io import sha256_file

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = REPO_ROOT / "artifacts" / "metadata" / "model_v1_report.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_model_report.py"
PHASE2 = REPO_ROOT / "experiments" / "results" / "phase2"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def saved() -> dict:
    return {
        "selection": json.loads((PHASE2 / "selection.json").read_text(encoding="utf-8")),
        "thresholds": json.loads((PHASE2 / "threshold_analysis.json").read_text(encoding="utf-8")),
        "test": json.loads((PHASE2 / "test_evaluation.json").read_text(encoding="utf-8")),
        "runs": list(csv.DictReader((PHASE2 / "all_runs.csv").open(encoding="utf-8"))),
        "metrics": json.loads(
            (REPO_ROOT / "artifacts/metadata/model_v1_metrics.json").read_text(encoding="utf-8")
        ),
    }


def test_committed_report_matches_the_pinned_hash():
    assert sha256_file(REPORT_PATH) == MODEL_REPORT_SHA256


def test_rebuilding_from_sources_gives_the_committed_report(load_script, report):
    assert load_script("export_model_report").build_report(REPO_ROOT) == report


def test_recorded_source_hashes_match_the_files(report):
    for relative, digest in report["source_files"].items():
        assert sha256_file(REPO_ROOT / relative) == digest, relative


def test_sources_are_saved_results_only(load_script):
    sources = load_script("export_model_report").SOURCES.values()
    assert all(
        path.startswith(("experiments/results/phase2/", "artifacts/metadata/")) for path in sources
    )
    assert not any(path.startswith("data/") or path.endswith(".parquet") for path in sources)


def test_script_imports_no_data_loader_and_mentions_no_data_folder():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    forbidden = {
        "app.ml.dataset_preparation",
        "app.ml.final_evaluation",
        "app.ml.experiments",
        "app.ml.experiment_stages",
        "pandas",
        "pyarrow",
    }
    assert not imported & forbidden
    assert '"data' not in source and "'data" not in source
    assert "parquet" not in source


def test_family_rows_copy_selection_values(report, saved):
    by_family = {row["family"]: row for row in report["families"]}
    for candidate in saved["selection"]["candidates"]:
        row = by_family[candidate["family"]]
        assert row["pr_auc"] == candidate["pr_auc"]
        assert row["roc_auc"] == candidate["roc_auc"]
        assert row["at_fpr_cap"]["recall"] == candidate["at_fpr_cap"]["recall"]
        assert row["training_seconds"] == candidate["training_seconds"]
        assert row["single_row_ms"] == candidate["single_row_ms"]
        assert row["pr_auc_interval"] == saved["selection"]["pr_auc_intervals"][candidate["family"]]
    assert len(by_family) == 6


def test_curves_are_copied_exactly(report, saved):
    assert report["family_validation_curves"] == saved["selection"]["candidate_curves"]
    assert report["selected_model_curves"]["test"] == saved["test"]["curves"]
    assert report["selected_model_curves"]["validation"] == saved["test"]["validation_curves"]


def test_history_has_every_run_with_its_values(report, saved):
    history = report["experiment_history"]
    assert len(history) == len(saved["runs"]) == 125
    for row, run in zip(history, saved["runs"], strict=True):
        assert row["run_id"] == run["run_id"]
        assert row["pr_auc"] == float(run["pr_auc"])


def test_matrix_has_the_24_recorded_cells(report):
    cells = {(row["family"], row["strategy"]) for row in report["imbalance_matrix"]}
    assert len(report["imbalance_matrix"]) == len(cells) == 24


def test_confusion_matrices_match_the_metrics_bundle(report, saved):
    test = saved["metrics"]["test"]["at_frozen_threshold"]
    assert report["confusion_matrices"]["test"] == {
        "true_positives": test["true_positives"],
        "false_positives": test["false_positives"],
        "false_negatives": test["false_negatives"],
        "true_negatives": test["true_negatives"],
    }


def test_threshold_section_matches_the_analysis(report, saved):
    section = report["thresholds"]
    assert section["selected_threshold"] == saved["thresholds"]["selected_threshold"]
    assert len(section["sweep"]) == len(saved["thresholds"]["sweep"])
    assert (
        section["prd_candidates"]["0.30"]["precision"]
        == (saved["thresholds"]["prd_candidates"]["0.30"]["precision"])
    )


def test_notes_state_the_tie_and_the_single_test_evaluation(report):
    text = " ".join(report["notes"])
    assert "statistically indistinguishable" in text
    assert "does not show" in text
    assert "single evaluation" in text
    assert "numerical divergence" in text


def test_check_mode_detects_a_stale_report(load_script, tmp_path, monkeypatch):
    module = load_script("export_model_report")
    stale = tmp_path / "report.json"
    stale.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "REPORT_PATH", stale)
    monkeypatch.setattr("sys.argv", ["export_model_report.py", "--check"])
    assert module.main() == 1
