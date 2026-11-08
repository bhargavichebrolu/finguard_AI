# Phase 5 plan: integration hardening, system-wide QA and reliability

**Status: proposed, awaiting approval (2026-11-08).** No Phase 5 code has been written. `main` is at `5c392a5` (Phase 4, merged fast-forward). The items marked **Decision needed** are for the reviewer; the plan states a recommendation for each.

## 1. Constraints carried into Phase 5

- The frozen model `fraud_detector_v1` (SHA-256 `69813c17…`), its threshold `0.02841914258897305`, the Phase 1 and 2 datasets, experiment results and evaluation metrics stay unchanged. Nothing is retrained. The test partition is not read, and the one backend test that rereads it stays deselected.
- Performance measurements use synthetic, hand-generated transactions only. No figure is estimated or typed in; every number in the performance record comes from a saved measurement run.
- No unrelated features, no visual redesign, and no dependency without a stated reason. Each new tool is listed in section 6.
- Every authored file gets a sibling explanation document; `PROJECT_CONNECTIONS.md` is updated with each milestone.
- Each milestone is tested, then committed on its own. Nothing is pushed without permission.

## 2. What the inspection found

| # | Finding | Where | Effect |
|---|---|---|---|
| F1 | Start-up batch recovery assumes one process. Every starting process marks **all** pending and processing jobs as failed and deletes **every** temporary upload. | `batch_service.recover_interrupted_jobs`, `main.lifespan` | With two workers, or during a rolling deploy, a starting process fails another process's live job and deletes the file it is reading. |
| F2 | Batch work runs as a FastAPI background task inside the process that received the upload, reading a file on local disk. | `routes/batches.py`, `batch_service.process_batch` | A restart or host sleep loses the job; the user must upload again. Free hosts may not keep local files (PRD 11.7). |
| F3 | Rate limits (failed sign-ins, predictions, uploads) are held in each process's memory. | `core/rate_limit.py` | N processes allow N times the limit; a restart resets it, so sign-in guessing can continue across restarts. |
| F4 | The backend suite and the browser suite share `finguard_test`; the backend suite empties `model_versions`. | `tests/conftest.py`, `scripts/e2e_database.py` | The browser stack must be restarted after backend tests; the suites cannot run together. |
| F5 | No CI. The model binary and dataset are Git-ignored, so a clean checkout cannot run model-dependent API or browser tests. | `.github/workflows/` (empty), `.gitignore` | PRD 15 requires GitHub Actions; what CI can and cannot verify is not yet defined. |
| F6 | The production path has never run: HTTPS, `Secure` cookies, a same-origin proxy, trusted proxy headers, `APP_ENV=production`. PRD 11.2 names Netlify or Vercel, while ADR 0004 requires the API on the same origin. | `config.py`, ADR 0004 | Production behaviour is asserted by unit tests only. |
| F7 | A lazily loaded page that fails to download (for example after a redeploy changes file names) has no error boundary. | `App.tsx` | The whole interface unmounts to a blank page. |
| F8 | Expired `user_sessions` rows and audit entries are never removed. | `security/sessions.py`, SECURITY.md | Tables grow without limit. |
| F9 | Only Chromium is tested. No screen-reader testing. | `playwright.config.ts` | Firefox, Safari and assistive-technology behaviour is unknown. NVDA is not installed here; Narrator is, but the agent cannot judge spoken output. |
| F10 | No performance measurement through the API or database. Phase 2 timed the model alone. | — | Latency, batch throughput, query cost at volume and memory per process are unknown. |
| F11 | No dependency vulnerability scanning. | SECURITY.md known limitations | Vulnerable packages would not be flagged. |
| F12 | The API image is 1.92 GB, 469 MB of it NVIDIA libraries pulled in by XGBoost's Linux wheel. | `backend/Dockerfile` | Relevant to hosting limits; investigated, not changed, in Phase 5 (section 7). |

## 3. Architecture decisions (condition 5)

### D1. Batch processing that survives restarts and multiple processes — **Decision needed**

| Option | For | Against |
|---|---|---|
| **A. PostgreSQL as the job queue (recommended).** The upload's bytes are stored in a new table (capped by the existing 10 MB limit, deleted when the job ends). Each API process runs one small worker thread that claims a job with `SELECT … FOR UPDATE SKIP LOCKED` and holds a lease (`lease_expires_at`, renewed per chunk, using database time). A job whose lease expires is claimed again and **resumes after the last committed chunk**: progress and stored rows are already committed in the same transaction, and identifiers are unique, so no row is stored twice. After a set number of failed attempts a job is marked failed with its reason. Start-up no longer touches other processes' jobs. | No new service or infrastructure; works with one or many processes and on hosts without separate workers; jobs pause while a host sleeps and resume on wake. | Upload bytes live in the database until processed; the worker polls (proposed every 2 s); one more table and migration. |
| B. A separate worker container with the same queue table. | Isolates batch CPU from web requests. | Free hosts may not offer background workers (PRD 11.7); a second deployable. |
| C. Redis with Celery or RQ. | Mature queueing. | New infrastructure and dependencies for a small workload; rejected. |
| D. Keep in-process tasks and enforce exactly one process. | No code change beyond the start-up fix. | Restarts still lose jobs; F2 remains. |

Interrupted behaviour after A: a restart, crash or killed container leaves the job processing; when the lease expires (proposed 60 s) any process resumes it from the last committed chunk. The interface shows "resuming".

### D2. Rate limits shared across processes — **Decision needed**

| Option | For | Against |
|---|---|---|
| **A. Counters in PostgreSQL (recommended).** One row per key and time window, incremented with a single `INSERT … ON CONFLICT DO UPDATE`; old windows pruned. Same keys and limits as today. | Correct with any number of processes and across restarts; no new infrastructure. | One small write per counted event. Accepted only if measured overhead on predictions stays within the budget set from the M2 baseline; otherwise predictions keep a per-process limit, documented as an upper bound. |
| B. Redis. | Fast. | New infrastructure. |
| C. Enforce a single process and keep memory counters. | Simplest. | Limits still reset on restart; blocks scaling. |

### D3. Process model

The API will accept a worker count from `WEB_CONCURRENCY` (Uvicorn's standard variable), defaulting to 1. The default is chosen from M2's measured memory per process, because each process loads the model. With D1 and D2 in place, more than one process is correct, and M3 proves it with two.

### D4. Same-origin production topology and a production-like local stack — **Decision needed (proxy image)**

Recommendation: keep ADR 0004. In production the browser reaches one origin; the frontend host forwards `/api/*` and `/health` to the API (Netlify `_redirects` with status 200, or Vercel `rewrites`), so cookies stay first-party and `SameSite=Strict` keeps working. This satisfies PRD 11.2 (Netlify or Vercel) and 11.1 (independently deployable). Cross-site cookies (`SameSite=None`) are rejected: weaker CSRF protection, and Safari and Firefox block them by default.

Phase 5 verifies this locally: a Compose profile `prodlike` with a reverse proxy serving the built frontend over HTTPS and forwarding `/api` to the API with `APP_ENV=production`, `Secure` cookies and `TRUSTED_PROXY_IPS` set to the proxy. **Recommended proxy: the official `caddy:2` image**, whose internal certificate authority gives HTTPS without extra tools. Alternative: `nginx` with a certificate made by `openssl`.

Also proposed for production only: cookie name prefixes `__Host-` (CSRF cookie) and `__Secure-` (session cookie), which browsers enforce. **Decision needed.**

### D5. Test isolation

Browser tests move to their own database, `finguard_e2e_test`, created idempotently by `scripts/e2e_stack.py` (and by the init script on new volumes). The backend suite keeps `finguard_test`. Both names end in `_test`, which every destructive tool still requires.

### D6. CI — **Decision needed (model artefact)**

GitHub Actions, on push and pull request: backend lint, format and tests on a PostgreSQL service; frontend type check, unit tests and build; the explanation checker; `export_openapi.py --check`; `export_model_report.py --check`; dependency audits. The model binary is not in Git, so model-dependent API and browser tests would skip.

| Option | For | Against |
|---|---|---|
| **A. Skip them in CI, but fail if the skipped set differs from a committed expected list (recommended for Phase 5).** | No artefact distribution decision needed yet; skips cannot grow silently. | CI does not run the API or browser tests; they run locally before each commit, as now. |
| B. Publish `model.joblib` as a GitHub Release asset; CI downloads it and checks the pinned hash. | Full CI coverage. | Needs a release, which needs push permission; belongs with Phase 6's artefact strategy (PRD 11.5). |
| C. Git LFS. | Versioned with the code. | LFS quotas; history rewrite risk. |

The workflow cannot run until it is pushed. Until then it is validated by running each of its commands locally and by `actionlint` if approved (section 6). It will not be reported as passing on GitHub without a real run.

## 4. Milestones

Each milestone ends with its tests passing, explanation documents, `PROJECT_CONNECTIONS.md` updated, and one commit.

| Milestone | Scope | Done when |
|---|---|---|
| **M1. Test isolation and reproducibility baseline** | D5; a clean-clone check (fresh clone in a temporary folder: `uv sync --frozen`, `npm ci`, tests without data or model) recording exactly which tests skip and why; base images pinned by digest. | Backend and browser suites run back to back without restarts; the clean clone passes with the recorded skips; frozen artefacts unchanged. |
| **M2. Performance baseline (measured)** | `scripts/measure_performance.py` with synthetic inputs: prediction latency through HTTP (p50, p95, p99; sequential and 8 concurrent clients), batch throughput (1,000 / 10,000 / 50,000 rows), explorer and dashboard query times at 100,000 and 500,000 stored predictions, memory per API process, frontend bundle sizes and page navigation timings. Hardware and versions recorded with each run. | `docs/performance/phase-5-baseline.md` generated from saved run output; budgets for later milestones set from it. Optimisation only where a measurement shows a problem, with before and after figures. |
| **M3. Multi-process correctness** | D2 rate limits; D3 worker count; start-up recovery limited to this process's own work (F1). | A test with two API processes proves the sign-in limit holds across them and across a restart; prediction overhead within budget. |
| **M4. Batch recovery** | D1: queue table and migration 0003, leases, resume from the last chunk, attempt limit, upload bytes removed when done; interface shows "resuming". | Integration tests: the API container is killed mid-batch, restarted, and the job completes with exactly the expected stored rows and no duplicates; two processes never process one job together; a poison file fails after the attempt limit; a browser test watches a job resume. |
| **M5. Production security review** | D4 `prodlike` stack; browser security tests run against it over HTTPS (`Secure` and prefixed cookies, CSRF, CSP, HSTS decision, no CORS needed on one origin, spoofed `X-Forwarded-For` from a client ignored while the proxy's is honoured); secrets review including a scan of all Git history; dependency audits with fixes; expired-session and audit-log pruning command (F8); findings recorded. | `docs/security/phase-5-review.md` lists every finding with severity and status; browser tests pass on the HTTPS stack; audits clean or each remaining advisory explained. |
| **M6. Cross-browser and assistive-technology evidence** | Playwright Firefox and WebKit projects running the functional and responsive suites; fixes for genuine issues; accessibility-tree snapshot tests of key pages (what assistive technology is given); a written screen-reader test protocol (NVDA or Narrator on Windows, VoiceOver on macOS). | Results per browser recorded exactly. WebKit on Windows is not Safari, and is reported as WebKit. Screen-reader compatibility is claimed only for runs a person actually performs and records (section 5). |
| **M7. Integration error handling** | Error boundary with a reload prompt for failed page downloads (F7); behaviour when the database stops and returns (status page, safe 503s, recovery without restart); sessions surviving an API restart; full journeys across a restart. | Browser and integration tests for each case, using the real stack. |
| **M8. CI pipeline** | D6 workflow; expected-skip list; local validation. | Every workflow command passes locally; the workflow file is documented; whether it has run on GitHub is stated plainly. |
| **M9. Documentation review and gate** | Every document checked against the implementation; ADR 0005 for D1–D6; Phase 5 completion record with test evidence, measurements, security findings, limitations, commits and Git status. | Checker 0 problems; all suites pass; frozen hash verified; working tree clean. |

## 5. Browser and screen-reader coverage (condition 7)

- **Firefox and WebKit:** Playwright's own builds, run on this Windows machine. Results will be reported per browser and per test. WebKit here approximates Safari's engine but is not Safari on macOS or iOS; no Safari claim will be made.
- **Screen readers:** automated tests cannot judge spoken output. Phase 5 will provide evidence that can be checked automatically (accessibility-tree snapshots, axe, keyboard tests) and a step-by-step manual protocol. **Decision needed:** whether you will run the protocol with Narrator or NVDA and record the results. If not, documentation will state that screen-reader behaviour is untested.

## 6. New tools and dependencies requested

| Item | Kind | Why | Decision needed |
|---|---|---|---|
| `caddy:2` image | Compose profile `prodlike` only | HTTPS same-origin stack (D4) | Yes (or nginx) |
| Playwright Firefox and WebKit browsers | Test downloads, no package change | M6 | Yes |
| `pip-audit` | Backend `dev` dependency group | Python vulnerability scanning (F11); `npm audit` is built in | Yes |
| `actionlint` | Local binary, not a project dependency | Validate the workflow before it can run on GitHub | Optional |

No runtime dependency is added. D1 and D2 use PostgreSQL, which the project already has.

## 7. Out of scope for Phase 5

- Deployment to any host, managed PostgreSQL, a production URL, releases (Phase 6).
- Slimming the API image by switching to the `xgboost-cpu` package (F12): it changes an installed package the model service pins, so it needs proof of identical scores; proposed for Phase 6 with that proof.
- New pages, features or visual changes.

## 8. Decisions requested

1. D1 batch processing: PostgreSQL queue with in-process workers (recommended), separate worker, or single process.
2. D2 rate limits: PostgreSQL counters (recommended), or single process.
3. D4 proxy for the production-like stack: Caddy (recommended) or nginx; and production cookie prefixes (recommended).
4. D6 CI model artefact: expected-skip list now (recommended), release asset, or LFS.
5. Section 6 tools: Caddy image, Firefox and WebKit browsers, `pip-audit`, optionally `actionlint`.
6. Screen-reader testing: will you run and record the manual protocol?
7. Retention for F8: proposed defaults are expired sessions removed after 7 days and audit entries kept for 365 days, run as a command, not a background job.
