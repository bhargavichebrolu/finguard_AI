# test_phase2_pipeline.py

Source: [backend/tests/integration/test_phase2_pipeline.py](../../../../../backend/tests/integration/test_phase2_pipeline.py)

## A. File Purpose
Runs the whole Phase 2 flow on small synthetic partitions: baselines, matrix, tuning, sensitivity, stability, freeze and the one-time test evaluation.

## B. Why This File Exists
Each rule in the authorisation depends on the order of events, which unit tests cannot show. This test does not create the test partition until after the freeze, so anything reading it earlier would fail immediately with a missing file.

## C. Dependencies
- **Libraries:** `json`, `subprocess`, `sys`, `numpy`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.drift`, `app.ml.experiment_stages`, `app.ml.experiments`, `app.ml.explainability`, `app.ml.final_evaluation`, `app.ml.model_artifacts`, `app.ml.pipeline_io`, `app.ml.selection`, `app.ml.splitting`, `tests.conftest`.
- **External services / database:** the local `git` command, in a temporary repository.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `workspace`
- **Purpose:** a module-level fixture that runs training and selection once.
- **Parameters / types:** `tmp_path_factory`. **Returns / type:** `dict` of paths and results.
- **Internal processing / errors:** writes train and validation only, then runs all stages and the freeze. A read of the test partition would raise `FileNotFoundError` and fail every test.
- **Calls:** all the stage functions and `freeze_selected_model`. **Used by:** most tests here.

### `_git`
- **Purpose:** run a Git command in a temporary repository.
- **Parameters / types:** `repo: Path`; `*args`. **Returns / type:** `None`.
- **Internal processing / errors:** raises if the command fails. Identity is set per command, so no global setting is touched.
- **Calls:** `subprocess.run`. **Used by:** `test_uncommitted_freeze_files_are_detected`.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_no_test_file_existed_during_selection` | `workspace` | Selection completed without a test file. |
| `test_guard_blocks_test_partition_even_when_the_file_exists` | `workspace`, `tmp_path` | The guard works by name, not by absence. |
| `test_matrix_covers_every_family_and_strategy` | `workspace` | All 24 cells ran. |
| `test_every_recorded_metric_is_present_in_every_successful_run` | `workspace` | Every requested metric and timing is saved. |
| `test_validation_rows_stay_natural_in_every_oversampled_run` | `workspace` | Oversampling grew the training rows only. |
| `test_rolling_folds_fit_on_earlier_rows_only` | `workspace` | Folds move forward in time. |
| `test_sensitivity_runs_cannot_be_selected` | `workspace` | Only planned stages can win. |
| `test_selected_run_is_reproduced_exactly_by_the_refit` | `workspace` | PRD 14.1 reproducibility, by score hash. |
| `test_selected_model_matches_its_family_winner` | `workspace` | The metadata states what was trained on what. |
| `test_frozen_model_loads_and_scores_new_inputs` | `workspace` | The model works from the four inputs alone. |
| `test_final_evaluation_runs_once_and_never_changes_the_threshold` | `workspace` | Single use, frozen threshold, all report sections. |
| `test_unfrozen_model_is_refused` | `tmp_path` | A draft model cannot open the test set. |
| `test_uncommitted_freeze_files_are_detected` | `tmp_path` | Untracked, committed and modified files are told apart. |
| `test_all_saved_scores_stay_in_range` | `workspace` | PRD 14.1 probability range, across all runs. |
| `test_reports_render_from_stage_outputs_and_match_the_results` | `workspace`, `load_script`, `monkeypatch` | `export_metrics.py` runs end to end on real stage outputs: all sections and charts exist, figures match saved results, and written text outside the generated block is kept. |

## E. Classes Explained
None.

## F. Execution Flow
The fixture runs once for the module. `test_final_evaluation_runs_once_and_never_changes_the_threshold` then creates the test file and runs the evaluation. Test order matters only in that the test-file check reads state before this one writes it, which pytest's file order guarantees.

## G. Input and Output
Input: synthetic partitions written to a temporary folder. Output: pass or fail.

## H. Important Technical Concepts
Proving absence is hard to do by inspection, so this test creates a situation in which a violation cannot succeed.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_phase2_pipeline.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
This fits about 70 small models, so it takes longer than other tests. Keep models in `small_experiment_config` small, but do not remove stages.

## K. Related Files
- [experiment_stages.py](../../app/ml/experiment_stages.py.explanation.md), [selection.py](../../app/ml/selection.py.explanation.md), [final_evaluation.py](../../app/ml/final_evaluation.py.explanation.md): code under test.
