# Changelog

## Phase 6: deployment and release (2026-11-15)

Branch `phase-5-hardening`: Step 1 `23dcb2f`, then the Step 2 verification commit. Not merged into `main`, not pushed, and **not deployed to a public host**: the production configuration was verified in a local rehearsal. Decisions are in [ADR 0006](docs/decisions/0006-phase-6-decisions.md), and evidence is in the [completion record](docs/plans/phase-6-completion.md).

### Added
- **Production deployment on one Docker host:**
  - `docker-compose.prod.yml` runs Caddy, the API, PostgreSQL, migrations and daily retention.
  - `docker/web/Dockerfile` builds the interface from source and serves it with Caddy.
  - `docker/caddy/Caddyfile.production` handles the ACME certificate, HSTS, CSP, and caching.
- **Deployment scripts:**
  - `scripts/generate_production_env.py` writes new secrets to a Git-ignored file.
  - `scripts/verify_deployment.py` runs 26 HTTPS checks of a running deployment.
  - `scripts/score_reference_grid.py` gives an inference-parity fingerprint for image changes.
- **`app/commands/create_admin.py`:** creates the first administrator inside the API container. `scripts/create_admin.py` now calls it.
- **CI:** a third job, `images`, builds both images and validates the production Compose file. It has not run on GitHub.
- **ADR 0006**, DEPLOYMENT.md rewritten, and the Phase 6 completion record.

### Changed
- **API image:**
  - Two-stage build; NVIDIA NCCL no longer installed; 1.92 GB to 979 MB.
  - XGBoost 3.2.0 and scikit-learn 1.9.1 unchanged; identical scores and explanations on 550 synthetic inputs.
- **Explorer pages use a deferred join:** at 180,285 rows, the last page went from 392 to 79 ms, with the same rows.
- **Database init script:** creates a test database only when `TEST_DB_NAME` is set.
- **Browser-test API sessions last 120 minutes**, so a slow run keeps its signed-in sessions.

### Fixed (security findings)
- **S13:** production no longer serves `/docs`, `/redoc` or `/openapi.json`, and refuses to turn them on.
- **S14:** production refuses to start without a trusted proxy, and every environment refuses malformed or all-covering `TRUSTED_PROXY_IPS` entries.
- **S15:** the production Caddyfile obtains a public certificate. This is untested without a public host.
- **Chunked uploads:** Caddy caps request bodies at 11 MB while streaming.

### Results (Step 2 verification, 2026-11-15)
| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Backend, full, with the model | 835 | 0 | 0 (1 deselected: rereads the test partition) |
| CI rehearsal, fresh clone: backend | 514 | 0 | 322, exactly the expected list |
| Frontend unit and component (Vitest) | 111 | 0 | 0 |
| Browser, all seven projects | 311 | 0 | 0 |
| HTTPS production-like | 7 | 0 | 0 |
| Production rehearsal checks (`verify_deployment.py --write`) | 26 | 0 | |
| README demonstration in Chromium | 13 | 0 | |

- **CI rehearsal:** all 23 workflow steps passed, including the explanation checker (245 files, 0 problems), the secret scan (0 findings), `pip-audit` and `npm audit` (0 vulnerabilities), and both image builds.
- **Production rehearsal:** run from a fresh clone, with images built without cache. It survived a crash, a database outage, a full restart, and a backup with data loss and restore. Details are in [DEPLOYMENT.md](DEPLOYMENT.md#6-local-rehearsal-what-was-verified).
- **Frozen model:** hash `69813c17…` and threshold `0.02841914258897305` unchanged; inference fingerprint identical in the old and new images.

### Fixed during verification
- **CI skip list:** the 24 new explorer cases were added to the expected list, and the minimum number of passing tests rose from 480 to 512.
- **API image contents:** it contained explanation documents and bytecode caches; `.dockerignore` now excludes them at every depth.
- **Backup commands:** the backup and restore commands lacked the database password.
- **Model folder:** the deployment steps now create the model folder in a fresh clone.
- **Demonstration wording:** the README demonstration misdescribed what an analyst sees.

### Known limitations
- **Not deployed:** no public host, DNS name or public certificate exists.
- **CI:** it has never run on GitHub.
- **Untested:** Safari, screen readers, and WebKit's SameSite enforcement.
- **Phase 5 residual risks:** the unexplained single Firefox status-change failure, and the Firefox teardown hang under CPU starvation.
- **Limits around the minute boundary:** prediction and upload limits use fixed windows, so up to twice the limit can pass across a minute boundary.
- **Deep explorer offsets:** still pass over earlier rows, though they no longer build them.
- **Development without the proxy:** chunked uploads to the API directly are still spooled before the size check.

## Phase 5: integration hardening, quality assurance and reliability (2026-11-11)

Branch `phase-5-hardening`, nine milestones and the Firefox investigation follow-up (`79b2947`). Accepted on 2026-11-13 with its documented residual risks; not merged into `main`, not pushed. Decisions are in [ADR 0005](docs/decisions/0005-phase-5-decisions.md), and evidence is in the [completion record](docs/plans/phase-5-completion.md).

### Added
- **M1, isolation and reproducibility:**
  - Browser tests have their own database, `finguard_e2e_test`.
  - `scripts/verify_clean_clone.py` records what a clean checkout skips.
  - Base images are pinned by digest.
- **M2, performance baseline:** `scripts/measure_performance.py` and `npm run perf:pages`, using synthetic inputs only. Two measured fixes:
  - Dashboard summary at 500,000 predictions: p50 862 ms to 434 ms.
  - CSV export of 500,000 rows: 109.5 s to 10.4 s, with the same bytes.
- **M3, multi-process correctness:**
  - Rate limits are counted in PostgreSQL, within the latency budget fixed in M2. A first, sliding-window design was over budget and rejected.
  - `WEB_CONCURRENCY` sets the worker count, default 1.
  - Model registration at start-up is serialised with an advisory lock.
- **M4, batch queue:**
  - Upload bytes are stored in `batch_uploads`.
  - One worker per process claims jobs with `FOR UPDATE SKIP LOCKED` and holds a 60-second lease.
  - Each 1,000-row chunk is idempotent, and a job gets at most 3 attempts.
  - A crashed or restarted process's job resumes from its last committed chunk, with no duplicates.
- **M5, production security review:**
  - An HTTPS production-like stack runs through Caddy.
  - Production cookies use `__Secure-` and `__Host-` prefixes.
  - A history-wide secret scan.
  - `pip-audit` and `npm audit`.
  - A retention command: sessions after 7 days, audit records after 365.
  - 15 findings recorded in [docs/security/phase-5-review.md](docs/security/phase-5-review.md).
- **M6, cross-browser:**
  - Playwright Firefox and WebKit projects.
  - Accessibility-tree tests.
  - A Narrator/NVDA checklist, marked UNTESTED.
- **M7, integration error handling:**
  - A database outage answers 503 and the API recovers without a restart.
  - A batch whose database connection drops is resumed, not failed.
  - A model failure while scoring says that nothing was stored.
  - Investigation status changes accept `expected_status`, and a stale one answers 409.
  - The interface says "unavailable" instead of signing out, has error boundaries per page, shows timeout and no-answer messages, and shows the API's message on failed downloads.
- **M8, CI:**
  - `.github/workflows/ci.yml` checks a clean checkout with a PostgreSQL database.
  - `scripts/check_test_run.py` fails on any change to the 298 expected skips, or on missing tests.
  - It has not run on GitHub.
- **M9:**
  - Every document checked against the implementation.
  - ADR 0005.
  - The completion record.

### Fixed
The tests for each fix are named in TESTING_GUIDE.md and in the milestone's commit message.

- **M1:**
  - The model report's source hashes depended on checkout line endings.
  - Three model tests failed instead of skipping without the binary.
  - `export_openapi.py --check` needed `.env`.
  - Component tests timed out on a cold start.
- **M3 and M4:**
  - Memory rate limits multiplied with processes and reset on restart.
  - Start-up failed every unfinished batch job and deleted files in every process (F1).
  - Concurrent start-ups could fail to register the model.
- **M5:** cookies had no browser-enforced prefixes.
- **M6:**
  - The phone menu button showed on desktop in every engine.
  - Large Dashboard totals overflowed their tile in WebKit.
- **M7:**
  - A database outage gave a bare 500.
  - A lost connection failed a resumable batch.
  - A scoring failure gave a bare 500.
  - A stale page could override a colleague's status.
  - A reload during an outage signed the user out.
  - A failed page download blanked the app (F7).
  - Failed downloads lost the API's message (since Phase 4).
  - No answer gave no hint that a change might have been saved.
- **M8:** a skip-reason check that would have accepted a database-caused skip.
- **Gate follow-up:** the batch progress test read the bar and its label in two calls, which could straddle a re-render (2 of 13 Firefox runs). They are now read in one call, with the same assertions.

### Results at the gate
| Suite | Passed | Failed | Skipped | Deselected |
|---|---|---|---|---|
| Backend, full, with the model | 778 | 0 | 0 | 1 (rereads the test partition) |
| Frontend unit and component (Vitest) | 111 | 0 | 0 | 0 |
| Browser, first gate run (all seven projects) | 309 | **2, both Firefox, unexplained** | 0 | 0 |
| Browser, full rerun (all seven projects) | 311 | 0 | 0 | 0 |
| HTTPS production-like | 6 | 0 | 0 | 0 |
| CI rehearsal, fresh clone: backend | 480 | 0 | 298, exactly the expected list | 1 |
| CI rehearsal, fresh clone: frontend | 111 | 0 | 0 | 0 |

Browser rerun by project: setup 5, desktop 83, tablet 19, mobile 19, firefox 83, webkit 83, webkit-mobile 19.

Other checks, all passed on the CI rehearsal of the final tree (all 19 workflow steps):
- `ruff check`, and `ruff format --check` (167 files).
- Explanation checker: 235 files, 0 problems.
- `export_openapi.py --check` and `export_model_report.py --check`.
- `scan_secrets.py`: 0 findings, 0 secret files.
- `pip-audit` and `npm audit`: 0 known vulnerabilities.
- Type check and production build.

The CI workflow itself has **not** run on GitHub.

Frozen model hash `69813c17…` unchanged. Nothing under `data/`, `artifacts/` or `experiments/` changed in Phase 5, apart from M1's correction of the source hashes in the derived `model_v1_report.json`, where every value is identical. Also, the threshold is unchanged and the test partition was not read.

### Known limitations
- **Not tested:** Safari itself, and any screen reader. The Narrator/NVDA checklist is UNTESTED until the owner runs it.
- **WebKit SameSite:** whether WebKit enforces SameSite=Strict is not established. These tests check only that the server sends it.
- **CI:** it has not run on GitHub, and it cannot run real-model, API, browser or HTTPS tests, because the model binary is not in Git.
- **Secure cookies:** `Secure` and the cookie prefixes are verified in Chromium only, on a local certificate authority.
- **Intermittent Firefox failures** (investigated after the gate; see [phase-5-firefox-investigation.md](docs/plans/phase-5-firefox-investigation.md)):
  - A case change in the Investigation Centre did not show within 10 seconds, once in M7 (assignment) and once in the first gate run (status). It was not reproduced in 33 runs, and its cause is not identified. The status test now checks the request and the API's answer in turn, so a recurrence would show which step broke. **Residual risk awaiting the reviewer's decision.**
  - Closing a browser context can hang in Playwright's Firefox build under CPU starvation (11 hangs in 3 loaded runs, none in 30 without load). This is a test-infrastructure limitation, not an application defect.
- **Stored test sessions last 30 minutes:** a browser run slower than that fails with Sign in pages.
- **Duplicates without an identifier:** a prediction without an identifier whose answer was lost can be stored twice if resubmitted. The interface warns about this.
- **Last writer wins on assignment:** assignment changes carry no expected value; every change is audited.
- **Interrupted batches while the database is down:** they resume after the 60-second lease rather than at once.
- **Deep explorer pages are slow:** they use `OFFSET`.
- **Limits around the minute boundary:** prediction and upload limits use fixed windows, so up to twice the limit can pass across a minute boundary.
- **Left for Phase 6:**
  - deployment;
  - a public certificate;
  - the trusted proxy list for the host;
  - whether to keep `/docs` in production;
  - the 1.92 GB API image.

## Phase 4: React frontend (2026-11-08)

### Added
- **M1, backend support:** HttpOnly, SameSite=Strict cookie sessions backed by a revocable `user_sessions` table, CSRF tokens and origin checks, permissions at sign-in, a restricted assignee list, a read-only model report built only from saved Phase 2 files (hash-pinned), Content Security Policy headers, and proxy trust that is off unless `TRUSTED_PROXY_IPS` is set.
- **M2, foundation:** React 18 and TypeScript strict, typed API calls generated from `frontend/openapi.json`, an Axios client that adds the CSRF header, role-aware navigation from one page registry, loading, empty, error and confirmation states, and the score disclosure.
- **M3–M6, pages:** all ten PRD 7.4 pages. Dashboard, Transaction Analysis, CSV Batch Analysis, Transaction Explorer, Investigation Centre, Model Performance, Explainable AI, Reports, Settings and System Information. Every chart has a table view. Pages are code-split.
- **M7, browser tests:** Playwright against the real API in Docker (port 8011) and the `finguard_test` database, at 1440 x 900, 768 x 1024 and 390 x 844, with axe-core WCAG 2.2 A/AA checks. `scripts/e2e_stack.py` and `scripts/e2e_database.py` start the isolated stack and seed it with random passwords, refusing any database not named `*_test`.
- Results: backend 677 passed, 1 deselected (the test that rereads the test partition), 0 failed, 0 skipped. Frontend unit and component 98 passed. Browser 103 passed (5 setup, 64 desktop, 17 tablet, 17 mobile), 0 failed, 0 skipped. Accessibility: 0 axe violations, no rules disabled.

### Fixed in M7 (each with a regression test)
- The API let an administrator deactivate their own account while another administrator existed; only the button had been disabled.
- Visually hidden table headers escaped their scroll area and widened pages by up to 512 px on tablets and phones.
- Scrolling tables were not reachable by keyboard; a long-option select widened the mobile viewport; some controls were under 24 px.
- The closed mobile menu's links could take keyboard focus; Escape now closes the menu.
- Confirmation dialogs let focus escape and did not return it.
- "FinGuard AI" and "Sign out" wrapped onto two lines at 390 px.
- A file chosen before the upload limits loaded skipped the client-side check.

### Verified
- Cookie flags, no token in browser storage, revocation on sign-out, expiry, tampered cookies, CSRF, origin and CORS refusals, and the sign-in rate limit, in a real browser.
- Every role's refusals hold when the API is called directly, not only in the interface.
- Model Performance values equal the original saved files (`selection.json`, `test_evaluation.json`, `model_v1_metrics.json`, `model_v1.json`, `all_runs.csv`), and those files still match their recorded hashes.
- Investigation history stays a consistent chain under 16 simultaneous changes from two users.
- Frozen model hash unchanged; no Phase 1 or 2 artefact or result changed; no file under `data/` was read.

### Known limitations
- Browser tests run over plain HTTP, so the `Secure` cookie flag is checked by unit tests only, and only Chromium is tested.
- Automated accessibility checks are partial: no screen-reader or real-device testing yet.
- The interface must be served from the same origin as the API (ADR 0004), which the Phase 6 host must provide.
- Rate limits are per API process, and the browser-test and backend suites share `finguard_test`, so they cannot run at the same time.

## Phase 3: Backend and database (2026-11-07)

### Added
- FastAPI service with prediction, transaction explorer, CSV batch, investigation, model, report, settings, user and audit endpoints, documented at `/docs`.
- Verified model loading: version, hash and threshold pinned in code, library versions and preprocessing hash checked, and the file hash checked before opening. Nothing trains.
- `model_score` (uncalibrated) and `FLAG_FOR_REVIEW` wording throughout. Each prediction records its model version, threshold and high risk boundary.
- PostgreSQL 17 through SQLAlchemy and Alembic, with 12 tables, CHECK constraints that refuse contradictory predictions, and labels stored separately from predictions.
- Argon2id passwords, signed tokens checked against the database on each request, four roles, rate limits, audit logging, safe errors and security headers.
- Docker Compose stack: SCRAM authentication from first initialisation, a non-superuser application role, and an API image without training libraries that mounts the model read-only.
- `scripts/generate_env.py` and `scripts/create_admin.py`.
- Explanation documents beside every new source and configuration file, and checker support for both locations.
- 625 backend tests passed, 0 failed, 0 skipped: 321 unit, 75 integration and 229 API tests. 253 of them run on real PostgreSQL. One Phase 2 test that rereads the test partition was deselected.

### Verified
- **Database authentication:** correct, wrong and missing passwords behaved as expected from Windows, from another container, and inside the database container. All rules were SCRAM before and after recreating the container on the same volume, and a marker row survived.
- **End to end in Docker:** login, prediction, CSV batch, investigation update, metrics and summary all worked over HTTP. The container and Windows gave identical scores.
- **Phase 2 metrics:** served unchanged, with the shortfalls stated. Test false positive rate was 0.282% against the 0.1% target, recall was 45.9% overall and 21.9% in normal steps.

### Fixed
- Database connections from Windows could hang indefinitely, because `localhost` tries IPv6 first and Compose publishes IPv4 only. Addresses now use `127.0.0.1`, and migrations have a connection timeout.
- Investigation history was ordered by transaction start time, which put simultaneous changes out of order. Rows are now stamped with `clock_timestamp()` after the lock is held.
- Flags-by-day grouping used true division in SQLAlchemy 2, which split each day.
- Two route-coverage tests checked nothing, because they walked a route list that was empty in this FastAPI version. They now walk the OpenAPI schema and require a minimum number of routes.
- `.env.example.explanation.md` matched `.env.*` in `.gitignore` and had never been committed. It now has an exception, and a test fails if any explanation document is ignored.

### Known limitations
- Rate limits and batch recovery assume one API process. A restart interrupts batch jobs, which must be uploaded again.
- The API image is 1.92 GB, 469 MB of it NVIDIA libraries required by XGBoost's Linux wheel and unused by this model.
- PRD 6.8's full model comparison, curves and experiment history are saved but not served by the API.
- No Content Security Policy, no token revocation list, and client addresses behind a proxy are not yet trusted correctly.
- Phase 1 and 2 explanation documents remain in `docs/file-explanations/`, and Phase 3 documents sit beside their files.
- The frontend is unchanged and has no automated tests.

## Phase 2: Machine learning experiments (2026-11-07)

### Added
- Six model families and four imbalance strategies, with oversampling confined to training folds.
- A selection rule and threshold objective, committed before any candidate was scored.
- Temporal drift analysis, a label-independent definition of sparse steps, threshold analysis, TreeSHAP explanations, and a single guarded test evaluation.
- Hash-verified model loading that imports no training code.
- 322 backend tests: 301 on synthetic data and 21 on real outputs. All passed, none skipped.

### Results
- 125 runs recorded on validation, none failed.
- Selected: XGBoost on the original distribution, threshold 0.02842. XGBoost, LightGBM and CatBoost were statistically tied on validation.
- Test, evaluated once: PR-AUC 0.4242, ROC-AUC 0.9524, precision 40.7%, recall 45.9%, false positive rate 0.282%.
- Recall was 56.1% in sparse steps and 21.9% in normal steps.

### Fixed
- `final_evaluation.py` labelled the commit the model was fitted from as the freeze commit, found on review before test was opened. The field was renamed and the tests now check Git history.
- Generated tables left out the sensitivity runs and listed partitions alphabetically.
- Chart label collisions and unreadable text in confusion matrices.
- `KeyError`s in reports for empty slices, found by testing on real outputs.

### Known limitations
- The false positive rate on test was 2.8 times the 0.1% cap set on validation.
- Validation overstated results in sparse steps (recall 95.6% against 56.1% on test). The likely cause, reliance on hour, is not confirmed.
- LightGBM's matrix results on the original distribution and class weighting reflect a numerical divergence, not those strategies. See `ML_EXPERIMENTS.md`.
- Scores are not calibrated probabilities.
- Phase 2 peak memory was not measured.
- PaySim has no untouched window left, so a revised model could not be fairly measured on it.

## Phase 1: Foundation and data engineering (2026-11-06)

### Added
- Repository structure from PRD section 13, with later-phase folders held empty.
- Python 3.11 environment with uv, and the full training stack verified to import.
- React, TypeScript and Vite toolchain, with a placeholder page.
- Streaming dataset validation, EDA, feature engineering, leakage audit and chronological partitioning.
- 89 backend tests, including tamper tests that prove the audit and documentation checker can fail.
- Documentation checker that enforces PRD section 12, and an explanation document for every source file.
- All documents required by PRD 12.4, with unbuilt parts clearly marked as planned.

### Results
- Dataset verified: 6,362,620 rows, 8,213 fraud rows, no missing values or duplicates.
- Partitions: train steps 1 to 322, validation 323 to 377, test 378 to 743.
- Preprocessing reproduced byte-identically on rerun.

### Fixed
- A floating-point error in split boundary selection, found by a unit test. It did not affect the real boundaries.
- Security advisories, by moving to React Router 7 and Vite 8 before any page used them.

### Known limitations
- `make` and Docker are not installed on the development machine, so the `Makefile` is unexecuted as a file and no container exists.
- The successful Kaggle download route has not been run, as no token is available.
- The frontend has no automated tests yet.
