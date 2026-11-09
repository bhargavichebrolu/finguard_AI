# prodlike_stack.py

Source: [scripts/prodlike_stack.py](prodlike_stack.py)

## A. File Purpose
Starts or stops the production-like stack: HTTPS through Caddy, one origin, and the API with `APP_ENV=production`.

## B. Why This File Exists
Phase 5 M5 required the complete HTTPS path to be tested, with production cookies, CSRF, CORS and proxy trust, without deploying anywhere.

## C. Dependencies
- **Libraries:** Python standard library.
- **Internal modules:** `scripts/e2e_stack.py` (`ensure_database`).
- **External services / database:** Docker Compose (profile `prodlike`), npm.
- **Depended on by:** Developers, before `npm run test:prodlike`.

## D. Every Function Explained

### `database_name`
`PRODLIKE_DB_NAME` or `finguard_prodlike_test`, refusing anything not lower case and ending in `_test`.

### `compose`
Runs `docker compose --profile prodlike`.

### `build_frontend`
Builds the frontend that Caddy serves.

### `up`
Creates the database if needed, builds the frontend and image, then starts the API and Caddy with a new random `PRODLIKE_SECRET_KEY`.

### `down`
Stops and removes the production-like containers.

### `main`
Parses `up` or `down`.

## E. Classes Explained
None.

## F. Execution Flow
Database, frontend build, image build, migrate, start.

## G. Input and Output
Output: https://127.0.0.1:8443 (HTTP on 8082 redirects there) and the API on 127.0.0.1:8012.

## H. Important Technical Concepts
- **`DEFAULT_DATABASE`, `PROFILE`:** the database name and Compose profile.
- **Production settings apply:** the API refuses to start unless cookies are Secure, rate limits are in the database, CORS has no localhost and the signing key is real.

## I. Example
```powershell
python scripts/prodlike_stack.py up
cd frontend; npm run test:prodlike
python scripts/prodlike_stack.py down
```

## J. Maintenance Notes
Keep the Caddyfile, Compose addresses and the tests' constants in step.

## K. Related Files
- [Caddyfile](../docker/caddy/Caddyfile.explanation.md): the proxy.
- [e2e_stack.py](e2e_stack.py.explanation.md): shared database creation.
