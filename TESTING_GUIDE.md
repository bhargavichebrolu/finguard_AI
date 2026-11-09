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

# Browser tests against the real API and finguard_e2e_test (see ENVIRONMENT_SETUP.md)

# Clean-clone reproducibility check: no dataset, model binary or .env
uv run --project backend python scripts/verify_clean_clone.py

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
| `frontend/tests/e2e/` | The built app in Chromium against the real API and `finguard_e2e_test` | Seeded accounts and data created by each test |

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
