# splitting.py

Source: [backend/app/ml/splitting.py](../../../../../backend/app/ml/splitting.py)

## A. File Purpose
Defines chronological train, validation and test partitions by simulation step.

## B. Why This File Exists
PRD 5.3 requires earlier data for training and later data for evaluation. Keeping boundary logic in one place means the pipeline, EDA and the audit agree exactly on where each partition starts and ends.

## C. Dependencies
- **Libraries:** `json`, `dataclasses`, `pathlib`, `pandas`.
- **Internal modules:** `app.ml.pipeline_io`.
- **External services / database:** none.
- **Depended on by:** `dataset_preparation.py`, `eda.py`, `leakage_audit.py`, `drift.py`, `experiment_stages.py`, scripts, tests.

## D. Every Function Explained

### `count_rows_per_step`
- **Purpose:** get the row count of each step with minimal memory.
- **Parameters / types:** `path: Path`, `chunk_size: int`.
- **Returns / type:** `pd.Series` indexed by step, sorted, `int64`.
- **Internal processing:** reads only the `step` column in chunks and adds the counts.
- **Error handling:** raises `ValueError` for a file without rows.
- **Calls:** `pandas.read_csv`.
- **Used by:** `prepare_dataset`.

### `compute_boundaries`
- **Purpose:** choose boundaries from row counts alone, never from labels or feature values.
- **Parameters / types:** `rows_per_step: pd.Series`, `config: SplitConfig`.
- **Returns / type:** `SplitBoundaries`.
- **Internal processing:** computes cumulative row share. Each boundary is the last step whose share does not exceed the target plus `_SHARE_TOLERANCE`.
- **Error handling:** raises `ValueError` for invalid fractions, an oversized first step or too few steps.
- **Calls:** pandas cumulative operations.
- **Used by:** `prepare_dataset`.

### `rolling_origin_folds`
- **Purpose:** define forward-in-time folds inside one partition, for Phase 2 stability checks.
- **Parameters / types:** `rows_per_step: pd.Series`; `row_share_anchors: tuple[float, ...]`.
- **Returns / type:** `list[dict[str, int]]`, one per fold, with fit and evaluation step ranges.
- **Internal processing:** each anchor ends a window by cumulative row share. A fold fits up to one anchor and evaluates up to the next, so fitted rows are always earlier.
- **Error handling:** `ValueError` for fewer than two anchors, non-increasing anchors, anchors outside (0, 1], or an empty evaluation window.
- **Calls:** pandas cumulative operations.
- **Used by:** `experiment_stages.run_stability`.

### `partition_masks`
- **Purpose:** assign rows to partitions.
- **Parameters / types:** `steps: pd.Series`, `boundaries: SplitBoundaries`.
- **Returns / type:** `dict[str, pd.Series]` of boolean masks, one per name in `PARTITIONS`.
- **Internal processing:** compares steps with the two inclusive end steps.
- **Error handling:** none needed; every value falls in exactly one range.
- **Calls:** pandas comparisons.
- **Used by:** `dataset_preparation.py`, `eda.py`.

## E. Classes Explained

### `SplitConfig`
- **Responsibility:** versioned split settings.
- **Constructor / attributes:** `version`, `train_row_fraction`, `validation_row_fraction`.
- **Methods:** `from_json(path)` (classmethod) returns a `SplitConfig`; a missing key raises `KeyError`, so a typo cannot silently fall back to a default.
- **Usage:** `scripts/prepare_dataset.py` loads `experiments/experiment-configs/split_v1.json`.

### `SplitBoundaries`
- **Responsibility:** the concrete split.
- **Constructor / attributes:** `first_step`, `train_end_step`, `validation_end_step`, `last_step`.
- **Methods:** none. **Usage:** saved in preprocessing metadata and reloaded by the EDA and audit scripts.

## F. Execution Flow
`prepare_dataset` calls `count_rows_per_step`, then `compute_boundaries`, then `partition_masks` per chunk. Later scripts rebuild `SplitBoundaries` from the saved metadata rather than recomputing it.

## G. Input and Output
Input: rows per step and the config. Output on the real data: train steps 1 to 322, validation 323 to 377, test 378 to 743.

## H. Important Technical Concepts
- **Whole steps only:** rows within a step have no known order, so splitting a step would mix unordered records across partitions.
- **No random seed:** the split has no randomness, which is why PRD 5.3's seed requirement does not apply here. It applies to Phase 2 model training.
- **Base-rate shift is not corrected here:** fraud prevalence differs sharply by partition (0.082%, 0.059%, 0.420%) because volume collapses late in the simulation while fraud stays constant. See `ML_EXPERIMENTS.md` for what this means for evaluation.
- **Floating-point tolerance:** `0.6 + 0.3` evaluates to `0.8999999999999999`. Without `_SHARE_TOLERANCE`, a step landing exactly on the share would be pushed to the next partition. A test caught this.

## I. Example
```python
compute_boundaries(rows_per_step, SplitConfig("v", 0.7, 0.15))
# SplitBoundaries(first_step=1, train_end_step=322, validation_end_step=377, last_step=743)
```

## J. Maintenance Notes
To change the split, add a new config such as `split_v2.json` instead of editing v1, so earlier experiments stay traceable, then rerun preparation and every later stage.

## K. Related Files
- [dataset_preparation.py](dataset_preparation.py.explanation.md): applies the split.
- [test_splitting.py](../../tests/unit/test_splitting.py.explanation.md): tests.
- `experiments/experiment-configs/split_v1.json`: the config.
