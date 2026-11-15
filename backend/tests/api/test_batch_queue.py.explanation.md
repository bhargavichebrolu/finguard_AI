# test_batch_queue.py

Source: [backend/tests/api/test_batch_queue.py](test_batch_queue.py)

## A. File Purpose
Tests the batch queue: claiming, crash and resume, lost ownership, the attempt limit, graceful release and several workers.

## B. Why This File Exists
Phase 5 M4 required transactional claiming, leases, heartbeats, abandoned-job recovery, idempotent chunks, no duplicates on retry and no shared chunks between workers, each tested.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy.
- **Internal modules:** `app.services.batch_service`, API test fixtures.
- **External services / database:** PostgreSQL (`finguard_test`).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `csv_text`
Builds a CSV in which half the rows have no identifier; a chunk stored twice would show up as extra rows.

### `queue`
Uploads a CSV through the API and returns the job id.

### `stored_rows`
Counts a job's stored transactions.

### `expire_lease`
Moves a job's lease into the past, standing in for a dead worker's lease running out.

### `settings`
Fixture: chunks of 100 rows and a private upload folder.

### `claim`
Nested: one claim in its own session.

### `dies_in_third_chunk`
Nested: raises `Crash` in the third chunk.

### `analyst`
Fixture: an analyst's headers.

## E. Classes Explained
### `Crash`
A `BaseException`, so nothing in the worker catches it: it stands in for the process dying mid-chunk.

## F. Execution Flow
Queue jobs through the API, drive workers directly, inspect the database.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_upload_is_stored_in_the_database_and_queued` | Bytes in the database, none left on disk, deleted when the job ends. |
| `test_simultaneous_claims_never_take_the_same_job` | Six simultaneous claims on three jobs: each job once. |
| `test_a_crash_mid_chunk_resumes_after_the_last_commit_without_duplicates` | The crashed chunk is rolled back; the job is not claimable during the lease, then resumes at row 200 and ends with 450 rows, each once, on attempt 2. |
| `test_a_worker_that_lost_its_lease_stores_nothing` | A stale worker stops; the new owner stores everything. |
| `test_a_job_interrupted_too_often_is_failed_and_its_bytes_removed` | The attempt limit. |
| `test_stopping_gives_the_job_back_for_immediate_resumption` | Graceful release. |
| `test_several_workers_on_several_jobs_store_every_row_once` | Three workers, four jobs, every row once. |

## H. Important Technical Concepts
- **`HEADER`** and **`UPLOAD`** are the CSV header and upload path.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_batch_queue.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Keep rows without identifiers in every scenario; they are what reveals a repeated chunk.

## K. Related Files
- [batch_service.py](../../app/services/batch_service.py.explanation.md): the queue.
- [test_multiprocess.py](../integration/test_multiprocess.py.explanation.md): real-process crashes.
