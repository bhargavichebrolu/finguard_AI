"""Checks on the real Phase 2 outputs. Each is skipped until the output it needs exists."""

import json
import subprocess

import numpy as np
import pytest

from app.ml.dataset_preparation import load_partition, partition_path
from app.ml.experiments import load_development_partition
from app.ml.model_artifacts import load_model_artifact
from app.ml.pipeline_io import (
    EXPERIMENT_CONFIG_PATH,
    MODEL_METADATA_PATH,
    MODELS_DIR,
    PHASE2_RESULTS_DIR,
    PROCESSED_DIR,
    REPO_ROOT,
    sha256_file,
)
from app.ml.preprocessing import compact_features
from app.ml.reporting import render_comparison_table, render_threshold_tables

pytestmark = pytest.mark.real_data

TRAIN_ROWS, TRAIN_FRAUD = 4_433_703, 3_633
VALIDATION_ROWS, VALIDATION_FRAUD = 973_173, 570
TEST_ROWS, TEST_FRAUD = 955_744, 4_010
_LEAKAGE_ALARM_PR_AUC = 0.95


def load_result(name):
    path = PHASE2_RESULTS_DIR / name
    if not path.is_file():
        pytest.skip(f"{name} does not exist yet")
    return json.loads(path.read_text(encoding="utf-8"))


def load_metadata():
    if not MODEL_METADATA_PATH.is_file():
        pytest.skip("The model has not been frozen yet")
    return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))


def test_all_24_matrix_cells_were_attempted_and_recorded():
    runs = load_result("runs.json")
    matrix = [run for run in runs.values() if run["stage"] == "matrix"]
    assert len(matrix) == 24
    assert len({(run["spec"]["family"], run["spec"]["strategy"]) for run in matrix}) == 24


def test_every_validation_run_fitted_train_and_scored_natural_validation():
    runs = load_result("runs.json")
    for run in runs.values():
        if run["status"] != "ok" or run["stage"] == "rolling_fold":
            continue
        assert run["training"]["source_rows"] == TRAIN_ROWS
        assert run["training"]["source_fraud_rows"] == TRAIN_FRAUD
        assert run["evaluation"]["ranking"]["rows"] == VALIDATION_ROWS
        assert run["evaluation"]["ranking"]["fraud_rows"] == VALIDATION_FRAUD


def test_oversampling_added_rows_only_to_the_data_being_fitted():
    runs = load_result("runs.json")
    for run in runs.values():
        if run["status"] != "ok":
            continue
        training = run["training"]
        if run["spec"]["strategy"] in ("smote", "adasyn"):
            added = training["resampling"]["synthetic_rows"]
            assert added > 0
            assert training["rows_fitted"] == training["source_rows"] + added
            assert training["fraud_rows_fitted"] == training["source_fraud_rows"] + added
        else:
            assert training["resampling"] is None
            assert training["rows_fitted"] == training["source_rows"]


def test_rolling_folds_stay_inside_training():
    folds = load_result("rolling_folds.json")["folds"]
    assert len(folds) == 3
    for fold in folds:
        assert fold["fit_end_step"] < fold["evaluation_first_step"]
        assert fold["evaluation_end_step"] <= 322


def test_no_result_is_implausibly_good_without_balances():
    """A near-perfect score from these seven features would be a leakage alarm."""
    runs = load_result("runs.json")
    for run in runs.values():
        if run["status"] == "ok":
            assert run["evaluation"]["ranking"]["pr_auc"] < _LEAKAGE_ALARM_PR_AUC


def test_frozen_file_matches_recorded_hash_and_loads():
    metadata = load_metadata()
    model_path = MODELS_DIR / metadata["model_file"]
    assert sha256_file(model_path) == metadata["model_sha256"]
    model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
    assert model.threshold == metadata["threshold"]["value"]
    assert metadata["trained_on"] == "train partition only"
    assert metadata["training_report"]["source_rows"] == TRAIN_ROWS


def test_frozen_model_reproduces_recorded_validation_results():
    thresholds = load_result("threshold_analysis.json")
    model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
    validation = load_development_partition(PROCESSED_DIR, "validation")
    labels = validation.labels.to_numpy()
    scores = model.pipeline.predict_proba(validation.features)[:, 1].astype("float64")
    alerts = scores >= model.threshold
    selected = thresholds["selected"]
    assert int((alerts & (labels == 1)).sum()) == selected["true_positives"]
    assert int((alerts & (labels == 0)).sum()) == selected["false_positives"]
    assert selected["false_positive_rate"] <= 0.001
    assert ((scores >= 0) & (scores <= 1)).all()


def test_selection_used_the_configured_rule_and_reports_every_family():
    selection = load_result("selection.json")
    config = json.loads(EXPERIMENT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert selection["decision"]["selected_family"]
    families = {item["family"] for item in selection["candidates"]}
    missing = set(selection["families_without_a_successful_run"])
    assert len(families | missing) == 6
    assert (
        set(selection["gates"]["passed"])
        | {item["family"] for item in selection["gates"]["rejected"]}
        == families
    )
    assert config["threshold"]["operational_fpr_cap"] == 0.001


def test_test_evaluation_used_the_frozen_model_and_threshold():
    test = load_result("test_evaluation.json")
    metadata = load_metadata()
    assert test["model_sha256"] == metadata["model_sha256"]
    assert test["frozen_threshold"] == metadata["threshold"]["value"]
    assert test["overall"]["at_frozen_threshold"]["threshold"] == metadata["threshold"]["value"]
    assert test["overall"]["ranking"]["rows"] == TEST_ROWS
    assert test["overall"]["ranking"]["fraud_rows"] == TEST_FRAUD


def test_test_results_can_be_recalculated_from_the_saved_model():
    test = load_result("test_evaluation.json")
    model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
    partition = load_partition(partition_path(PROCESSED_DIR, "test"))
    features = compact_features(partition.features)
    alerts = model.pipeline.predict_proba(features)[:, 1].astype("float64") >= model.threshold
    labels = partition.labels.to_numpy()
    recorded = test["overall"]["at_frozen_threshold"]
    assert int((alerts & (labels == 1)).sum()) == recorded["true_positives"]
    assert int((alerts & (labels == 0)).sum()) == recorded["false_positives"]


def commits_touching(path):
    """Return the commits that changed a file, newest first."""
    return subprocess.run(
        ["git", "log", "--format=%H", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()


def is_ancestor(earlier, later):
    command = ["git", "merge-base", "--is-ancestor", earlier, later]
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode == 0


FREEZE_FILES = (
    "artifacts/metadata/model_v1.json",
    "experiments/results/phase2/selection.json",
    "experiments/results/phase2/threshold_analysis.json",
)


def test_freeze_commit_precedes_the_test_evaluation():
    evaluated = load_result("test_evaluation.json")["evaluated_at_commit"]
    for path in FREEZE_FILES:
        history = commits_touching(path)
        assert history, f"{path} was never committed"
        assert is_ancestor(history[-1], evaluated), f"{path} was committed after the test run"


def test_freeze_files_have_not_changed_since_they_were_committed():
    for path in FREEZE_FILES:
        history = commits_touching(path)
        if not history:
            pytest.skip("The freeze is not committed yet")
        assert len(history) == 1, f"{path} changed after the freeze: {history}"


def test_rule_commit_precedes_all_results():
    """The commit that added runs.json must descend from the commit that added the rule."""
    rule = commits_touching("docs/decisions/0002-phase-2-decisions.md")
    results = commits_touching("experiments/results/phase2/runs.json")
    if not rule or not results:
        pytest.skip("Results are not committed yet")
    assert rule[-1] != results[-1]
    assert is_ancestor(rule[-1], results[-1])


def test_documentation_tables_match_the_saved_results():
    selection = load_result("selection.json")
    thresholds = load_result("threshold_analysis.json")
    text = (REPO_ROOT / "ML_EXPERIMENTS.md").read_text(encoding="utf-8")
    assert render_comparison_table(selection) in text
    assert render_threshold_tables(thresholds) in text


def test_scores_are_not_constant():
    load_metadata()
    model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
    validation = load_development_partition(PROCESSED_DIR, "validation")
    assert np.unique(model.pipeline.predict_proba(validation.features.head(1000))[:, 1]).size > 1
