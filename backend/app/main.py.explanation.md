# main.py

Source: [backend/app/main.py](main.py)

## A. File Purpose
Builds the FastAPI application, and defines what happens at start-up.

## B. Why This File Exists
It is the entry point for `uvicorn`. It also records the start-up rule from the authorisation: load the existing model after verifying it, and never retrain.

## C. Dependencies
- **Libraries:** `fastapi`, `contextlib`, `logging`.
- **Internal modules:** `app.api.router`, `app.core`, `app.database.session`, `app.services`.
- **External services / database:** PostgreSQL, and `artifacts/`.
- **Depended on by:** `uvicorn` through `app.main:app`, and tests.

## D. Every Function Explained

### `lifespan`
- **Purpose:** run start-up steps.
- **Parameters / types:** `app: FastAPI`. **Returns / type:** an async iterator.
- **Internal processing:** verifies and loads the model, records it in `model_versions`, removes stale temporary upload files, stores the model on `app.state`, and starts this process's `BatchWorker` unless `BATCH_WORKER_ENABLED` is false. On shutdown it stops the worker, which gives its job back for another process to resume. Since Phase 5 M4 it no longer fails unfinished jobs at start-up.
- **Error handling:** any exception stops the application, so it can never run without a verified model.
- **Calls:** `load_verified_model`, `register_active_model`, `remove_stale_uploads`, `BatchWorker`. **Used by:** FastAPI.

### `create_app`
- **Purpose:** build and configure the application.
- **Parameters / types:** none. **Returns / type:** `FastAPI`.
- **Internal processing:** sets logging, error handlers, routes and middleware.
- **Error handling:** invalid settings raise here.
- **Calls:** `configure_logging`, `register_exception_handlers`. **Used by:** the module body, tests.
- **Proxy middleware:** added only when trusted proxies are configured.

## E. Classes Explained
None.

## F. Execution Flow
Import builds `app`. When the server starts, `lifespan` runs up to `yield`. Requests are then served.

## G. Input and Output
Input: settings and artefacts. Output: a running API, with interactive documentation at `/docs` and the schema at `/openapi.json`.

## H. Important Technical Concepts
- **No migrations at start-up:** schema changes are a controlled step (PRD 11.4), done by the `migrate` service. If the schema is behind, start-up fails when it first touches the database.
- **CORS:** explicit origins only, with credentials allowed and `X-CSRF-Token` permitted, because the web app uses cookie sessions. The app normally calls the API on its own origin through a proxy, so CORS matters mainly for direct development calls.
- **Proxy trust:** `ProxyHeadersMiddleware` is added only when `TRUSTED_PROXY_IPS` lists proxies. It is outermost, so later steps see the address the proxy reported.
- **Middleware order:** the last one added is the outermost, so CORS headers also appear on responses from `RequestContextMiddleware`.

## I. Example
```powershell
cd backend
uv run uvicorn app.main:app --port 8010
```

## J. Maintenance Notes
Keep `lifespan` fast and free of training. Anything needing the data should not run here. A single worker is assumed by rate limits and batch recovery.

## K. Related Files
- [model_service.py](services/model_service.py.explanation.md): verification.
- [router.py](api/router.py.explanation.md): routes.
- [middleware.py](core/middleware.py.explanation.md): request context.
- [ADR 0003](../../docs/decisions/0003-phase-3-decisions.md): decisions.
