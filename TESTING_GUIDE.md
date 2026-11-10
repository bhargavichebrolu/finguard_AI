# Testing Guide

## Commands

Run from the repository root.

```powershell
# Database tests need PostgreSQL: start it once
docker compose up -d --wait db

# Everything, including checks on real pipeline outputs where present
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml

# Phase 3 and later: leave out the one test that rereads the test partition
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml --deselect tests/integration/test_real_models.py::test_test_results_can_be_recalculated_from_the_saved_model

# Without real data or a database, as CI will start
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml -m "not real_data and not database"

# Lint and format, from the repository root
uv run --project backend ruff check backend scripts --config backend/pyproject.toml
uv run --project backend ruff format --check backend/app backend/tests/api backend/migrations --config backend/pyproject.toml

# Documentation rule
uv run --project backend python scripts/check_explanations.py

# Frontend: type check, unit and component tests, production build
cd frontend; npm run typecheck; npm test; npm run build

# Browser tests against the real API and finguard_e2e_test (see ENVIRONMENT_SETUP.md);
# every engine by default, or one: npm run test:e2e -- --project=setup --project=webkit

# Clean-clone reproducibility check: no dataset, model binary or .env
uv run --project backend python scripts/verify_clean_clone.py

# HTTPS production-like stack (see ENVIRONMENT_SETUP.md)
uv run --project backend python scripts/prodlike_stack.py up
cd frontend; npm run test:prodlike

# Secrets in all history, and dependency audits
uv run --project backend python scripts/scan_secrets.py
uv run --project backend pip-audit
cd frontend; npm audit

# Performance (browser-test stack running; see docs/performance/phase-5-baseline.md)
uv run --project backend python scripts/measure_performance.py run --out docs/performance/<name>.json
cd frontend; npm run perf:pages
uv run --project backend python scripts/e2e_stack.py up
cd frontend; npm run test:e2e
```

Frontend unit and component tests use Vitest with Testing Library and a mock API (Mock Service Worker) answering the real paths with typed fixtures. `source-rules.test.ts` also scans `src/` for forbidden wording, hardcoded Phase 2 figures, browser storage and inline styles, and checks the generated API types are current.

Database tests read `TEST_DATABASE_URL` from the environment or `.env`, and skip when it is absent. They delete rows, so they refuse any database whose name does not end in `_test`. API tests also need the frozen model file, and skip without it.

**The test partition after Phase 2.** `test_test_results_can_be_recalculated_from_the_saved_model` rereads the test partition to confirm recorded counts. That is an integrity check, not analysis, but Phase 3 was told to do no further work on the test set, so it was deselected throughout Phase 3. No Phase 3 test reads test data. Phase 3 tests use hand-written inputs and the saved metrics file.

## Coverage by PRD 14.1 requirement

| Requirement | Where it is tested | Status |
|---|---|---|
| Dataset validation | `test_dataset_validation.py`, `test_real_data.py` | Done |
| Feature schema | `test_schema.py` | Done |
| Target separation | `test_data_pipeline.py`, `test_features.py` | Done |
| Leakage prevention | `test_features.py`, `test_data_pipeline.py`, `test_model_service.py` (label and balance columns do not change scores) | Done |
| Train/test temporal boundaries | `test_splitting.py`, `test_data_pipeline.py`, `test_real_data.py` | Done |
| Preprocessing consistency | `test_data_pipeline.py`, `test_features.py`, `test_model_service.py` (single row equals batch) | Done |
| Reproducibility | `test_data_pipeline.py`, `test_experiments.py`, `test_phase2_pipeline.py`, `test_real_models.py` | Done |
| Model loading | `test_model_artifacts.py`, `test_model_service.py` (tampered files refused before opening) | Done |
| Prediction output, probability range | `test_candidates.py`, `test_model_artifacts.py`, `test_model_service.py` | Done |
| Threshold behaviour | `test_evaluation.py`, `test_selection.py`, `test_model_service.py` (exactly at the threshold, and the next float below) | Done |

## Coverage by PRD 14.2 requirement

| Requirement | Where it is tested |
|---|---|
| Health endpoint | `test_auth.py` |
| Input validation | `test_transactions.py`, `test_batches.py`, `test_config.py` |
| Prediction endpoint | `test_transactions.py` (score equals the model called directly, and version and threshold are stored) |
| Invalid requests | `test_transactions.py`, `test_batches.py`, `test_investigations.py`, `test_models_and_reports.py` |
| CSV upload | `test_batches.py` |
| Database integration | `test_migrations.py`, plus every API test on real PostgreSQL |
| Investigation updates | `test_investigations.py`, including simultaneous changes |
| Authentication | `test_auth.py`, including forged, expired and unsigned tokens |
| Error responses | `test_auth.py`, `test_batches.py` |

## Phase 3 rules and their tests

| Rule | Where it is tested |
|---|---|
| Model and threshold cannot change | `test_model_service.py`, `test_config.py`, `test_models_and_reports.py` (settings refuse any threshold) |
| Hashes verified before loading | `test_model_service.py` (`joblib.load` never runs on a tampered file) |
| Phase 2 metrics preserved | `test_models_and_reports.py` (exact equality with the saved file, and the required figures) |
| `model_score`, not probability | `test_transactions.py`, `test_migrations.py` |
| Labels never affect scores | `test_model_service.py`, `test_batches.py` |
| Flags, workflow and labels kept apart | `test_models_and_reports.py`, `test_investigations.py` |
| SCRAM and least privilege | `test_migrations.py`, plus manual checks in `DATABASE_SCHEMA.md` |
| Every route needs a token | `test_auth.py`, from the OpenAPI schema |

## Phase 4 browser tests

Playwright drives Chromium against the real API (Docker, port 8011) and PostgreSQL (`finguard_e2e_test`, apart from the backend suite's `finguard_test`), never a mock. 103 tests: 5 sign-in setups, 64 on desktop (1440 x 900), and the layout and accessibility spec again on tablet (768 x 1024) and mobile (390 x 844), 17 each.

| Area | Spec | Checks |
|---|---|---|
| Authentication | `auth.spec.ts` | Sign-in and sign-out, reload persistence, cookie flags, nothing in browser storage, revocation, expiry, tampered cookies, one message for bad credentials, the sign-in rate limit, CSRF and origin refusals, CORS, security headers |
| Roles | `roles.spec.ts` | Navigation per role in PRD order, restricted pages by address, and every restricted action refused by the API when called directly; demo records kept apart |
| Predictions | `predictions.spec.ts` | Field and API validation, the score as an uncalibrated four-decimal number, no sentence presenting it as a probability, limitations recomputed from `model_v1_metrics.json`, the stored record in the explorer |
| CSV batches | `batches.spec.ts` | File and column checks, progress on 20,000 rows, row-level errors, paging, results and error downloads, no formula cells in exports |
| Investigations | `investigations.spec.ts` | Filters, assignment, status changes with confirmation, notes and history after reload, and history order under 16 simultaneous changes from two users |
| Model Performance | `model-performance.spec.ts` | Values compared with `selection.json`, `test_evaluation.json`, `model_v1_metrics.json`, `model_v1.json` and `all_runs.csv`; source hashes unchanged; validation and test labelled apart; only GET requests, none to `data/` |
| Reports and Settings | `reports-settings.spec.ts` | Four downloads and their contents, the high risk boundary with confirmation and its effect on new predictions, password change, account creation, role change, deactivation ending a live session, no self-deactivation in the interface or the API |
| Layout and accessibility | `responsive.spec.ts` | Every page at three sizes: no horizontal scrolling, axe WCAG 2.0/2.1/2.2 A and AA, no CSP or console errors, 24 px targets; the top bar on one line; the menu, skip link, focus ring, dialog focus trap, chart tables by keyboard; the sign-in page and its error state |

### Accessibility results

Automated: axe-core 4.14.0 with the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` and `wcag22aa` tags, on all ten pages, an open investigation with its dialog, the open mobile menu, the collapsed desktop menu and the sign-in page with an error, at all three sizes. **Final result: 0 violations. No rules are disabled and no elements are excluded, so there are no exceptions to justify.**

Defects found and fixed in M7, each with a regression test:

| Defect | Fix | Regression test |
|---|---|---|
| A visually hidden column header escaped its table's scroll area, widening pages by up to 512 px on tablet and mobile | `.table-wrap` is positioned | `responsive.spec.ts` overflow checks |
| Scrolling tables could not be reached by keyboard (axe `scrollable-region-focusable`, serious) | `TableScroll`: a focusable, named group around every table | `accessibility.test.tsx`, axe |
| The assignee select widened the mobile layout viewport to 405 px | Selects in inline rows can shrink | `responsive.spec.ts` viewport check |
| Table "Open" buttons and a checkbox were under 24 px | 24 px minimum | `responsive.spec.ts` target sizes |
| The closed mobile menu's links could take keyboard focus | Closed menu is `visibility: hidden`; Escape closes it and returns focus | `responsive.spec.ts`, `accessibility.test.tsx` |
| Confirmation dialogs let focus escape and did not return it | Focus trap and return in `ConfirmDialog` | `accessibility.test.tsx`, `responsive.spec.ts` |
| "FinGuard AI" and "Sign out" wrapped at 390 px | No wrapping; icon-only sign-out with its accessible name below 480 px | `responsive.spec.ts` (failed before the fix) |
| A file chosen before upload limits loaded skipped the client check | Check derived on every render | `pages-m4.test.tsx` |
| The API allowed an administrator to deactivate their own account | Refused in `update_user` | `test_auth.py`, `reports-settings.spec.ts` |

Not automated: screen-reader listening, colour contrast inside chart images (charts have table views, and the palette passed the dataviz validator in M3), and real touch devices. Automated checks find only part of all accessibility problems.

## Cross-browser and assistive-technology results (Phase 5 M6)

The same browser tests run in Playwright's Firefox and WebKit builds as well as Chromium, all against the real API and `finguard_e2e_test`. Final run, 2026-11-09, one worker:

| Project | Engine (Playwright 1.65 build) | Viewport | Tests | Passed | Failed | Skipped |
|---|---|---|---|---|---|---|
| setup | Chromium | 1440 x 900 | 5 | 5 | 0 | 0 |
| desktop | Chromium | 1440 x 900 | 72 | 72 | 0 | 0 |
| tablet | Chromium | 768 x 1024, touch | 19 | 19 | 0 | 0 |
| mobile | Chromium | 390 x 844, mobile emulation | 19 | 19 | 0 | 0 |
| firefox | Firefox 159 | 1440 x 900 | 72 | 72 | 0 | 0 |
| webkit | WebKit 27.2 | 1440 x 900 | 72 | 72 | 0 | 0 |
| webkit-mobile | WebKit 27.2 | 390 x 844, touch | 19 | 19 | 0 | 0 |
| **Total** | | | **278** | **278** | **0** | **0** |

**What this does and does not show.** The WebKit results are Playwright's WebKit build on Windows: the engine Safari uses, not Safari on macOS or iOS, and `webkit-mobile` is a narrow touch window, not an iPhone (WebKit does not support Playwright's mobile emulation). Safari itself is untested. Firefox is Playwright's build of the release engine.

**Defects found by the new engines, each fixed with a regression test:**

| Defect | Engines affected | Fix | Regression test |
|---|---|---|---|
| The phone menu button was also shown on desktop, beside the collapse toggle, and took keyboard focus; the collapse toggle likewise showed on phones | All, since Phase 4 (found through WebKit's focus order) | `.mobile-only` and `.desktop-only` win over `.button` | `responsive.spec.ts` "only the navigation control for this width is shown" |
| Dashboard totals in the billions overflowed their tile by 9 px | WebKit | Tiles at least 220 px; the figure's size follows the tile and never wraps | `responsive.spec.ts` "every figure fits its tile on one line" |

**Test changes for engine behaviour, none removing a check:**

- **Screenshots after the CSP check:** in WebKit every Playwright screenshot injects a style that the page's CSP refuses. Nothing is reported on load or after axe; the order keeps the check about the app.
- **Skip link in WebKit:** this WebKit build moves focus to no link with Tab or Option+Tab, so the test focuses the skip link directly and checks the rest. Its place first in the Tab order is checked in Chromium and Firefox.
- **Dialog focus return:** opened from the keyboard. In WebKit, as in Safari, a click does not focus a button, so there is no control to return to.
- **SameSite:** every engine checks the server's `Set-Cookie: SameSite=Strict`. WebKit's stored attribute reads `None` here and is not asserted (recorded in SECURITY.md).
- **Accounts:** tests that use an account up create their own, and the Accounts table is paged through, so each engine starts clean.
- **Batch progress:** the test polls until the job is completed, not until the bar reads 100. The last chunk is stored a moment before completion, which made one check depend on timing.

**Assistive technology.** `accessibility-tree.spec.ts` checks the tree screen readers receive on key screens: landmarks, the ten links in order, names, the invalid state and its description, a named modal dialog, and chart tables. It passes in all three engines. It shows what is exposed, not what is spoken. **Screen-reader behaviour is UNTESTED:** the Narrator and NVDA checklist in [docs/accessibility/screen-reader-checklist.md](docs/accessibility/screen-reader-checklist.md) has not been run.

## Integration failure results (Phase 5 M7)

Failures are produced for real wherever possible: the browser-test API container is stopped or restarted, and the browser-test database refuses connections (`python scripts/e2e_stack.py database off`, which affects `finguard_e2e_test` only). Faults that cannot be produced on demand otherwise (a page's code failing to download, a delayed or dropped response, a connection lost inside one chunk) are injected, and the code behind them is real.

| Requirement | Where it is tested | Result |
|---|---|---|
| API unavailable, slow or returning errors | `resilience.spec.ts` (API stopped and started; delayed answer; dropped answer; failed page download), `resilience.test.tsx` (timeout, no answer, 503, proxy 502) | Passed |
| Session ending during a task | `resilience.spec.ts` (expired on the server mid-form: sign-in, back to the same page, nothing stored); `auth.spec.ts` (expiry, revocation) | Passed |
| Database lost and recovered | `test_failures.py` (real connection failure gives 503; all connections ended, next request succeeds); `resilience.spec.ts` (outage: actionable message with reference, still signed in, recovers without a restart) | Passed |
| Batch failures, interruptions, retries, duplicate submissions | `test_failures.py` (lost connection resumes with every row once; lease recovery while still down; other errors still fail), `test_batch_queue.py` (crashes, leases, attempt limit), `batches.spec.ts` (database off mid-job: resumes at attempt 2, 20,000 rows once; same file twice stores each identified row once; API restart mid-job) | Passed |
| Model loading and inference failures | `test_model_service.py` (start-up refuses altered, missing or mismatched model files), `test_failures.py` (scoring failure: 500 with a reference, nothing stored, retry succeeds), `test_batches.py` (scoring failure in a batch fails the job without revealing the cause) | Passed |
| Report download failures | `resilience.spec.ts` (download during the outage: message and reference, no file; works after), `pages-m6.test.tsx` | Passed |
| Concurrent investigation updates and history | `test_failures.py` (stale status refused; of eight simultaneous changes from one status exactly one applies), `test_investigations.py` (16 simultaneous changes keep the history chain), `investigations.spec.ts` (stale page refused, current status shown, fresh decision succeeds) | Passed |
| Errors safe and actionable | `assert_safe` in `test_failures.py` and `expectSafeAlert` in `resilience.spec.ts`: no SQL, driver, host, trace or password text; a reference to quote | Passed |
| No duplicate predictions, no silently lost jobs | Batch resume tests count rows and predictions per job; double-pressing Score stores one transaction; an interrupted job is resumed, never left or failed silently | Passed |

**Browser runs, 2026-11-10, all seven projects, one worker:**

| Run | Tests | Passed | Failed | Skipped |
|---|---|---|---|---|
| First full run | 311 | 310 | 1 | 0 |
| Final full run | 311 | 311 | 0 | 0 |

Per project in the final run: setup 5, desktop 83, tablet 19, mobile 19, firefox 83, webkit 83, webkit-mobile 19, all passed.

**An unexplained intermittent failure.** In the first run, the Phase 4 test "assigns a case to a colleague, to me and to nobody" failed once in Firefox: after "Assign to me", the case still showed the colleague for 10 seconds. It was investigated and not reproduced: the batch and investigation specs were rerun in Firefox in the same order, building the same large queue, with every request logged. All 18 tests passed, and each action sent exactly one PATCH, answered 200 within about 60 ms, so a stray second change from the select is ruled out. The test passed in four repeated runs and in the final full run. Its cause is not known; the test is unchanged and still asserts the same thing. If it recurs, record the request log in the same way.

**Defects found and fixed, each with a regression test that failed before the fix:**

| Defect | Fix | Regression test |
|---|---|---|
| A database outage answered `500 Internal server error`, which says nothing useful | Connection errors answer 503 "The database could not be reached. Try again in a moment; if this continues, tell an administrator." with `Retry-After` | `test_failures.py` (two outage tests), `resilience.spec.ts` |
| A batch whose database connection dropped mid-job was marked FAILED, although its stored chunks made it resumable | A lost connection gives the job back for resumption (within the attempt limit); other errors still fail it | `test_failures.py` (two batch tests), `batches.spec.ts` |
| A model failure while scoring answered a bare 500 | `ScoringError`: nothing stored, a message saying so and a reference | `test_failures.py` |
| A stale investigation page could silently override a colleague's newer status | `expected_status`: a change from a stale status is refused with 409 naming the current status; the page reloads the case | `test_failures.py`, `investigations.spec.ts`, `pages-m5.test.tsx` |
| Reloading during an API restart or database outage sent a signed-in user to the sign-in page | Only a 401 means signed out; otherwise "FinGuard AI is unavailable" with Try again, keeping the session and the page | `resilience.test.tsx`, `resilience.spec.ts` |
| A page whose code failed to download blanked the whole interface (finding F7) | `ErrorBoundary` per page and around the app, with a reload prompt | `resilience.test.tsx`, `resilience.spec.ts` |
| Failed downloads showed only a default message, without the API's text or reference (since Phase 4) | The client reads Blob error bodies before mapping them | `pages-m6.test.tsx` (two tests), `resilience.spec.ts` |
| A request with no answer could not say it timed out, nor warn that a change may have been saved | Timeout and no-answer messages; "may still have been saved" for changes | `resilience.test.tsx` |

**Known limitations from this milestone:**

- A prediction submitted **without** a transaction identifier whose answer is lost may already be stored; submitting it again stores a second record. The interface warns that the change may have been saved; giving an identifier makes a repeat a refused duplicate (409).
- If the database is still down when a batch is interrupted, the job resumes when its lease runs out (60 seconds) rather than at once. A job interrupted three times is failed, with its stored rows kept.
- Assignment changes carry no expected value: the last one wins, and each is audited.
- The reload prompt reloads the page, so unsaved input on that page is lost.

## Clean-clone results (Phase 5 M1)

`scripts/verify_clean_clone.py` on a fresh clone without `.env`, the model binary or the dataset: lockfile installs, backend 421 passed, 0 failed, 270 skipped (1 deselected); repository checks passed; frontend 98 passed and the build succeeded. Every skip has one of two reasons:

| Reason | Tests | Where |
|---|---|---|
| Frozen model binary absent (not in Git) | 264 | `tests/api/*` (242, because the app verifies the model at start-up), `test_model_service.py` (19), `test_real_models.py` (3) |
| Full dataset and processed partitions absent | 6 | `test_real_data.py` |

The first run found four problems, all fixed in M1: the report's source hashes depended on checkout line endings; three model tests failed instead of skipping without the binary; `export_openapi.py --check` needed `.env`; and three component tests timed out on a cold start.

## Test types

| Folder | Purpose | Data |
|---|---|---|
| `backend/tests/unit/` | One module at a time | Synthetic fixtures, and the frozen model for `test_model_service.py` |
| `backend/tests/integration/` | Pipeline stages, real outputs, and migrations on PostgreSQL | Synthetic fixtures, real outputs, test database |
| `backend/tests/api/` | The real application through HTTP, on real PostgreSQL with the frozen model | Hand-written requests |
| `frontend/tests/unit/` | Components and pages with Vitest and a mock API | Typed fixtures with invented values |
| `frontend/tests/e2e/` | The built app in Chromium, Firefox and WebKit against the real API and `finguard_e2e_test` | Seeded accounts and data created by each test |

## Manual checks run in Phase 3

Not automated, so they are listed here with their results:
- **Database security:** correct, wrong and missing passwords from another container, from Windows and inside the database container, before and after recreating the container. All behaved as expected. See `DATABASE_SCHEMA.md`.
- **Docker end to end:** the image has no training libraries, migrations ran, the API loaded the model from a read-only mount, and login, prediction, CSV batch, investigation update and metrics all worked over HTTP.
- **Cross-platform score:** the Linux container and Windows gave the same `model_score` to every bit, 0.8377037048339844, for one transaction.

## Writing tests

- Corrupt one thing per test, and state the expected result by hand rather than copying it from output.
- A check that can fail must have a test proving it fails.
- A test that loops over something must also assert that it found something. Phase 3 found two tests checking nothing this way, because the route list they walked was empty in this FastAPI version.
- Update an expected value only when the behaviour change is intended.

## Latest recorded results

Latest results are recorded per phase in [CHANGELOG.md](CHANGELOG.md).
