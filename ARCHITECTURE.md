# Architecture

**Implemented through Phase 1:** the offline data pipeline and frontend toolchain. Everything else below is the target design from the [PRD](docs/PRD.md) and is marked as planned.

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
| Model training | `backend/app/ml/`, `scripts/` | Planned: Phase 2 |
| REST API, services, repositories | `backend/app/` | Planned: Phase 3 |
| Database models and migrations | `backend/app/models/`, `backend/migrations/` | Planned: Phase 3 |
| React application | `frontend/src/` | Toolchain only; pages in Phase 4 |
| CI | `.github/workflows/` | Planned: Phase 5 |
| Containers and deployment | Dockerfiles, compose file | Planned: Phases 3 and 6 |

## Design rules

1. **One feature implementation.** `engineer_features` is the only place features are computed, and it accepts only values available at prediction time.
2. **Allow-listed reads.** The pipeline reads only named raw columns, so leaky columns never enter its memory.
3. **Separated labels.** Partitions store labels in their own column, and `load_partition` returns them apart from features.
4. **Fixed direction of dependencies.** `schema` depends on nothing. `features` and `splitting` build on it, then `dataset_preparation`, `eda` and `leakage_audit`, then `scripts`. Lower layers never import higher ones.
5. **Library code takes paths as arguments.** Only `scripts/` uses repository defaults, which is what lets tests run on small fixtures.
6. **Saved outputs are the source of truth.** Charts render from saved summaries, and documentation and the planned UI report saved results.
7. **Three kinds of truth stay separate** (PRD 6.1): ground-truth labels, model predictions and investigation outcomes.

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
        |--- eda.py               uses features, schema, splitting, pipeline_io
        ^
scripts/*.py                    command-line wrappers
```

## Key decisions

Recorded in [docs/decisions/0001-phase-1-decisions.md](docs/decisions/0001-phase-1-decisions.md).
