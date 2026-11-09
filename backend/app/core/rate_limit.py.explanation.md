# rate_limit.py

Source: [backend/app/core/rate_limit.py](rate_limit.py)

## A. File Purpose
Counts requests and failed sign-ins against their limits, in PostgreSQL by default, so every API process and every restart see the same counts.

## B. Why This File Exists
Phase 5 M3 found that per-process counts let each process allow the full limit and forgot every count on restart, so sign-in guessing could continue across restarts. The approval required shared counts, within a latency budget measured beforehand.

## C. Dependencies
- **Libraries:** SQLAlchemy (`text`), Python standard library.
- **Internal modules:** `app.core.errors`, `app.core.config` and `app.database.session` (imported late, to keep `core` free of import cycles).
- **External services / database:** PostgreSQL tables `rate_limit_events` and `rate_limit_windows`.
- **Depended on by:** `app/security/dependencies.py` (`rate_limited`), `app/services/auth_service.py` (sign-in), API test fixtures (`reset`).

## D. Every Function Explained

### `_refuse`
Raises `RateLimitedError` with a whole-second wait of at least one second.

### `require_below_limit`
Raises if the key has reached its limit within the sliding window, without counting this call. Memory and database versions.

### `record`
Counts one event. The database version commits immediately in its own transaction, so a failing request still counts.

### `hit`
Sliding-window check and count. The database version takes a transaction-scoped advisory lock on the key, then counts and inserts in a second statement, whose fresh snapshot includes events committed by other processes while it waited.

### `hit_window`
- **Purpose:** the per-request limit for predictions and uploads.
- **Parameters / types:** `key`, `limit`, `window_seconds`. **Returns / type:** `None`.
- **Internal processing:** database: one autocommit `INSERT … ON CONFLICT DO UPDATE SET count = count + 1 WHERE count < limit RETURNING count` on the current fixed window; no row back means the limit is reached, and only then is the wait read from database time. Memory: the sliding-window `hit`.
- **Error handling:** `RateLimitedError`. **Calls:** `_refuse`. **Used by:** `rate_limited`.

### `clear`
Forgets a key, such as after a successful sign-in.

### `reset`
Forgets everything; tests use it.

### `_engine`
The application's database engine, imported late.

### `store`
Returns the database or memory store, as `RATE_LIMIT_STORE` says.

### `__init__`
Two constructors: `MemoryRateLimiter` creates its event lists and lock; `ConfiguredRateLimiter` creates one memory and one database store.

### `_recent`
Memory store: drops a key's events older than the window and returns the rest.

## E. Classes Explained
### `RateLimitStore`
A protocol listing what a store must do.

### `MemoryRateLimiter`
Counts in this process only, with a lock. Kept for comparison measurements and code without a database; production refuses it.

### `DatabaseRateLimiter`
Counts in PostgreSQL using database time, so separate processes and machines agree.

### `ConfiguredRateLimiter`
The `limiter` object the application uses; delegates to the configured store.

## F. Execution Flow
A request's dependency calls `hit_window`; sign-in calls `require_below_limit`, then `record` on failure or `clear` on success.

## G. Input and Output
Input: a key such as `predict:<user id>` or `login:<address>:<email>`, a limit and a window. Output: nothing, or `RateLimitedError` (HTTP 429 with `Retry-After`).

## H. Important Technical Concepts
- **Two window kinds.** Failed sign-ins use a sliding window (every failure counts for exactly 60 seconds), because a fixed window could allow up to twice the limit across a boundary, which matters for guessing. Predictions and uploads use a fixed one-minute window, which costs one round trip.
- **Why two designs:** the sliding-window design on the prediction path exceeded the latency budget in a paired comparison (`docs/performance/phase-5-ratelimit-sliding-decision.json`: +3.1 ms sequential median against 2.4 ms allowed) and was rejected. The fixed-window design passed every check, with differences inside run-to-run noise (`phase-5-ratelimit-window-decision.json`).
- **`_LOCK`, `_RECENT`, `_WAIT`, `_CHECK`, `_HIT`, `_WINDOW_HIT`, `_WINDOW_WAIT`** are the SQL statements.
- **Concurrency:** 20 simultaneous attempts on one key admit exactly the limit in both designs (`test_rate_limits.py`); separate processes and restarts share counts (`test_multiprocess.py`).

## I. Example
```python
limiter.hit_window(f"predict:{user.id}", 120, 60)
```

## J. Maintenance Notes
Expired rows are removed as keys are used (sliding) and by the retention command (M5). Keep production on the database store; the setting refuses anything else there.

## K. Related Files
- [dependencies.py](../security/dependencies.py.explanation.md): per-request limits.
- [auth_service.py](../services/auth_service.py.explanation.md): sign-in limits.
