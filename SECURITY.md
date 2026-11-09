# Security

FinGuard AI is a demonstration platform using synthetic data. Phase 3 implemented the PRD section 10 controls for the backend and database. The API runs locally only and has not been deployed or independently reviewed.

## Implemented

| Control | How |
|---|---|
| Environment-based configuration | `app/core/config.py` reads the environment and `.env`. Credentials have no defaults, and placeholder values, short signing keys and wildcard CORS stop start-up. |
| Secrets stay out of Git | `.env`, `.env.*`, `*.pem` and `*.key` are ignored. `scripts/generate_env.py` creates `.env` with random values, never prints them, and refuses if Git would track the file. |
| Password hashing | Argon2id. Unknown emails take the same time as wrong passwords. |
| Authentication | Browser sessions in HttpOnly, SameSite=Strict cookies, Secure in production, backed by a revocable server-side session (Phase 4). Bearer tokens remain for API clients. Both last 30 minutes, and each request reloads the user, so deactivation, role changes and password changes apply immediately. |
| CSRF protection | Cookie requests that change data need `X-CSRF-Token` matching their own session's hashed token, and an allowed `Origin`. Sign-in accepts JSON only, so a cross-site form cannot submit it. |
| Logout | Revokes that session on the server. A replayed cookie is refused. |
| Role-based permissions | One table in `app/security/permissions.py`, covering demo, analyst, investigator and admin. A test confirms that every non-public route refuses requests without a token, and browser tests call the API directly to confirm each role's refusals do not depend on the interface (Phase 4). |
| Account self-protection | Administrators cannot deactivate their own account, and the last active administrator cannot be removed. Both are enforced by the API (self-deactivation since Phase 4 M7; before that only the button was disabled). |
| Input validation | Pydantic schemas refuse unknown fields, including labels and balances. The database repeats the key rules as CHECK constraints. |
| Upload restrictions | Extension, size (checked before the body is read and while streaming), row count, encoding, NUL bytes, headers and cell values. Files are stored under random names and deleted afterwards. |
| CORS | Explicit origin list, with credentials allowed only for those origins. Wildcards are refused, and production also refuses `localhost`. |
| Content Security Policy | `default-src 'none'` on API responses, with a narrow allowance for `/docs` (Phase 4). The frontend's own policy is served with the frontend. |
| Proxy trust | Off by default. Forwarded addresses are honoured only from `TRUSTED_PROXY_IPS`, and Uvicorn's built-in trust of 127.0.0.1 is turned off with `--no-proxy-headers` (Phase 4). |
| Rate limiting | Failed logins (5 per minute per address and email, sliding window), predictions and uploads (fixed one-minute window per user). Counted in PostgreSQL since Phase 5 M3, so every API process and every restart share the counts; production refuses the per-process memory store. Tested with real separate processes and restarts. |
| Safe error responses | One JSON format with a request ID. Validation errors omit submitted values, and unexpected errors return a generic message. |
| Audit logging | Logins, user changes, predictions, uploads, investigation changes and settings. No passwords, emails of failed logins or note text. |
| Export safety | Exported CSV cells starting with `=`, `+`, `-` or `@` are prefixed so spreadsheets treat them as text. |
| Security headers | `nosniff`, `DENY` framing, no referrer, and `no-store` on API responses. |
| Database access control | SCRAM authentication for every connection, including inside the container. The API uses a role without superuser rights, and the port is bound to `127.0.0.1`. |
| Frozen model protection | The model version, file hash and threshold are pinned in code. Start-up checks the metadata, library versions and preprocessing hash, then the file hash, before opening the file. The model folder is mounted read-only in Docker. |
| Container | Runs as an ordinary user, with no training libraries, tests or `.env` in the image. |
| Data stays out of Git | Datasets and model binaries are ignored. |
| Dependencies pinned | `uv.lock` and `package-lock.json`. |
| Browser-verified controls (Phase 4) | Playwright tests against the real API check cookie flags, that no token reaches browser storage, sign-out revocation, expiry, tampered cookies, CSRF and origin refusals, CORS, the sign-in rate limit, security headers, and that pages raise no Content Security Policy violations. |
| Browser-test isolation | Tests use only `finguard_e2e_test`: the seed and stack scripts refuse any name not ending in `_test`, and global setup proves the API reads that database before any test runs. Test passwords are random per run, stored in a Git-ignored file, and never printed; traces and HTML reports, which record typed values, are off. |

## Known limitations

| Limitation | Effect | When to address |
|---|---|---|
| Fixed windows for prediction and upload limits | Up to twice the per-minute limit can pass across a minute boundary | Accepted: chosen to meet the latency budget; failed sign-ins keep the strict sliding window |
| Proxy address must be configured per host | Until `TRUSTED_PROXY_IPS` is set, login limits behind a proxy are shared by all users | Phase 6, when the host is known |
| Bearer tokens cannot be revoked individually | A stolen bearer token works for up to 30 minutes unless the account is deactivated or the password changed. Browser sessions can be revoked. | Accepted for this scale |
| `/docs` needs `'unsafe-inline'` scripts | Its CSP is looser than the rest of the API | Could self-host Swagger UI later |
| Expired session rows are not deleted | `user_sessions` grows | Before long-running use |
| Chunked uploads without `Content-Length` | Spooled by the framework before the size check | Phase 6, with a proxy body limit |
| No Python dependency scanning | Vulnerable packages would not be flagged | Phase 5, with CI |
| HTTPS | Not provided locally | Phase 6, by the host |
| The `Secure` cookie flag is not exercised in a browser | Browser tests run over plain HTTP with `APP_ENV=test`, so they confirm Secure is off there; production refusing to start without it is a unit test (`test_config.py`) | Phase 6, with HTTPS end-to-end tests |
| Audit log has no retention policy | Grows without limit | Before long-running use |

## Rules

Never commit `.env` files, API tokens (including Kaggle's), database passwords, private keys, real user data or trained private data exports. Never set `POSTGRES_HOST_AUTH_METHOD=trust`.

## Responsible use

Predictions must not be presented as verified financial crime findings, nor used to block real customer transactions. `model_score` is not calibrated, `FLAG_FOR_REVIEW` is a request for review, and investigation statuses are workflow labels. The model missed its false positive target on test (0.282% against 0.1%) and flagged 45.9% of labelled fraud.

## Reporting a problem

If you find a security issue, contact the repository owner privately rather than opening a public issue. A contact route should be added before the public release in Phase 6.
