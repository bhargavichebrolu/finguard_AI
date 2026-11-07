"""The whole Phase 2 flow on synthetic partitions, including the order the rules depend on.

The test partition file does not exist until after the freeze, which proves that nothing from
training to selection reads it: any attempt would fail with a missing file.
"""

import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from tests.conftest import build_model_partition, small_experiment_config, write_partition

from app.ml.drift import build_prevalence_report, feature_drift
from app.ml.experiment_stages import (
    best_run,
    load_development_data,
    run_baselines,
    run_matrix,
    run_sensitivity,
    run_stability,
    run_tuning,
)
from app.ml.experiments import RunStore, TestPartitionAccessError, load_development_partition
from app.ml.explainability import explain_validation_rows
from app.ml.final_evaluation import (
    ModelNotFrozenError,
    TestAlreadyEvaluatedError,
    assert_ready_for_test,
    evaluate_frozen_model,
)
from app.ml.model_artifacts import load_model_artifact
from app.ml.pipeline_io import uncommitted_paths, write_json
from app.ml.selection import freeze_selected_model
from app.ml.splitting import SplitBoundaries


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    """Run training and selection once. There is deliberately no test partition yet."""
    root = tmp_path_factory.mktemp("phase2")
    processed = root / "processed"
    results = root / "results"
    results.mkdir()
    write_partition(build_model_partition(4000, 1, 60, seed=1), processed, "train")
    write_partition(build_model_partition(1500, 61, 90, seed=2), processed, "validation")
    preprocessing = root / "preprocessing.json"
    preprocessing.write_text("{}", encoding="utf-8")

    config = small_experiment_config()
    data = load_development_data(processed, config)
    store = RunStore(results / "runs.json", root / "scores")
    run_baselines(data, config, results / "baselines.json")
    run_matrix(data, config, store)
    run_tuning(data, config, store)
    run_sensitivity(data, config, store)
    run_stability(data, config, store, results / "rolling_folds.json")
    report = freeze_selected_model(
        data,
        config,
        store,
        results,
        root / "models",
        root / "model.json",
        preprocessing,
        "test-commit",
    )
    return {
        "root": root,
        "processed": processed,
        "results": results,
        "config": config,
        "store": store,
        "report": report,
        "data": data,
    }


def test_no_test_file_existed_during_selection(workspace):
    assert not (workspace["processed"] / "test.parquet").exists()
    assert workspace["report"]["decision"]["selected_family"]


def test_guard_blocks_test_partition_even_when_the_file_exists(workspace, tmp_path):
    write_partition(build_model_partition(100, 91, 95, seed=3), tmp_path, "test")
    with pytest.raises(TestPartitionAccessError):
        load_development_partition(tmp_path, "test")


def test_matrix_covers_every_family_and_strategy(workspace):
    matrix = [run for run in workspace["store"].runs.values() if run["stage"] == "matrix"]
    assert len(matrix) == 24
    cells = {(run["spec"]["family"], run["spec"]["strategy"]) for run in matrix}
    assert len(cells) == 24


def test_every_recorded_metric_is_present_in_every_successful_run(workspace):
    for run in workspace["store"].runs.values():
        if run["status"] != "ok":
            continue
        ranking = run["evaluation"]["ranking"]
        assert {"pr_auc", "roc_auc", "prevalence"} <= set(ranking)
        at_cap = run["evaluation"]["at_fpr_cap"]
        assert {
            "precision",
            "recall",
            "f1",
            "balanced_accuracy",
            "true_positives",
            "false_positives",
            "true_negatives",
            "false_negatives",
            "false_positive_rate",
            "false_negative_rate",
        } <= set(at_cap)
        assert run["training"]["total_seconds"] > 0
        assert run["inference"]["batch_seconds"] > 0


def test_validation_rows_stay_natural_in_every_oversampled_run(workspace):
    labels = workspace["data"].validation.labels
    for run in workspace["store"].runs.values():
        if run["status"] == "ok" and run["spec"]["strategy"] in ("smote", "adasyn"):
            if run["stage"] == "rolling_fold":
                continue
            assert run["evaluation"]["ranking"]["rows"] == len(labels)
            assert run["evaluation"]["ranking"]["fraud_rows"] == int(labels.sum())
            assert run["training"]["rows_fitted"] > run["training"]["source_rows"]


def test_rolling_folds_fit_on_earlier_rows_only(workspace):
    folds = json.loads((workspace["results"] / "rolling_folds.json").read_text("utf-8"))["folds"]
    assert len(folds) == 2
    for fold in folds:
        assert fold["fit_end_step"] < fold["evaluation_first_step"]
    assert folds[0]["fit_rows"] < folds[1]["fit_rows"]


def test_sensitivity_runs_cannot_be_selected(workspace):
    report = workspace["report"]
    for candidate in report["candidates"]:
        assert candidate["stage"] in ("matrix", "tuning")


def test_selected_run_is_reproduced_exactly_by_the_refit(workspace):
    assert workspace["report"]["refit_matches_recorded_run"] is True


def test_selected_model_matches_its_family_winner(workspace):
    report = workspace["report"]
    family = report["decision"]["selected_family"]
    assert best_run(workspace["store"].runs, family) is not None
    metadata = json.loads((workspace["root"] / "model.json").read_text("utf-8"))
    assert metadata["family"] == family
    assert metadata["status"] == "frozen"
    assert metadata["threshold"]["chosen_on"] == "validation partition"
    assert metadata["trained_on"] == "train partition only"


def test_frozen_model_loads_and_scores_new_inputs(workspace):
    model = load_model_artifact(workspace["root"] / "model.json", workspace["root"] / "models")
    inputs = pd.DataFrame(
        [
            {
                "amount": 1000.0,
                "transaction_type": "TRANSFER",
                "step": 100,
                "destination_category": "customer",
            }
        ]
    )
    score = model.predict_scores(inputs)[0]
    assert 0.0 <= score <= 1.0
    assert model.classify(inputs)[0] == (score >= model.threshold)


def test_final_evaluation_runs_once_and_never_changes_the_threshold(workspace):
    root = workspace["root"]
    write_partition(build_model_partition(1500, 91, 120, seed=3), workspace["processed"], "test")
    model = load_model_artifact(root / "model.json", root / "models")
    threshold_before = model.threshold
    output = workspace["results"] / "test_evaluation.json"

    report = evaluate_frozen_model(
        model, workspace["processed"], output, workspace["config"], "test-commit-2"
    )
    assert report["frozen_threshold"] == threshold_before
    assert report["overall"]["at_frozen_threshold"]["threshold"] == threshold_before
    assert report["overall"]["ranking"]["rows"] == 1500
    assert set(report["regimes"]) == {"sparse", "normal"}
    assert "test_precision_expected_from_prior_shift_alone" in report["prior_shift_check"]
    assert "feature_drift_train_to_test" in report

    with pytest.raises(TestAlreadyEvaluatedError):
        evaluate_frozen_model(
            model, workspace["processed"], output, workspace["config"], "test-commit-3"
        )


def test_unfrozen_model_is_refused(tmp_path):
    with pytest.raises(ModelNotFrozenError):
        assert_ready_for_test({"status": "draft"}, tmp_path / "result.json")


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_uncommitted_freeze_files_are_detected(tmp_path):
    _git(tmp_path, "init")
    frozen = tmp_path / "frozen.json"
    frozen.write_text("{}", encoding="utf-8")
    assert uncommitted_paths([frozen], tmp_path) == ["frozen.json"]

    _git(tmp_path, "add", "frozen.json")
    _git(tmp_path, "commit", "-m", "freeze")
    assert uncommitted_paths([frozen], tmp_path) == []

    frozen.write_text('{"changed": true}', encoding="utf-8")
    assert uncommitted_paths([frozen], tmp_path) == ["frozen.json"]


def test_all_saved_scores_stay_in_range(workspace):
    store = workspace["store"]
    for run_id, run in store.runs.items():
        if run["status"] == "ok" and run["stage"] != "rolling_fold":
            scores = store.load_scores(run_id)
            assert np.isfinite(scores).all()
            assert ((scores >= 0) & (scores <= 1)).all()


def test_reports_render_from_stage_outputs_and_match_the_results(
    workspace, load_script, monkeypatch
):
    """Runs after the final evaluation, so every section exists. Uses real stage outputs."""
    root, results = workspace["root"], workspace["results"]
    data, config = workspace["data"], workspace["config"]

    model = load_model_artifact(root / "model.json", root / "models")
    features = data.validation.features
    labels = data.validation.labels.to_numpy()
    scores = model.pipeline.predict_proba(features)[:, 1].astype("float64")
    explanation = explain_validation_rows(
        model.pipeline,
        model.metadata["family"],
        features,
        labels,
        scores,
        data.validation_slices,
        model.threshold,
        config["shap"]["legitimate_sample_rows"],
        config["shap"]["seed"],
    )
    write_json(results / "shap_summary.json", explanation["report"])
    np.savez_compressed(
        results / "shap_sample.npz",
        values=explanation["values"].astype("float32"),
        feature_names=np.array(explanation["feature_names"]),
        amount=explanation["sample"]["amount"].to_numpy(),
        hour_of_day=explanation["sample"]["hour_of_day"].to_numpy(),
        labels=explanation["sample_labels"],
    )

    eda = {
        "whole_dataset": {
            "steps": list(range(1, 121)),
            "rows_per_step": [10 if step % 3 == 0 else 50 for step in range(1, 121)],
            "fraud_per_step": [1] * 120,
        }
    }
    boundaries = SplitBoundaries(1, 60, 90, 120)
    drift = build_prevalence_report(eda, boundaries, 20, [10, 40])
    drift["feature_drift_train_to_validation"] = feature_drift(
        data.train.features, data.train.labels.to_numpy(), features, labels
    )
    write_json(results / "temporal_drift.json", drift)

    document = root / "report.md"
    document.write_text(
        "kept\n<!-- BEGIN GENERATED RESULTS -->\n<!-- END GENERATED RESULTS -->\n", encoding="utf-8"
    )
    figures = root / "figures"
    metrics = root / "metrics.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_metrics",
            "--results-dir",
            str(results),
            "--figures-dir",
            str(figures),
            "--metadata",
            str(root / "model.json"),
            "--metrics",
            str(metrics),
            "--document",
            str(document),
        ],
    )
    load_script("export_metrics").main()

    text = document.read_text(encoding="utf-8")
    assert text.startswith("kept\n")
    for heading in (
        "Temporal drift",
        "Imbalance matrix",
        "Model comparison",
        "Stability and selection gates",
        "Threshold behaviour",
        "SHAP",
        "Final test evaluation",
    ):
        assert f"### {heading}" in text

    # A generated figure must equal the saved result it came from.
    selection = json.loads((results / "selection.json").read_text("utf-8"))
    for candidate in selection["candidates"]:
        assert f"{candidate['pr_auc']:.4f}" in text

    expected_charts = {
        "imbalance_matrix.png",
        "family_curves.png",
        "regime_comparison.png",
        "compute_cost.png",
        "temporal_drift.png",
        "sparse_by_hour.png",
        "threshold_behaviour.png",
        "validation_confusion_matrix.png",
        "shap_global.png",
        "shap_dependence.png",
        "test_curves.png",
        "test_confusion_matrix.png",
    }
    assert expected_charts == {path.name for path in figures.glob("*.png")}

    bundle = json.loads(metrics.read_text("utf-8"))
    assert bundle["threshold"]["value"] == model.threshold
    assert bundle["test"]["at_frozen_threshold"]["threshold"] == model.threshold
    assert bundle["global_feature_importance"]["by_group"]
    assert any("does not establish" in text for text in bundle["explanation_limitations"])
    assert (results / "all_runs.csv").is_file()
