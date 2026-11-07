# reporting.py

Source: [backend/app/ml/reporting.py](../../../../../backend/app/ml/reporting.py)

## A. File Purpose
Draws charts and renders Markdown tables from saved results. It never fits or scores a model.

## B. Why This File Exists
Every figure in the Phase 2 documentation must come from an executed run. Rendering tables directly from result files removes the chance of copying errors, and means a table cannot show a value that the results do not contain.

## C. Dependencies
- **Libraries:** `csv`, `matplotlib`, `numpy`, `pathlib`.
- **Internal modules:** `app.ml.candidates`, `app.ml.explainability`.
- **External services / database:** none.
- **Depended on by:** `scripts/export_metrics.py`.

## D. Every Function Explained

The plotting functions share one pattern. Each takes saved results and an output location, returns the `Path` it wrote, raises `KeyError` if a report has the wrong shape, and calls `_style_axis` and `_save`. All are used by `export_metrics.py`.

| Function | Parameters | Draws |
|---|---|---|
| `plot_imbalance_matrix` | `runs`, `out_dir` | Heatmap of validation PR-AUC for all 24 cells, labelled in each cell, marking failures. |
| `plot_family_curves` | `selection`, `out_dir` | PR and ROC curves of each family's best run. |
| `plot_threshold_behaviour` | `thresholds`, `out_dir` | Precision, recall and false positive rate against the threshold, marking the selection. |
| `plot_confusion_matrix` | `metrics`, `title`, `path` | One confusion matrix with counts. |
| `plot_regime_comparison` | `selection`, `out_dir` | PR-AUC lift and recall, sparse against normal, by family. |
| `plot_compute_cost` | `selection`, `out_dir` | Training and single-row time by family. |
| `plot_temporal_drift` | `drift`, `out_dir` | Daily rows and fraud rate, with partition boundaries. |
| `plot_sparse_by_hour` | `drift`, `out_dir` | Share of sparse steps per hour, per partition. |
| `plot_shap_summary` | `shap_report`, `out_dir` | Importance by group and by column. |
| `plot_shap_dependence` | `sample_path`, `shap_report`, `out_dir` | Amount and hour contributions against their values. Its nested helper `group_values` sums a group's columns. |
| `plot_test_results` | `test`, `out_dir` | Test and validation curves, plus the test confusion matrix. Returns a list of two paths. |

### `_style_axis`
- **Purpose:** apply one recessive axis style.
- **Parameters / types:** `axis`, `ylabel`, `xlabel`.
- **Returns / type:** `None`.
- **Internal processing:** hides the top and right spines and lightens the grid.
- **Error handling:** none needed.
- **Calls:** matplotlib.
- **Used by:** plotting functions.

### `_save`
- **Purpose:** add a title and write a PNG.
- **Parameters / types:** `figure`, `title`, `path`.
- **Returns / type:** `Path`.
- **Internal processing:** creates the folder, saves at 150 dpi on white, closes the figure.
- **Error handling:** write errors propagate.
- **Calls:** matplotlib.
- **Used by:** plotting functions.

### `_search_runs`
- **Purpose:** index a stage's runs by family and strategy.
- **Parameters / types:** `runs: dict`; `stage: str`.
- **Returns / type:** `dict`.
- **Internal processing:** filters by stage.
- **Error handling:** none needed.
- **Calls:** nothing.
- **Used by:** `_matrix_values`, `render_matrix_tables`.

### `_matrix_values`
- **Purpose:** build the PR-AUC array.
- **Parameters / types:** `runs: dict`.
- **Returns / type:** `np.ndarray`.
- **Internal processing:** fills cells from successful runs.
- **Error handling:** a failed or absent run stays NaN, shown as "failed".
- **Calls:** `_search_runs`.
- **Used by:** `plot_imbalance_matrix`.

### `_fmt`, `_pct`, `_count`, `_table`
Formatting helpers. The first three show `n/a` for a missing value, so an undefined metric never looks like a zero. `_table` builds a Markdown table, with an alignment string such as `lrr`.

### `write_runs_csv`
- **Purpose:** save every run, including failures, as one spreadsheet row.
- **Parameters / types:** `runs: dict`; `path: Path`.
- **Returns / type:** `Path`.
- **Internal processing:** one row per run, with metrics at the 0.50, capped and best-F1 thresholds, and timings.
- **Error handling:** failed runs leave metric cells empty and fill `error`.
- **Calls:** `csv`.
- **Used by:** `export_metrics.py`.

### Rendering functions
All return Markdown text, read only from their arguments, and are used by `export_metrics.py`.

| Function | Renders |
|---|---|
| `render_drift_tables` | Prevalence by partition, sparse and normal steps, decomposition, counterfactual, feature drift. |
| `render_matrix_tables` | Baselines, and the 24-cell matrix by PR-AUC, recall and training time. Its nested helper `pivot` builds one table. |
| `render_comparison_table` | Each family's best run with all requested metrics and costs. |
| `render_stability_table` | Seed variation, rolling folds, paired gap to the top, gate outcome. |
| `render_threshold_tables` | All threshold rules, checks on unseen steps, and reliability. Its nested helper `row` builds one table row. |
| `render_shap_tables` | Importance by group and slice, and the explained examples. |
| `render_test_tables` | The single test evaluation, always next to baselines and validation. |
| `render_results_markdown` | Joins sections under headings. |

### `inject_generated_results`
- **Purpose:** update the generated block of a document.
- **Parameters / types:** `document: Path`; `generated: str`.
- **Returns / type:** `None`.
- **Internal processing:** replaces text between the two markers and leaves the rest unchanged.
- **Error handling:** `ValueError` if the markers are missing.
- **Calls:** nothing.
- **Used by:** `export_metrics.py`.

## E. Classes Explained
None.

## F. Execution Flow
`export_metrics.py` loads results, calls these functions for whatever exists, and writes the outputs.

## G. Input and Output
Input: dictionaries from saved JSON. Output: PNG charts, a CSV and Markdown text.

## H. Important Technical Concepts
**Colour by job:** each family has a fixed categorical colour from a palette checked for colour-vision deficiency, so colour follows the model across charts. Three of the colours fall below 3:1 contrast on white, so the same figures are always given as tables in `ML_EXPERIMENTS.md`. Magnitude uses one blue ramp. Colours are chart-only, so the PRD's status colours keep their meaning.

**One axis per scale:** values with different scales go in separate panels rather than on a second y-axis.

**Log and logit scales:** recall at very low false positive rates and scores near 0 or 1 cannot be seen on a linear scale. Axis labels state the scale.

## I. Example
```python
print(render_matrix_tables(runs, baselines))
plot_imbalance_matrix(runs, Path("experiments/figures/models"))
```

## J. Maintenance Notes
Do not add calculations that aren't in the results: compute them in the experiment code and save them, so they can be traced. Render new charts and look at them before committing.

## K. Related Files
- [export_metrics.py](../../../scripts/export_metrics.py.explanation.md): runs this.
- [test_reporting.py](../../tests/unit/test_reporting.py.explanation.md): tests.
