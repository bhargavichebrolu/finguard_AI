"""The guard on the test partition, oversampling containment, and run storage."""

import ast
from pathlib import Path

import numpy as np
import pytest
from tests.conftest import small_experiment_config, write_partition

import app.ml.experiments as experiments
from app.ml.candidates import CandidateSpec
from app.ml.evaluation import build_slices
from app.ml.experiments import (
    RunStore,
    TestPartitionAccessError,
    evaluate_candidate,
    fit_candidate,
    load_development_partition,
    measure_inference,
    run_candidate,
    score_rows,
    scores_digest,
)
from app.ml.imbalance import oversample_training_fold

HYPERPARAMETERS = {"n_estimators": 5, "num_leaves": 7, "min_child_samples": 5}
SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts"
APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def spec_for(strategy="original", target_ratio=None, seed=42):
    return CandidateSpec("lightgbm", strategy, HYPERPARAMETERS, seed, target_ratio=target_ratio)


@pytest.mark.parametrize("name", ["test", "TEST", "holdout", ""])
def test_guard_refuses_anything_but_train_and_validation(tmp_path, name):
    with pytest.raises(TestPartitionAccessError):
        load_development_partition(tmp_path, name)


def test_guard_allows_train_and_compacts_it(tmp_path, model_partition):
    write_partition(model_partition, tmp_path, "train")
    loaded = load_development_partition(tmp_path, "train")
    assert loaded.features["amount"].dtype == "float32"
    assert len(loaded.labels) == len(model_partition.labels)


def _partition_names_read_in(path: Path) -> set[str]:
    """Return every string literal in a file that names the test partition or its file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in {"test", "test.parquet"}:
                found.add(node.value)
    return found


@pytest.mark.parametrize(
    "path",
    [
        SCRIPTS_ROOT / "train_models.py",
        SCRIPTS_ROOT / "evaluate_models.py",
        SCRIPTS_ROOT / "explain_model.py",
        SCRIPTS_ROOT / "analyse_temporal_drift.py",
        APP_ROOT / "ml" / "experiments.py",
        APP_ROOT / "ml" / "experiment_stages.py",
        APP_ROOT / "ml" / "selection.py",
        APP_ROOT / "ml" / "explainability.py",
    ],
    ids=lambda path: path.name,
)
def test_selection_code_never_names_the_test_partition(path):
    assert _partition_names_read_in(path) == set()


def test_only_final_evaluation_and_preparation_can_load_a_named_partition():
    allowed = {
        "final_evaluation.py",
        "dataset_preparation.py",
        "experiments.py",
        "leakage_audit.py",
    }
    callers = set()
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "load_partition":
                    callers.add(path.name)
    assert callers <= allowed


def test_oversampling_sees_only_training_rows(monkeypatch, model_partition, later_partition):
    seen = []

    def spy(features, labels, *args, **kwargs):
        seen.append(len(features))
        return oversample_training_fold(features, labels, *args, **kwargs)

    monkeypatch.setattr(experiments, "oversample_training_fold", spy)
    fitted = fit_candidate(
        spec_for("smote", 0.2),
        model_partition.features,
        model_partition.labels.to_numpy(),
        threads=1,
        k_neighbors=3,
    )
    scores = score_rows(fitted.pipeline, later_partition.features)

    assert seen == [len(model_partition.features)]
    # Scoring produces one score per real row, and the rows are not resampled.
    assert scores.size == len(later_partition.features)


def test_fit_report_counts_real_and_synthetic_rows(model_partition):
    labels = model_partition.labels.to_numpy()
    report = fit_candidate(
        spec_for("smote", 0.2), model_partition.features, labels, threads=1, k_neighbors=3
    ).report
    added = report["resampling"]["synthetic_rows"]
    assert report["source_rows"] == labels.size
    assert report["source_fraud_rows"] == int(labels.sum())
    assert report["rows_fitted"] == labels.size + added
    assert report["fraud_rows_fitted"] == int(labels.sum()) + added


def test_fit_without_oversampling_reports_no_resampling(model_partition):
    report = fit_candidate(
        spec_for(), model_partition.features, model_partition.labels.to_numpy(), 1, 3
    ).report
    assert report["resampling"] is None
    assert report["rows_fitted"] == report["source_rows"]


def test_fit_without_fraud_is_rejected(model_partition):
    with pytest.raises(ValueError):
        fit_candidate(spec_for(), model_partition.features, np.zeros(3000, dtype="int8"), 1, 3)


def test_same_seed_reproduces_scores_exactly(model_partition, later_partition):
    labels = model_partition.labels.to_numpy()
    first = fit_candidate(spec_for("smote", 0.2), model_partition.features, labels, 1, 3)
    second = fit_candidate(spec_for("smote", 0.2), model_partition.features, labels, 1, 3)
    assert scores_digest(score_rows(first.pipeline, later_partition.features)) == scores_digest(
        score_rows(second.pipeline, later_partition.features)
    )


def test_measure_inference_returns_batch_scores_and_timings(model_partition, later_partition):
    pipeline = fit_candidate(
        spec_for(), model_partition.features, model_partition.labels.to_numpy(), 1, 3
    ).pipeline
    scores, timing = measure_inference(pipeline, later_partition.features, 1, 3)
    assert scores.size == len(later_partition.features)
    assert timing["single_row_samples"] == 3
    assert timing["batch_seconds"] > 0
    assert timing["single_row_ms_median"] > 0


def test_evaluate_candidate_reports_natural_evaluation_rows(model_partition, later_partition):
    config = small_experiment_config()
    slices = build_slices(later_partition.features, later_partition.steps, 20)
    record, scores = evaluate_candidate(
        spec_for("adasyn", 0.2), "matrix", model_partition, later_partition, slices, config
    )
    assert record["status"] == "ok"
    assert record["evaluation"]["ranking"]["rows"] == len(later_partition.labels)
    assert record["evaluation"]["ranking"]["fraud_rows"] == int(later_partition.labels.sum())
    assert record["scores_sha256"] == scores_digest(scores)


def test_store_saves_and_resumes(tmp_path):
    results, scores_dir = tmp_path / "runs.json", tmp_path / "scores"
    store = RunStore(results, scores_dir)
    store.add("run-a", {"status": "ok"}, np.array([0.25, 0.5]))
    reopened = RunStore(results, scores_dir)
    assert reopened.has("run-a")
    assert not reopened.has("run-b")
    assert reopened.load_scores("run-a").tolist() == [0.25, 0.5]


def test_run_candidate_skips_finished_runs(tmp_path):
    store = RunStore(tmp_path / "runs.json", tmp_path / "scores")
    spec = spec_for()
    store.add(spec.run_id, {"status": "ok", "marker": 1})

    def must_not_run():
        raise AssertionError("A recorded run was repeated")

    assert run_candidate(spec, "matrix", store, must_not_run)["marker"] == 1


def test_run_candidate_records_failure_rather_than_dropping_it(tmp_path):
    store = RunStore(tmp_path / "runs.json", tmp_path / "scores")
    spec = spec_for()

    def failing():
        raise RuntimeError("no neighbours")

    record = run_candidate(spec, "matrix", store, failing)
    assert record["status"] == "failed"
    assert "no neighbours" in record["error"]
    assert RunStore(tmp_path / "runs.json", tmp_path / "scores").has(spec.run_id)


def test_scores_digest_detects_any_change():
    scores = np.array([0.1, 0.2])
    assert scores_digest(scores) != scores_digest(np.array([0.1, 0.2000001]))
