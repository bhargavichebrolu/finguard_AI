# Phase 6 completion: deployment and release

Status: **complete, awaiting the owner's review.** Step 1 (engineering) is commit `23dcb2f`; Step 2 (full-system verification, below) is the commit that follows it, on branch `phase-5-hardening`. Not merged into `main`, not pushed, and **not deployed to a public host**: the production configuration was verified in a local rehearsal from a fresh clone.

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
| API image (F12) | Two stages; NVIDIA NCCL removed; 1.92 GB to 979 MB | Identical fingerprint of 550 synthetic scores and explanations in both images (`score_reference_grid.py`) |
| Explorer | Deferred join for pages | Same rows; last page 392 to 79 ms at 180,285 rows; `test_explorer_pages_match_one_full_sort` |
| First account | `python -m app.commands.create_admin` inside the image | `test_create_admin.py` |
| Database init | Test database only when `TEST_DB_NAME` is set | Rehearsal: no test database in production |
| Browser tests | Browser-test sessions last 120 minutes | Phase 5 investigation finding |
| CI | Third job builds both images and checks the production Compose file | `test_deployment.py`; not run on GitHub |

## Verification (Step 2, 2026-11-15)

| Suite | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|
| Backend, full, with the real model | 835 | 0 | 0 | 1 deselected: the test that rereads the test partition |
| CI rehearsal on a fresh clone: backend | 514 | 0 | 322, exactly the expected list | no model, no dataset, no `.env` (as on GitHub) |
| Frontend unit and component (Vitest) | 111 | 0 | 0 | fresh clone |
| CI rehearsal, every workflow step (backend, frontend and images jobs) | 23 of 23 steps | 0 | | fresh clone; GitHub Actions itself has not run |
| Type check and production build | passed | | | fresh clone |
| Browser, all seven projects (Chromium, Firefox, WebKit) | 311 | 0 | 0 | setup 5, desktop 83, tablet 19, mobile 19, firefox 83, webkit 83, webkit-mobile 19 |
| HTTPS production-like | 7 | 0 | 0 | includes the new no-documentation test |
| Production rehearsal, `verify_deployment.py --write` | 26 checks | 0 | | fresh clone, `--no-cache` images, new volumes |
| README demonstration in Chromium | 13 steps | 0 | | against the production rehearsal |

**Infrastructure** ([DEPLOYMENT.md](../../DEPLOYMENT.md#6-local-rehearsal-what-was-verified), section 6):
- The API refused to start without the model.
- With the model, every service was healthy 20 seconds after start.
- Migration 0004 was applied; no test database exists; the application role is not a superuser.
- No API or database port is published.
- The API process killed with SIGKILL was restarted by its policy.
- Caddy restarted, and every container restarted at once, without loss.
- The database outage gave 503 with `Retry-After` and recovered without an API restart.
- A full stop and start, and a backup, data loss and restore, kept every row.
- No secret appeared in any log.

**Security:**
- The CI rehearsal's secret scan of all history had 0 findings.
- `pip-audit` reported "No known vulnerabilities found", and `npm audit` "found 0 vulnerabilities" (fresh-clone rehearsal).
- Production serves no API documentation.
- The proxy body limit and cookie attributes were checked over HTTPS.

**Frozen model:**

| Check | Result |
|---|---|
| `model.joblib` SHA-256 | `69813c176b02d035f550e80f0f694f44bb9fec8a31222a25de189525a91ad40c`, unchanged (file last written 2026-11-07, Phase 2) |
| Threshold | `0.02841914258897305` in code, metadata, metrics and report |
| Preprocessing metadata | Hash matches the model metadata; start-up verified it in every API start |
| Library versions | scikit-learn 1.9.1, XGBoost 3.2.0, as recorded; start-up checks them |
| Inference parity | 550 synthetic inputs gave fingerprint `c188cdf2…` in the original 1.92 GB image and in the final 979 MB image |
| `data/`, `artifacts/`, `experiments/` | No change since Phase 5 (`git diff 79b2947 HEAD`) |
| Retraining and test-set analysis | None: no training command ran; the one test that rereads the test partition stayed deselected |

**Defects found by Step 2, and fixed:**
- **CI skip list.** The 24 new explorer cases skip without the model in CI. They were added to `.github/expected-tests.json` by `--update` on a fresh clone, and the minimum number of passing tests rose from 480 to 512.
- **API image contents.** The image contained explanation documents and local bytecode caches, because `.dockerignore` patterns matched only at the root. Fixed, with a test.
- **Backup commands.** The backup and restore commands in DEPLOYMENT.md lacked the database password. Fixed and re-run.
- **Model folder.** The model step did not say the folder must be created in a fresh clone. Fixed.
- **Demonstration wording.** The README demonstration said an analyst's navigation is restricted. Analysts see every page read-only, by design; the wording was corrected.

## Known limitations and residual risks

- **Not deployed:** no public host, DNS name or public certificate. ACME issuance and renewal are untested.
- **CI:** it has never run on GitHub; nothing is pushed.
- **Untested:** Safari on macOS, manual screen-reader checks (the checklist is UNTESTED), and WebKit's SameSite enforcement.
- **Accepted Phase 5 residual risks:**
  - the unexplained single Firefox status-change failure; the test now records which step fails;
  - the Firefox teardown hang under CPU starvation.
- **Limits around the minute boundary:** prediction and upload limits use fixed windows, so up to twice the limit can pass across a minute boundary.
- **Deep explorer offsets:** still pass over earlier rows, though no longer building them.
- **API used directly, without Caddy:** chunked uploads are spooled before the size check.
- **Rehearsal certificate:** on a non-default HTTPS port, Caddy's automatic redirect omits the port. Production uses 443.
