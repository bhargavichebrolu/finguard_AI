"""Model input preparation, shared by training and serving.

Features leave engineer_features as a mixed table. This module turns them into the numeric
matrix every model family receives, so comparisons run on identical inputs. It imports no
training library, because the saved model refers to it and the API must be able to load it.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from app.ml.schema import (
    CATEGORICAL_FEATURES,
    DESTINATION_CATEGORIES,
    NUMERIC_FEATURES,
    TRANSACTION_TYPES,
)

_CATEGORY_ORDERS = {
    "transaction_type": list(TRANSACTION_TYPES),
    "destination_category": list(DESTINATION_CATEGORIES),
}


def to_float32(matrix: np.ndarray) -> np.ndarray:
    """Cast to float32, the precision every family trains on. Importable, so it can be saved."""
    return np.asarray(matrix, dtype=np.float32)


def compact_features(features: pd.DataFrame) -> pd.DataFrame:
    """Return the same table with float32 numeric columns, which halves training memory."""
    compact = features.copy(deep=False)
    for column in NUMERIC_FEATURES:
        compact[column] = features[column].astype("float32")
    return compact


def build_preprocessor(
    scale_numeric: bool = False, dropped_features: tuple[str, ...] = ()
) -> Pipeline:
    """Build the step that one-hot encodes categories and passes numeric features.

    Category lists are fixed rather than learned, so an unseen category raises an error instead
    of silently becoming all zeros. Scaling is fitted from the rows it is given, which are
    always training rows. The final float32 cast makes served values identical to trained ones.
    """
    unknown = set(dropped_features) - {*CATEGORICAL_FEATURES, *NUMERIC_FEATURES}
    if unknown:
        raise ValueError(f"Cannot drop unknown features: {sorted(unknown)}")

    categorical = [name for name in CATEGORICAL_FEATURES if name not in dropped_features]
    numeric = [name for name in NUMERIC_FEATURES if name not in dropped_features]
    columns = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(
                    categories=[_CATEGORY_ORDERS[name] for name in categorical],
                    sparse_output=False,
                    dtype=np.float32,
                ),
                categorical,
            ),
            ("numeric", StandardScaler() if scale_numeric else "passthrough", numeric),
        ],
        sparse_threshold=0.0,
        verbose_feature_names_out=False,
    )
    cast = FunctionTransformer(to_float32, feature_names_out="one-to-one")
    return Pipeline([("columns", columns), ("float32", cast)])
