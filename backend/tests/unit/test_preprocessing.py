"""Shared preprocessing: same matrix for every family, and for training and serving."""

import numpy as np
import pandas as pd
import pytest

from app.ml.features import engineer_features
from app.ml.preprocessing import build_preprocessor, compact_features, to_float32
from app.ml.schema import NUMERIC_FEATURES


def sample_features() -> pd.DataFrame:
    inputs = pd.DataFrame(
        {
            "amount": [100.25, 2500.5, 10_000_000.0],
            "transaction_type": ["TRANSFER", "PAYMENT", "CASH_OUT"],
            "step": [1, 30, 700],
            "destination_category": ["customer", "merchant", "customer"],
        }
    )
    return engineer_features(inputs)


def test_output_columns_are_one_hot_then_numeric():
    preprocessor = build_preprocessor().fit(sample_features())
    names = list(preprocessor.get_feature_names_out())
    assert names[:5] == [
        "transaction_type_CASH_IN",
        "transaction_type_CASH_OUT",
        "transaction_type_DEBIT",
        "transaction_type_PAYMENT",
        "transaction_type_TRANSFER",
    ]
    assert names[5:7] == ["destination_category_customer", "destination_category_merchant"]
    assert names[7:] == list(NUMERIC_FEATURES)


def test_output_is_float32():
    assert build_preprocessor().fit_transform(sample_features()).dtype == np.float32


def test_one_hot_encodes_all_categories_even_if_absent_from_fit_rows():
    # DEBIT and CASH_IN are absent here, and their columns must still exist.
    matrix = build_preprocessor().fit_transform(sample_features())
    assert matrix.shape == (3, 12)
    assert matrix[0, 4] == 1.0  # First row is TRANSFER.


def test_serving_float64_matches_training_float32():
    features = sample_features()
    preprocessor = build_preprocessor().fit(compact_features(features))
    from_training_path = preprocessor.transform(compact_features(features))
    from_raw_path = preprocessor.transform(features)
    assert np.array_equal(from_training_path, from_raw_path)


def test_unseen_category_raises():
    preprocessor = build_preprocessor().fit(sample_features())
    tampered = sample_features()
    tampered["transaction_type"] = tampered["transaction_type"].astype(object)
    tampered.loc[0, "transaction_type"] = "BITCOIN"
    with pytest.raises(ValueError):
        preprocessor.transform(tampered)


def test_dropped_features_are_absent():
    preprocessor = build_preprocessor(dropped_features=("amount", "amount_log1p"))
    names = list(preprocessor.fit(sample_features()).get_feature_names_out())
    assert "amount" not in names and "amount_log1p" not in names
    assert "hour_sin" in names


def test_unknown_dropped_feature_raises():
    with pytest.raises(ValueError):
        build_preprocessor(dropped_features=("balance",))


def test_scaling_is_centred_on_fit_rows_only():
    fit_rows = sample_features()
    preprocessor = build_preprocessor(scale_numeric=True).fit(fit_rows)
    centred = preprocessor.transform(fit_rows)[:, 7:]
    assert np.abs(centred.mean(axis=0)).max() < 1e-5
    # A later row with a far larger amount must not change the fitted scale.
    other = sample_features().iloc[[0]].copy()
    other["amount"] = 1e9
    assert preprocessor.transform(other)[0, 7] > centred[:, 0].max()


def test_compact_features_leaves_the_input_unchanged():
    features = sample_features()
    compact = compact_features(features)
    assert features["amount"].dtype == "float64"
    assert compact["amount"].dtype == "float32"
    assert list(compact.columns) == list(features.columns)


def test_to_float32_does_not_copy_when_already_float32():
    matrix = np.ones((2, 2), dtype=np.float32)
    assert to_float32(matrix) is matrix
