# batches.py (routes)

Source: [backend/app/api/routes/batches.py](batches.py)

## A. File Purpose
Exposes CSV upload, job status, results, result export and the error report.

## B. Why This File Exists
These are the PRD 8.2 batch endpoints. `GET /batches` and `GET /batches/{id}/errors` are additions: PRD 6.4 requires a downloadable error report, and a client needs to find its jobs.

## C. Dependencies
- **Libraries:** `fastapi`, `python-multipart`, for file uploads.
- **Internal modules:** `app.api.schemas`, `app.repositories.transactions`, `app.security`, `app.services.batch_service`, `app.services.export_service`.
- **External services / database:** through the services.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `_is_demo`
Returns whether a user's records are demo records.

### `_csv_response`
Wraps lines in a `StreamingResponse`, with a download header. The name is built from the job's identifier, not from client text.

### `upload`
`POST /api/v1/batches/upload`. Takes a multipart `file` and returns `BatchView` with status 202. Bad files give 422, and oversized ones give 413. Calls `start_batch`, which stores the file and queues the job, then wakes this process's batch worker. Any API process's worker may process it (Phase 5 M4).

### `list_batches`
`GET /api/v1/batches`. Returns `Page[BatchView]`.

### `read_batch`
`GET /api/v1/batches/{batch_id}`. Returns status and progress, or 404.

### `read_results`
`GET /api/v1/batches/{batch_id}/results`. Returns a page of `TransactionSummary`, or 404.

### `export_results`
`GET /api/v1/batches/{batch_id}/export`. Streams CSV, or 404.

### `export_errors`
`GET /api/v1/batches/{batch_id}/errors`. Streams the error report, or 404.

## E. Classes Explained
None.

## F. Execution Flow
Upload returns 202 once the file is accepted. Processing continues afterwards. The client polls `read_batch` for progress.

## G. Input and Output
See `API_DOCUMENTATION.md`.

## H. Important Technical Concepts
- **202 means accepted, not finished.** Row-level problems appear later, in the job's counts and the error report.
- **Scope:** demo users see only demo batches, and others get 404 for them.

## I. Example
```powershell
curl.exe -H "Authorization: Bearer <token>" -F "file=@sample.csv" http://127.0.0.1:8010/api/v1/batches/upload
```

## J. Maintenance Notes
Keep processing logic in `batch_service`.

## K. Related Files
- [batch_service.py](../../services/batch_service.py.explanation.md): the logic.
- [test_batches.py](../../../tests/api/test_batches.py.explanation.md): tests.
