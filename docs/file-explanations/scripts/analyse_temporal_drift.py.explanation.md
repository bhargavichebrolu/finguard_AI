# analyse_temporal_drift.py

Source: [scripts/analyse_temporal_drift.py](../../../scripts/analyse_temporal_drift.py)

## A. File Purpose
Command-line wrapper that measures prevalence shift and sparse-step behaviour before any model is fitted.

## B. Why This File Exists
The authorisation asks for an investigation of the temporal prevalence shift. Doing it first means it can inform how results are read, without being influenced by them. It keeps the test file closed: test appears only through per-step counts that Phase 1 already published.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `pathlib`.
- **Internal modules:** `app.ml.drift`, `app.ml.experiment_stages`, `app.ml.pipeline_io`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** the `drift` target in the `Makefile`. `export_metrics.py` reads its output.

## D. Every Function Explained

### `main`
- **Purpose:** run the analysis.
- **Parameters / types:** none directly; reads `--config`, `--eda-summary`, `--metadata`, `--processed-dir` and `--output`.
- **Returns / type:** `None`.
- **Internal processing:** builds the count-based report, loads train and validation, adds their feature drift, saves the report and prints a summary.
- **Error handling:** errors propagate with a traceback, so no partial report is saved.
- **Calls:** `build_prevalence_report`, `feature_drift`, `load_development_data`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Read the config, EDA report and boundaries; build the report; add feature drift; save.

## G. Input and Output
Input: `eda_summary.json`, `preprocessing_v1.json`, `train.parquet`, `validation.parquet`. Output: `experiments/results/phase2/temporal_drift.json`.

## H. Important Technical Concepts
Test feature values are deliberately left out here. They are added by `final_evaluation.py` after the freeze. A test confirms that this script names no test file.

## I. Example
```powershell
uv run --project backend python scripts/analyse_temporal_drift.py
```

## J. Maintenance Notes
Run it after `run_eda.py`, since it reads that report. Do not add test feature values here.

## K. Related Files
- [drift.py](../backend/app/ml/drift.py.explanation.md): the analysis.
- [final_evaluation.py](../backend/app/ml/final_evaluation.py.explanation.md): completes it for test.
