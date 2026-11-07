# auth.py

Source: [backend/app/api/routes/auth.py](auth.py)

## A. File Purpose
Provides the sign-in route and the routes for a user's own account.

## B. Why This File Exists
PRD 8.2 does not list these, but authentication is a Phase 3 deliverable and clients need a way to get a token. These routes are additions, permitted by PRD section 13.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.security.dependencies`, `app.services.auth_service`.
- **External services / database:** through the service.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `login`
- **Purpose:** `POST /api/v1/auth/login`.
- **Parameters / types:** `request`, `db`, `form: OAuth2PasswordRequestForm`. **Returns / type:** `TokenResponse`.
- **Internal processing:** takes the client address and calls the service.
- **Error handling:** 401 for bad credentials, 429 when limited, 422 for a malformed form.
- **Calls:** `auth_service.authenticate`. **Used by:** clients, and Swagger's Authorize button.

### `read_current_user`
- **Purpose:** `GET /api/v1/auth/me`.
- **Parameters / types:** `user: CurrentUser`. **Returns / type:** `UserView`.
- **Internal processing:** none beyond serialising.
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
