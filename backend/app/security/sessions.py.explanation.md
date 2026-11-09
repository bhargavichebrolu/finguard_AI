# sessions.py

Source: [backend/app/security/sessions.py](sessions.py)

## A. File Purpose
Creates, checks and ends browser sessions held in HttpOnly cookies, and protects them against cross-site request forgery (CSRF).

## B. Why This File Exists
The Phase 4 authorisation requires HttpOnly authentication cookies with CSRF protection, strict CORS, SameSite, expiry and logout, and forbids keeping tokens in browser storage. Cookies are sent automatically by the browser, which is what makes CSRF possible, so a cookie session needs these extra checks where a bearer token does not.

## C. Dependencies
- **Libraries:** `fastapi`, `sqlalchemy`, `hashlib`, `hmac`, `secrets`.
- **Internal modules:** `app.core.config`, `app.core.errors`, `app.models.records`, `app.security.tokens`, `app.services.audit_service`.
- **External services / database:** the `user_sessions` and `audit_logs` tables.
- **Depended on by:** `security/dependencies.py`, `api/routes/auth.py`.

## D. Every Function Explained

### `_digest`
Returns the SHA-256 of a string, so CSRF tokens are stored as hashes rather than as usable values.

### `open_session`
- **Purpose:** start a session.
- **Parameters / types:** `db: Session`, `user: User`. **Returns / type:** `tuple[str, str, UserSession]`, giving the signed token, the CSRF token and the row.
- **Internal processing:** makes a random CSRF token, stores its hash with an expiry `access_token_minutes` ahead, writes an audit entry, and signs a token naming the row (`sid`).
- **Error handling:** database errors propagate.
- **Calls:** `create_access_token`, `record_event`. **Used by:** `start_session` in the auth route.

### `set_session_cookies`
- **Purpose:** attach both cookies to a response.
- **Parameters / types:** `response`, `token`, `csrf_token`. **Returns / type:** `None`.
- **Internal processing:** the session cookie is `HttpOnly`, `SameSite=Strict`, `Path=/api`, with `Max-Age` set to the token lifetime. The CSRF cookie has the same flags except `HttpOnly`, and uses `Path=/`, because page script must read it on every page.
- **Error handling:** none needed. **Calls:** `response.set_cookie`. **Used by:** the auth route.

### `clear_session_cookies`
Deletes both cookies with matching attributes, since a browser only deletes a cookie whose path matches.

### `find_active_session`
- **Purpose:** decide whether a token's session is live.
- **Parameters / types:** `db`, `claims: TokenClaims`. **Returns / type:** `UserSession | None`.
- **Internal processing:** the row must exist, belong to the token's user, not be revoked and not be expired.
- **Error handling:** returns `None` for any failure, which callers turn into 401.
- **Calls:** `db.get`. **Used by:** `get_current_user`, `end_session`.

### `require_allowed_origin`
Refuses a cookie request that changes something unless its `Origin` header is in `CORS_ALLOWED_ORIGINS`. A missing `Origin` is refused too, because browsers send one with these requests. Raises `PermissionDeniedError`.

### `require_csrf_token`
Compares the `X-CSRF-Token` header with the stored hash using `hmac.compare_digest`, which takes the same time whatever the input. Raises `PermissionDeniedError`.

### `revoke_session`
Marks one row revoked, writes an audit entry and commits. The user's other sessions stay active.

### `session_cookie_name`
`__Secure-finguard_session` when cookies are Secure (production), otherwise `finguard_session`. Phase 5 M5.

### `csrf_cookie_name`
`__Host-finguard_csrf` when cookies are Secure, otherwise `finguard_csrf`. Phase 5 M5.

## E. Classes Explained
None.

## F. Execution Flow
Sign-in calls `open_session`, then `set_session_cookies`. Each request calls `find_active_session`, and `require_allowed_origin` and `require_csrf_token` for unsafe methods. Sign-out calls `revoke_session`, then `clear_session_cookies`.

## G. Input and Output
Input: a user, or a request. Output: cookies, a session row, or a refusal.

## H. Important Technical Concepts
- **Cookie prefixes (Phase 5 M5):** browsers refuse a `__Secure-` cookie without Secure, and a `__Host-` cookie that also has a Domain or a path other than `/`, so a look-alike cookie set by another page or subdomain cannot replace them. Only the CSRF cookie can take `__Host-`, because the session cookie is scoped to `/api`. With Secure cookies the unprefixed names are not read at all.
- **Why CSRF is still possible with SameSite=Strict:** Strict stops other sites causing the cookie to be sent, but it is one layer. The origin check and CSRF token remain correct even if an older browser ignores SameSite.
- **Double submit, tied to the session:** another site can neither read the CSRF cookie nor guess its value. The server compares the header with the hash stored for this session, not with the cookie, so a token planted from another session fails too.
- **Same origin:** the web app calls `/api` on its own origin, through the Vite proxy locally and a host rewrite in deployment. That keeps cookies first-party, which `SameSite=Strict` needs and browsers' third-party cookie blocking would otherwise defeat.
- **Secure flag:** set in production. Over plain HTTP during development it is off, because browsers refuse to store Secure cookies from an insecure origin. `config.py` refuses `SESSION_COOKIE_SECURE=false` in production.

## I. Example
```python
token, csrf, row = open_session(db, user)
set_session_cookies(response, token, csrf)
```

## J. Maintenance Notes
Keep the cookie attributes in `set_session_cookies` and `clear_session_cookies` identical. Expired rows are not deleted yet, so a periodic clean-up will be needed for long-running use.

## K. Related Files
- [dependencies.py](dependencies.py.explanation.md): enforces these checks on each request.
- [auth.py route](../api/routes/auth.py.explanation.md): sign-in and sign-out.
- [test_sessions.py](../../tests/api/test_sessions.py.explanation.md): tests.
- [ADR 0004](../../../docs/decisions/0004-phase-4-decisions.md): decisions.
