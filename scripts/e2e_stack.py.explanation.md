# e2e_stack.py

Source: [scripts/e2e_stack.py](e2e_stack.py)

## A. File Purpose
Starts or stops the browser-test API: the normal image on 127.0.0.1:8011, migrated against and connected to the test database.

## B. Why This File Exists
Browser tests must run against the real Docker backend and PostgreSQL, separate from development data and from the development API on port 8010.

## C. Dependencies
- **Libraries:** Python standard library.
- **Internal modules:** none.
- **External services / database:** Docker Compose, profile `e2e`.
- **Depended on by:** Developers, before `npm run test:e2e`.

## D. Every Function Explained

### `compose`
Runs `docker compose --profile e2e` with the given arguments.

### `database_name`
Returns `E2E_DB_NAME` or `finguard_e2e_test`, refusing anything that is not lower case and ending in `_test`, so the name is safe to place in SQL.

### `ensure_database`
Starts the database container if needed and runs `_CREATE_IF_MISSING` inside it, as its superuser with that container's own credentials, creating the browser-test database owned by the application role if it does not exist. No password passes through this machine's command line.

### `up`
Ensures the database, builds the image, then starts `api-e2e` (after `migrate-e2e`) with a freshly generated `E2E_SECRET_KEY` and `E2E_DB_NAME`, recreating it so it registers the model again. The running database container is not recreated.

### `down`
Stops and removes the two browser-test containers.

### `main`
Parses `up` or `down`.

### `set_connections`
Allows or refuses connections to the browser-test database, as the superuser inside the database container; refusing also ends open connections. `up` always allows them, ending an outage a stopped test run left behind (Phase 5 M7).

## E. Classes Explained
None.

## F. Execution Flow
Build, migrate, start, wait for health.

## G. Input and Output
Output: the `finguard-api-e2e-1` container on 127.0.0.1:8011.

## H. Important Technical Concepts
- **`database off|on` (Phase 5 M7):** simulates a database outage for `finguard_e2e_test` only, using `ALTER DATABASE ... ALLOW_CONNECTIONS`; other databases in the container are untouched.
- **Own database (Phase 5 M1):** the browser tests use `finguard_e2e_test`, so running the backend suite no longer forces a restart of this stack.
- **The signing key** exists only in this process's environment for the Compose call. Without it the API refuses to start, because `SECRET_KEY` must have 32 characters.

## I. Example
```powershell
python scripts/e2e_stack.py up
python scripts/e2e_stack.py down
```

## J. Maintenance Notes
Since Phase 5 M1 the backend suite no longer affects this stack: it uses `finguard_test`, and this stack `finguard_e2e_test`.

## K. Related Files
- [docker-compose.yml](../docker-compose.yml.explanation.md): the e2e profile.
