"""Sparse and normal step definition."""

import inspect

import pandas as pd
import pytest

from app.ml.regimes import (
    NORMAL,
    SPARSE,
    SPARSE_STEP_MAX_ROWS,
    classify_steps,
    row_regime_masks,
    rows_per_step,
)


def test_cutoff_is_strict():
    counts = pd.Series([999, 1000, 1001], index=[1, 2, 3])
    assert classify_steps(counts, 1000).tolist() == [SPARSE, NORMAL, NORMAL]


def test_invalid_cutoff_is_rejected():
    with pytest.raises(ValueError):
        classify_steps(pd.Series([1], index=[1]), 0)


def test_rows_per_step_counts_in_step_order():
    assert rows_per_step(pd.Series([3, 1, 3, 3])).to_dict() == {1: 1, 3: 3}


def test_masks_cover_every_row_exactly_once():
    steps = pd.Series([1, 1, 1, 2, 3, 3])
    masks = row_regime_masks(steps, cutoff=2)
    assert (masks[SPARSE] ^ masks[NORMAL]).all()
    # Step 2 has one row, which is below 2. Steps 1 and 3 are not.
    assert masks[SPARSE].tolist() == [False, False, False, True, False, False]


def test_definition_takes_no_label_input():
    for function in (rows_per_step, classify_steps, row_regime_masks):
        names = inspect.signature(function).parameters
        assert not {"labels", "is_fraud", "fraud", "y"} & set(names)


def test_default_cutoff_matches_phase_1():
    assert SPARSE_STEP_MAX_ROWS == 1000
