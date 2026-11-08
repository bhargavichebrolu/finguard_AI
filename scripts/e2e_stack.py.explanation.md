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

### `up`
Builds the image, then starts `api-e2e` (after `migrate-e2e`) with a freshly generated `E2E_SECRET_KEY`, recreating it so it registers the model again.

### `down`
Stops and removes the two browser-test containers.

### `main`
Parses `up` or `down`.

## E. Classes Explained
None.

## F. Execution Flow
Build, migrate, start, wait for health.

## G. Input and Output
Output: the `finguard-api-e2e-1` container on 127.0.0.1:8011.

## H. Important Technical Concepts
- **The signing key** exists only in this process's environment for the Compose call. Without it the API refuses to start, because `SECRET_KEY` must have 32 characters.

## I. Example
```powershell
python scripts/e2e_stack.py up
python scripts/e2e_stack.py down
```

## J. Maintenance Notes
Run `up` again after the backend test suite, which empties the test database.

## K. Related Files
- [docker-compose.yml](../docker-compose.yml.explanation.md): the e2e profile.
