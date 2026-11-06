# Security

FinGuard AI is a demonstration platform using synthetic data. It has no authentication or network service yet: those arrive in Phase 3, so most PRD section 10 controls are planned rather than implemented.

## Implemented now

| Control | How |
|---|---|
| Secrets stay out of Git | `.gitignore` excludes `.env`, `.env.*`, `*.pem` and `*.key`. `.env.example` holds placeholders only. |
| Data stays out of Git | `data/raw/*` and `data/processed/*` are ignored. |
| Model binaries stay out of Git | `artifacts/models/*`, `*.joblib` and `*.cbm` are ignored. |
| Dependencies are pinned and checked | `uv.lock` and `package-lock.json` are committed. `npm audit` last reported 0 vulnerabilities. |
| Dataset files are verified | SHA-256 and a structural check run before use. |

There is no Python dependency scanning yet; it should be added with CI in Phase 5.

## Planned

| Control | Phase |
|---|---|
| Secure password hashing, authentication, role-based permissions | 3 |
| Input validation with Pydantic | 3 |
| Upload restrictions: extension, size, headers, types | 3 |
| CORS allow-list from environment | 3 |
| Rate limiting, where the platform supports it | 3 |
| Safe error responses, audit logs | 3 |
| Separate development and production configuration | 3 and 6 |
| Security review | 5 |

## Rules

Never commit `.env` files, API tokens (including Kaggle's), database passwords, private keys, real user data or trained private data exports.

## Responsible use

Predictions must not be presented as verified financial crime findings, nor used to block real customer transactions. Investigation statuses are workflow labels, not findings.

## Reporting a problem

If you find a security issue, contact the repository owner privately rather than opening a public issue. A contact route should be added before the public release in Phase 6.
