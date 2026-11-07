"""Label-independent definition of sparse and normal simulation steps.

A step's regime depends only on how many rows it holds. No label is read, so the definition
cannot be tuned to fraud. It describes a completed step, which a live request cannot know, so
it is an analysis slice and must never become a model feature.
"""

import numpy as np
import pandas as pd

SPARSE = "sparse"
NORMAL = "normal"
REGIMES: tuple[str, ...] = (SPARSE, NORMAL)

# A step with fewer rows than this is sparse. Phase 1 fixed the value from row counts alone.
SPARSE_STEP_MAX_ROWS = 1_000


def rows_per_step(steps: pd.Series) -> pd.Series:
    """Count the rows in each step, ordered by step number."""
    return steps.value_counts().sort_index().astype("int64")


def classify_steps(step_rows: pd.Series, cutoff: int = SPARSE_STEP_MAX_ROWS) -> pd.Series:
    """Map each step number to its regime."""
    if cutoff <= 0:
        raise ValueError(f"cutoff must be positive, got {cutoff}")
    return pd.Series(
        np.where(step_rows.to_numpy() < cutoff, SPARSE, NORMAL), index=step_rows.index, dtype=object
    )


def row_regime_masks(steps: pd.Series, cutoff: int = SPARSE_STEP_MAX_ROWS) -> dict[str, np.ndarray]:
    """Return one boolean row mask per regime for rows of one partition."""
    regime_by_step = classify_steps(rows_per_step(steps), cutoff)
    regimes = steps.map(regime_by_step).to_numpy()
    return {regime: regimes == regime for regime in REGIMES}
