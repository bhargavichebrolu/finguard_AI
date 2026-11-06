"""Chronological split tests: strict temporal order, whole steps and full coverage."""

import json

import pandas as pd
import pytest

from app.ml.splitting import (
    SplitBoundaries,
    SplitConfig,
    compute_boundaries,
    count_rows_per_step,
    partition_masks,
)


def uniform_counts(steps: int = 100, rows: int = 10) -> pd.Series:
    return pd.Series(rows, index=range(1, steps + 1), dtype="int64")


def test_boundaries_follow_cumulative_row_share():
    config = SplitConfig("v", 0.7, 0.15)
    boundaries = compute_boundaries(uniform_counts(), config)
    assert boundaries == SplitBoundaries(1, 70, 85, 100)


def test_boundaries_reflect_rows_not_step_numbers():
    # 70% of 10,900 rows is 7,630: seven 1,000-row steps fit and an eighth would exceed it.
    counts = pd.Series([1000] * 10 + [10] * 90, index=range(1, 101), dtype="int64")
    boundaries = compute_boundaries(counts, SplitConfig("v", 0.7, 0.15))
    assert boundaries.train_end_step == 7


def test_boundary_includes_a_step_landing_exactly_on_the_share():
    # 0.6 + 0.3 is 0.8999999999999999 in floating point, while the cumulative share is 0.9.
    counts = pd.Series([50, 20, 20, 10], index=[1, 2, 3, 4], dtype="int64")
    boundaries = compute_boundaries(counts, SplitConfig("v", 0.6, 0.3))
    assert boundaries.train_end_step == 1
    assert boundaries.validation_end_step == 3


@pytest.mark.parametrize(
    ("train", "validation"), [(0.0, 0.1), (0.7, 0.3), (0.9, 0.2), (1.2, 0.1), (0.7, -0.1)]
)
def test_invalid_fractions_are_rejected(train, validation):
    with pytest.raises(ValueError, match="Fractions"):
        compute_boundaries(uniform_counts(), SplitConfig("v", train, validation))


def test_too_few_steps_is_rejected():
    with pytest.raises(ValueError, match="Too few steps"):
        compute_boundaries(uniform_counts(steps=3), SplitConfig("v", 0.7, 0.15))


def test_first_step_too_large_is_rejected():
    counts = pd.Series([1000, 1, 1, 1], index=[1, 2, 3, 4], dtype="int64")
    with pytest.raises(ValueError, match="first step"):
        compute_boundaries(counts, SplitConfig("v", 0.5, 0.2))


def test_masks_cover_every_row_exactly_once():
    steps = pd.Series(range(1, 101))
    masks = partition_masks(steps, SplitBoundaries(1, 70, 85, 100))
    combined = masks["train"].astype(int) + masks["validation"].astype(int) + masks["test"]
    assert (combined == 1).all()


def test_masks_are_strictly_chronological():
    steps = pd.Series(range(1, 101))
    masks = partition_masks(steps, SplitBoundaries(1, 70, 85, 100))
    assert steps[masks["train"]].max() == 70
    assert steps[masks["validation"]].min() == 71
    assert steps[masks["validation"]].max() == 85
    assert steps[masks["test"]].min() == 86


def test_count_rows_per_step_handles_chunks(raw_csv):
    counts = count_rows_per_step(raw_csv, chunk_size=7)
    assert counts.index.tolist() == list(range(1, 31))
    assert (counts == 20).all()


def test_config_loads_from_json(tmp_path):
    path = tmp_path / "split.json"
    path.write_text(
        json.dumps({"version": "x", "train_row_fraction": 0.6, "validation_row_fraction": 0.2})
    )
    assert SplitConfig.from_json(path) == SplitConfig("x", 0.6, 0.2)


def test_config_missing_key_raises(tmp_path):
    path = tmp_path / "split.json"
    path.write_text(json.dumps({"version": "x"}))
    with pytest.raises(KeyError):
        SplitConfig.from_json(path)
