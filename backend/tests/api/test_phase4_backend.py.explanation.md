# test_phase4_backend.py

Source: [backend/tests/api/test_phase4_backend.py](test_phase4_backend.py)

## A. File Purpose
Tests the Phase 4 backend additions: the assignee list, the served model report, Content Security Policy headers, and trust of forwarded client addresses.

## B. Why This File Exists
The authorisation approved these additions with conditions. Proxy trust must be off by default, and the report must come only from saved outputs and be served unchanged.

## C. Dependencies
- **Libraries:** `pytest`, `fastapi.testclient`, `pydantic`.
- **Internal modules:** `app.core`, `app.models.enums`, `app.main`, API fixtures.
- **External services / database:** PostgreSQL and the frozen model.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `_failed_logins_from`
Sends failed logins with a given `X-Forwarded-For` header, and returns the status codes.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_assignable_users_lists_active_investigators_and_admins_only` | Only active investigators and admins, sorted, with three fields each. |
| `test_assignable_users_need_investigation_rights` | Analysts and demo users get 403. |
| `test_model_report_is_served_unchanged` | The response equals the committed report file exactly. |
| `test_api_responses_carry_a_strict_content_security_policy` | JSON routes allow loading nothing. |
| `test_documentation_pages_get_their_own_policy` | `/docs` gets the CDN allowance, and still blocks framing. |
| `test_forwarded_addresses_are_ignored_by_default` | A spoofed header gives no fresh rate-limit allowance. |
| `test_forwarded_addresses_are_used_only_from_a_configured_proxy` | A configured proxy's header is honoured. |
| `test_wildcard_proxy_trust_is_refused` | `*` cannot be configured. |
| `test_container_command_disables_uvicorn_proxy_trust` | The Dockerfile and Makefile turn off Uvicorn's own default trust of 127.0.0.1. |

## E. Classes Explained
None.

## F. Execution Flow
Most tests use the shared client. The proxy test builds a second application with trust configured.

## G. Input and Output
Input: HTTP requests. Output: pass or fail.

## H. Important Technical Concepts
- **Uvicorn's hidden default:** Uvicorn trusts `X-Forwarded-For` from 127.0.0.1 unless told otherwise, so the application setting alone would not guarantee trust is off. `--no-proxy-headers` closes that.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_phase4_backend.py
```

## J. Maintenance Notes
If the documentation pages change their CDN, update the policy in `middleware.py` and the test.

## K. Related Files
- [middleware.py](../../app/core/middleware.py.explanation.md): security headers.
- [main.py](../../app/main.py.explanation.md): proxy configuration.
- [users.py route](../../app/api/routes/users.py.explanation.md): the assignee list.
