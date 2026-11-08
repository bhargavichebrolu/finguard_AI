# test_real_models.py

Source: [backend/tests/integration/test_real_models.py](../../../../../backend/tests/integration/test_real_models.py)

## A. File Purpose
Checks the real Phase 2 results and model against the rules they must satisfy. Each test is skipped until the output it needs exists.

## B. Why This File Exists
Synthetic tests show the code is correct. These show that the saved results really came from that code, with the right partitions and in the right order. They also recalculate key figures from the saved model.

## C. Dependencies
- **Libraries:** `json`, `subprocess`, `numpy`, `pytest`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.experiments`, `app.ml.model_artifacts`, `app.ml.pipeline_io`, `app.ml.preprocessing`, `app.ml.reporting`.
- **External services / database:** the local `git` command.
- **Depended on by:** none; run by pytest. The `real_data` marker excludes these from CI.

## D. Every Function Explained

### `load_result`
- **Purpose:** read a results file, or skip the test if it is absent.
- **Parameters / types:** `name: str`. **Returns / type:** `dict`.
- **Internal processing / errors:** calls `pytest.skip`.
- **Calls:** `json`. **Used by:** most tests.

### `load_metadata`
- **Purpose:** read model metadata, or skip the test if it is absent.
- **Parameters / types:** none. **Returns / type:** `dict`.
- **Internal processing / errors:** calls `pytest.skip`.
- **Calls:** `json`. **Used by:** model tests.

### `commits_touching`, `is_ancestor`
Git helpers. `commits_touching` lists the commits that changed a file, newest first. `is_ancestor` says whether one commit came before another. `FREEZE_FILES` names the three files that fix the model and threshold.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError`. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_all_24_matrix_cells_were_attempted_and_recorded` | none | No cell was dropped. |
| `test_every_validation_run_fitted_train_and_scored_natural_validation` | none | Every run used the expected rows, with natural class counts. |
| `test_oversampling_added_rows_only_to_the_data_being_fitted` | none | Row counts add up in every run. |
| `test_rolling_folds_stay_inside_training` | none | Folds never reach validation. |
| `test_no_result_is_implausibly_good_without_balances` | none | A leakage alarm. |
| `test_frozen_file_matches_recorded_hash_and_loads` | none | The saved model is the recorded one. |
| `test_frozen_model_reproduces_recorded_validation_results` | none | Validation results recalculate exactly from the saved file. |
| `test_selection_used_the_configured_rule_and_reports_every_family` | none | No family disappears from the report. |
| `test_test_evaluation_used_the_frozen_model_and_threshold` | none | Test used the frozen hash and threshold, and every test row. |
| `test_test_results_can_be_recalculated_from_the_saved_model` | none | Test figures recalculate from the saved file. |
| `test_freeze_commit_precedes_the_test_evaluation` | none | Git order: every freeze file was committed before test was opened. |
| `test_freeze_files_have_not_changed_since_they_were_committed` | none | Each freeze file has exactly one commit, so nothing was revised after seeing test results. |
| `test_rule_commit_precedes_all_results` | none | Git order: rule before results. |
| `test_documentation_tables_match_the_saved_results` | none | Tables in `ML_EXPERIMENTS.md` match the results files. |
| `test_scores_are_not_constant` | none | The model produces varied scores. |

### `require_model_file`
Skips the test when the frozen model binary is absent, as in a clean clone or CI, where it is not stored in Git. Added in Phase 5 M1: three tests previously failed instead of skipping.

### `require_partition`
Skips the test when a processed partition is absent, since the dataset is not in Git.

## E. Classes Explained
None.

## F. Execution Flow
Each test loads what it needs. Those that recalculate figures load the model and a partition.

## G. Input and Output
Input: the real results, model and partitions. Output: pass, fail or skip.

## H. Important Technical Concepts
**Recalculating test figures reads the test partition.** That happens only after the single evaluation, and only reproduces its numbers from the frozen model, so it cannot influence anything. Before the evaluation exists, `load_result` skips the test without opening the file.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_real_models.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
A new model version needs its row counts and rule values reviewed here. Treat a failure of the leakage alarm as a serious finding, not a threshold to raise.

## K. Related Files
- [test_phase2_pipeline.py](test_phase2_pipeline.py.explanation.md): the same rules on synthetic data.
- [test_real_data.py](test_real_data.py.explanation.md): real data pipeline outputs.
