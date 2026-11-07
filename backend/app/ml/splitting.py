"""Chronological train, validation and test partitioning by simulation step.

Rows within a step have no known order, so a boundary always falls between steps and one
step is never divided across partitions. There is no randomness, hence no seed is needed:
the same file and config always give the same boundaries.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.ml.pipeline_io import DEFAULT_CHUNK_SIZE

PARTITIONS: tuple[str, ...] = ("train", "validation", "test")
# Absorbs floating-point error such as 0.6 + 0.3 evaluating to 0.8999999999999999.
_SHARE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class SplitConfig:
    """Versioned split settings, loaded from experiments/experiment-configs."""

    version: str
    train_row_fraction: float
    validation_row_fraction: float

    @classmethod
    def from_json(cls, path: Path) -> "SplitConfig":
        """Read a config file; a missing or misspelled key raises KeyError."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=data["version"],
            train_row_fraction=float(data["train_row_fraction"]),
            validation_row_fraction=float(data["validation_row_fraction"]),
        )


@dataclass(frozen=True)
class SplitBoundaries:
    """Inclusive last step of train and validation; test takes every later step."""

    first_step: int
    train_end_step: int
    validation_end_step: int
    last_step: int


def count_rows_per_step(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> pd.Series:
    """Count rows per step, reading only the step column."""
    total: pd.Series | None = None
    for chunk in pd.read_csv(path, usecols=["step"], dtype={"step": "int32"}, chunksize=chunk_size):
        counts = chunk["step"].value_counts()
        total = counts if total is None else total.add(counts, fill_value=0)
    if total is None:
        raise ValueError(f"No rows found in {path}")
    return total.sort_index().astype("int64")


def compute_boundaries(rows_per_step: pd.Series, config: SplitConfig) -> SplitBoundaries:
    """Choose boundaries from row counts alone, never from labels or feature values.

    Each boundary is the last step whose cumulative row share does not exceed the target,
    so the partitions land slightly under the requested fractions.
    """
    train_fraction = config.train_row_fraction
    combined_fraction = train_fraction + config.validation_row_fraction
    if not 0 < train_fraction < combined_fraction < 1:
        raise ValueError(
            "Fractions must satisfy 0 < train < train + validation < 1, "
            f"got {train_fraction} and {config.validation_row_fraction}"
        )

    ordered = rows_per_step.sort_index()
    cumulative_share = ordered.cumsum() / ordered.sum()
    train_steps = cumulative_share[cumulative_share <= train_fraction + _SHARE_TOLERANCE].index
    validation_steps = cumulative_share[
        cumulative_share <= combined_fraction + _SHARE_TOLERANCE
    ].index
    if train_steps.empty:
        raise ValueError("The first step alone exceeds the train fraction")

    train_end = int(train_steps.max())
    validation_end = int(validation_steps.max())
    last_step = int(ordered.index.max())
    if not train_end < validation_end < last_step:
        raise ValueError(
            "Too few steps for three non-empty partitions: "
            f"train_end={train_end}, validation_end={validation_end}, last={last_step}"
        )
    return SplitBoundaries(
        first_step=int(ordered.index.min()),
        train_end_step=train_end,
        validation_end_step=validation_end,
        last_step=last_step,
    )


def rolling_origin_folds(
    rows_per_step: pd.Series, row_share_anchors: tuple[float, ...]
) -> list[dict[str, int]]:
    """Return forward-in-time folds inside one partition, from row counts alone.

    Each anchor ends a fit window, and the next anchor ends the window evaluated. Rows are always
    fitted on earlier steps and evaluated on later ones, which a random k-fold would not respect.
    """
    if len(row_share_anchors) < 2 or list(row_share_anchors) != sorted(set(row_share_anchors)):
        raise ValueError(f"Need at least two increasing anchors, got {row_share_anchors}")
    if not 0 < row_share_anchors[0] or row_share_anchors[-1] > 1:
        raise ValueError(f"Anchors must lie in (0, 1], got {row_share_anchors}")

    ordered = rows_per_step.sort_index()
    cumulative_share = ordered.cumsum() / ordered.sum()
    last_steps = [
        int(cumulative_share[cumulative_share <= anchor + _SHARE_TOLERANCE].index.max())
        for anchor in row_share_anchors
    ]
    folds = []
    for fit_end, evaluation_end in zip(last_steps, last_steps[1:], strict=False):
        if evaluation_end <= fit_end:
            raise ValueError(f"Anchors {row_share_anchors} give an empty evaluation window")
        folds.append(
            {
                "fit_first_step": int(ordered.index.min()),
                "fit_end_step": fit_end,
                "evaluation_first_step": fit_end + 1,
                "evaluation_end_step": evaluation_end,
            }
        )
    return folds


def partition_masks(steps: pd.Series, boundaries: SplitBoundaries) -> dict[str, pd.Series]:
    """Return one boolean mask per partition; every row is in exactly one."""
    return {
        "train": steps <= boundaries.train_end_step,
        "validation": (steps > boundaries.train_end_step)
        & (steps <= boundaries.validation_end_step),
        "test": steps > boundaries.validation_end_step,
    }
