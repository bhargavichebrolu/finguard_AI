# batch_service.py

Source: [backend/app/services/batch_service.py](batch_service.py)

## A. File Purpose
Accepts CSV uploads, checks them, processes them in chunks in the background, and reports progress and row errors.

## B. Why This File Exists
PRD 6.4 lists the requirements, PRD 9.2 forbids storing uploads as unbounded blobs, and PRD 11.7 says not to assume background workers or persistent storage.

## C. Dependencies
- **Libraries:** `csv`, `pydantic`, `sqlalchemy`, including PostgreSQL's `insert ... on conflict`.
- **Internal modules:** `app.api.schemas.transactions`, `app.core`, `app.database.session`, `app.ml.schema`, `app.models`, `app.services`, `app.utils.csv_safety`.
- **External services / database:** a temporary folder, `batch_jobs`, `batch_row_errors`, `transactions`, `predictions`, `ground_truth_labels`.
- **Depended on by:** the batches route, and `app/main.py` for recovery.

## D. Every Function Explained

### `save_upload`
- **Purpose:** copy the upload to a temporary file.
- **Parameters / types:** `source: BinaryIO`, `destination: Path`, `max_bytes: int`. **Returns / type:** `None`.
- **Internal processing:** reads in pieces, stopping as soon as the limit is passed.
- **Error handling:** `PayloadTooLargeError`, or `InvalidInputError` for NUL bytes or an empty file.
- **Calls:** none. **Used by:** `start_batch`.

### `validate_header`
- **Purpose:** check the columns.
- **Parameters / types:** `names: list[str]`. **Returns / type:** `CsvInspection`.
- **Internal processing:** refuses balance and account columns, requires the four inputs, refuses unknown ones, and accepts `isFraud` and `isFlaggedFraud` as ignored.
- **Error handling:** `InvalidInputError` naming the columns.
- **Calls:** none. **Used by:** `inspect_csv`.

### `inspect_csv`
- **Purpose:** check encoding and structure, and count rows before accepting the file.
- **Parameters / types:** `path: Path`, `max_rows: int`. **Returns / type:** `CsvInspection`.
- **Internal processing:** reads the whole file once.
- **Error handling:** bad encoding or structure gives `InvalidInputError`, and too many rows gives `PayloadTooLargeError`.
- **Calls:** `validate_header`. **Used by:** `start_batch`.

### `start_batch`
- **Purpose:** accept an upload.
- **Parameters / types:** `session`, `source`, `filename`, `user`, `settings`. **Returns / type:** `tuple[BatchJob, Path]`.
- **Internal processing:** checks the extension, saves under a random name, inspects, and creates the job.
- **Error handling:** any failure deletes the temporary file and re-raises.
- **Calls:** `save_upload`, `inspect_csv`, `clean_filename`, `record_event`. **Used by:** the upload route.

### `_parse_label`
Returns the label and whether it was invalid. A blank means no label.

### `_parse_row`
- **Purpose:** validate one row.
- **Parameters / types:** `row: dict`, `row_number: int`, `seen: set[str]`, `chunk`. **Returns / type:** `None`.
- **Internal processing:** checks for extra cells, missing values, then the same `TransactionInput` rules as a single prediction, then repeats within the file.
- **Error handling:** problems are added to the chunk. Messages never include the rejected value.
- **Calls:** `TransactionInput`, `_parse_label`. **Used by:** `_process_chunk`.

### `_read_chunks`
Yields lists of rows with their spreadsheet row numbers. Reads the file gradually, so memory use stays small.

### `_store_scored_rows`
- **Purpose:** insert valid rows and their predictions.
- **Parameters / types:** `session`, `job`, `scored_rows`, `labels`, `model`, `high_boundary`. **Returns / type:** `list[str]` of identifiers that already existed.
- **Internal processing:** `ON CONFLICT DO NOTHING` skips existing identifiers without failing the chunk, and `RETURNING` shows which rows were inserted. Labels go to `ground_truth_labels` only.
- **Error handling:** database errors propagate to `process_batch`.
- **Calls:** `add_prediction_records`. **Used by:** `_process_chunk`.

### `_process_chunk`
- **Purpose:** handle one chunk in one database transaction.
- **Parameters / types:** `session`, `job`, `rows`, `seen`, `model`, `high_boundary`, `settings`. **Returns / type:** `None`.
- **Internal processing:** parses, scores, stores, records errors up to `max_stored_row_errors`, updates progress and commits.
- **Error handling:** as above.
- **Calls:** `_parse_row`, `score_inputs`, `_store_scored_rows`. **Used by:** `process_batch`.

### `process_batch`
- **Purpose:** the background task.
- **Parameters / types:** `job_id`, `path`, `model`. **Returns / type:** `None`.
- **Internal processing:** runs all chunks with one high boundary, and sets the final status.
- **Error handling:** any exception is logged and marks the job failed. `finally` always deletes the file.
- **Calls:** `_read_chunks`, `_process_chunk`, `_mark_failed`. **Used by:** the upload route.

### `_mark_failed`
Records a failed status with a safe message, in a new session.

### `recover_interrupted_jobs`
- **Purpose:** tidy up after a restart.
- **Parameters / types:** `session`, `upload_dir`. **Returns / type:** `int`.
- **Internal processing:** marks unfinished jobs failed and deletes leftover files.
- **Error handling:** a missing folder is ignored.
- **Calls:** `update`. **Used by:** `lifespan` in `app/main.py`.

### `get_job`
Returns a job in the user's scope, or raises `NotFoundError`.

### `list_jobs`
Returns a page of jobs, newest first.

### `error_report_lines`
Streams row errors as CSV. It opens its own session, because streaming continues after the route function has returned.

### `rows`
Nested inside `error_report_lines`. Yields the error rows.

## E. Classes Explained

### `CsvInspection`
Row count, ignored columns and whether labels came with the file. A frozen dataclass.

### `_ParsedChunk`
Valid payloads, their labels, errors and the failed-row count. A dataclass.

## F. Execution Flow
Upload: check extension, save, inspect, create job, respond 202. Background: chunks of parse, score, store and commit. Finally: status, audit entry, delete file.

## G. Input and Output
Input: a CSV with `amount`, `transaction_type`, `step`, `destination_category` and optionally `external_transaction_id`. Output: stored results, an error report, and progress.

## H. Important Technical Concepts
- **Labels cannot affect scores.** The label is read separately and never enters `TransactionInput`. Even an invalid label leaves the row scored.
- **`processed_records` counts rows read, and `failed_records` counts those refused.** Stored successes are the difference.
- **Explanations for flagged rows only,** which saves time and storage. An unflagged batch row has no stored explanation.
- **A failed job keeps committed chunks.** Those results are valid, and the status makes the partial result clear.
- **Row number 0 in the error report** marks an identifier that already existed in the database, because the insert does not track which file row it came from.
- **Limitation:** background tasks run inside the API process, so a restart interrupts a job, which must then be uploaded again.

## I. Example
```csv
external_transaction_id,amount,transaction_type,step,destination_category
A-1,181.00,TRANSFER,2,customer
```

## J. Maintenance Notes
Lowering limits is safe. Raising them needs thought about memory and hosting limits (PRD 11.7). If several API processes are ever used, `recover_interrupted_jobs` must change, because it assumes one.

## K. Related Files
- [batches.py route](../api/routes/batches.py.explanation.md): the entry points.
- [prediction_service.py](prediction_service.py.explanation.md): scoring.
- [test_batches.py](../../tests/api/test_batches.py.explanation.md): tests.
