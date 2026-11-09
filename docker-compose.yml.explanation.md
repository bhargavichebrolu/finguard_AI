# docker-compose.yml

Source: [docker-compose.yml](docker-compose.yml)

## A. File Purpose
Defines the local stack: PostgreSQL (`db`), a one-shot migration job (`migrate`) and the API (`api`). It meets PRD 11.6, which asks for a PostgreSQL development service, health checks, environment variables and a persistent development volume.

## B. Why This File Exists
One command should start a working stack. It is also where the database's security settings are recorded, so they apply from the first start of a volume rather than depending on someone remembering them.

## C. Dependencies
- **Libraries / tools:** Docker Compose v2 or later.
- **Internal files:** `.env` (values), `docker/postgres/init/` (first-start SQL), `backend/Dockerfile` (image), `artifacts/` (frozen model, mounted read-only).
- **External services / database:** the official `postgres:17-alpine` image.
- **Depended on by:** developers, and the database tests through the published port.

## D. Every Function Explained
No functions: this is declarative configuration. The settings that matter:

### `db` service
- `POSTGRES_INITDB_ARGS` sets `scram-sha-256` for local and host rules. The official image otherwise writes `trust` for local and loopback connections. Diagnostics showed a wrong password being accepted over loopback under those defaults.
- Host port bound to `127.0.0.1`, so the database is reachable from this computer only.
- `${VAR:?message}` makes Compose stop if a credential is missing, instead of starting with an empty value.

### `migrate` service
Runs `alembic upgrade head` once, after the database is healthy. It shares the `finguard-api:local` image with `api`, so the image is built once. Keeping this separate means the API never changes the schema on start-up.

### `api` service
Starts only after `migrate` succeeds. `./artifacts` is mounted read-only, so the running API cannot alter the frozen model. Its environment is shared with `migrate` through the `&api-environment` YAML anchor. Phase 4 added `MODEL_REPORT_PATH`, and `TRUSTED_PROXY_IPS`, which is empty unless set in `.env`.

### `migrate-e2e` and `api-e2e` services (profile `e2e`)
The browser-test stack. Same image and settings as `api`, through the `<<: *api-environment` merge, but with `APP_ENV=test`, the test database (`TEST_DB_NAME`), only `http://127.0.0.1:4173` allowed as an origin, no trusted proxies, and port 127.0.0.1:8011. `SECRET_KEY` comes from `E2E_SECRET_KEY`, which `scripts/e2e_stack.py` generates per start; without it the API refuses to start. Profiles keep these out of a plain `docker compose up`. Since Phase 5 they use their own database, `${E2E_DB_NAME:-finguard_e2e_test}`, created by `scripts/e2e_stack.py`.

### `WEB_CONCURRENCY`, `RATE_LIMIT_STORE` (Phase 5 M3)
The API environment passes `WEB_CONCURRENCY` (default 1) to Uvicorn as its worker count. The browser-test services take `E2E_WEB_CONCURRENCY` and `E2E_RATE_LIMIT_STORE`, used only for the comparison measurements.

## E. Classes Explained
None.

## F. Execution Flow
`db` starts and passes its health check, `migrate` applies migrations and exits, then `api` starts, verifies the model and serves requests.

## G. Input and Output
Input: `.env`. Output: three containers and the named volume `finguard_pgdata`, which survives `docker compose down` and is deleted only by `docker compose down -v`.

## H. Important Technical Concepts
- **Pinned image (Phase 5 M1):** `postgres:17-alpine` is pinned by digest to the image tested. Changing the pin recreates the `db` container on the next `up`; the named volume keeps the data.
- **`POSTGRES_INITDB_ARGS` applies once.** It only takes effect when a volume is first initialised. An older volume keeps its old rules until it is recreated.
- **Container and host addresses differ.** Inside Compose the database host is `db`. From Windows it is `127.0.0.1` on `POSTGRES_HOST_PORT`, not `localhost`, because only IPv4 is published.
- **`$$` in the health check** stops Compose substituting the value itself, so the shell inside the container reads it.

## I. Example
```powershell
uv run --project backend python scripts/generate_env.py
docker compose up -d db
docker compose up -d --build
```

## J. Maintenance Notes
Changing the PostgreSQL major version needs a data migration, not just a new tag. Never add `POSTGRES_HOST_AUTH_METHOD=trust`. If a port is taken, change `POSTGRES_HOST_PORT` or `API_HOST_PORT` in `.env`. Both default to the usual ports, and 8000 was already in use on the development computer.

## K. Related Files
- [01_app_role.sql](docker/postgres/init/01_app_role.sql.explanation.md): creates the API's role and the test database.
- [.env.example](.env.example.explanation.md): the variables used here.
- [Dockerfile](backend/Dockerfile.explanation.md): the API image.
- [ADR 0003](docs/decisions/0003-phase-3-decisions.md): the two-role decision.
