"""Feature engineering tests, including the guarantees training and serving rely on."""

import math

import pandas as pd
import pytest

from app.ml.features import (
    destination_category_from_account,
    engineer_features,
    raw_to_prediction_inputs,
)
from app.ml.schema import FEATURE_COLUMNS, LEAKY_BALANCE_COLUMNS, RULE_FLAG_COLUMN, TARGET_COLUMN


def make_inputs(**overrides) -> pd.DataFrame:
    values = {
        "amount": [100.0],
        "transaction_type": ["TRANSFER"],
        "step": [25],
        "destination_category": ["customer"],
    }
    values.update(overrides)
    return pd.DataFrame(values)


def test_output_has_exact_columns_in_schema_order(raw_frame):
    features = engineer_features(raw_to_prediction_inputs(raw_frame))
    assert list(features.columns) == list(FEATURE_COLUMNS)
    assert len(features) == len(raw_frame)


def test_hour_wraps_at_24():
    features = engineer_features(make_inputs(step=[0, 23, 24, 25, 743],
                                             amount=[1.0] * 5,
                                             transaction_type=["DEBIT"] * 5,
                                             destination_category=["customer"] * 5))
    assert features["hour_of_day"].tolist() == [0, 23, 0, 1, 23]


def test_cyclical_encoding_places_hour_on_the_unit_circle():
    features = engineer_features(make_inputs(step=[6]))
    assert features["hour_sin"].iloc[0] == pytest.approx(1.0)
    assert features["hour_cos"].iloc[0] == pytest.approx(0.0, abs=1e-12)


def test_amount_log_transform_handles_zero():
    features = engineer_features(make_inputs(amount=[0.0]))
    assert features["amount_log1p"].iloc[0] == 0.0
    features = engineer_features(make_inputs(amount=[math.e - 1]))
    assert features["amount_log1p"].iloc[0] == pytest.approx(1.0)


def test_labels_and_balances_cannot_change_features(raw_frame):
    baseline = engineer_features(raw_to_prediction_inputs(raw_frame))
    tampered = raw_frame.copy()
    tampered[TARGET_COLUMN] = 1 - tampered[TARGET_COLUMN]
    tampered[RULE_FLAG_COLUMN] = 1
    tampered["nameOrig"] = "C0"
    for column in LEAKY_BALANCE_COLUMNS:
        tampered[column] = -1.0
    pd.testing.assert_frame_equal(
        baseline, engineer_features(raw_to_prediction_inputs(tampered))
    )


def test_extra_input_columns_are_ignored():
    with_extra = make_inputs(isFraud=[1], oldbalanceOrg=[9.0])
    pd.testing.assert_frame_equal(
        engineer_features(make_inputs()), engineer_features(with_extra)
    )


def test_single_row_matches_the_same_row_in_a_batch(raw_frame):
    inputs = raw_to_prediction_inputs(raw_frame)
    batch = engineer_features(inputs)
    single = engineer_features(inputs.iloc[[37]])
    pd.testing.assert_frame_equal(batch.iloc[[37]], single)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"amount": [-1.0]}, "negative"),
        ({"step": [-1]}, "negative"),
        ({"amount": [None]}, "Null"),
        ({"transaction_type": ["WIRE"]}, "Unknown transaction types"),
        ({"destination_category": ["bank"]}, "Unknown destination categories"),
    ],
)
def test_invalid_inputs_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        engineer_features(make_inputs(**overrides))


def test_missing_input_column_is_rejected():
    with pytest.raises(ValueError, match="Missing prediction input columns"):
        engineer_features(make_inputs().drop(columns=["step"]))


def test_destination_category_mapping():
    accounts = pd.Series(["C123", "M456"])
    assert destination_category_from_account(accounts).tolist() == ["customer", "merchant"]


def test_unknown_destination_prefix_is_rejected():
    with pytest.raises(ValueError, match="Unrecognised destination"):
        destination_category_from_account(pd.Series(["X123"]))
