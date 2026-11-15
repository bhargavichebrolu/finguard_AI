# test_sessions.py

Source: [backend/tests/api/test_sessions.py](test_sessions.py)

## A. File Purpose
Tests browser sessions through the real API: cookie flags, CSRF, origin checks, expiry, logout, and how sessions end.

## B. Why This File Exists
Each requirement in the authorisation's cookie decision needs proof, and most of that proof comes from attacks failing: forged CSRF tokens, other origins, replayed cookies after logout.

## C. Dependencies
- **Libraries:** `pytest`, `fastapi.testclient`, `sqlalchemy`.
- **Internal modules:** `app.core.config`, `app.models`, `app.security.sessions`, API fixtures.
- **External services / database:** PostgreSQL and the frozen model.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `browser`
Fixture returning a separate client with its own cookie jar, standing in for one browser.

### `sign_in`
Posts a JSON sign-in with an `Origin` header.

### `csrf_headers`
Builds the `Origin` and `X-CSRF-Token` headers from the client's CSRF cookie, as page script does.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_sign_in_sets_httponly_strict_cookies_and_no_token_in_the_body` | Cookie flags, path and lifetime, and no token in the body. |
| `test_cookies_are_secure_in_production` | Secure is on in production and off in development by default. |
| `test_me_reports_permissions_and_expiry` | Permissions come from the role table, with the session expiry. |
| `test_wrong_password_sets_no_cookie` | A failure leaves no session. |
| `test_sign_in_from_another_origin_is_refused` | Login CSRF is blocked. |
| `test_sign_in_accepts_json_only` | A cross-site HTML form cannot submit a sign-in. |
| `test_reads_work_with_the_cookie_alone` | Safe requests need no CSRF token. |
| `test_changes_need_the_csrf_header` | Missing and forged tokens are refused, and the real one works. |
| `test_changes_need_an_allowed_origin` | No origin, another origin and `null` are all refused. |
| `test_csrf_token_of_another_session_is_refused` | Tokens are bound to their own session. |
| `test_bearer_tokens_still_work_without_csrf` | Phase 3 API clients are unaffected. |
| `test_bearer_token_in_the_session_cookie_is_refused` | A token without a session cannot pose as one. |
| `test_logout_revokes_only_this_session` | A replayed cookie fails after logout, the user's other session continues, and an audit entry is written. |
| `test_logout_needs_csrf_for_a_live_session` | Another site cannot sign you out. |
| `test_logout_without_a_session_just_clears_cookies` | Logout always succeeds in removing cookies. |
| `test_expired_session_is_refused` | Server-side expiry is enforced. |
| `test_password_change_ends_cookie_sessions` | All sessions end after a password change. |
| `test_deactivation_ends_cookie_sessions` | Deactivation applies at once. |
| `test_session_sign_in_is_rate_limited` | Browser sign-in shares the login limit. |
| `test_cors_allows_credentials_and_the_csrf_header_for_listed_origins` | CORS is strict, and credentials are allowed only for listed origins. |

### `test_secure_cookies_carry_browser_enforced_prefixes`
Phase 5 M5: over HTTPS with Secure cookies, sign-in sets `__Secure-finguard_session` (HttpOnly, Path=/api) and `__Host-finguard_csrf` (Path=/, no Domain); signed-in reads and CSRF-protected changes work; a cookie under the unprefixed name is refused.

## E. Classes Explained
None.

## F. Execution Flow
The `session` fixture empties the database. Each test signs in with fresh clients.

## G. Input and Output
Input: HTTP requests with cookies. Output: pass or fail.

## H. Important Technical Concepts
- **Separate clients are separate browsers,** so tests can show that one session's logout leaves another running.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_sessions.py
```

## J. Maintenance Notes
Changing cookie attributes needs updates here and in `clear_session_cookies`.

## K. Related Files
- [sessions.py](../../app/security/sessions.py.explanation.md): the code under test.
- [auth.py route](../../app/api/routes/auth.py.explanation.md): the routes.
