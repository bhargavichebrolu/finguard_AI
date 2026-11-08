# ADR 0004: Phase 4 decisions

Status: accepted for Phase 4, subject to review at the phase gate. It builds on the approved plan in [docs/plans/phase-4-plan.md](../plans/phase-4-plan.md).

## 1. Browser authentication uses HttpOnly cookies
Chosen by the reviewer over in-memory tokens. Sign-in through `POST /api/v1/auth/session` sets two cookies:

| Cookie | Flags | Holds |
|---|---|---|
| `finguard_session` | HttpOnly, SameSite=Strict, Path=/api, Max-Age 30 minutes, Secure in production | A signed token naming a `user_sessions` row |
| `finguard_csrf` | SameSite=Strict, Path=/, Max-Age 30 minutes, Secure in production, readable by script | A random CSRF token, stored on the server only as a hash |

- **Requests that change data** must also send `X-CSRF-Token`, matching this session's token, and an `Origin` in `CORS_ALLOWED_ORIGINS`.
- **Logout** (`DELETE /api/v1/auth/session`) revokes the row, ending that session only.
- **Ending all sessions:** password changes and deactivation end all of them.
- **Storage:** no token is ever placed in `localStorage` or `sessionStorage`, or returned in a response body to the web app.

The bearer token route `/api/v1/auth/login` stays for Swagger and API clients, preserving Phase 3 behaviour. Browsers never attach that header automatically, so it needs no CSRF token.

## 2. The web application calls the API on its own origin
The frontend calls relative `/api` paths. Locally, the Vite development and preview servers proxy `/api` to the backend. In deployment the host must do the same, which is a Phase 6 requirement. This keeps cookies first-party, which `SameSite=Strict` requires, and avoids browsers' third-party cookie blocking. It also lets the frontend's Content Security Policy use `connect-src 'self'`.

## 3. Secure cookies in production only
Browsers do not store Secure cookies from plain-HTTP origins. Locally the API runs on HTTP, so `Secure` is off outside production by default, and `config.py` refuses to start production with it off.

## 4. Proxy trust is off by default
`TRUSTED_PROXY_IPS` is empty unless configured, and a wildcard is refused. Uvicorn itself trusts `X-Forwarded-For` from 127.0.0.1 by default, so the Dockerfile and Makefile pass `--no-proxy-headers`. Forwarded addresses are honoured only through `ProxyHeadersMiddleware`, added when proxies are listed.

## 5. Content Security Policy on the API
JSON responses allow loading nothing: `default-src 'none'; frame-ancestors 'none'`. `/docs` and `/redoc` get a separate policy allowing the CDN and inline start-up script FastAPI's pages need, because the PRD requires Swagger.

## 6. The model report is derived, pinned and read-only
`scripts/export_model_report.py` copies values from six saved Phase 2 files into `artifacts/metadata/model_v1_report.json`. That is a new file, and no existing file changes. Its hash is pinned in `frozen_model.py`, and start-up refuses a different file. `GET /api/v1/models/report` serves it unchanged.

## 7. Permissions come from the server
`/auth/me` returns the caller's permission list from the same table the API enforces, so the interface never keeps its own copy.

## 8. Restricted assignee list
`GET /api/v1/users/assignable` returns only the identifier, email and role of active investigators and admins, to roles that can update investigations. The full user list stays admin-only.
