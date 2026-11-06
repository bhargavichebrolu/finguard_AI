# run_eda.py

Source: [scripts/run_eda.py](../../../scripts/run_eda.py)

## A. File Purpose
Command-line wrapper that computes the EDA summary and charts using the split boundaries saved in preprocessing metadata.

## B. Why This File Exists
EDA must use the exact boundaries the pipeline used. Reading them from metadata makes disagreement impossible, and it fixes the run order: prepare first, EDA second.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `pathlib`.
- **Internal modules:** `app.ml.eda`, `app.ml.pipeline_io`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** the `eda` target in the `Makefile`.

## D. Every Function Explained

### `main`
- **Purpose:** produce EDA outputs from the command line.
- **Parameters / types:** none directly; reads `--input`, `--metadata`, `--output`, `--figures-dir` as `Path`.
- **Returns / type:** `None`.
- **Internal processing:** loads boundaries from metadata, computes the summary, writes JSON, renders charts.
- **Error handling:** missing metadata raises `FileNotFoundError`; this means `prepare_dataset.py` has not been run.
- **Calls:** `compute_eda`, `write_json`, `render_eda_figures`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments, load boundaries, compute, save, draw, print output paths.

## G. Input and Output
Input: raw CSV and `artifacts/metadata/preprocessing_v1.json`. Output: `experiments/results/eda_summary.json` and four PNGs in `experiments/figures/eda/`. All of these are committed so findings can be reviewed without the dataset.

## H. Important Technical Concepts
Charts are generated from the saved summary rather than from raw data, so a chart cannot show a number the JSON does not contain.

## I. Example
```powershell
uv run --project backend python scripts/run_eda.py
```

## J. Maintenance Notes
No analysis belongs here; add it to `eda.py` so it is tested.

## K. Related Files
- [eda.py](../backend/app/ml/eda.py.explanation.md): the logic.
- [prepare_dataset.py](prepare_dataset.py.explanation.md): must run first.
