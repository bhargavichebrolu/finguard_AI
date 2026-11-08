# test_auth.py

Source: [backend/tests/api/test_auth.py](test_auth.py)

## A. File Purpose
Tests health checks, sign-in, token handling, role permissions, account management and safe error responses through the real API.

## B. Why This File Exists
PRD 14.2 requires tests of the health endpoint, authentication and error responses. Security rules are worth testing from an attacker's angle: forged, expired and unsigned tokens, and wrong roles.

## C. Dependencies
- **Libraries:** `pytest`, `pyjwt`, `fastapi`, `sqlalchemy`.
- **Internal modules:** `app.core`, `app.models`, `app.security`, `tests/api/conftest.py`.
- **External services / database:** PostgreSQL and the frozen model.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `login`
Sends the login form. Parameters: `client`, `email`, `password`. Returns the response.

### `bearer`
Builds an `Authorization` header for a user.

### `documented_operations`
Returns every method, path and operation from `/openapi.json`. FastAPI generates that schema from the real routes, so it cannot go out of date, and a new route is covered automatically.

### `explode`
Nested stand-in that raises an error containing a fake secret, used by `test_unexpected_errors_reveal_nothing`.

**Common to every test below:** parameters are fixtures, and failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_health_is_public_and_reveals_nothing` | `/health` works without a token and returns only a status. |
| `test_openapi_documents_the_api` | `/docs` and the schema work, and bearer security is declared. |
| `test_system_status_reports_the_frozen_model` | Status shows the frozen version, hash and threshold. |
| `test_login_returns_a_working_token` | A real login works, and no hash is returned. |
| `test_login_email_is_not_case_sensitive` | Capitals and spaces do not matter. |
| `test_wrong_password_and_unknown_email_look_the_same` | The response does not reveal which emails exist. |
| `test_inactive_account_cannot_log_in` | Deactivated accounts are refused. |
| `test_repeated_failures_are_rate_limited_even_with_the_right_password` | Guessing is stopped, with `Retry-After`. |
| `test_success_clears_the_failure_count` | A real user is not penalised for earlier typos. |
| `test_failed_login_is_audited_without_the_email_or_password` | Failures are recorded without sensitive text. |
| `test_requests_without_a_valid_token_are_refused` | Missing and malformed tokens give 401. |
| `test_expired_token_is_refused` | Expiry is enforced. |
| `test_token_signed_with_another_key_is_refused` | Forged signatures fail. |
| `test_unsigned_token_is_refused` | The `none` algorithm attack fails. |
| `test_token_for_a_deleted_user_is_refused` | A valid signature alone is not enough. |
| `test_deactivation_applies_immediately` | An existing token stops working at once. |
| `test_role_change_applies_immediately` | Authorisation follows the database, not the token. |
| `test_changing_password_invalidates_old_tokens` | Old tokens and the old password stop working. |
| `test_changing_password_needs_the_current_one` | A stolen token alone cannot change the password. |
| `test_permissions_matrix` | The full role table, stated separately from the code. |
| `test_every_api_route_requires_authentication` | Every route except the public ones gives 401 without a token, including any added later. |
| `test_every_route_declares_a_response_schema` | PRD 8.2, except routes that stream files. |
| `test_routes_that_accept_a_json_body_declare_a_schema` | PRD 8.2 for requests. |
| `test_non_admins_cannot_manage_users_or_read_the_audit_log` | Each lesser role gets 403. |
| `test_admin_can_create_a_user_who_can_then_log_in` | Full account creation, with an Argon2id hash stored. |
| `test_duplicate_email_is_a_conflict` | Duplicates give 409, ignoring case. |
| `test_rejected_password_is_not_echoed` | A refused password is not repeated in the response. |
| `test_unknown_fields_are_refused` | Extra fields give 422. |
| `test_last_admin_cannot_be_removed` | Neither deactivation nor demotion can cause a lockout. |
| `test_admin_can_be_removed_when_another_exists` | The rule only blocks the last one. |
| `test_user_changes_are_audited` | Who, what and which record are recorded. |
| `test_unknown_user_is_not_found` | 404 for a missing user. |
| `test_page_size_is_capped` | Oversized and negative paging is refused. |
| `test_responses_carry_security_headers` | Headers and request ID are present. |
| `test_api_responses_are_not_cached` | `no-store` on API routes. |
| `test_unknown_route_uses_the_error_format` | Framework errors match the project's format. |
| `test_unexpected_errors_reveal_nothing` | A crash returns a generic message without internals. |
| `test_oversized_request_is_refused_before_reading` | The early size limit works. |
| `test_cors_allows_only_the_configured_origin` | Other origins get no CORS approval. |

## E. Classes Explained
None.

## F. Execution Flow
The `session` fixture empties the database before each test.

## G. Input and Output
Input: HTTP requests. Output: pass or fail.

## H. Important Technical Concepts
- **`test_every_api_route_requires_authentication` walks the OpenAPI schema,** so a new route that forgets its check fails automatically. An earlier version walked `app.routes`, which held no routes in this FastAPI version. Its `checked > 0` guard exposed that, so the test now also requires a minimum number of routes, and cannot pass by checking nothing.

## I. Example
```powershell
docker compose up -d --wait db
uv run --project backend pytest backend/tests/api/test_auth.py
```

## J. Maintenance Notes
Add new public paths to `PUBLIC_PATHS` only deliberately. Phase 4 added `/api/v1/auth/session`, because signing in and out must work without a session.

## K. Related Files
- [conftest.py](conftest.py.explanation.md): fixtures.
- [dependencies.py](../../app/security/dependencies.py.explanation.md): the checks.
- [errors.py](../../app/core/errors.py.explanation.md): error handling.
