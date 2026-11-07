"""SMOTE and ADASYN in a representation where a synthetic row is a possible transaction.

Running these methods directly on the feature table would break it: interpolating one-hot
columns gives fractions of a transaction type, hour_of_day stops being a whole number, and
amount_log1p stops matching amount. So each type is oversampled separately, on the continuous
values only (log amount and the hour's position on the clock). Every synthetic row then goes
back through engineer_features, which guarantees it obeys the same rules as a real row.

This function may only ever receive training rows. Its one caller is experiments.fit_candidate.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from imblearn.over_sampling import ADASYN, SMOTE
from sklearn.preprocessing import StandardScaler

from app.ml.features import HOURS_PER_DAY, engineer_features
from app.ml.preprocessing import compact_features
from app.ml.schema import TRANSACTION_TYPES

OVERSAMPLING_METHODS: tuple[str, ...] = ("smote", "adasyn")
_LATENT_COLUMNS = ["amount_log1p", "hour_sin", "hour_cos"]


@dataclass
class OversampleResult:
    """Training rows plus appended synthetic fraud rows, and a report of what was generated."""

    features: pd.DataFrame
    labels: np.ndarray
    report: dict[str, Any]


def _build_sampler(method: str, target_ratio: float, k_neighbors: int, seed: int) -> Any:
    """Create the imbalanced-learn sampler for one transaction type."""
    if method == "smote":
        return SMOTE(sampling_strategy=target_ratio, k_neighbors=k_neighbors, random_state=seed)
    if method == "adasyn":
        return ADASYN(sampling_strategy=target_ratio, n_neighbors=k_neighbors, random_state=seed)
    raise ValueError(f"Unknown oversampling method: {method}")


def _reconstruct_rows(
    latent_rows: np.ndarray, transaction_type: str, destination_category: str
) -> pd.DataFrame:
    """Rebuild full feature rows from interpolated values, through the shared feature code."""
    angles = np.arctan2(latent_rows[:, 1], latent_rows[:, 2]) % (2 * np.pi)
    hours = np.rint(angles * HOURS_PER_DAY / (2 * np.pi)).astype("int64") % HOURS_PER_DAY
    inputs = pd.DataFrame(
        {
            "amount": np.maximum(np.expm1(latent_rows[:, 0]), 0.0),
            "transaction_type": transaction_type,
            "step": hours,  # Features use only step modulo 24, so the hour is a valid step.
            "destination_category": destination_category,
        }
    )
    return engineer_features(inputs)


def _synthesise_for_type(
    features: pd.DataFrame,
    labels: np.ndarray,
    method: str,
    target_ratio: float,
    k_neighbors: int,
    seed: int,
) -> pd.DataFrame:
    """Generate synthetic fraud rows for rows that all share one transaction type."""
    latent = features[_LATENT_COLUMNS].to_numpy(dtype="float64")
    scaler = StandardScaler().fit(latent)
    sampler = _build_sampler(method, target_ratio, k_neighbors, seed)
    resampled, _ = sampler.fit_resample(scaler.transform(latent), labels)
    # imbalanced-learn appends new rows after the originals.
    synthetic = scaler.inverse_transform(resampled[latent.shape[0] :])
    fraud_rows = features.loc[labels == 1]
    return _reconstruct_rows(
        synthetic,
        str(fraud_rows["transaction_type"].iloc[0]),
        str(fraud_rows["destination_category"].mode().iloc[0]),
    )


def oversample_training_fold(
    features: pd.DataFrame,
    labels: np.ndarray,
    method: str,
    target_ratio: float,
    k_neighbors: int,
    seed: int,
) -> OversampleResult:
    """Add synthetic fraud rows to a training fold, per transaction type.

    A type with too little fraud to find neighbours is left unchanged and reported. target_ratio
    is the fraud-to-legitimate ratio wanted within each oversampled type.
    """
    labels = np.asarray(labels)
    if labels.size != len(features):
        raise ValueError("features and labels have different lengths")

    transaction_types = features["transaction_type"].astype(object).to_numpy()
    new_frames: list[pd.DataFrame] = []
    by_type: dict[str, dict[str, Any]] = {}
    for offset, transaction_type in enumerate(TRANSACTION_TYPES):
        mask = transaction_types == transaction_type
        fraud = int(np.count_nonzero(labels[mask] == 1))
        legitimate = int(mask.sum()) - fraud
        entry: dict[str, Any] = {"fraud_rows": fraud, "legitimate_rows": legitimate, "added": 0}
        if fraud <= k_neighbors:
            entry["skipped"] = f"fraud rows ({fraud}) do not exceed k_neighbors ({k_neighbors})"
        elif legitimate == 0 or fraud / legitimate >= target_ratio:
            entry["skipped"] = "already at or above the target ratio"
        else:
            frame = _synthesise_for_type(
                features.loc[mask], labels[mask], method, target_ratio, k_neighbors, seed + offset
            )
            entry["added"] = len(frame)
            new_frames.append(compact_features(frame))
        by_type[transaction_type] = entry

    added = sum(len(frame) for frame in new_frames)
    report = {
        "method": method,
        "target_ratio": target_ratio,
        "k_neighbors": k_neighbors,
        "synthetic_rows": added,
        "by_type": by_type,
    }
    if not new_frames:
        return OversampleResult(features, labels, report)
    return OversampleResult(
        pd.concat([features, *new_frames], ignore_index=True),
        np.concatenate([labels, np.ones(added, dtype=labels.dtype)]),
        report,
    )
