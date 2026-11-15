# Phase 5 production security review (M5)

Reviewed on 2026-11-09 against the production-like stack (`scripts/prodlike_stack.py`: HTTPS through Caddy, one origin, `APP_ENV=production`) and the whole repository history. Every result below comes from a test or a recorded run named in the Evidence column.

## Findings

| # | Area | Finding | Severity | Status | Evidence |
|---|---|---|---|---|---|
| S1 | HTTPS path | The production path (HTTPS, Secure cookies, a same-origin proxy, trusted proxy headers, `APP_ENV=production`) had never run; it was asserted by unit tests only. | Medium | **Verified**: runs end to end through Caddy. | `frontend/tests/prodlike/production.spec.ts` (6 passed) |
| S2 | Cookies | No `__Secure-` / `__Host-` prefixes, so a look-alike cookie set by another page or subdomain could shadow the real ones. | Low | **Fixed**: production cookies are `__Secure-finguard_session` (Secure, HttpOnly, SameSite=Strict, Path=/api) and `__Host-finguard_csrf` (Secure, Path=/, host-only). With Secure cookies, unprefixed names are not read. | `test_sessions.py::test_secure_cookies_carry_browser_enforced_prefixes`; prodlike sign-in test |
| S3 | CSRF and origin | Checked under HTTPS: missing or forged token, foreign origin, and the right host with the wrong scheme are all refused; the correct request succeeds. | — | **Verified** | prodlike CSRF test |
| S4 | CORS | Other origins get no `Access-Control-Allow-Origin`, through the proxy. One origin needs no CORS at all. | — | **Verified** | prodlike CORS test |
| S5 | Forwarded headers | Spoofed `X-Forwarded-For` values do not change the client address the sign-in limit uses, whether sent through Caddy (which replaces them) or straight to the API (which trusts only Caddy's fixed address, 172.30.250.10). Wildcards are refused by configuration. | — | **Verified** | prodlike forwarded-header and configuration tests; `test_phase4_backend.py` for the positive case |
| S6 | Headers | HSTS (one year) on every HTTPS response, set by the proxy; the frontend's CSP equals the development preview's; the API's own CSP; no `Server` header; plain HTTP redirects with 308. | — | **Verified** | prodlike header and redirect tests |
| S7 | Secrets in history | All 135,531 lines ever added on every branch scanned for private keys, cloud and GitHub tokens, database URLs with passwords and secret-named assignments; no `.env`, `.pem` or `.key` file ever committed. 14 first-run candidates were each read and found to be deliberate test fixtures, now listed with reasons. | — | **Clean** | `scripts/scan_secrets.py`; `test_scan_secrets.py` proves it still finds real secrets |
| S8 | Scanner flaw | An early false-positive rule would have ignored every all-capitals value, including real AWS access keys. | Medium (tooling) | **Fixed before use**, caught by its own test | `test_scan_secrets.py` |
| S9 | Dependencies | `pip-audit`: 96 Python packages, 0 known vulnerabilities (the unpublished project package itself is skipped). `npm audit`: 283 packages, 0 vulnerabilities. | — | **Clean** on 2026-11-09 | Phase 5 M5 run; repeated in CI (M8) |
| S10 | Retention | Expired sessions, audit entries and rate-limit rows were never removed (finding F8). | Low | **Fixed**: `python -m app.commands.retention` (dry run by default, `--apply` to delete): ended sessions after 7 days, audit records after 365, rate-limit rows after 1 day; counts, cutoffs and an audit entry. | `test_retention.py` |
| S11 | Configuration separation | Production refuses: a short or template signing key, `localhost` origins, insecure cookies, per-process rate limits and wildcard proxies. Development and test keep their own values in `.env` and Compose. | — | **Verified** | `test_config.py`; the prodlike API starts only because its settings pass |
| S12 | Batch uploads (PRD 9.2) | Upload bytes are now held in the database (`batch_uploads`) so any container can process them. They are bounded (10 MB, 50,000 rows, checked before storage) and temporary (deleted on completion, failure or exhaustion). | Note | **Interpretation recorded** in ADR 0005 for review | `test_batch_queue.py`, `test_batches.py` |
| S13 | `/docs` | The interactive API documentation stays available in production, with a looser CSP than the rest of the API. | Low | **Open: Phase 6 decision** (disable, or protect) | SECURITY.md known limitations |
| S14 | Sign-in limit behind a platform proxy | The limit is keyed by client address and email. On a host whose proxies are not listed in `TRUSTED_PROXY_IPS`, every user appears to come from the proxy, so the limit becomes per email for everyone; it still stops guessing against one account. | Low | **Open: Phase 6 configuration** | this review |
| S15 | Certificates | The local stack uses Caddy's own authority, which browsers do not trust; tests ignore the certificate error. A real host must use a public certificate. | Note | **Phase 6** | Caddyfile |

## Phase 6 follow-up

The three findings left for Phase 6 are closed in the production configuration (`docker-compose.prod.yml`, [DEPLOYMENT.md](../../DEPLOYMENT.md)). The table above is kept as written in Phase 5.

| Finding | Phase 6 outcome | Evidence |
|---|---|---|
| S13 `/docs` | **Fixed:** production serves no `/docs`, `/redoc` or `/openapi.json`, and refuses `API_DOCS_ENABLED=true` | `test_config.py`, `test_phase4_backend.py::test_production_serves_no_api_documentation`, `production.spec.ts`; 404 from the rehearsal API |
| S14 sign-in limit behind a proxy | **Fixed for the Compose deployment:** the API trusts Caddy's fixed address; production refuses to start without a trusted proxy and refuses all-covering entries | `test_config.py`, `test_deployment.py`; the rehearsal API logged the caller's address, not Caddy's |
| S15 certificates | **Configured, not proven on a public host:** Caddy obtains a public ACME certificate when `FINGUARD_TLS` is an email address | `Caddyfile.production`; no public DNS name exists, so issuance is untested |
| Chunked uploads (SECURITY.md) | **Fixed behind the proxy:** Caddy caps request bodies at 11 MB while streaming | `test_deployment.py`; a 12 MB chunked upload got 413 from Caddy in the rehearsal |

## Same-origin deployment (ADR 0004 and PRD 11.2)

The production-like stack demonstrates the required shape: the browser reaches one origin; the frontend host serves the built files and forwards `/api` and `/health` to the API. On Netlify or Vercel the same is done with a rewrite (`_redirects` with status 200, or `rewrites`), so cookies stay first-party and SameSite=Strict keeps working. Cross-site cookies (SameSite=None) remain rejected.

## What was not done

- No deployment, and no certificate from a public authority (Phase 6).
- No penetration test or external review. These results are from automated tests and one manual review pass.
