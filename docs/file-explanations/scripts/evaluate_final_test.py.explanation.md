# evaluate_final_test.py

Source: [scripts/evaluate_final_test.py](../../../scripts/evaluate_final_test.py)

## A. File Purpose
Runs the single evaluation of the frozen model on the test partition, after checking that the freeze was committed.

## B. Why This File Exists
The authorisation requires the test partition to stay untouched until the model and threshold are frozen. Requiring a commit first creates a dated record of the order of events, which anyone can check with `git log`.

## C. Dependencies
- **Libraries:** `argparse`, `sys`, `pathlib`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.final_evaluation`, `app.ml.model_artifacts`, `app.ml.pipeline_io`.
- **External services / database:** the local `git` command.
- **Depended on by:** the `final-test` target in the `Makefile`.

## D. Every Function Explained

### `main`
- **Purpose:** check the freeze, then run the evaluation.
- **Parameters / types:** none directly; reads `--config`, `--processed-dir`, `--models-dir`, `--metadata` and `--results-dir`.
- **Returns / type:** `int`, the exit code.
- **Internal processing:** checks that freeze files are committed and unchanged, loads the verified model, runs the evaluation and prints the headline results.
- **Error handling:** returns 1 and names the files if the freeze is not committed. `final_evaluation.py` raises if the model is not frozen or if a result already exists.
- **Calls:** `uncommitted_paths`, `load_experiment_config`, `load_model_artifact`, `evaluate_frozen_model`, `current_commit`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Check the commit, load the config and model, evaluate, print.

## G. Input and Output
Input: the frozen model, all partitions. Output: `experiments/results/phase2/test_evaluation.json`.

## H. Important Technical Concepts
**Why Git:** a timestamp in a file can be edited, whereas a commit chain makes altering the order of events far more visible. The file records both the frozen commit and the evaluated commit. This is good evidence, not proof against deliberate tampering.

The script has no `--force` option on purpose. To evaluate again, a person must delete a results file by hand, and that deletion would appear in Git.

## I. Example
```powershell
uv run --project backend python scripts/evaluate_final_test.py
```

## J. Maintenance Notes
After this has run, the test set has been used. Do not change the model or threshold in response to its results under the same version.

## K. Related Files
- [final_evaluation.py](../backend/app/ml/final_evaluation.py.explanation.md): the logic.
- [evaluate_models.py](evaluate_models.py.explanation.md): the freeze.
