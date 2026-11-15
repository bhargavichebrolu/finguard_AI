# auth.spec.ts

Source: [frontend/tests/e2e/auth.spec.ts](auth.spec.ts)

## A. File Purpose
Browser tests for signing in and out, sessions, cookies, CSRF, origin checks, security headers and CORS against the real API.

## B. Why This File Exists
Authorisation decision 1 requires HttpOnly cookies, CSRF protection, strict CORS, SameSite, expiry and logout, and no tokens in browser storage. These tests check each in a real browser.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_e2e_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `preflight`
A local value in the CORS test, not a function: sends an `OPTIONS` preflight from a chosen origin.

## E. Classes Explained
None.

## F. Execution Flow
Signed-out tests start with `NO_SESSION`; the CSRF tests use the analyst's saved state.

## G. Input and Output
| Test | Proves |
|---|---|
| signs in, survives a reload, keeps tokens out of storage, and signs out | Cookie flags (HttpOnly, SameSite=Strict, Path=/api; Secure off only on this plain-HTTP test API), nothing in localStorage or sessionStorage, reload keeps the session, sign-out revokes it on the server, a replayed cookie is refused. |
| gives one message for a wrong password and an unknown account | No account enumeration. |
| limits repeated failed sign-ins | Five failures, then 429 with Retry-After even for the right password, and the page message. |
| ends a session that has expired on the server | Expiry, set in the database, ends the session with a notice. |
| rejects a tampered session cookie | A forged cookie leads to sign-in. |
| refuses sign-in from another origin | 403. |
| needs the CSRF token and an allowed origin, but reads need neither | Missing, wrong and foreign-origin requests get 403; correct ones succeed. |
| sends security headers on API responses and on the page | CSP and nosniff. |
| CORS answers only the configured origin | No Access-Control-Allow-Origin for other origins; credentials allowed for the preview origin. |

## H. Important Technical Concepts
- **SameSite (Phase 5 M6):** the sign-in test reads the `Set-Cookie` header the server sent and requires `HttpOnly` and `SameSite=Strict` in every browser. It also checks the attribute the browser stored, except in WebKit: Playwright's WebKit build on Windows reports `None` for these cookies although the server sends `Strict`. The CSRF token and origin check protect changes regardless.
- **Secure flag:** the test API runs over plain HTTP with `APP_ENV=test`, so `Secure` is off here. Production refuses to start with it off (`backend/tests/unit/test_config.py`).
- **Rate-limit isolation:** the limit lives in the API's memory for a minute, so the lockout test creates a new account through the API each run.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/auth.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
Do not weaken an assertion to make a run pass; a failure here is a security regression.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [sessions.py](../../../backend/app/security/sessions.py.explanation.md): the server side.
