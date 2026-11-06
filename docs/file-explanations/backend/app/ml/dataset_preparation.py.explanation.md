# dataset_preparation.py

Source: [backend/app/ml/dataset_preparation.py](../../../../../backend/app/ml/dataset_preparation.py)

## A. File Purpose
Streams the raw CSV into one Parquet file per partition, with engineered features and separated tracking columns, and returns preprocessing metadata. It also loads those partitions back with the label held apart from the features.

## B. Why This File Exists
Phase 2 experiments must all start from identical, leakage-free data. Doing this once and saving the result avoids recomputing features for every run, and records exactly which data every model saw.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `pyarrow`, `hashlib`, `platform`, `dataclasses`, `pathlib`, `typing`.
- **Internal modules:** `app.ml.features`, `app.ml.pipeline_io`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** `scripts/prepare_dataset.py`, `leakage_audit.py` (for `partition_path`), tests, and Phase 2 training.

## D. Every Function Explained

### `partition_path`
- **Purpose:** one definition of partition file names.
- **Parameters / types:** `processed_dir: Path`, `partition: str`.
- **Returns / type:** `Path`, such as `data/processed/train.parquet`.
- **Internal processing / errors:** builds the path; no checks.
- **Calls:** none. **Used by:** this module, `leakage_audit.py`, tests.

### `_build_processed_chunk`
- **Purpose:** create one output chunk.
- **Parameters / types:** `chunk: pd.DataFrame`, `first_row: int`.
- **Returns / type:** `pd.DataFrame` of features plus `is_fraud`, `is_flagged_fraud`, `step`, `source_row`.
- **Internal processing:** computes features through the shared function and attaches tracking columns. `source_row` is the row's position in the raw file.
- **Error handling:** propagates `ValueError` from feature validation.
- **Calls:** `raw_to_prediction_inputs`, `engineer_features`. **Used by:** `_write_partitions`.

### `_new_partition_stats`
- **Purpose:** an empty statistics record.
- **Parameters / types:** none. **Returns / type:** `dict[str, Any]`.
- **Internal processing / errors:** returns zeroed counts; no checks.
- **Calls:** none. **Used by:** `_write_partitions`.

### `_update_partition_stats`
- **Purpose:** add rows to a partition's statistics.
- **Parameters / types:** `stats: dict[str, Any]`, `rows: pd.DataFrame`.
- **Returns / type:** `None`; updates `stats` in place.
- **Internal processing:** counts rows, fraud and rule flags, and widens the step range.
- **Error handling:** none needed. **Calls:** pandas. **Used by:** `_write_partitions`.

### `_write_partitions`
- **Purpose:** the streaming core.
- **Parameters / types:** `raw_path: Path`, `processed_dir: Path`, `boundaries: SplitBoundaries`, `chunk_size: int`.
- **Returns / type:** `dict[str, dict[str, Any]]`, statistics per partition.
- **Internal processing:** reads only `PIPELINE_RAW_COLUMNS`, builds each chunk, applies the masks, appends to each partition's Parquet writer and updates a rolling content hash.
- **Error handling:** `try/finally` closes writers even on failure, so a Parquet file is never left open.
- **Calls:** `_build_processed_chunk`, `partition_masks`, `partition_path`, `_update_partition_stats`. **Used by:** `prepare_dataset`.

### `prepare_dataset`
- **Purpose:** public entry point.
- **Parameters / types:** `raw_path: Path`, `processed_dir: Path`, `config: SplitConfig`, `chunk_size: int`.
- **Returns / type:** `dict[str, Any]` of metadata.
- **Internal processing:** computes boundaries, writes partitions, assembles metadata with versions, hashes and library versions.
- **Error handling:** propagates errors; an incomplete run must not produce metadata.
- **Calls:** `count_rows_per_step`, `compute_boundaries`, `_write_partitions`, `sha256_file`. **Used by:** `scripts/prepare_dataset.py`.

### `load_partition`
- **Purpose:** the only supported way to read a partition.
- **Parameters / types:** `path: Path`.
- **Returns / type:** `PartitionData`.
- **Internal processing:** reads Parquet, restores fixed category orders and separates the columns.
- **Error handling:** propagates read errors. **Calls:** `pyarrow.parquet.read_table`. **Used by:** tests and Phase 2 training.

## E. Classes Explained

### `PartitionData`
- **Responsibility:** keeps the label out of the feature frame, so training code cannot include it by accident.
- **Constructor / attributes:** `features`, `labels`, `rule_flags`, `steps`, `source_rows`.
- **Methods:** none. **Usage:** returned by `load_partition`.

## F. Execution Flow
Count rows per step, compute boundaries, then for each chunk: engineer features, assign partitions, append to files, update statistics and hashes. Finally assemble metadata, which the script saves.

## G. Input and Output
Input: raw CSV, output folder, split config. Output: `data/processed/{train,validation,test}.parquet` (Git-ignored, about 123 MB in total) and the metadata saved to `artifacts/metadata/preprocessing_v1.json` (committed).

## H. Important Technical Concepts
- **Column allow-list at read time:** balances never enter memory here, so a later bug cannot leak them into a file.
- **Content hash, not file hash:** rows are hashed in order. The result does not depend on chunk size or Parquet layout. A test proves this.
- **No timestamps in metadata:** an identical rerun produces byte-identical JSON, which was verified on the real dataset.
- **Rows are never dropped:** every row lands in one partition, verified through `source_row`.
- **`step` is stored but is not a feature:** it enables time-window evaluation in Phase 2.

## I. Example
```python
part = load_partition(partition_path(PROCESSED_DIR, "train"))
part.features.shape, part.labels.sum()  # ((4433703, 7), 3633)
```

## J. Maintenance Notes
Read partitions only through `load_partition`. If output columns change, update `test_real_data.py` and `leakage_audit.py`. Processed files can always be regenerated, so never edit them by hand.

## K. Related Files
- [features.py](features.py.explanation.md), [splitting.py](splitting.py.explanation.md): building blocks.
- [prepare_dataset.py](../../../scripts/prepare_dataset.py.explanation.md): command-line wrapper.
- [test_data_pipeline.py](../../tests/integration/test_data_pipeline.py.explanation.md): tests.
