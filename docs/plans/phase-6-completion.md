# Phase 6 completion: deployment and release

Status: **Step 1 (engineering) committed on branch `phase-5-hardening`; Step 2 (full-system verification) recorded below when it has run.** Not merged into `main`, not pushed, and not deployed to a public host.

Decisions: [ADR 0006](../decisions/0006-phase-6-decisions.md). Deployment: [DEPLOYMENT.md](../../DEPLOYMENT.md).

## What Phase 6 changed

| Area | Change | Evidence |
|---|---|---|
| Deployment | `docker-compose.prod.yml`: Caddy, API, PostgreSQL, migrations, daily retention on one host; only Caddy publishes ports; secrets from a generated, Git-ignored `.env.production` | `test_deployment.py`; local rehearsal with `verify_deployment.py` (26 of 26) |
| HTTPS (S15) | `docker/caddy/Caddyfile.production`: ACME certificate when `FINGUARD_TLS` is an email address; HSTS; CSP; API responses uncompressed | Rehearsal with Caddy's own authority; a public certificate is untested |
| Web image | `docker/web/Dockerfile`: the interface built from source, served by Caddy (92.7 MB) | CI `images` job; rehearsal |
| API documentation (S13) | Off in production, cannot be turned on there | `test_config.py`, `test_phase4_backend.py`, `production.spec.ts`; 404 in the rehearsal |
| Proxy trust (S14) | Production requires `TRUSTED_PROXY_IPS`; entries must be addresses or networks, never all-covering | `test_config.py`; the rehearsal API logged callers' addresses |
| Chunked uploads | Caddy caps request bodies at 11 MB while streaming | `test_deployment.py`; 12 MB chunked upload got 413 from Caddy |
| API image (F12) | Two stages; NVIDIA NCCL removed; 1.92 GB to 981 MB | Identical fingerprint of 550 synthetic scores and explanations in both images (`score_reference_grid.py`) |
| Explorer | Deferred join for pages | Same rows; last page 392 to 79 ms at 180,285 rows; `test_explorer_pages_match_one_full_sort` |
| First account | `python -m app.commands.create_admin` inside the image | `test_create_admin.py` |
| Database init | Test database only when `TEST_DB_NAME` is set | Rehearsal: no test database in production |
| Browser tests | Browser-test sessions last 120 minutes | Phase 5 investigation finding |
| CI | Third job builds both images and checks the production Compose file | `test_deployment.py`; not run on GitHub |

## Verification (Step 2)

Recorded after the full-system verification run.
