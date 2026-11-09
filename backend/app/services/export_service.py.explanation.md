# export_service.py

Source: [backend/app/services/export_service.py](export_service.py)

## A. File Purpose
Streams stored predictions as a CSV file.

## B. Why This File Exists
PRD 6.4 lets batch results be exported, and PRD 6.9 lists a transaction prediction CSV. Both use the same columns, and streaming means a large export does not fill memory.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.database.session`, `app.models.records`, `app.utils.csv_safety`.
- **External services / database:** `transactions`, `predictions`, `investigations`.
- **Depended on by:** the batches route and `report_service.py`.

## D. Every Function Explained

### `_prediction_rows`
- **Purpose:** yield rows from the database.
- **Parameters / types:** `is_demo: bool`, `batch_job_id: uuid.UUID | None`. **Returns / type:** an iterator of tuples.
- **Internal processing:** `yield_per` is passed as an execution option, which streams rows from a server-side cursor 1,000 at a time. Until Phase 5 M2 it was called on the result, after the driver had fetched every row, and the API's memory reached 496 MiB during a 500,000-row export. It opens its own session, because the request's session has closed by the time streaming happens.
- **Error handling:** an error ends the stream early.
- **Calls:** `session_scope`, `_plain`. **Used by:** `prediction_csv_lines`.

### `_plain`
Converts enums to their text and timestamps to ISO format. Other values pass through unchanged.

### `prediction_csv_lines`
- **Purpose:** the public function.
- **Parameters / types:** `is_demo: bool`, `batch_job_id` (optional). **Returns / type:** an iterator of strings.
- **Internal processing:** combines the header with the rows.
- **Error handling:** as above. **Calls:** `csv_lines`, `_prediction_rows`. **Used by:** routes.

## E. Classes Explained
None.

## F. Execution Flow
A route wraps the iterator in a `StreamingResponse`, and rows are read as the client downloads.

## G. Input and Output
Output columns are listed in `PREDICTION_HEADER`. They include `model_score`, `score_is_calibrated` (always false), `prediction`, `model_version` and `threshold_used`.

## H. Important Technical Concepts
- **Ground-truth labels are not in this file.** Predictions and labels stay separate (PRD 6.1).

## I. Example
```python
"".join(prediction_csv_lines(False, job.id))
```

## J. Maintenance Notes
Adding a column here changes every export of predictions.

## K. Related Files
- [csv_safety.py](../utils/csv_safety.py.explanation.md): safe output.
- [report_service.py](report_service.py.explanation.md): other reports.
