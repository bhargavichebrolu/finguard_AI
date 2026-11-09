# test_batches.py

Source: [backend/tests/api/test_batches.py](test_batches.py)

## A. File Purpose
Tests the whole CSV path: upload checks, row validation, processing, labels, error reports, exports, failure handling and recovery.

## B. Why This File Exists
PRD 14.2 requires CSV upload tests, and PRD 6.4 lists many behaviours. Uploads are also the main route for untrusted input, so refusals get as much testing as success.

## C. Dependencies
- **Libraries:** `pytest`, `csv`, `sqlalchemy`.
- **Internal modules:** `app.services.batch_service`, `app.utils.csv_safety`, `app.models`, API fixtures.
- **External services / database:** PostgreSQL and the frozen model. All CSV content is hand-written, and no test partition data is used.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `analyst`, `tmp_uploads`
Fixtures giving analyst headers and pointing uploads at a temporary folder.

### `send`
Posts a file. Parameters: `client`, `headers`, `text`, `name`. Returns the response.

### `finished_job`
Uploads a file, and returns the job's status. `TestClient` runs background tasks before returning, so the job has finished.

### `explode`
Nested stand-in that makes scoring fail, with a fake secret in the message.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_valid_file_is_processed_completely` | Status, counts and progress for a good file. |
| `test_temporary_file_is_deleted_after_processing` | No upload is left on disk. |
| `test_batch_results_match_single_predictions` | Batch and single scores are identical, with version and threshold recorded. |
| `test_flagged_rows_open_investigations_and_get_explanations` | Only flagged rows get these. |
| `test_chunks_commit_progress_across_many_rows` | Files larger than a chunk finish fully. |
| `test_identifier_column_is_optional` | An identifier is generated if there is none. |
| `test_byte_order_mark_and_spaces_are_handled` | Files saved by Excel work. |
| `test_wrong_extension_is_refused` | Only `.csv`, and `.csv.exe` is refused. |
| `test_oversized_file_is_refused_and_removed` | The size limit applies and nothing remains. |
| `test_too_many_rows_are_refused` | The row limit applies and no job is created. |
| `test_bad_files_are_refused` | Empty, wrong headers, repeated columns, no rows, bad encoding and NUL bytes. |
| `test_leaky_columns_are_refused` | Balance and account columns are refused by name. |
| `test_bad_rows_are_reported_and_good_rows_still_processed` | Each kind of bad cell is reported by row and column, and other rows are stored. |
| `test_error_report_does_not_repeat_rejected_values` | Rejected content does not reach the report. |
| `test_identifier_repeated_in_file_is_reported` | The second occurrence fails. |
| `test_identifier_already_stored_is_reported_without_stopping` | An existing identifier does not stop other rows. |
| `test_stored_error_count_is_capped_but_failures_are_all_counted` | Storage is bounded and counts stay true. |
| `test_labels_are_stored_separately_and_do_not_change_scores` | Identical inputs score identically with and without labels, which go to their own table. |
| `test_label_values_are_read_strictly_and_never_affect_scoring` | Valid, blank and invalid labels never stop a row being scored. |
| `test_export_contains_results_and_scores_are_labelled` | Export content, with no label column and no probability wording. |
| `test_upload_needs_permission_and_rate_limit_applies` | 401 without a token, and 429 beyond the limit. |
| `test_missing_file_field_is_refused` | 422 without a file. |
| `test_demo_batches_are_labelled_and_kept_apart` | Separation in both directions, and no investigations. |
| `test_unknown_batch_is_not_found` | 404 on each route. |
| `test_processing_failure_marks_the_job_and_removes_the_file` | The job shows `FAILED`, without internal detail, and the file is gone. |
| `test_restart_recovery_fails_unfinished_jobs_and_removes_files` | Recovery after a restart. |
| `test_safe_cell` | Formula characters are neutralised, and numbers are untouched. |
| `test_csv_lines_neutralise_formulas_and_stream` | Formulas are neutralised and output still streams in pieces (several lines per piece since Phase 5 M2). |
| `test_clean_filename` | Path parts and unsafe characters are removed. |

## E. Classes Explained
None.

## F. Execution Flow
Each test uploads hand-written content, then checks the job, database and files.

## G. Input and Output
Input: CSV text. Output: pass or fail.

## H. Important Technical Concepts
- **`monkeypatch` on settings** lets tests use small limits, and it restores them afterwards.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_batches.py
```

## J. Maintenance Notes
A new upload rule needs a case in `test_bad_files_are_refused` or `test_bad_rows_are_reported_and_good_rows_still_processed`.

## K. Related Files
- [batch_service.py](../../app/services/batch_service.py.explanation.md): the logic.
- [csv_safety.py](../../app/utils/csv_safety.py.explanation.md): output safety.
