"""Model families and experiment specs."""

import numpy as np
import pytest
from tests.conftest import small_experiment_config

from app.ml.candidates import (
    IMBALANCE_STRATEGIES,
    MODEL_FAMILIES,
    CandidateSpec,
    build_estimator,
    build_pipeline,
    set_inference_threads,
)

HYPERPARAMETERS = small_experiment_config()["baseline_hyperparameters"]


def spec_for(family, strategy="original", **overrides):
    fields = {
        "family": family,
        "strategy": strategy,
        "hyperparameters": HYPERPARAMETERS[family],
        "seed": 42,
    }
    return CandidateSpec(**{**fields, **overrides})


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_every_family_fits_and_gives_probabilities(family, model_partition):
    pipeline = build_pipeline(spec_for(family, "class_weight"), positive_weight=20.0, threads=1)
    pipeline.fit(model_partition.features, model_partition.labels.to_numpy())
    scores = pipeline.predict_proba(model_partition.features)[:, 1]
    assert scores.shape == (len(model_partition.features),)
    assert ((scores >= 0) & (scores <= 1)).all()
    assert np.isfinite(scores).all()


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_pipeline_contains_no_sampler(family):
    pipeline = build_pipeline(spec_for(family), positive_weight=1.0, threads=1)
    assert list(pipeline.named_steps) == ["preprocess", "model"]


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_inference_threads_can_be_set_after_fitting(family, model_partition):
    pipeline = build_pipeline(spec_for(family), positive_weight=1.0, threads=1)
    pipeline.fit(model_partition.features, model_partition.labels.to_numpy())
    set_inference_threads(pipeline, 1)
    assert pipeline.predict_proba(model_partition.features.iloc[[0]]).shape == (1, 2)


def test_only_logistic_regression_scales_numeric_features(model_partition):
    def has_scaler(family):
        pipeline = build_pipeline(spec_for(family), positive_weight=1.0, threads=1)
        transformers = pipeline.named_steps["preprocess"].named_steps["columns"].transformers
        return transformers[1][1] != "passthrough"

    assert has_scaler("logistic_regression")
    assert not has_scaler("xgboost")


@pytest.mark.parametrize(
    ("family", "parameter", "expected"),
    [("xgboost", "scale_pos_weight", 50.0), ("lightgbm", "scale_pos_weight", 50.0)],
)
def test_booster_weight_applies_only_when_class_weighted(family, parameter, expected):
    weighted = build_estimator(family, {}, True, 50.0, 1, 1)
    unweighted = build_estimator(family, {}, False, 50.0, 1, 1)
    assert weighted.get_params()[parameter] == expected
    assert unweighted.get_params()[parameter] == 1.0


def test_sklearn_weight_applies_only_when_class_weighted():
    assert build_estimator("decision_tree", {}, True, 50.0, 1, 1).class_weight == "balanced"
    assert build_estimator("decision_tree", {}, False, 50.0, 1, 1).class_weight is None


def test_run_id_changes_with_every_field():
    base = spec_for("xgboost")
    variants = [
        spec_for("xgboost", seed=7),
        spec_for("xgboost", hyperparameters={"n_estimators": 6}),
        spec_for("xgboost", dropped_features=("amount",)),
        spec_for("xgboost", "class_weight"),
        spec_for("xgboost", "smote", target_ratio=0.1),
        spec_for("xgboost", "smote", target_ratio=0.2),
    ]
    assert len({base.run_id, *[variant.run_id for variant in variants]}) == 7


def test_run_id_ignores_key_order():
    first = spec_for("xgboost", hyperparameters={"a": 1, "b": 2})
    second = spec_for("xgboost", hyperparameters={"b": 2, "a": 1})
    assert first.run_id == second.run_id


def test_spec_rejects_unknown_family_and_strategy():
    with pytest.raises(ValueError):
        CandidateSpec("svm", "original", {}, 1)
    with pytest.raises(ValueError):
        CandidateSpec("xgboost", "undersample", {}, 1)


@pytest.mark.parametrize("strategy", ["smote", "adasyn"])
def test_oversampling_spec_requires_target_ratio(strategy):
    with pytest.raises(ValueError):
        CandidateSpec("xgboost", strategy, {}, 1)


def test_non_oversampling_spec_rejects_target_ratio():
    with pytest.raises(ValueError):
        CandidateSpec("xgboost", "original", {}, 1, target_ratio=0.1)


def test_strategies_cover_the_four_in_the_prd():
    assert set(IMBALANCE_STRATEGIES) == {"original", "class_weight", "smote", "adasyn"}


def test_build_estimator_rejects_unknown_family():
    with pytest.raises(ValueError):
        build_estimator("svm", {}, False, 1.0, 1, 1)
