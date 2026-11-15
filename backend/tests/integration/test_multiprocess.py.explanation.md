# test_multiprocess.py

Source: [backend/tests/integration/test_multiprocess.py](test_multiprocess.py)

## A. File Purpose
Starts real API processes together against the test database and checks that they share rate limits and register the model safely.

## B. Why This File Exists
Phase 5 M3 required correctness across multiple processes and restarts, tested with real processes rather than threads.

## C. Dependencies
- **Libraries:** pytest, httpx, Python `subprocess`, `socket`.
- **Internal modules:** `app.services.auth_service`, `app.models.records`, `tests.conftest`.
- **External services / database:** Uvicorn processes on free local ports; PostgreSQL (`finguard_test`).
- **Depended on by:** none; run by pytest. Skipped without the model binary.

## D. Every Function Explained

### `free_port`
An unused local port.

### `_wait_until_healthy`
Polls `/health` until the process answers, failing if it exits or takes over 90 seconds.

### `api_processes`
Starts several API processes at the same moment, then waits for all, so their start-ups overlap; stops them afterwards.

### `sign_in`
One bearer sign-in attempt; returns the status code.

### `account`
Fixture: an empty database with one account.

### `ApiProcess`
A class, not a function: a `str` holding a process's address that also carries the `subprocess.Popen`, so a test can kill one process.

### `batch_csv`
A CSV of synthetic rows, half without identifiers.

### `bearer`
Signs in and returns a bearer header.

### `upload`
Uploads a CSV and returns the job id.

### `wait_for`
Polls a job until a condition holds, failing after a timeout.

### `stored`
Counts a job's stored rows and distinct identifiers in the database.

### `test_a_killed_process_s_batch_is_finished_by_another_process`
Kills an API process outright partway through 6,000 rows; a second process with a different, empty upload folder finishes the job on its second attempt, with every row stored exactly once.

### `test_two_processes_share_the_queue_and_store_every_row_once`
Two processes with workers process four jobs; each completes on one attempt with every row once.

## E. Classes Explained
None.

## F. Execution Flow
Launch processes, act over HTTP, stop them, check the database.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_failed_sign_ins_are_counted_across_processes_and_restarts` | Five failures split across two processes reach the limit in both; a new process still refuses. |
| `test_the_memory_store_lets_each_process_allow_the_full_limit` | The old per-process behaviour: ten failures allowed across two processes, forgotten on restart. |
| `test_processes_starting_together_register_the_model_once` | Four simultaneous start-ups leave exactly one active model row. Without the advisory lock this failed in two of three runs. |

## H. Important Technical Concepts
- **`QUEUE_SETTINGS`** shorten chunks, leases and polling so crash tests finish quickly; **`BATCH_HEADER`** is the CSV header.
- **`LOGIN_LIMIT`** is the configured failed sign-in limit, five.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_multiprocess.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If start-up gets slower, raise the health wait rather than removing the overlap.

## K. Related Files
- [rate_limit.py](../../app/core/rate_limit.py.explanation.md): shared counts.
- [model_service.py](../../app/services/model_service.py.explanation.md): registration lock.
