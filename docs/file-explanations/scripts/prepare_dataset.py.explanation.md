# prepare_dataset.py

Source: [scripts/prepare_dataset.py](../../../scripts/prepare_dataset.py)

## A. File Purpose
Command-line wrapper that builds the chronological Parquet partitions and saves preprocessing metadata and the feature dictionary.

## B. Why This File Exists
It connects the library to the repository's file layout and versioned config. The library takes explicit paths, which is why tests can run it on a small fixture.

## C. Dependencies
- **Libraries:** `argparse`, `pathlib`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.pipeline_io`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** the `prepare` target in the `Makefile`. `run_eda.py` and `audit_leakage.py` read the metadata it writes.

## D. Every Function Explained

### `main`
- **Purpose:** run preparation from the command line.
- **Parameters / types:** none directly; reads `--input`, `--output-dir`, `--config`, `--metadata` as `Path`.
- **Returns / type:** `None`.
- **Internal processing:** loads the split config, calls the library, writes the metadata and feature dictionary, prints one line per partition.
- **Error handling:** errors propagate with a traceback, so no metadata is written after a failed run.
- **Calls:** `SplitConfig.from_json`, `prepare_dataset`, `write_json`, `feature_dictionary_records`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments, load config, build partitions (about 30 seconds on the development machine), save metadata and dictionary, print summary.

## G. Input and Output
Input: raw CSV and `experiments/experiment-configs/split_v1.json`. Output: `data/processed/*.parquet`, `artifacts/metadata/preprocessing_v1.json`, `artifacts/metadata/feature_dictionary_v1.json`.

## H. Important Technical Concepts
The metadata is committed although the Parquet files are not. It records the source hash and each partition's content hash, so a teammate who regenerates the data can confirm an exact match with `git diff`.

## I. Example
```powershell
uv run --project backend python scripts/prepare_dataset.py
git diff artifacts/metadata/preprocessing_v1.json   # empty means an exact reproduction
```

## J. Maintenance Notes
Run this after any change to `schema.py`, `features.py` or the split config, then rerun the EDA and audit scripts.

## K. Related Files
- [dataset_preparation.py](../backend/app/ml/dataset_preparation.py.explanation.md): the logic.
- [splitting.py](../backend/app/ml/splitting.py.explanation.md): config and boundaries.
