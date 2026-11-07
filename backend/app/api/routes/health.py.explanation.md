# health.py

Source: [backend/app/api/routes/health.py](health.py)

## A. File Purpose
Provides the public liveness check and the signed-in system status.

## B. Why This File Exists
PRD 8.2 lists both endpoints, and PRD 11.3 requires a health endpoint for deployment. Container health checks need something quick that has no dependencies.

## C. Dependencies
- **Libraries:** `fastapi`, `pydantic`.
- **Internal modules:** `app.core.config`, `app.database.session`, `app.security`, `app.api.schemas.common`.
- **External services / database:** a test query for the status route.
- **Depended on by:** `app/api/router.py`, the Dockerfile health check, Phase 4 settings page.

## D. Every Function Explained

### `health`
- **Purpose:** `GET /health`.
- **Parameters / types:** none. **Returns / type:** `HealthResponse`.
- **Internal processing:** none.
- **Error handling:** none needed. **Calls:** none. **Used by:** Docker and hosting platforms.

### `system_status`
- **Purpose:** `GET /api/v1/system/status`.
- **Parameters / types:** `_user`, `db`, `model`. **Returns / type:** `SystemStatus`.
- **Internal processing:** runs a test query, and reports `degraded` if it fails.
- **Error handling:** a database failure becomes `database_available: false` rather than an error.
- **Calls:** `database_is_available`. **Used by:** signed-in clients.

## E. Classes Explained

### `HealthResponse`
`status`. **Inheritance:** `BaseModel`.

### `SystemStatus`
Application version, environment, database and model state, and the frozen hash and threshold. **Inheritance:** `ApiModel`.

## F. Execution Flow
`/health` returns immediately. The status route checks its permission, then the database.

## G. Input and Output
`/health` returns `{"status": "ok"}`.

## H. Important Technical Concepts
- **`model_loaded` is always true when this route answers:** the application refuses to start without a verified model, so a running API has one.
- **Public versus signed in:** `/health` reveals nothing. Version and environment details need a login.

## I. Example
```powershell
curl.exe http://127.0.0.1:8010/health
```

## J. Maintenance Notes
Keep `/health` free of dependencies. If it checked the database, a database outage would make the platform restart a healthy API process.

## K. Related Files
- [session.py](../../database/session.py.explanation.md): `database_is_available`.
- [Dockerfile](../../../Dockerfile.explanation.md): uses `/health`.
