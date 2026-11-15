# test_models_and_reports.py

Source: [backend/tests/api/test_models_and_reports.py](test_models_and_reports.py)

## A. File Purpose
Tests that frozen Phase 2 results are served unchanged, that reports keep different kinds of information apart, and that settings cannot change the threshold.

## B. Why This File Exists
The authorisation requires preserving the Phase 2 metrics, and documenting the shortfalls. These tests compare API output with the saved files, and fail if the required figures disappear or change.

## C. Dependencies
- **Libraries:** `pytest`, `csv`, `json`, `sqlalchemy`.
- **Internal modules:** `app.core`, `app.models`, API fixtures.
- **External services / database:** PostgreSQL, the frozen model and saved metadata. No test partition is read.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `analyst`
Fixture returning analyst headers.

### `_report`
Downloads a report, checks its headers and parses its rows.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_active_model_is_the_frozen_one` | Version, algorithm, hash, threshold and uncalibrated flag. |
| `test_model_list_has_only_the_frozen_model` | Only one is registered. |
| `test_saved_metrics_are_stored_unchanged_in_the_registry` | `metrics_json` equals the saved file. |
| `test_metrics_endpoint_serves_saved_values_exactly` | Every section equals the saved file, with exact comparison. |
| `test_saved_results_are_the_phase_2_figures` | The saved file holds 0.282%, 45.9%, 40.7%, 21.9%, the confusion matrix and the 0.1% target. |
| `test_performance_notes_state_the_required_shortfalls` | The notes state the missed target and the recall figures. |
| `test_feature_importance_comes_from_saved_results_with_limitations` | Importance equals the saved file, with the causality warning. |
| `test_summary_counts_stored_records` | Each summary figure. |
| `test_summary_of_an_empty_database` | No division by zero. |
| `test_summary_keeps_flags_workflow_and_labels_separate` | A row with a flag, a false alarm status and a contradicting label keeps each count independent. |
| `test_demo_summary_is_labelled_and_separate` | Demo and real figures do not mix. |
| `test_prediction_report` | Prediction export. |
| `test_flag_summary_report` | Flags by type. |
| `test_investigation_report` | Investigation export. |
| `test_model_evaluation_report_matches_saved_values` | The evaluation export equals the saved values, including the target. |
| `test_unknown_report_type_is_refused` | 422. |
| `test_demo_user_cannot_export_reports` | 403. |
| `test_settings_show_everything_prd_lists` | PRD 6.10 fields. |
| `test_admin_can_change_the_boundary_and_it_is_audited` | The change and its audit entry. |
| `test_only_admins_can_change_settings` | 403 for others. |
| `test_threshold_cannot_be_changed_through_settings` | Bad boundaries and any threshold field are refused, and the threshold stays frozen. |
| `test_changing_the_boundary_never_changes_flags_or_stored_rows` | Later decisions and earlier stored rows are unaffected. |

## E. Classes Explained
None.

## F. Execution Flow
`SAVED_METRICS` is read once. Each test compares responses with it.

## G. Input and Output
Input: saved files and HTTP requests. Output: pass or fail.

## H. Important Technical Concepts
- **Queued uploads (Phase 5 M4):** the summary test drains the batch queue after uploading, as a worker would.
- **Exact equality, not approximate.** Results are served, not recalculated, so they should match to the last digit.
- **`test_saved_results_are_the_phase_2_figures` is a tripwire.** It fails if the frozen file is ever altered.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_models_and_reports.py
```

## J. Maintenance Notes
These figures should change only with a new model and a new evaluation.

## K. Related Files
- [metrics_service.py](../../app/services/metrics_service.py.explanation.md): the notes.
- [report_service.py](../../app/services/report_service.py.explanation.md): reports.
- [settings.py route](../../app/api/routes/settings.py.explanation.md): settings.
