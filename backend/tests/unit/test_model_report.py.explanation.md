# test_model_report.py

Source: [backend/tests/unit/test_model_report.py](test_model_report.py)

## A. File Purpose
Tests that the model report is copied faithfully from saved Phase 2 outputs, and that its generator touches nothing else.

## B. Why This File Exists
The authorisation requires the report to come exclusively from saved outputs, without `data/`, retraining or changed results. These tests check both the values and the code.

## C. Dependencies
- **Libraries:** `pytest`, `ast`, `csv`, `json`.
- **Internal modules:** `app.core.frozen_model`, `app.ml.pipeline_io`, and `scripts/export_model_report.py` through `load_script`.
- **External services / database:** none. It reads saved result files.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `report`, `saved`
Module fixtures holding the committed report and the saved sources.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_committed_report_matches_the_pinned_hash` | The file matches the hash the API checks. |
| `test_rebuilding_from_sources_gives_the_committed_report` | The report is reproducible and current. |
| `test_recorded_source_hashes_match_the_files` | Its sources are the committed ones. |
| `test_sources_are_saved_results_only` | Every source is a saved result, and none is under `data/` or a Parquet file. |
| `test_script_imports_no_data_loader_and_mentions_no_data_folder` | A source scan finds no partition loader, experiment code, pandas or `data` path. |
| `test_family_rows_copy_selection_values` | Comparison rows equal `selection.json`. |
| `test_curves_are_copied_exactly` | Validation and test curves are identical to the saved ones. |
| `test_history_has_every_run_with_its_values` | All 125 runs, in order. |
| `test_matrix_has_the_24_recorded_cells` | The imbalance matrix is complete. |
| `test_confusion_matrices_match_the_metrics_bundle` | Test counts equal the frozen bundle. |
| `test_threshold_section_matches_the_analysis` | Threshold values are copied. |
| `test_notes_state_the_tie_and_the_single_test_evaluation` | The required statements are present. |
| `test_check_mode_detects_a_stale_report` | `--check` fails on a stale file. |

## E. Classes Explained
None.

## F. Execution Flow
Fixtures load files once. Tests compare sections.

## G. Input and Output
Input: saved files. Output: pass or fail.

## H. Important Technical Concepts
- **A source scan cannot prove everything,** but together with the source list check and the value comparisons it leaves little room for an undeclared input.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_model_report.py
```

## J. Maintenance Notes
A new report section needs a comparison test here.

## K. Related Files
- [export_model_report.py](../../../scripts/export_model_report.py.explanation.md): the generator.
- [model_service.py](../../app/services/model_service.py.explanation.md): the start-up check.
