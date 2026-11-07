"""Checks that excluded information cannot reach the model, with measured evidence.

Three kinds of check are combined:
1. Schema: no forbidden column is declared as a feature.
2. Files: processed partitions physically lack leaky columns and respect time boundaries.
3. Empirical: on the training partition only, how strongly each column separates fraud.
   This shows why balances are excluded; it is evidence, not a pass/fail test.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score

from app.ml.dataset_preparation import partition_path
from app.ml.features import engineer_features, raw_to_prediction_inputs
from app.ml.pipeline_io import DEFAULT_CHUNK_SIZE
from app.ml.schema import (
    ACCOUNT_IDENTIFIER_COLUMNS,
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FEATURE_DICTIONARY,
    FORBIDDEN_FEATURE_COLUMNS,
    LEAKY_BALANCE_COLUMNS,
    PROCESSED_STEP_COLUMN,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
)
from app.ml.splitting import PARTITIONS, SplitBoundaries

_BALANCE_MATCH_TOLERANCE = 0.01


class LeakageError(RuntimeError):
    """Raised when a hard leakage rule is broken."""


def assert_feature_schema_clean() -> dict[str, Any]:
    """Fail if a forbidden column is a feature or a feature is unavailable at assessment time."""
    forbidden = sorted(set(FEATURE_COLUMNS) & FORBIDDEN_FEATURE_COLUMNS)
    if forbidden:
        raise LeakageError(f"Forbidden columns declared as features: {forbidden}")
    unavailable = [spec.name for spec in FEATURE_DICTIONARY if not spec.available_before_completion]
    if unavailable:
        raise LeakageError(f"Features unavailable before completion: {unavailable}")
    return {"passed": True, "feature_columns": list(FEATURE_COLUMNS)}


def assert_processed_files_clean(
    processed_dir: Path, boundaries: SplitBoundaries
) -> dict[str, Any]:
    """Fail if a partition holds a raw leaky column or crosses its time boundary."""
    never_allowed = {
        TARGET_COLUMN,
        RULE_FLAG_COLUMN,
        *LEAKY_BALANCE_COLUMNS,
        *ACCOUNT_IDENTIFIER_COLUMNS,
    }
    observed: dict[str, dict[str, int]] = {}
    for name in PARTITIONS:
        path = partition_path(processed_dir, name)
        leaked = sorted(set(pq.read_schema(path).names) & never_allowed)
        if leaked:
            raise LeakageError(f"{path.name} contains excluded columns: {leaked}")
        steps = pq.read_table(path, columns=[PROCESSED_STEP_COLUMN])[PROCESSED_STEP_COLUMN]
        step_values = steps.to_numpy()
        observed[name] = {"min_step": int(step_values.min()), "max_step": int(step_values.max())}

    train_ok = observed["train"]["max_step"] <= boundaries.train_end_step
    validation_ok = (
        boundaries.train_end_step
        < observed["validation"]["min_step"]
        <= observed["validation"]["max_step"]
        <= boundaries.validation_end_step
    )
    test_ok = observed["test"]["min_step"] > boundaries.validation_end_step
    if not (train_ok and validation_ok and test_ok):
        raise LeakageError(f"Partition steps overlap their boundaries: {observed}")
    return {"passed": True, "observed_steps": observed}


def _separation(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    """Return ROC-AUC and its direction-free form, where 0.5 means no separation."""
    auc = float(roc_auc_score(labels, scores))
    return {"roc_auc": auc, "separation": max(auc, 1.0 - auc)}


def _rate_by_class(flag: pd.Series, labels: pd.Series) -> dict[str, float]:
    return {
        "fraud": float(flag[labels == 1].mean()),
        "legitimate": float(flag[labels == 0].mean()),
    }


def measure_training_signal(
    raw_path: Path, boundaries: SplitBoundaries, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> dict[str, Any]:
    """Measure single-column separation of balances and features on training rows only.

    Rows after the training boundary are dropped before any statistic is computed, so
    this audit does not look at validation or test labels. Categorical features are scored
    by their in-sample fraud rate, which is suitable for this description but not for a model.
    """
    columns = ["step", "type", "amount", "nameDest", *LEAKY_BALANCE_COLUMNS, TARGET_COLUMN]
    training_chunks = []
    for chunk in pd.read_csv(raw_path, usecols=columns, chunksize=chunk_size):
        training_chunks.append(chunk.loc[chunk["step"] <= boundaries.train_end_step])
    train = pd.concat(training_chunks, ignore_index=True)
    labels = train[TARGET_COLUMN]
    label_values = labels.to_numpy()

    balance_signal = {
        column: _separation(label_values, train[column].to_numpy())
        for column in LEAKY_BALANCE_COLUMNS
    }
    origin_error = (train["oldbalanceOrg"] - train["amount"] - train["newbalanceOrig"]).abs()
    destination_error = (train["oldbalanceDest"] + train["amount"] - train["newbalanceDest"]).abs()
    balance_signal["derived_origin_balance_error"] = _separation(
        label_values, origin_error.to_numpy()
    )
    balance_signal["derived_destination_balance_error"] = _separation(
        label_values, destination_error.to_numpy()
    )

    features = engineer_features(raw_to_prediction_inputs(train))
    feature_signal = {}
    for column in FEATURE_COLUMNS:
        if column in CATEGORICAL_FEATURES:
            fraud_rates = label_values_by_category(features[column], labels)
            scores = features[column].astype("object").map(fraud_rates).to_numpy(dtype="float64")
        else:
            scores = features[column].to_numpy(dtype="float64")
        feature_signal[column] = _separation(label_values, scores)

    return {
        "scope": "training partition only",
        "training_rows": len(train),
        "training_fraud_rows": int(labels.sum()),
        "excluded_balance_columns": balance_signal,
        "selected_features": feature_signal,
        "balance_behaviour_rate_by_class": {
            "newbalanceOrig_is_zero": _rate_by_class(train["newbalanceOrig"] == 0, labels),
            "origin_balance_reconciles_exactly": _rate_by_class(
                origin_error <= _BALANCE_MATCH_TOLERANCE, labels
            ),
            "destination_balance_unchanged": _rate_by_class(
                train["oldbalanceDest"] == train["newbalanceDest"], labels
            ),
        },
    }


def label_values_by_category(categories: pd.Series, labels: pd.Series) -> dict[str, float]:
    """Return the mean label for each category value."""
    rates = labels.groupby(categories.astype("object")).mean()
    return {str(key): float(value) for key, value in rates.items()}


def run_leakage_audit(
    raw_path: Path,
    processed_dir: Path,
    boundaries: SplitBoundaries,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    """Run all checks and return a JSON-ready report; a broken hard rule raises LeakageError."""
    return {
        "schema_check": assert_feature_schema_clean(),
        "processed_file_check": assert_processed_files_clean(processed_dir, boundaries),
        "training_signal": measure_training_signal(raw_path, boundaries, chunk_size),
    }
