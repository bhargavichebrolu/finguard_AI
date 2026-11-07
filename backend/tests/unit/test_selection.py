"""The selection rule and threshold analysis, using constructed candidates."""

import numpy as np
import pytest
from tests.conftest import small_experiment_config

from app.ml.experiment_stages import best_run, load_experiment_config
from app.ml.pipeline_io import EXPERIMENT_CONFIG_PATH
from app.ml.selection import (
    analyse_thresholds,
    apply_gates,
    choose_candidate,
    reliability_table,
    score_semantics,
    summarise_family,
)

RULE = {"max_seed_coefficient_of_variation": 0.1, "recall_tie_margin": 0.01}


def candidate(family, pr_auc=0.3, recall=0.5, single_row_ms=5.0, cv=0.01, folds=(0.2, 0.2)):
    return {
        "family": family,
        "pr_auc_mean": pr_auc,
        "pr_auc_seed_cv": cv,
        "seed_runs_failed": 0,
        "folds": [
            {"fold": index, "pr_auc": value, "type_rate_baseline_pr_auc": 0.1}
            for index, value in enumerate(folds)
        ],
        "at_fpr_cap": {"recall": recall},
        "single_row_ms": single_row_ms,
    }


def tied(*_families):
    return {"includes_zero": True}


def test_gate_rejects_a_model_no_better_than_the_type_baseline():
    passed, rejected = apply_gates([candidate("a", pr_auc=0.05)], 0.1, RULE)
    assert passed == []
    assert "baseline" in rejected[0]["reasons"][0]


def test_gate_rejects_high_seed_variation():
    _, rejected = apply_gates([candidate("a", cv=0.2)], 0.1, RULE)
    assert "seed variation" in rejected[0]["reasons"][0]


def test_gate_rejects_a_failed_seed_run():
    bad = candidate("a")
    bad["seed_runs_failed"] = 1
    _, rejected = apply_gates([bad], 0.1, RULE)
    assert "seed run failed" in rejected[0]["reasons"][0]


def test_gate_rejects_losing_to_the_baseline_in_any_fold():
    _, rejected = apply_gates([candidate("a", folds=(0.5, 0.05))], 0.1, RULE)
    assert "rolling fold 1" in rejected[0]["reasons"][0]


def test_gate_rejects_a_failed_fold():
    _, rejected = apply_gates([candidate("a", folds=(0.5, None))], 0.1, RULE)
    assert "rolling fold 1 failed" in rejected[0]["reasons"][0]


def test_gate_passes_a_good_candidate():
    passed, rejected = apply_gates([candidate("a")], 0.1, RULE)
    assert [item["family"] for item in passed] == ["a"] and rejected == []


def test_clear_pr_auc_winner_is_chosen_even_if_slower():
    decision = choose_candidate(
        [candidate("a", pr_auc=0.5, single_row_ms=50), candidate("b", pr_auc=0.2, single_row_ms=1)],
        {"b": {"includes_zero": False}},
        RULE,
    )
    assert decision["statistically_indistinguishable"] == ["a"]
    assert decision["selected_family"] == "a"


def test_statistical_tie_goes_to_higher_recall():
    decision = choose_candidate(
        [candidate("a", pr_auc=0.5, recall=0.4), candidate("b", pr_auc=0.48, recall=0.6)],
        {"b": tied()},
        RULE,
    )
    assert decision["tied_on_recall"] == ["b"]
    assert decision["selected_family"] == "b"


def test_recall_tie_within_the_margin_goes_to_the_faster_model():
    decision = choose_candidate(
        [
            candidate("a", pr_auc=0.5, recall=0.6, single_row_ms=20),
            candidate("b", pr_auc=0.49, recall=0.595, single_row_ms=2),
        ],
        {"b": tied()},
        RULE,
    )
    assert decision["tied_on_recall"] == ["a", "b"]
    assert decision["selected_family"] == "b"


def test_recall_outside_the_margin_is_not_a_tie():
    decision = choose_candidate(
        [
            candidate("a", pr_auc=0.5, recall=0.6, single_row_ms=20),
            candidate("b", pr_auc=0.49, recall=0.58, single_row_ms=2),
        ],
        {"b": tied()},
        RULE,
    )
    assert decision["selected_family"] == "a"


def test_empty_candidate_list_is_rejected():
    with pytest.raises(ValueError):
        choose_candidate([], {}, RULE)


def _run(family, pr_auc, stage="matrix", status="ok", hyperparameters=None, seed=42):
    return {
        "status": status,
        "stage": stage,
        "spec": {
            "family": family,
            "strategy": "original",
            "hyperparameters": hyperparameters or {"depth": 1},
            "seed": seed,
            "target_ratio": None,
            "dropped_features": [],
        },
        "evaluation": {
            "ranking": {"pr_auc": pr_auc, "roc_auc": 0.9},
            "at_fpr_cap": {"recall": 0.5},
            "at_max_f1": {},
            "slices": {},
        },
        "training": {"total_seconds": 1.0},
        "inference": {"single_row_ms_median": 1.0, "batch_microseconds_per_row": 1.0},
    }


def test_best_run_ignores_stability_sensitivity_and_failed_runs():
    runs = {
        "a": _run("xgboost", 0.2),
        "b": _run("xgboost", 0.9, stage="sensitivity_features"),
        "c": _run("xgboost", 0.95, stage="stability_seed"),
        "d": _run("xgboost", 0.99, status="failed"),
        "e": _run("xgboost", 0.3, stage="tuning"),
    }
    assert best_run(runs, "xgboost")[0] == "e"


def test_best_run_is_none_when_nothing_succeeded():
    assert best_run({"a": _run("xgboost", 0.9, status="failed")}, "xgboost") is None


def test_summary_uses_all_seeds_of_the_same_settings_only():
    runs = {
        "a": _run("xgboost", 0.30),
        "b": _run("xgboost", 0.40, stage="stability_seed", seed=7),
        "c": _run("xgboost", 0.10, hyperparameters={"depth": 2}),
    }
    summary = summarise_family("xgboost", runs, [])
    assert sorted(summary["seed_pr_aucs"]) == [0.30, 0.40]
    assert summary["pr_auc_mean"] == pytest.approx(0.35)


def test_summary_finds_rolling_folds_by_run_id():
    runs = {"a": _run("xgboost", 0.3), "a-fold0": _run("xgboost", 0.25, stage="rolling_fold")}
    folds = [{"transaction_type_rate": {"pr_auc": 0.1}}, {"transaction_type_rate": {"pr_auc": 0.1}}]
    summary = summarise_family("xgboost", runs, folds)
    assert summary["folds"][0]["pr_auc"] == 0.25
    assert summary["folds"][1]["pr_auc"] is None


def _threshold_data():
    generator = np.random.default_rng(0)
    steps = np.repeat(np.arange(100, 140), 100)
    labels = (generator.random(steps.size) < 0.05).astype(int)
    raw = labels * 2.0 + generator.normal(0, 1, steps.size)
    scores = 1 / (1 + np.exp(-raw))
    return labels, scores, steps


def test_threshold_analysis_selects_by_the_fixed_objective():
    labels, scores, steps = _threshold_data()
    settings = small_experiment_config()
    slices = {"all": np.ones(labels.size, dtype=bool)}
    result = analyse_thresholds(labels, scores, steps, slices, settings)
    assert result["selected"]["false_positive_rate"] <= 0.05
    assert set(result["prd_candidates"]) == {"0.30", "0.40", "0.50", "0.60", "0.70"}
    assert {"max_f1", "max_f2", "fpr_cap_0.05", "fpr_cap_0.1"} == set(result["rule_alternatives"])
    assert result["validation_steps"] == 40
    assert "late" in " ".join(result["temporal_check"])
    assert result["out_of_bag"]["replicates_used"] > 0


def test_sweep_shows_recall_falling_as_the_threshold_rises():
    labels, scores, steps = _threshold_data()
    settings = small_experiment_config()
    sweep = analyse_thresholds(labels, scores, steps, {}, settings)["sweep"]
    recalls = [item["recall"] for item in sweep]
    assert recalls == sorted(recalls, reverse=True)
    assert [item["threshold"] for item in sweep] == sorted(item["threshold"] for item in sweep)


def test_reliability_table_covers_every_row():
    labels, scores, _ = _threshold_data()
    table = reliability_table(labels, scores)
    assert sum(row["rows"] for row in table) == labels.size
    assert sum(row["fraud_rows"] for row in table) == labels.sum()


def test_score_semantics_warns_that_inflated_scores_are_not_probabilities():
    assert "must not be presented as a probability" in score_semantics("class_weight")
    assert "must not be presented as a probability" in score_semantics("smote")
    assert "not a calibrated probability" in score_semantics("original")


def test_real_config_loads_and_records_the_pre_registered_objective():
    config = load_experiment_config(EXPERIMENT_CONFIG_PATH)
    assert config["threshold"]["operational_fpr_cap"] == 0.001
    assert config["selection"]["max_seed_coefficient_of_variation"] == 0.1
    assert config["selection"]["recall_tie_margin"] == 0.01
    assert config["regimes"]["sparse_step_max_rows"] == 1000
