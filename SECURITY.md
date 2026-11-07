# Security

FinGuard AI is a demonstration platform using synthetic data. Phase 3 implemented the PRD section 10 controls for the backend and database. The API runs locally only and has not been deployed or independently reviewed.

## Implemented

| Control | How |
|---|---|
| Environment-based configuration | `app/core/config.py` reads the environment and `.env`. Credentials have no defaults, and placeholder values, short signing keys and wildcard CORS stop start-up. |
| Secrets stay out of Git | `.env`, `.env.*`, `*.pem` and `*.key` are ignored. `scripts/generate_env.py` creates `.env` with random values, never prints them, and refuses if Git would track the file. |
| Password hashing | Argon2id. Unknown emails take the same time as wrong passwords. |
| Authentication | Signed HS256 tokens valid for 30 minutes. Each request reloads the user, so deactivation and role changes apply immediately, and a password change invalidates old tokens. |
| Role-based permissions | One table in `app/security/permissions.py`, covering demo, analyst, investigator and admin. A test confirms that every non-public route refuses requests without a token. |
| Input validation | Pydantic schemas refuse unknown fields, including labels and balances. The database repeats the key rules as CHECK constraints. |
| Upload restrictions | Extension, size (checked before the body is read and while streaming), row count, encoding, NUL bytes, headers and cell values. Files are stored under random names and deleted afterwards. |
| CORS | Explicit origin list. Wildcards are refused, and production also refuses `localhost`. |
| Rate limiting | Failed logins (5 per minute per address and email), predictions and uploads. Held in memory per process. |
| Safe error responses | One JSON format with a request ID. Validation errors omit submitted values, and unexpected errors return a generic message. |
| Audit logging | Logins, user changes, predictions, uploads, investigation changes and settings. No passwords, emails of failed logins or note text. |
| Export safety | Exported CSV cells starting with `=`, `+`, `-` or `@` are prefixed so spreadsheets treat them as text. |
| Security headers | `nosniff`, `DENY` framing, no referrer, and `no-store` on API responses. |
| Database access control | SCRAM authentication for every connection, including inside the container. The API uses a role without superuser rights, and the port is bound to `127.0.0.1`. |
| Frozen model protection | The model version, file hash and threshold are pinned in code. Start-up checks the metadata, library versions and preprocessing hash, then the file hash, before opening the file. The model folder is mounted read-only in Docker. |
| Container | Runs as an ordinary user, with no training libraries, tests or `.env` in the image. |
| Data stays out of Git | Datasets and model binaries are ignored. |
| Dependencies pinned | `uv.lock` and `package-lock.json`. |

## Known limitations

| Limitation | Effect | When to address |
|---|---|---|
| Rate limits are per process and reset on restart | Several workers would each allow the full limit | If more than one process is used |
| Behind a proxy, the client address is the proxy's | Login limits would be shared by all users | Phase 6, by trusting forwarded headers from the proxy only |
| No token revocation list | A stolen token works for up to 30 minutes unless the account is deactivated or the password changed | Accepted for this scale |
| No Content Security Policy | `/docs` loads Swagger UI from a CDN | Phase 4 or 6, with the frontend |
| Chunked uploads without `Content-Length` | Spooled by the framework before the size check | Phase 6, with a proxy body limit |
| No Python dependency scanning | Vulnerable packages would not be flagged | Phase 5, with CI |
| HTTPS | Not provided locally | Phase 6, by the host |
| Audit log has no retention policy | Grows without limit | Before long-running use |

## Rules

Never commit `.env` files, API tokens (including Kaggle's), database passwords, private keys, real user data or trained private data exports. Never set `POSTGRES_HOST_AUTH_METHOD=trust`.

## Responsible use

Predictions must not be presented as verified financial crime findings, nor used to block real customer transactions. `model_score` is not calibrated, `FLAG_FOR_REVIEW` is a request for review, and investigation statuses are workflow labels. The model missed its false positive target on test (0.282% against 0.1%) and flagged 45.9% of labelled fraud.

## Reporting a problem

If you find a security issue, contact the repository owner privately rather than opening a public issue. A contact route should be added before the public release in Phase 6.
