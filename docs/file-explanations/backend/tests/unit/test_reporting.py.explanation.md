# test_reporting.py

Source: [backend/tests/unit/test_reporting.py](../../../../../backend/tests/unit/test_reporting.py)

## A. File Purpose
Tests that reports show exactly what the results contain, including failed runs.

## B. Why This File Exists
The authorisation forbids adjusting or selectively reporting results. A reporting bug that dropped failures or changed a number would break that rule silently.

## C. Dependencies
- **Libraries:** `csv`, `numpy`, `pytest`.
- **Internal modules:** `app.ml.reporting`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `_metrics`
- **Purpose:** build threshold metrics with known values.
- **Parameters / types:** none. **Returns / type:** `dict`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** nothing. **Used by:** `_run`, chart tests.

### `_run`
- **Purpose:** build a run record, successful or failed.
- **Parameters / types:** `family`, `strategy`, `status`, `pr_auc`. **Returns / type:** `dict`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** `_metrics`. **Used by:** tests.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_matrix_values_mark_a_failed_run_as_missing` | none | A failure is never shown as a score. |
| `test_all_runs_csv_keeps_failures_and_exact_values` | `tmp_path` | The CSV has every run and unrounded values. |
| `test_partitions_are_reported_in_time_order_not_key_order` | none | Tables and charts read train, validation, test. |
| `test_sensitivity_runs_are_all_reported_beside_what_they_changed` | none | Sensitivity runs appear with their reference, and a failed one still appears. `_sensitivity_runs` builds the fixture data. |
| `test_search_table_counts_failed_settings` | none | Failed search settings are counted, not hidden. |
| `test_lightgbm_diagnostic_states_it_was_outside_selection_and_shows_crashes` | none | The diagnostic is labelled, and a crashed fit stays visible. |
| `test_undefined_values_show_as_not_available_not_zero` | none | `n/a` and 0 stay distinct. |
| `test_table_aligns_columns_and_has_a_separator` | none | Markdown is well formed. |
| `test_injection_replaces_only_the_generated_block` | `tmp_path` | Written interpretation is preserved. |
| `test_injection_is_repeatable` | `tmp_path` | Rerunning does not duplicate results. |
| `test_injection_without_markers_is_refused` | `tmp_path` | A wrong document fails clearly. |
| `test_sections_render_under_headings` | none | Heading format. |
| `test_charts_are_written` | `tmp_path` | Charts render without error. |

## E. Classes Explained
None.

## F. Execution Flow
Constructed records go through the reporting functions, and temporary files are read back.

## G. Input and Output
Input: constructed run records. Output: pass or fail.

## H. Important Technical Concepts
These tests cover format and fidelity. Whether a chart reads clearly is judged by looking at it, and the integration test exercises the fuller rendering functions with realistic results.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_reporting.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Add a test for any new table that summarises or filters runs, to confirm that failures remain visible.

## K. Related Files
- [reporting.py](../../app/ml/reporting.py.explanation.md): code under test.
