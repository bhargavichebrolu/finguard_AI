# batch_service.py

Source: [backend/app/services/batch_service.py](batch_service.py)

## A. File Purpose
Accepts CSV uploads, checks them, queues them, and processes them in chunks through a queue any API process can work, with leases, resumption and an attempt limit; reports progress and row errors.

## B. Why This File Exists
PRD 6.4 lists the requirements, PRD 9.2 asks for controlled temporary storage rather than unbounded blobs, and PRD 11.7 says not to assume background workers or persistent local storage. Phase 5 M4 required batches to survive crashes and restarts, to run safely with several processes, and to use storage every container can reach.

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
- **Parameters / types:** `session`, `source`, `filename`, `user`, `settings`. **Returns / type:** `BatchJob`.
- **Internal processing:** checks the extension, saves under a random name, inspects, reads the checked bytes, deletes the temporary file, then creates the `PENDING` job and its `BatchUpload` row in one commit.
- **Error handling:** the temporary file is always deleted; any failure re-raises.
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
Yields lists of rows with their spreadsheet row numbers, from the stored bytes. Skips the rows a previous attempt already committed, adding their identifiers to `seen`, so a repeat later in the file is still reported as repeated.

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

### `new_worker_id`
A unique worker name: host, process id and a random part.

### `fail_exhausted_jobs`
Marks failed every processing job whose lease has expired after its last allowed attempt, with a message saying how many interruptions it had, and deletes its stored bytes.

### `claim_next_job`
- **Purpose:** give this worker the oldest waiting job, or one whose lease expired.
- **Parameters / types:** `session`, `worker_id`, `lease_seconds`, `max_attempts`. **Returns / type:** the job id or `None`.
- **Internal processing:** `UPDATE batch_jobs ... WHERE id = (SELECT ... ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED)` sets the owner, a lease from database time, and adds one attempt. SKIP LOCKED makes simultaneous claims pass over a row being claimed.
- **Error handling:** none needed. **Calls:** SQLAlchemy. **Used by:** `process_available_jobs`.

### `_owned_job`
Locks the job row (`FOR UPDATE`) if this worker still owns it; `None` means another worker took it over after the lease expired.

### `process_job`
- **Purpose:** work a claimed job to the end.
- **Parameters / types:** `job_id`, `worker_id`, `model`, `settings`, optional `stop` event. **Returns / type:** `"completed"`, `"failed"`, `"released"` or `"lost"`.
- **Internal processing:** loads the stored bytes and the committed progress, then for each remaining chunk: locks the job row and checks ownership, renews the lease (the heartbeat), and stores the chunk's rows, errors and progress in one commit. Finishing sets the final status, clears the owner and deletes the bytes. If `stop` is set it gives the job back between chunks.
- **Error handling:** an ordinary exception marks the job failed with a safe message. A crash or killed process leaves the job owned until its lease expires, and loses at most the uncommitted chunk. A worker that lost ownership stops without writing.
- **Calls:** `_read_chunks`, `_owned_job`, `_process_chunk`, `release_job`, `_mark_failed`, `record_event`. **Used by:** `process_available_jobs`.

### `release_job`
Clears the owner and sets the lease to now, so another worker resumes the job immediately.

### `_mark_failed`
Records a failed status with a safe message, only if this worker still owns the job, and deletes the stored bytes.

### `process_available_jobs`
Fails exhausted jobs, then claims and processes jobs until none is waiting or `stop` is set. Returns how many it claimed. Tests call it directly to drain the queue.

### `remove_stale_uploads`
At start-up, deletes temporary upload files older than an hour, which can only belong to a request that crashed mid-upload. Unlike the removed `recover_interrupted_jobs`, it never touches jobs or another process's work.

### `__init__`
`BatchWorker`: stores the model and settings, names the worker and creates its thread and events.

### `start`
Starts the worker thread.

### `wake`
Makes the worker look for work now instead of at its next poll; the upload route calls it.

### `stop`
Asks the worker to finish its current chunk, give the job back, and stop; waits up to 30 seconds.

### `_run`
The thread's loop: process available jobs, then wait for a wake-up or the poll interval.

### `get_job`
Returns a job in the user's scope, or raises `NotFoundError`.

### `list_jobs`
Returns a page of jobs, newest first.

### `error_report_lines`
Streams row errors as CSV. It opens its own session, because streaming continues after the route function has returned.

### `rows`
Nested inside `error_report_lines`. Yields the error rows.

### `_release_after_interruption`
Gives an interrupted job back for immediate resumption. If the database is still unreachable, it logs that the job will resume when its lease expires; any other error is raised.

## E. Classes Explained
### `BatchWorker`
One background thread per API process that works the queue. Started and stopped by `lifespan` in `app/main.py`.


### `CsvInspection`
Row count, ignored columns and whether labels came with the file. A frozen dataclass.

### `_ParsedChunk`
Valid payloads, their labels, errors and the failed-row count. A dataclass.

## F. Execution Flow
Upload: check extension, save, inspect, create job, respond 202. Background: chunks of parse, score, store and commit. Finally: status, audit entry, delete file.

## G. Input and Output
Input: a CSV with `amount`, `transaction_type`, `step`, `destination_category` and optionally `external_transaction_id`. Output: stored results, an error report, and progress.

## H. Important Technical Concepts
- **Lost connections interrupt, never fail (Phase 5 M7):** in `process_job`, a connection error (`is_connection_error`) returns "interrupted" and gives the job back instead of marking it failed, because chunks are idempotent and progress is stored; the next claim resumes it and counts an attempt, so `batch_max_attempts` still stops a job that keeps failing. `process_available_jobs` then waits for the next poll rather than reclaiming at once. Any other error still fails the job.
- **`FAILED_MESSAGE`** is the safe message for an unexpected error; **`_STALE_UPLOAD_SECONDS`** is one hour.
- **Removed in M4:** `process_batch` (in-process background task) and `recover_interrupted_jobs`, which assumed one process and failed every unfinished job, deleting files, at each start-up.
- **PRD 9.2 and storage.** Upload bytes live in the database only within the 10 MB and 50,000-row limits and only until the job ends (completed, failed or exhausted): controlled temporary storage that every container can reach, as PRD 11.7 and the Phase 5 approval require. The temporary file on disk exists only while the upload request runs.
- **The queue (Phase 5 M4).** `batch_jobs` is the queue; `batch_uploads` holds the bytes. Each chunk commit both stores rows and advances `processed_records`, so progress and data never disagree, and a resumed job never stores a row twice; `test_batch_queue.py` checks this with rows that have no identifier, which would show up twice if a chunk were repeated.
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
