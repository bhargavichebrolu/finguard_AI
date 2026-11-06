"""Feature engineering shared by training and live inference.

engineer_features is the only place features are computed. It accepts just the four
prediction inputs, so training cannot use a value that serving will not have.
"""

import numpy as np
import pandas as pd

from app.ml.schema import (
    DESTINATION_CATEGORIES,
    DESTINATION_PREFIX_TO_CATEGORY,
    FEATURE_COLUMNS,
    PREDICTION_INPUT_COLUMNS,
    TRANSACTION_TYPES,
)

HOURS_PER_DAY = 24


def destination_category_from_account(accounts: pd.Series) -> pd.Series:
    """Map PaySim destination identifiers such as C123 or M456 to their category.

    Raises ValueError on an unrecognised prefix instead of guessing a category.
    """
    categories = accounts.astype("string").str[0].map(DESTINATION_PREFIX_TO_CATEGORY)
    if categories.isna().any():
        bad_values = accounts[categories.isna()].head(3).tolist()
        raise ValueError(f"Unrecognised destination account prefix, for example: {bad_values}")
    return categories.astype("object")


def raw_to_prediction_inputs(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert raw PaySim rows into the same four inputs the prediction API receives."""
    return pd.DataFrame(
        {
            "amount": raw["amount"].to_numpy(),
            "transaction_type": raw["type"].astype("object").to_numpy(),
            "step": raw["step"].to_numpy(),
            "destination_category": destination_category_from_account(raw["nameDest"]).to_numpy(),
        },
        index=raw.index,
    )


def _validate_inputs(inputs: pd.DataFrame) -> None:
    """Reject inputs that would otherwise produce silently wrong features."""
    missing = [column for column in PREDICTION_INPUT_COLUMNS if column not in inputs.columns]
    if missing:
        raise ValueError(f"Missing prediction input columns: {missing}")

    frame = inputs[list(PREDICTION_INPUT_COLUMNS)]
    null_columns = frame.columns[frame.isna().any()].tolist()
    if null_columns:
        raise ValueError(f"Null values in prediction input columns: {null_columns}")
    if (frame["amount"] < 0).any():
        raise ValueError("amount must not be negative")
    if (frame["step"] < 0).any():
        raise ValueError("step must not be negative")

    unknown_types = set(frame["transaction_type"].unique()) - set(TRANSACTION_TYPES)
    if unknown_types:
        raise ValueError(f"Unknown transaction types: {sorted(unknown_types)}")
    unknown_categories = set(frame["destination_category"].unique()) - set(DESTINATION_CATEGORIES)
    if unknown_categories:
        raise ValueError(f"Unknown destination categories: {sorted(unknown_categories)}")


def engineer_features(inputs: pd.DataFrame) -> pd.DataFrame:
    """Return model features, in FEATURE_COLUMNS order, from the four prediction inputs.

    Any extra column on `inputs`, including labels or balances, is ignored. The function
    is stateless: one row's result never depends on another row, which keeps single
    predictions and batch predictions identical.
    """
    _validate_inputs(inputs)

    amount = inputs["amount"].astype("float64")
    hour = inputs["step"].astype("int64") % HOURS_PER_DAY
    angle = 2.0 * np.pi * hour / HOURS_PER_DAY

    features = pd.DataFrame(
        {
            "amount": amount,
            "amount_log1p": np.log1p(amount),
            "transaction_type": pd.Categorical(
                inputs["transaction_type"], categories=TRANSACTION_TYPES
            ),
            "destination_category": pd.Categorical(
                inputs["destination_category"], categories=DESTINATION_CATEGORIES
            ),
            "hour_of_day": hour,
            "hour_sin": np.sin(angle),
            "hour_cos": np.cos(angle),
        },
        index=inputs.index,
    )
    return features[list(FEATURE_COLUMNS)]
