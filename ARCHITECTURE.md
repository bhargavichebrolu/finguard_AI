# Architecture

**Implemented through Phase 3:** the offline data pipeline, experiments and model artefacts, the FastAPI service and PostgreSQL database, running locally in Docker, and the frontend toolchain. Everything else below is the target design from the [PRD](docs/PRD.md) and is marked as planned.

## Target system

```
Offline (developer machine or CI)         Online (deployed, independent services)

PaySim CSV                                React frontend (Netlify or Vercel)
   |                                          |
validation, EDA, leakage audit                | HTTPS REST
   |                                          v
Parquet partitions                        FastAPI backend (container)
   |                                          |        |
training and evaluation  ---- artefacts --->  |        +--- PostgreSQL (managed)
   |                                          |
saved experiment results ----- metrics ------>+--- temporary batch storage
```

Training and live inference are separate processes. The API loads an already-trained, validated model at startup and never trains or downloads PaySim.

## Components

| Component | Location | Status |
|---|---|---|
| Schema and feature code | `backend/app/ml/` | Implemented |
| Data pipeline commands | `scripts/` | Implemented |
| Model experiments, selection, final evaluation | `backend/app/ml/`, `scripts/` | Implemented |
| Model loading for serving | `backend/app/ml/model_artifacts.py`, `backend/app/services/model_service.py` | Implemented, with pins and hash checks |
| REST API | `backend/app/main.py`, `app/api/` | Implemented |
| Business logic | `backend/app/services/` | Implemented |
| Database queries | `backend/app/repositories/`, for multi-table queries | Implemented |
| Authentication and permissions | `backend/app/security/` | Implemented |
| Configuration, errors, logging, middleware | `backend/app/core/` | Implemented |
| Database models and migrations | `backend/app/models/`, `backend/migrations/` | Implemented |
| React application | `frontend/src/` | Toolchain only; pages in Phase 4 |
| CI | `.github/workflows/` | Planned: Phase 5 |
| Containers | `backend/Dockerfile`, `docker-compose.yml` | Implemented for local use |
| Deployment | | Planned: Phase 6 |

## Design rules

1. **One feature implementation.** `engineer_features` is the only place features are computed, and it accepts only values available at prediction time.
2. **Allow-listed reads.** The pipeline reads only named raw columns, so leaky columns never enter its memory.
3. **Separated labels.** Partitions store labels in their own column, and `load_partition` returns them apart from features.
4. **Fixed direction of dependencies.** `schema` depends on nothing. `features` and `splitting` build on it, then `dataset_preparation`, `eda` and `leakage_audit`, then `scripts`. Lower layers never import higher ones.
5. **Library code takes paths as arguments.** Only `scripts/` uses repository defaults, which is what lets tests run on small fixtures.
6. **Saved outputs are the source of truth.** Charts render from saved summaries, and documentation and the planned UI report saved results.
7. **Three kinds of truth stay separate** (PRD 6.1): ground-truth labels, model predictions and investigation outcomes.
8. **The serving path is light.** `model_artifacts`, `preprocessing`, `features` and `schema` import no training-only code, which a test checks in a new process.
9. **One choke point per rule.** Oversampling happens only in `fit_candidate`. The test partition is read only by `final_evaluation`. The served model is loaded only by `load_verified_model`.
10. **Routes stay thin** (PRD 8.1). Routes validate and call one service function. Services hold the rules and commit. Repositories hold multi-table queries.
11. **The frozen model is pinned in code.** Its version, hash and threshold are in `app/core/frozen_model.py`, not in settings.
12. **The database repeats key rules** as CHECK constraints, so no route can store a decision that contradicts its score and threshold.

## Dependency layout

```
backend/app/ml/schema.py        no internal imports
backend/app/ml/pipeline_io.py   no internal imports
        ^
        |--- features.py          uses schema
        |--- splitting.py         uses pipeline_io
        |--- dataset_validation.py uses schema, pipeline_io
        ^
        |--- dataset_preparation.py uses features, splitting, schema, pipeline_io
        ^
        |--- leakage_audit.py     uses dataset_preparation, features, schema, splitting, pipeline_io
        |--- eda.py               uses features, regimes, schema, splitting, pipeline_io
        |--- regimes.py           no internal imports
        |--- preprocessing.py     uses schema
        |--- model_artifacts.py   uses features, preprocessing, schema, pipeline_io  (serving path)
        ^
        |--- imbalance.py         uses features, preprocessing, schema
        |--- candidates.py        uses imbalance, preprocessing
        |--- evaluation.py        uses regimes, schema
        |--- drift.py             uses features, regimes, schema, splitting
        ^
        |--- experiments.py       uses candidates, dataset_preparation, evaluation, imbalance, preprocessing, pipeline_io
        |--- experiment_stages.py uses experiments and the modules above
        |--- selection.py         uses experiment_stages, experiments, model_artifacts, evaluation
        |--- explainability.py    no internal imports
        |--- final_evaluation.py  uses dataset_preparation, drift, evaluation, experiment_stages, model_artifacts
        |--- reporting.py         uses candidates, explainability
        ^
scripts/*.py                    command-line wrappers
```

## Backend layers (Phase 3)

```
app/main.py           application factory, start-up checks, middleware
    |
app/api/routes/       HTTP only: permission dependency, schema validation, one service call
app/api/schemas/      request and response shapes
    |
app/security/         tokens, passwords, permissions, request dependencies
app/services/         rules and transactions: prediction, batch, investigation, auth, settings,
    |                 reports, metrics, export, audit, model
app/repositories/     multi-table queries: transactions, investigations, reports
app/models/           SQLAlchemy tables and enums
app/database/         engine, sessions, base class
app/core/             settings, frozen pins, errors, logging, middleware, rate limits
app/utils/            CSV safety
app/ml/               Phase 1 and 2 code; the API uses features, preprocessing, schema,
                      model_artifacts and explainability only
```

Lower layers never import route modules. Services import schemas only to share input validation and response building.

## Key decisions

Recorded in [ADR 0001](docs/decisions/0001-phase-1-decisions.md), [ADR 0002](docs/decisions/0002-phase-2-decisions.md) and [ADR 0003](docs/decisions/0003-phase-3-decisions.md).
