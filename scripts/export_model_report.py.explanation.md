# export_model_report.py

Source: [scripts/export_model_report.py](export_model_report.py)

## A. File Purpose
Builds `artifacts/metadata/model_v1_report.json`, the data behind the Model Performance page, from saved Phase 2 outputs only.

## B. Why This File Exists
PRD 6.8 asks for a model comparison table, curves, confusion matrices, threshold comparison, timing and experiment history. The Phase 4 authorisation requires these to come exclusively from saved outputs, with no access to `data/`, no retraining and no change to thresholds or frozen results. One script that only copies values makes that easy to check.

## C. Dependencies
- **Libraries:** `argparse`, `csv`, `json`, `sys`, `pathlib`.
- **Internal modules:** `app.ml.pipeline_io` for `sha256_file` and `write_json`. No partition loader, experiment or evaluation code is imported.
- **External services / database:** none. It reads the six files in `SOURCES`.
- **Depended on by:** developers, and `test_model_report.py`.

## D. Every Function Explained

### `read_sources`
Loads every file in `SOURCES`. A missing file raises, so a partial report is never written.

### `source_hashes`
Returns each source's SHA-256, stored in the report so it can be traced.

### `csv_value`
Converts one `all_runs.csv` cell back to a number, keeps text fields as text, and turns empty cells into `None`. `seed` becomes an integer.

### `without_slices`
Drops per-slice breakdowns, which the interface does not show, and keeps every other field unchanged.

### `family_comparison`
Returns one row per family from `selection.json`, holding the best validation run, its interval, its difference from the top family, results at the FPR cap, and timings.

### `experiment_history`
Returns all 125 runs from `all_runs.csv`, with the fields the history table shows.

### `imbalance_matrix`
Returns the 24 family and strategy cells from runs at the `matrix` stage.

### `threshold_section`
Returns the validation threshold analysis: sweep, PRD candidates, rule alternatives and out-of-bag results.

### `confusion_section`
Returns confusion matrices at the frozen threshold from the metrics bundle, with the nested `counts`, overall and by step type.

### `counts`
Nested in `confusion_section`. Picks the four confusion matrix cells from a results dictionary.

### `notes`
Returns statements the page must show. The tie is built from the recorded decision lists, and the rest is fixed text containing no figures.

### `build_report`
Assembles every section, with the model version, threshold and source hashes.

### `main`
Writes the report, or with `--check` returns 1 if the saved report differs from a fresh build.

## E. Classes Explained
None.

## F. Execution Flow
Read sources, hash them, copy sections, then write with sorted keys so the output is byte-for-byte reproducible.

## G. Input and Output
Input: `selection.json`, `all_runs.csv`, `threshold_analysis.json`, `test_evaluation.json`, `lightgbm_diagnostic.json` and `model_v1_metrics.json`. Output: one JSON file of about 268 KB.

## H. Important Technical Concepts
- **Saved test results are not test access.** `test_evaluation.json` records the single evaluation made after the freeze. Copying its curves reads no test data and changes nothing.
- **Pinned hash:** `frozen_model.py` holds the report's SHA-256, and the API refuses to start if the file differs. Rebuilding from the same sources gives the same bytes.
- **No existing file is changed.** The report is a new file.

## I. Example
```powershell
uv run --project backend python scripts/export_model_report.py --check
```

## J. Maintenance Notes
If a source changes, which should not happen for frozen results, rebuild the report and update `MODEL_REPORT_SHA256` in the same commit. Never add a computed metric here. Only copy values.

## K. Related Files
- [model_service.py](../backend/app/services/model_service.py.explanation.md): verifies and serves the report.
- [test_model_report.py](../backend/tests/unit/test_model_report.py.explanation.md): tests.
- [ML_EXPERIMENTS.md](../ML_EXPERIMENTS.md): the results described.
