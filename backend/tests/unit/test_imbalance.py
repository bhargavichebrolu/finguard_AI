"""Oversampling: synthetic rows must be valid, and may only ever reach training rows."""

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.features import HOURS_PER_DAY, engineer_features
from app.ml.imbalance import oversample_training_fold

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts"


@pytest.fixture(params=["smote", "adasyn"])
def method(request):
    return request.param


@pytest.fixture
def result(model_partition, method):
    return oversample_training_fold(
        model_partition.features, model_partition.labels.to_numpy(), method, 0.5, 3, seed=11
    )


def synthetic_part(result, original_rows):
    return result.features.iloc[original_rows:], result.labels[original_rows:]


def test_original_rows_are_kept_unchanged_and_first(result, model_partition):
    rows = len(model_partition.features)
    pd.testing.assert_frame_equal(
        result.features.iloc[:rows].reset_index(drop=True),
        model_partition.features.reset_index(drop=True),
    )
    assert np.array_equal(result.labels[:rows], model_partition.labels.to_numpy())


def test_only_fraud_rows_are_added(result, model_partition):
    rows = len(model_partition.features)
    _, new_labels = synthetic_part(result, rows)
    assert new_labels.size == result.report["synthetic_rows"] > 0
    assert (new_labels == 1).all()


def test_synthetic_rows_only_use_types_that_contain_fraud(result, model_partition):
    new_rows, _ = synthetic_part(result, len(model_partition.features))
    assert set(new_rows["transaction_type"].astype(object)) <= {"CASH_OUT", "TRANSFER"}
    assert (new_rows["destination_category"].astype(object) == "customer").all()


def test_synthetic_rows_obey_the_feature_rules(result, model_partition):
    new_rows, _ = synthetic_part(result, len(model_partition.features))
    hours = new_rows["hour_of_day"].to_numpy()
    assert np.array_equal(hours, np.rint(hours))
    assert ((hours >= 0) & (hours < HOURS_PER_DAY)).all()
    assert (new_rows["amount"].to_numpy() >= 0).all()

    # Passing the recovered inputs back through the shared code must give the same features.
    rebuilt = engineer_features(
        pd.DataFrame(
            {
                "amount": new_rows["amount"].to_numpy(dtype="float64"),
                "transaction_type": new_rows["transaction_type"].astype(object).to_numpy(),
                "step": hours.astype("int64"),
                "destination_category": new_rows["destination_category"].astype(object).to_numpy(),
            }
        )
    )
    np.testing.assert_allclose(
        rebuilt["amount_log1p"], new_rows["amount_log1p"].to_numpy(), rtol=1e-4
    )
    np.testing.assert_allclose(rebuilt["hour_sin"], new_rows["hour_sin"].to_numpy(), atol=1e-6)


def test_synthetic_amounts_stay_within_the_fraud_range(result, model_partition):
    new_rows, _ = synthetic_part(result, len(model_partition.features))
    fraud = model_partition.features.loc[model_partition.labels == 1, "amount"]
    assert new_rows["amount"].max() <= fraud.max() * 1.001
    assert new_rows["amount"].min() >= fraud.min() * 0.999


def test_target_ratio_is_reached_per_type(result, model_partition):
    labels = model_partition.labels.to_numpy()
    types = model_partition.features["transaction_type"].astype(object).to_numpy()
    for name, entry in result.report["by_type"].items():
        if entry["added"] == 0:
            continue
        legitimate = int(((types == name) & (labels == 0)).sum())
        fraud = int(((types == name) & (labels == 1)).sum())
        # ADASYN aims for the ratio approximately, because it rounds per neighbourhood.
        assert (fraud + entry["added"]) / legitimate == pytest.approx(0.5, abs=0.05)


def test_same_seed_gives_the_same_rows_and_another_seed_does_not(model_partition, method):
    features, labels = model_partition.features, model_partition.labels.to_numpy()
    first = oversample_training_fold(features, labels, method, 0.5, 3, seed=1)
    second = oversample_training_fold(features, labels, method, 0.5, 3, seed=1)
    third = oversample_training_fold(features, labels, method, 0.5, 3, seed=2)
    pd.testing.assert_frame_equal(first.features, second.features)
    assert not first.features["amount"].iloc[-50:].equals(third.features["amount"].iloc[-50:])


def test_input_frame_is_not_modified(model_partition, method):
    features = model_partition.features
    before = features.copy()
    oversample_training_fold(features, model_partition.labels.to_numpy(), method, 0.5, 3, seed=1)
    pd.testing.assert_frame_equal(features, before)


def test_type_with_too_little_fraud_is_skipped_and_reported(model_partition):
    labels = model_partition.labels.to_numpy().copy()
    types = model_partition.features["transaction_type"].astype(object).to_numpy()
    labels[types == "TRANSFER"] = 0
    fraud_positions = np.flatnonzero(types == "TRANSFER")[:2]
    labels[fraud_positions] = 1
    result = oversample_training_fold(model_partition.features, labels, "smote", 0.5, 3, seed=1)
    assert result.report["by_type"]["TRANSFER"]["added"] == 0
    assert "k_neighbors" in result.report["by_type"]["TRANSFER"]["skipped"]
    assert result.report["by_type"]["CASH_OUT"]["added"] > 0


def test_type_already_above_target_is_left_alone(model_partition):
    labels = model_partition.labels.to_numpy()
    result = oversample_training_fold(model_partition.features, labels, "smote", 1e-6, 3, seed=1)
    assert result.report["synthetic_rows"] == 0
    assert len(result.features) == len(model_partition.features)


def test_unknown_method_is_rejected(model_partition):
    with pytest.raises(ValueError):
        oversample_training_fold(
            model_partition.features, model_partition.labels.to_numpy(), "copying", 0.5, 3, seed=1
        )


def test_mismatched_lengths_are_rejected(model_partition):
    with pytest.raises(ValueError):
        oversample_training_fold(model_partition.features, np.zeros(3), "smote", 0.5, 3, seed=1)


def test_only_experiments_module_calls_the_oversampler():
    callers = set()
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "oversample_training_fold":
                    callers.add(path.name)
    assert callers == {"experiments.py"}
