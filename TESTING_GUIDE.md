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

## Test types

| Folder | Purpose | Data |
|---|---|---|
| `backend/tests/unit/` | One module at a time | Synthetic fixtures, and the frozen model for `test_model_service.py` |
| `backend/tests/integration/` | Pipeline stages, real outputs, and migrations on PostgreSQL | Synthetic fixtures, real outputs, test database |
| `backend/tests/api/` | The real application through HTTP, on real PostgreSQL with the frozen model | Hand-written requests |

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
