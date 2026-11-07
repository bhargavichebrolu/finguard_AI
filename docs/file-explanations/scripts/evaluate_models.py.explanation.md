# evaluate_models.py

Source: [scripts/evaluate_models.py](../../../scripts/evaluate_models.py)

## A. File Purpose
Applies the pre-registered selection rule on validation evidence, then freezes the model and threshold.

## B. Why This File Exists
PRD 13 names this script. Keeping selection separate from the test evaluation makes the order clear: first freeze and commit, then open the test set.

## C. Dependencies
- **Libraries:** `argparse`, `pathlib`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.experiments`, `app.ml.pipeline_io`, `app.ml.selection`.
- **External services / database:** the local `git` command, through `current_commit`.
- **Depended on by:** the `select` target in the `Makefile`. `explain_model.py` and `evaluate_final_test.py` read its output.

## D. Every Function Explained

### `main`
- **Purpose:** run the selection.
- **Parameters / types:** none directly; reads `--config`, `--processed-dir`, `--results-dir`, `--scores-dir`, `--models-dir`, `--metadata` and `--preprocessing`.
- **Returns / type:** `None`.
- **Internal processing:** loads train and validation, calls `freeze_selected_model`, and prints each decision.
- **Error handling:** errors propagate. Missing inputs from earlier stages raise `FileNotFoundError`.
- **Calls:** `load_experiment_config`, `load_development_data`, `RunStore`, `freeze_selected_model`, `current_commit`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Load, select, refit, set the threshold, save, print.

## G. Input and Output
Input: results from `train_models.py`. Output: `selection.json`, `threshold_analysis.json`, `artifacts/models/fraud_detector_v1/model.joblib`, `artifacts/metadata/model_v1.json`.

## H. Important Technical Concepts
The script takes no threshold or family as an argument, so neither can be chosen by hand. It is the rule's output or nothing. Rerunning it before the freeze commit gives the same selection and threshold when the refit is deterministic, which `refit_matches_recorded_run` reports.

## I. Example
```powershell
uv run --project backend python scripts/evaluate_models.py
```

## J. Maintenance Notes
Commit the outputs before running `evaluate_final_test.py`, which refuses to start otherwise.

## K. Related Files
- [selection.py](../backend/app/ml/selection.py.explanation.md): the logic.
- [evaluate_final_test.py](evaluate_final_test.py.explanation.md): the next step.
