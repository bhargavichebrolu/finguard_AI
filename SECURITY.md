# Security

FinGuard AI is a demonstration platform using synthetic data. Phase 3 implemented the PRD section 10 controls for the backend and database, Phase 4 added browser sessions, and Phase 5 reviewed the production settings over HTTPS ([docs/security/phase-5-review.md](docs/security/phase-5-review.md)). Phase 6 closed findings S13 to S15 and the chunked-upload limitation in the production configuration ([DEPLOYMENT.md](DEPLOYMENT.md)), which was verified in a local rehearsal. It has not been deployed to a public host, penetration-tested or independently reviewed.

## Implemented

| Control | How |
|---|---|
| Environment-based configuration | `app/core/config.py` reads the environment and `.env`. Credentials have no defaults, and placeholder values, short signing keys and wildcard CORS stop start-up. |
| Secrets stay out of Git | `.env`, `.env.*`, `*.pem` and `*.key` are ignored. `scripts/generate_env.py` creates `.env` with random values, never prints them, and refuses if Git would track the file. |
| Password hashing | Argon2id. Unknown emails take the same time as wrong passwords. |
| Authentication | Browser sessions in HttpOnly, SameSite=Strict cookies, Secure in production with browser-enforced `__Secure-` and `__Host-` name prefixes (Phase 5), backed by a revocable server-side session (Phase 4). Bearer tokens remain for API clients. Both last 30 minutes, and each request reloads the user, so deactivation, role changes and password changes apply immediately. |
| CSRF protection | Cookie requests that change data need `X-CSRF-Token` matching their own session's hashed token, and an allowed `Origin`. Sign-in accepts JSON only, so a cross-site form cannot submit it. |
| Logout | Revokes that session on the server. A replayed cookie is refused. |
| Role-based permissions | One table in `app/security/permissions.py`, covering demo, analyst, investigator and admin. A test confirms that every non-public route refuses requests without a token, and browser tests call the API directly to confirm each role's refusals do not depend on the interface (Phase 4). |
| Account self-protection | Administrators cannot deactivate their own account, and the last active administrator cannot be removed. Both are enforced by the API (self-deactivation since Phase 4 M7; before that only the button was disabled). |
| Input validation | Pydantic schemas refuse unknown fields, including labels and balances. The database repeats the key rules as CHECK constraints. |
| Upload restrictions | Extension, size (checked before the body is read and while streaming), row count, encoding, NUL bytes, headers and cell values. The temporary file uses a random name and is deleted when the request ends; since Phase 5 M4 the checked bytes (10 MB at most) are held in `batch_uploads` until the job ends, then deleted. |
| CORS | Explicit origin list, with credentials allowed only for those origins. Wildcards are refused, and production also refuses `localhost`. |
| Content Security Policy | `default-src 'none'` on API responses, with a narrow allowance for `/docs` (Phase 4) outside production. The frontend's own policy is served with the frontend. |
| API documentation in production (Phase 6, S13) | `/docs`, `/redoc` and `/openapi.json` do not exist when `APP_ENV=production`, and `API_DOCS_ENABLED=true` is refused there, so the looser documentation policy is never served in production. |
| Proxy trust | Off by default. Forwarded addresses are honoured only from `TRUSTED_PROXY_IPS`, and Uvicorn's built-in trust of 127.0.0.1 is turned off with `--no-proxy-headers` (Phase 4). Since Phase 6 every entry must be an IP address or network, and anything covering every address (`0.0.0.0/0`, `::/0`) is refused; production refuses to start without a trusted proxy (S14). `docker-compose.prod.yml` sets Caddy's fixed address. |
| Rate limiting | Failed logins (5 per minute per address and email, sliding window), predictions and uploads (fixed one-minute window per user). Counted in PostgreSQL since Phase 5 M3, so every API process and every restart share the counts; production refuses the per-process memory store. Tested with real separate processes and restarts. |
| Safe error responses | One JSON format with a request ID. Validation errors omit submitted values, and unexpected errors return a generic message. Since Phase 5 M7, a database that cannot be reached answers 503 with an actionable message and `Retry-After`, logging only the driver error's type (its message can name the host and role); a model failure answers a message saying nothing was stored. Tests check error bodies for SQL, driver, host, trace and password text, in the API and in the browser. |
| Audit logging | Logins, user changes, predictions, uploads, investigation changes and settings. No passwords, emails of failed logins or note text. |
| Export safety | Exported CSV cells starting with `=`, `+`, `-` or `@` are prefixed so spreadsheets treat them as text. |
| Security headers | `nosniff`, `DENY` framing, no referrer, and `no-store` on API responses. |
| Database access control | SCRAM authentication for every connection, including inside the container. The API uses a role without superuser rights, and the port is bound to `127.0.0.1`. |
| Frozen model protection | The model version, file hash and threshold are pinned in code. Start-up checks the metadata, library versions and preprocessing hash, then the file hash, before opening the file. The model folder is mounted read-only in Docker. |
| Container | Runs as an ordinary user, with no training libraries, tests or `.env` in the image. |
| Data stays out of Git | Datasets and model binaries are ignored. |
| Dependencies pinned | `uv.lock` and `package-lock.json`. |
| Dependency audits (Phase 5) | `pip-audit` and `npm audit`: 0 known vulnerabilities on 2026-11-09. Steps in the CI workflow since Phase 5 M8, which has not yet run on GitHub; until it does, they are run by hand. |
| Secrets in history (Phase 5) | `scripts/scan_secrets.py` scans every line ever added on every branch; clean on 2026-11-09. Also a CI step (Phase 5 M8). |
| CI permissions (Phase 5 M8) | The workflow has a read-only token, uses no repository secrets, does not keep the token in Git's configuration, pins every action to a commit hash, and starts its database with generated, unprinted passwords and SCRAM authentication. `test_ci.py` checks these rules. |
| Retention (Phase 5) | `python -m app.commands.retention [--apply]`: ended sessions after 7 days, audit records after 365, rate-limit rows after 1 day. In production the `retention` service runs it daily (Phase 6). |
| Production deployment (Phase 6) | `docker-compose.prod.yml`: only Caddy publishes ports; the database is on a network Caddy cannot reach; secrets come from a generated, Git-ignored `.env.production` and have no defaults; a public certificate from an ACME authority (S15); request bodies capped at 11 MB by Caddy while streaming; API responses never compressed (BREACH). `scripts/verify_deployment.py` checks a running deployment. |
| Production-like verification (Phase 5) | HTTPS through Caddy with production settings: prefixed Secure cookies, HSTS, CSP, CSRF, origin, CORS and forwarded-header rules, tested end to end. See [docs/security/phase-5-review.md](docs/security/phase-5-review.md). |
| Browser-verified controls (Phase 4) | Playwright tests against the real API check cookie flags, that no token reaches browser storage, sign-out revocation, expiry, tampered cookies, CSRF and origin refusals, CORS, the sign-in rate limit, security headers, and that pages raise no Content Security Policy violations. |
| Browser-test isolation | Tests use only `finguard_e2e_test`: the seed and stack scripts refuse any name not ending in `_test`, and global setup proves the API reads that database before any test runs. Test passwords are random per run, stored in a Git-ignored file, and never printed; traces and HTML reports, which record typed values, are off. |

## Known limitations

| Limitation | Effect | When to address |
|---|---|---|
| Fixed windows for prediction and upload limits | Up to twice the per-minute limit can pass across a minute boundary | Accepted: chosen to meet the latency budget; failed sign-ins keep the strict sliding window |
| Bearer tokens cannot be revoked individually | A stolen bearer token works for up to 30 minutes unless the account is deactivated or the password changed. Browser sessions can be revoked. | Accepted for this scale |
| `/docs` needs `'unsafe-inline'` scripts | Its CSP is looser than the rest of the API | Resolved for production in Phase 6: the pages do not exist there. Development and test still serve them |
| Chunked uploads without `Content-Length` | Spooled by the framework before the size check when the API is reached directly | Resolved in production (Phase 6): Caddy refuses bodies over 11 MB while they stream (a 12 MB chunked upload got 413 from Caddy in the rehearsal). Still applies when the API is used without the proxy, as in development |
| Public certificate not yet obtained | The production Caddyfile obtains one from an ACME authority (S15), but no public host exists, so issuance and renewal are untested | On the first public deployment |
| Sign-in limit behind other platforms' proxies | Keyed by address and email. The Compose deployment trusts Caddy's fixed address. On a platform with its own proxies, `TRUSTED_PROXY_IPS` must list them, or the limit becomes per email only | When deploying anywhere other than `docker-compose.prod.yml` |
| `Secure` and the cookie prefixes are checked in Chromium only | The HTTPS browser tests (`npm run test:prodlike`) confirm `Secure`, `__Secure-`, `__Host-` and host-only scope in Chromium; `verify_deployment.py` checks the `Set-Cookie` attributes of a deployment; the main browser tests run over plain HTTP, where Secure is off | On a public host, in each browser |
| CI has not run on GitHub | The workflow's checks (tests, audits, secret scan) have only been rehearsed locally; nothing is pushed | First push, with the owner's permission |
| Screen readers untested | No Narrator, NVDA or VoiceOver run has been performed; the checklist is marked UNTESTED | When the owner runs [the checklist](docs/accessibility/screen-reader-checklist.md) |
| WebKit's stored SameSite attribute | Playwright's WebKit build on Windows reports these cookies as `SameSite=None`, although the server sends `Strict` (checked from the `Set-Cookie` header in every engine). Whether Safari applies Strict is untested; the CSRF token and origin check protect changes either way | Check in Safari on macOS when one is available |

## Rules

Never commit `.env` files, API tokens (including Kaggle's), database passwords, private keys, real user data or trained private data exports. Never set `POSTGRES_HOST_AUTH_METHOD=trust`.

## Responsible use

Predictions must not be presented as verified financial crime findings, nor used to block real customer transactions. `model_score` is not calibrated, `FLAG_FOR_REVIEW` is a request for review, and investigation statuses are workflow labels. The model missed its false positive target on test (0.282% against 0.1%) and flagged 45.9% of labelled fraud.

## Reporting a problem

If you find a security issue, report it privately through the repository's **Security** tab (GitHub private vulnerability reporting), not as a public issue. Whether private reporting is enabled is a repository setting, which the owner must turn on when the repository is published; until then, contact the owner privately.
