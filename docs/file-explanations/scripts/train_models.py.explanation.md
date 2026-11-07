# train_models.py

Source: [scripts/train_models.py](../../../scripts/train_models.py)

## A. File Purpose
Command-line entry point for the experiment plan, one stage at a time or all of them.

## B. Why This File Exists
PRD 13 names this script. Running stages separately lets a long experiment be inspected as it goes, and resume after an interruption.

## C. Dependencies
- **Libraries:** `argparse`, `pathlib`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.experiments`, `app.ml.pipeline_io`.
- **External services / database:** none.
- **Depended on by:** the `train` target in the `Makefile`. `evaluate_models.py` reads its results.

## D. Every Function Explained

### `main`
- **Purpose:** run the chosen stages.
- **Parameters / types:** none directly; reads `--stage`, `--config`, `--processed-dir`, `--results-dir` and `--scores-dir`.
- **Returns / type:** `None`.
- **Internal processing:** loads the config and the two development partitions, runs the stages in order, and lists any failed runs.
- **Error handling:** individual run failures are recorded and do not stop the others. A stage that cannot start, such as tuning with no matrix results, skips with a message.
- **Calls:** `load_experiment_config`, `load_development_data`, `run_baselines`, `run_matrix`, `run_tuning`, `run_sensitivity`, `run_stability`, `RunStore`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Baselines, then matrix, tuning, sensitivity and stability. Tuning needs the matrix, and the last two need tuning.

## G. Input and Output
Input: `experiments_v1.json`, `train.parquet`, `validation.parquet`. Output: `baselines.json`, `runs.json`, `rolling_folds.json` in `experiments/results/phase2/`, and scores in `experiments/scores/`.

## H. Important Technical Concepts
**Resuming:** a run's id comes from its settings, so a rerun skips what is already recorded, and a changed setting becomes a new run.

**Failures are results:** a run that fails is saved with its error, and is listed at the end.

**No test access:** data arrives through `load_development_data`, which refuses the test partition.

## I. Example
```powershell
uv run --project backend python scripts/train_models.py --stage matrix
```

## J. Maintenance Notes
To redo a run, delete its entry from `runs.json`. Never edit values there by hand.

## K. Related Files
- [experiment_stages.py](../backend/app/ml/experiment_stages.py.explanation.md): the plan.
- [evaluate_models.py](evaluate_models.py.explanation.md): the next step.
