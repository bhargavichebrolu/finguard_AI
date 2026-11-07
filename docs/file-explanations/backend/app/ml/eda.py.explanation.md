# eda.py

Source: [backend/app/ml/eda.py](../../../../../backend/app/ml/eda.py)

## A. File Purpose
Computes exploratory statistics in one streaming pass and renders four charts to files.

## B. Why This File Exists
PRD 4.5 requires EDA. Using a tested module rather than a notebook makes results reproducible and lets the code enforce a boundary: anything that could influence feature choices comes from training rows only.

## C. Dependencies
- **Libraries:** `matplotlib`, `numpy`, `pandas`, `pathlib`, `typing`.
- **Internal modules:** `app.ml.features` (`HOURS_PER_DAY`), `app.ml.pipeline_io`, `app.ml.regimes` (`SPARSE_STEP_MAX_ROWS`), `app.ml.schema` (`SIMULATOR_AMOUNT_CAP`), `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** `scripts/run_eda.py`, `test_data_pipeline.py`.

## D. Every Function Explained

### `compute_eda`
- **Purpose:** build the whole summary.
- **Parameters / types:** `raw_path: Path`, `boundaries: SplitBoundaries`, `chunk_size: int`.
- **Returns / type:** `dict[str, Any]` with `whole_dataset` and `training_partition`.
- **Internal processing:** adds per-step counts for all rows; for training rows only, adds counts by type and hour, amount histograms for TRANSFER and CASH_OUT by class, simulator-cap counts and whole-number counts.
- **Error handling:** raises `ValueError` for a file without rows.
- **Calls:** `partition_masks`, `_add_counts`, `_partition_summary`. **Used by:** `scripts/run_eda.py`, tests.

### `_add_counts`
- **Purpose:** add one chunk's per-step counts to a running total.
- **Parameters / types:** `total: pd.Series | None`, `counts: pd.Series`.
- **Returns / type:** `pd.Series`.
- **Internal processing / errors:** index-aligned addition, treating a missing step as 0; no special errors.
- **Calls:** pandas. **Used by:** `compute_eda`.

### `_partition_summary`
- **Purpose:** summarise each partition from per-step counts.
- **Parameters / types:** `rows_per_step: pd.Series`, `fraud_per_step: pd.Series`, `boundaries: SplitBoundaries`.
- **Returns / type:** `dict[str, dict[str, Any]]`.
- **Internal processing:** computes rows, fraud, prevalence, means per step, and low-volume figures using `SPARSE_STEP_MAX_ROWS` from `regimes.py`, so that EDA and Phase 2 share one definition.
- **Error handling:** none; boundaries guarantee non-empty partitions.
- **Calls:** `partition_masks`. **Used by:** `compute_eda`.

### `_style_axis`
- **Purpose:** apply one recessive axis style.
- **Parameters / types:** `axis: plt.Axes`, `ylabel: str`. **Returns / type:** `None`.
- **Internal processing / errors:** hides top and right spines and sets a light grid; no errors expected.
- **Calls:** matplotlib. **Used by:** all plot functions.

### `_save`
- **Purpose:** apply the title, write the PNG and free the figure.
- **Parameters / types:** `figure: plt.Figure`, `title: str`, `path: Path`. **Returns / type:** `None`.
- **Internal processing:** left-aligned title; saved at 150 DPI on white.
- **Error handling:** lets `OSError` propagate.
- **Calls:** matplotlib. **Used by:** all plot functions.

### `_plot_volume_and_fraud`, `_plot_types`, `_plot_hours`, `_plot_amounts`
- **Purpose:** one chart each: rows and fraud by step with partition boundaries; rows and fraud rate by type; class share by hour; class share by amount.
- **Parameters / types:** `summary: dict[str, Any]`, `out_dir: Path`.
- **Returns / type:** `Path` of the written PNG.
- **Internal processing:** read only from `summary`, so charts always match the saved numbers. `_plot_volume_and_fraud` uses two panels rather than two y-axes because the scales differ.
- **Error handling:** lets matplotlib and file errors propagate.
- **Calls:** `_style_axis`, `_save`. **Used by:** `render_eda_figures`.

### `render_eda_figures`
- **Purpose:** public chart entry point.
- **Parameters / types:** `summary: dict[str, Any]`, `out_dir: Path`.
- **Returns / type:** `list[Path]`.
- **Internal processing / errors:** creates the folder and calls each plot; no special handling.
- **Calls:** the four plot functions. **Used by:** `scripts/run_eda.py`, tests.

## E. Classes Explained
None.

## F. Execution Flow
`compute_eda` reads the file once, and the script saves the summary. `render_eda_figures` then draws from that summary alone.

## G. Input and Output
Input: raw CSV and boundaries. Output: `experiments/results/eda_summary.json` and four PNGs in `experiments/figures/eda/`.

## H. Important Technical Concepts
- **Scope boundary:** validation and test rows contribute only volume and label counts, which are needed to describe the split. Feature behaviour by hour, type and amount comes from training rows only, and a test checks this.
- **Low-volume steps:** steps with fewer than 1,000 rows. Train has 139, validation 15 and test 246. About 11% to 15% of rows in these steps are fraud, compared with under 0.1% overall in train. This is the key shift documented in `ML_EXPERIMENTS.md`.
- **Chart colours:** blue and orange passed a colour-vision-deficiency separation check. An earlier slate colour failed its chroma check. Red and amber stay reserved for status in the app.

## I. Example
```python
summary = compute_eda(RAW_CSV_PATH, boundaries)
summary["whole_dataset"]["partitions"]["test"]["fraud_rate"]  # 0.0042
render_eda_figures(summary, EDA_FIGURES_DIR)
```

## J. Maintenance Notes
Add a statistic to the correct scope section, and never compute feature behaviour on later partitions. Chart titles state a finding, so recheck them if the split changes. Keep chart functions reading only from `summary`.

## K. Related Files
- [run_eda.py](../../../scripts/run_eda.py.explanation.md): command-line wrapper.
- [splitting.py](splitting.py.explanation.md): partition definitions.
- `DATASET_DOCUMENTATION.md`: findings in prose.
