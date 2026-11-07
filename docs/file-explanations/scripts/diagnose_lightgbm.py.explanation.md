# diagnose_lightgbm.py

Source: [scripts/diagnose_lightgbm.py](../../../scripts/diagnose_lightgbm.py)

## A. File Purpose
Command-line wrapper that finds out why LightGBM collapsed in the imbalance matrix on two strategies.

## B. Why This File Exists
In the matrix, LightGBM's PR-AUC collapsed on the original distribution and with class weighting, while the other tree models held. Tuning kept only each family's best strategy, so those two strategies never met any other settings. Without this check, the matrix could be misread as showing that class weighting fails and SMOTE rescues LightGBM. It was added after the results were seen, so it is labelled as a diagnostic and is not eligible for selection.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `pathlib`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.pipeline_io`.
- **External services / database:** none.
- **Depended on by:** the `diagnose` target in the `Makefile`. `export_metrics.py` reads its output.

## D. Every Function Explained

### `main`
- **Purpose:** run the diagnostic and save it.
- **Parameters / types:** none directly; reads `--config`, `--processed-dir` and `--results-dir`.
- **Returns / type:** `None`.
- **Internal processing:** reads LightGBM's tuned settings from `selection.json`, loads train and validation, runs the eight fits, saves the report and prints each cell.
- **Error handling:** a crash inside one fit is recorded in the report. Missing files raise an error with a traceback, so no partial report is saved.
- **Calls:** `load_experiment_config`, `load_development_data`, `run_lightgbm_diagnostic`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Read the config and selection, load the two development partitions, refit eight cells, save.

## G. Input and Output
Input: `experiments_v1.json`, `selection.json`, `train.parquet`, `validation.parquet`. Output: `experiments/results/phase2/lightgbm_diagnostic.json`.

## H. Important Technical Concepts
A confound means two things changed together, so the result cannot tell which one mattered. Here the matrix compared strategies under one fixed setting, so a setting that only fails on some strategies looks like a strategy effect.

`boost_from_average` makes LightGBM start from a score based on the fraud rate. With `scale_pos_weight` near 1,219, the split gains explode within a few trees and training stops. The report records the largest split gain so this divergence can be seen directly.

## I. Example
```powershell
uv run --project backend python scripts/diagnose_lightgbm.py
```

## J. Maintenance Notes
Run it after `evaluate_models.py`, since it reads `selection.json`. Do not use its results to change the selected model: it ran after selection, so that would break the pre-registered rule.

## K. Related Files
- [experiment_stages.py](../backend/app/ml/experiment_stages.py.explanation.md): `run_lightgbm_diagnostic`.
- [reporting.py](../backend/app/ml/reporting.py.explanation.md): `render_lightgbm_diagnostic`.
