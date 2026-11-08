# auth.py

Source: [backend/app/api/routes/auth.py](auth.py)

## A. File Purpose
Provides bearer sign-in for API clients, cookie sessions for the web application, and the routes for a user's own account.

## B. Why This File Exists
PRD 8.2 does not list these, but authentication is a Phase 3 deliverable and clients need a way to get a token. These routes are additions, permitted by PRD section 13.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.core.errors`, `app.security.dependencies`, `app.security.sessions`, `app.security.tokens`, `app.services.auth_service`.
- **External services / database:** through the service.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `_client`
Returns the client address used for rate limiting, which is the proxy's report only when that proxy is trusted.

### `login`
- **Purpose:** `POST /api/v1/auth/login`.
- **Parameters / types:** `request`, `db`, `form: OAuth2PasswordRequestForm`. **Returns / type:** `TokenResponse`.
- **Internal processing:** takes the client address and calls the service.
- **Error handling:** 401 for bad credentials, 429 when limited, 422 for a malformed form.
- **Calls:** `auth_service.authenticate`. **Used by:** clients, and Swagger's Authorize button.

### `start_session`
- **Purpose:** `POST /api/v1/auth/session`, for the web app.
- **Parameters / types:** `request`, `response`, `db`, `body: SessionCreate` (JSON). **Returns / type:** `CurrentUserView`.
- **Internal processing:** checks `Origin` if present, verifies credentials with the same rate limit as `login`, opens a session and sets the cookies. No token is in the body.
- **Error handling:** 401 for bad credentials, 403 for another origin, 422 for a non-JSON body, 429 when limited.
- **Calls:** `require_allowed_origin`, `verify_login`, `open_session`, `set_session_cookies`, `current_user_view`. **Used by:** the frontend.

### `end_session`
- **Purpose:** `DELETE /api/v1/auth/session`.
- **Parameters / types:** `request`, `response`, `db`. **Returns / type:** `None`, status 204.
- **Internal processing:** for a live session, checks origin and CSRF, then revokes it. In every case it clears the cookies.
- **Error handling:** 403 if a live session's CSRF check fails. An expired or missing session just clears cookies.
- **Calls:** `find_active_session`, `revoke_session`, `clear_session_cookies`. **Used by:** the frontend.

### `read_current_user`
- **Purpose:** `GET /api/v1/auth/me`.
- **Parameters / types:** `request`, `user: CurrentUser`. **Returns / type:** `CurrentUserView`.
- **Internal processing:** adds permissions and, for a cookie session, its expiry.
- **Error handling:** 401 without a valid token.
- **Calls:** none. **Used by:** clients.

### `change_own_password`
- **Purpose:** `POST /api/v1/auth/change-password`.
- **Parameters / types:** `user`, `db`, `body: PasswordChange`. **Returns / type:** `None`, status 204.
- **Internal processing:** calls the service.
- **Error handling:** 401 for a wrong current password, 422 for a short new one.
- **Calls:** `auth_service.change_password`. **Used by:** clients.

## E. Classes Explained
None.

## F. Execution Flow
Dependencies run, the route calls the service, and the response is filtered through its schema.

## G. Input and Output
Login takes a form with `username` and `password`, and returns `{"access_token": "...", "token_type": "bearer"}`.

## H. Important Technical Concepts
- **Form encoding and `username`:** that is what the OAuth2 password flow specifies, and what makes `/docs` work. The value is the user's email.
- **JSON for the session route:** HTML forms cannot send JSON, so a hostile page cannot submit a sign-in, and a cross-origin JSON request needs a CORS preflight that other origins fail.

## I. Example
```powershell
curl.exe -X POST http://127.0.0.1:8010/api/v1/auth/login -d "username=ana@example.com" -d "password=..."
```

## J. Maintenance Notes
Keep logic in the service. Phase 4 must not store tokens anywhere readable by third-party scripts.

## K. Related Files
- [auth_service.py](../../services/auth_service.py.explanation.md): the rules.
- [auth.py schemas](../schemas/auth.py.explanation.md): the shapes.
- [test_auth.py](../../../tests/api/test_auth.py.explanation.md): tests.
