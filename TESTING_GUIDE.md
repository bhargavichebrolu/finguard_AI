# Testing Guide

## Commands

Run from the repository root.

```powershell
# Everything, including checks on real pipeline outputs where present
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml

# Skip real-data checks, as CI will
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml -m "not real_data"

# Lint
uv run --project backend ruff check backend scripts --config backend/pyproject.toml

# Documentation rule
uv run --project backend python scripts/check_explanations.py

# Frontend type-check and build
cd frontend; npm run build
```

## Coverage by PRD 14.1 requirement

| Requirement | Where it is tested | Status |
|---|---|---|
| Dataset validation | `test_dataset_validation.py`, `test_real_data.py` | Done |
| Feature schema | `test_schema.py` | Done |
| Target separation | `test_data_pipeline.py`, `test_features.py` | Done |
| Leakage prevention | `test_features.py` (tampering has no effect), `test_data_pipeline.py` (tampered files rejected) | Done |
| Train/test temporal boundaries | `test_splitting.py`, `test_data_pipeline.py`, `test_real_data.py` | Done |
| Preprocessing consistency | `test_data_pipeline.py` (stored features equal a direct call), `test_features.py` (single row equals batch) | Done |
| Reproducibility | `test_data_pipeline.py`; byte-identical metadata also checked by hand on the real data | Done for data; models in Phase 2 |
| Model loading, prediction output, probability range, threshold behaviour | None yet | Phase 2 |

Backend, frontend, integration and deployment tests (PRD 14.2 to 14.5) belong to later phases. The frontend has no automated tests yet: its only check is the type-check and production build.

## Test types

| Folder | Purpose | Data |
|---|---|---|
| `backend/tests/unit/` | One module at a time | Small synthetic fixture from `conftest.py` |
| `backend/tests/integration/test_data_pipeline.py` | Pipeline stages together, tamper tests | Same synthetic fixture |
| `backend/tests/integration/test_real_data.py` | Saved outputs versus published dataset figures | Real outputs; skipped if absent |
| `backend/tests/api/` | API tests | Empty until Phase 3 |

## Writing tests

- Corrupt one thing per test, and state the expected result by hand rather than copying it from output.
- A check that can fail must have a test proving it fails. The audit and documentation checker both have known-bad tests.
- Update an expected value only when the behaviour change is intended. Treat a failing leakage test as an alarm.

## Latest recorded results

Latest results are recorded per phase in [CHANGELOG.md](CHANGELOG.md).
