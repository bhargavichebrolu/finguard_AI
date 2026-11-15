# config.py

Source: [backend/app/core/config.py](config.py)

## A. File Purpose
Reads and validates all application settings from environment variables or a local `.env`.

## B. Why This File Exists
PRD section 10 requires environment-based configuration and separate development and production settings. Validating everything in one place means a bad configuration stops the API at start-up, not partway through a request.

## C. Dependencies
- **Libraries:** `pydantic`, `pydantic-settings`, `functools`, `pathlib`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** almost every backend module, through `get_settings`.

## D. Every Function Explained

### `_secret_key_must_be_real`
- **Purpose:** refuse a short or placeholder signing key.
- **Parameters / types:** `value: SecretStr`. **Returns / type:** `SecretStr`.
- **Internal processing:** checks length against `MINIMUM_SECRET_KEY_LENGTH` and looks for template text.
- **Error handling:** raises `ValueError`, which stops start-up. The message never includes the value.
- **Calls:** none. **Used by:** pydantic, when `Settings` is created.

### `_database_url_must_be_real`
- **Purpose:** refuse the template's connection address.
- **Parameters / types:** `value: SecretStr`. **Returns / type:** `SecretStr`.
- **Internal processing:** looks for template text.
- **Error handling:** raises `ValueError`.
- **Calls:** none. **Used by:** pydantic.

### `_origins_must_be_explicit`
- **Purpose:** enforce the PRD's CORS restriction.
- **Parameters / types:** the settings object. **Returns / type:** `Settings`.
- **Internal processing:** rejects `*` everywhere and `localhost` in production. Also rejects non-Secure session cookies in production, a wildcard proxy list, and any proxy entry `check_proxy_entry` refuses. In production it also requires database rate limits, refuses `API_DOCS_ENABLED=true` (security finding S13), and requires at least one trusted proxy (S14, Phase 6): production cookies need HTTPS, which the API never terminates, so a proxy is always in front.
- **Error handling:** raises `ValueError`.
- **Calls:** `cors_origins`. **Used by:** pydantic.

### `cors_origins`
- **Purpose:** turn the comma-separated setting into a list.
- **Parameters / types:** none. **Returns / type:** `list[str]`.
- **Internal processing:** splits, trims and drops blanks.
- **Error handling:** none needed.
- **Calls:** none. **Used by:** `_origins_must_be_explicit`, `app/main.py`.

### `cookie_secure`
Returns `SESSION_COOKIE_SECURE` if set, otherwise true in production only.

### `trusted_proxies`
Returns `TRUSTED_PROXY_IPS` as a list. It is empty by default, which trusts no proxy.

### `docs_enabled`
Whether `/docs`, `/redoc` and `/openapi.json` are served: `API_DOCS_ENABLED` if set, otherwise on everywhere except production (Phase 6, security finding S13). `app/main.py` passes `None` as each route's URL when it is off, so the routes do not exist.

### `check_proxy_entry`
- **Purpose:** accept one proxy address or network, as uvicorn's `ProxyHeadersMiddleware` will parse it.
- **Parameters / types:** `entry: str`. **Returns / type:** `None`.
- **Internal processing:** `ipaddress.ip_network` in strict mode, so host bits must be clear (`10.0.0.5/24` is refused, because uvicorn would fail on it at start-up). A prefix of length 0 (`0.0.0.0/0`, `::/0`) trusts every address and is refused.
- **Error handling:** raises `ValueError`, which pydantic reports.
- **Calls:** `ipaddress.ip_network`. **Used by:** `_origins_must_be_explicit`.

### `get_settings`
- **Purpose:** provide one validated settings object.
- **Parameters / types:** none. **Returns / type:** `Settings`.
- **Internal processing:** `lru_cache` means the environment is read once.
- **Error handling:** validation errors propagate.
- **Calls:** `Settings`. **Used by:** the rest of the backend.

## E. Classes Explained

### `Settings`
- **Purpose:** the full list of settings, with types and limits.
- **Attributes:** credentials (`database_url`, `secret_key`) have no default. Model paths default to the repository's `artifacts/` folder and are overridden in Docker. Batch limits, token lifetime, rate limits and `default_high_risk_boundary` have defaults with bounds. Phase 4 added `model_report_path`, `session_cookie_secure` and `trusted_proxy_ips`. Phase 5 M4 added `batch_worker_enabled`, `batch_poll_seconds` (2), `batch_lease_seconds` (60) and `batch_max_attempts` (3). Phase 5 M3 added `rate_limit_store` (`database` by default; production refuses `memory`, because per-process counts multiply the limits and reset on restart).
- **Methods:** the validators above, plus `cors_origins`.
- **Inheritance:** `pydantic_settings.BaseSettings`.

## F. Execution Flow
The first `get_settings` call reads the environment and `.env`, validates, and caches the result. Real environment variables take priority over `.env`.

## G. Input and Output
Input: environment variables and `.env`. Output: a `Settings` object.

## H. Important Technical Concepts
- **`SecretStr`:** prints as `**********`, so a secret cannot leak through a log line or error message by accident. The value must be requested explicitly.
- **`protected_namespaces=()`:** pydantic normally warns about fields starting with `model_`, and these settings do so legitimately.
- **The frozen threshold is not a setting.** It is in `frozen_model.py`, so no environment variable can change who gets flagged.

## I. Example
```python
from app.core.config import get_settings

get_settings().max_batch_rows  # 50000 unless MAX_BATCH_ROWS is set
```

## J. Maintenance Notes
Add new variables to `.env.example` in the same change. Tests must set their environment before the first `get_settings` call, or clear the cache.

## K. Related Files
- [.env.example](../../../.env.example.explanation.md): the variables.
- [frozen_model.py](frozen_model.py.explanation.md): values that are deliberately not settings.
- [session.py](../database/session.py.explanation.md): uses `database_url`.
