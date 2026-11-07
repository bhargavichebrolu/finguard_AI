# session.py

Source: [backend/app/database/session.py](session.py)

## A. File Purpose
Creates the database connection pool, and hands out sessions to requests and background work.

## B. Why This File Exists
Connections should be set up in one place, with a single route for credentials. PRD 9.2 requires database credentials to stay outside source code.

## C. Dependencies
- **Libraries:** `sqlalchemy`, `psycopg` (through the URL), `contextlib`, `functools`.
- **Internal modules:** `app.core.config`.
- **External services / database:** PostgreSQL.
- **Depended on by:** API routes through `get_db`, background batch processing, start-up steps.

## D. Every Function Explained

### `get_engine`
- **Purpose:** create the process's connection pool.
- **Parameters / types:** none. **Returns / type:** `Engine`.
- **Internal processing:** `pool_pre_ping` tests a connection before use, so a restarted database does not break the next request. `lru_cache` keeps it to one pool.
- **Error handling:** connection errors appear on first use, after the timeout.
- **Calls:** `get_settings`. **Used by:** `_session_factory`, tests.

### `_session_factory`
- **Purpose:** build the session factory.
- **Parameters / types:** none. **Returns / type:** `sessionmaker`.
- **Internal processing:** `expire_on_commit=False` lets response building read attributes after a commit without another query.
- **Error handling:** none needed.
- **Calls:** `get_engine`. **Used by:** `get_db`, `session_scope`.

### `get_db`
- **Purpose:** FastAPI dependency that provides one session per request.
- **Parameters / types:** none. **Returns / type:** an iterator yielding `Session`.
- **Internal processing:** closes the session afterwards, which rolls back anything uncommitted.
- **Error handling:** an exception in the route still closes the session through `finally`.
- **Calls:** `_session_factory`. **Used by:** routes and security dependencies.

### `session_scope`
- **Purpose:** the same thing for code outside a request.
- **Parameters / types:** none. **Returns / type:** a context manager yielding `Session`.
- **Internal processing:** as `get_db`.
- **Error handling:** closes the session even on error.
- **Calls:** `_session_factory`. **Used by:** batch processing, start-up, `scripts/create_admin.py`.

### `database_is_available`
- **Purpose:** report whether the database responds.
- **Parameters / types:** `session: Session`. **Returns / type:** `bool`.
- **Internal processing:** runs `SELECT 1`.
- **Error handling:** any failure returns `False`, so a health report never exposes a connection error.
- **Calls:** `session.execute`. **Used by:** the system status endpoint.

## E. Classes Explained
None.

## F. Execution Flow
A request asks for `get_db`, gets a session, runs its service, which commits, and the session closes.

## G. Input and Output
Input: `DATABASE_URL`. Output: sessions.

## H. Important Technical Concepts
- **Services commit, not this module.** A related set of changes (PRD 9.2) succeeds or fails together, and leaving a request without committing discards everything.
- **Synchronous sessions:** routes are plain functions that FastAPI runs on a thread pool, which also suits the model's CPU work.

## I. Example
```python
with session_scope() as session:
    database_is_available(session)
```

## J. Maintenance Notes
Tests clear these caches only by setting the environment before the first call. If the API ever runs several processes, each has its own pool, so the pool size needs to fit the database's connection limit.

## K. Related Files
- [config.py](../core/config.py.explanation.md): provides the address.
- [base.py](base.py.explanation.md): table definitions.
