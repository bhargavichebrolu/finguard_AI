# test_failures.py

Source: [backend/tests/api/test_failures.py](test_failures.py)

## A. File Purpose
Tests what the API does when the database goes away and comes back, when the model fails, when a batch job loses its database connection, and when an investigation change is based on a stale status.

## B. Why This File Exists
Phase 5 M7 asked for integration failure handling to be tested, for errors to be actionable without exposing internals, and for recovery never to duplicate predictions or silently lose batch jobs. Each test here failed before its fix, except the three noted as checks.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy, concurrent.futures.
- **Internal modules:** `app.core.errors`, `app.services.batch_service`, `app.services.prediction_service`, `app.api.routes.health`, `app.database.session`; `tests.api.test_batch_queue` helpers.
- **External services / database:** The PostgreSQL test database; a closed local port for a real connection failure.
- **Depended on by:** The backend test suite.

## D. Every Function Explained

### `assert_safe`
Checks an error body has only `detail`, `request_id` and `errors`, a request ID, and none of the words in `FORBIDDEN` (SQL, driver and server names, traces, addresses, passwords).

### `connection_lost`
Builds the `OperationalError` SQLAlchemy raises when a connection dies mid-use (`connection_invalidated=True`), or, with no statement, while connecting.

### `unreachable_database`
Fixture: requests get sessions on the configured database address with port 1, where nothing listens, so the driver raises a real connection error.

### `broken_db`
Inside `unreachable_database`: the replacement for `get_db`.

### `history_of`
Reads an investigation's status history in order, as (from, to) pairs.

### `analyst`
Fixture: request headers for a new analyst.

### `admin`
Fixture: request headers for a new administrator.

### `investigator`
Fixture: request headers for a new investigator.

### `settings`
Fixture: settings with a temporary upload folder and 100-row chunks.

### `case`
Fixture: scores a flagged transaction and returns its investigation's URL.

### `timed_out`
Stand-in that raises a statement timeout: an `OperationalError` with a statement, which is not an outage.

### `lost`
Stand-in that raises a connection lost mid-request.

### `broken`
Stand-in model scoring that raises.

### `connection_drops_in_third_chunk`
Stand-in chunk processor that loses the connection in the third chunk and otherwise runs the real one.

### `drops`
The same, in the second chunk.

### `cannot_release`
Stand-in `release_job` that cannot reconnect, as while the database stays down.

### `test_an_unreachable_database_gives_a_safe_503_with_retry_after`
See G.

### `test_signing_in_while_the_database_is_unreachable_says_so`
See G.

### `test_the_api_recovers_from_lost_connections_without_a_restart`
See G.

### `test_a_database_error_that_is_not_an_outage_stays_a_plain_500`
See G.

### `test_a_connection_lost_mid_request_is_an_outage`
See G.

### `test_a_scoring_failure_stores_nothing_and_says_what_to_do`
See G.

### `test_a_lost_connection_interrupts_a_batch_which_resumes_storing_every_row_once`
See G.

### `test_while_the_database_stays_down_the_lease_brings_the_job_back`
See G.

### `test_a_database_error_that_is_not_an_outage_fails_the_job`
See G.

### `test_a_change_based_on_a_stale_status_is_refused_and_changes_nothing`
See G.

### `test_expected_status_alone_changes_nothing_and_is_refused`
See G.

### `test_of_two_simultaneous_changes_from_the_same_status_exactly_one_applies`
See G.

## E. Classes Explained
None.

## F. Execution Flow
Each test arranges a failure, makes real requests or runs the real worker, then checks the response, the stored rows and, for errors, the body's safety.

## G. Input and Output
| Test | Proves |
|---|---|
| an unreachable database gives a safe 503 with Retry-After | Real driver error -> 503, `Retry-After: 5`, the actionable message, nothing internal |
| signing in while the database is unreachable says so | Same on the sign-in route |
| the API recovers from lost connections without a restart | Every connection ended, as a database restart does; the next request succeeds (check: `pool_pre_ping` already did this) |
| a database error that is not an outage stays a plain 500 | A statement timeout is not reported as an outage |
| a connection lost mid-request is an outage | `connection_invalidated` -> 503 |
| a scoring failure stores nothing and says what to do | Model error -> 500 with a reference; no transaction, prediction or audit entry; the same request then succeeds |
| a lost connection interrupts a batch, which resumes storing every row once | Job given back, not failed; resumed to 450 rows with 450 predictions |
| while the database stays down the lease brings the job back | Release also fails; the job resumes once its lease expires |
| a database error that is not an outage fails the job | Not retried; the stored message reveals nothing |
| a change based on a stale status is refused and changes nothing | 409 naming the current status; history unchanged; a current change then works |
| expected_status alone changes nothing and is refused | 422 (check) |
| of two simultaneous changes from the same status exactly one applies | Eight concurrent changes: one 200, seven 409, one history entry |

## H. Important Technical Concepts
- **Real failures where possible:** the outage uses a real connection to a closed port; the recovery test really ends the application's connections. Mid-job connection loss is injected, because its timing cannot be arranged otherwise; the browser test `batches.spec.ts` covers a real one.
- **`db_engine.dispose()`:** ending every connection also ends the test engine's pooled ones, which has no pre-ping, so its pool is replaced afterwards.

## I. Example
```powershell
cd backend; uv run pytest tests/api/test_failures.py -q
```

## J. Maintenance Notes
Keep `FORBIDDEN` strict. A new error path should get a test here that calls `assert_safe`.

## K. Related Files
- [errors.py](../../app/core/errors.py.explanation.md): the handlers.
- [batch_service.py](../../app/services/batch_service.py.explanation.md): the worker.
