# Project Connections

How FinGuard AI fits together, from raw data to the screen. **Each section states whether it describes implemented code or a plan.** Current state: Phase 1 is implemented, and Phases 2 to 6 are planned.

## 1. Project introduction
FinGuard AI analyses simulated mobile-money transactions, predicts a fraud probability, explains it and supports investigation through a dashboard. It uses the synthetic PaySim dataset and is for research and demonstration only. The point of the project is the connected system rather than any one model.

## 2. Full project architecture
```
PaySim CSV                                  [implemented]
    |
    v
Dataset validation                          [implemented] scripts/validate_dataset.py
    |
    v
Data cleaning                               [implemented] typing and category mapping only; validation found no rows needing change
    |
    v
Feature engineering                         [implemented] app/ml/features.py
    |
    v
Chronological dataset splitting             [implemented] app/ml/splitting.py, scripts/prepare_dataset.py
    |
    v
Model training and experiments              [planned: Phase 2]
    |
    v
Model evaluation                            [planned: Phase 2]
    |
    v
Model selection                             [planned: Phase 2]
    |
    v
Model artefact persistence                  [planned: Phase 2]
    |
    v
FastAPI model loading                       [planned: Phase 3]
    |
    v
Prediction endpoint                         [planned: Phase 3]
    |
    v
React application                           [planned: Phase 4]
    |
    v
User sees prediction and explanation        [planned: Phase 4]
    |
    v
PostgreSQL stores prediction history        [planned: Phase 3]
    |
    v
Dashboard and reports retrieve stored results [planned: Phase 4]
```

**Model training and live inference are separate processes.** Training runs offline on the full dataset and produces artefacts. The API only loads those artefacts. The one thing they share is `engineer_features`, which keeps feature calculations identical in both.

## 3. Complete directory structure
```
finguard-ai/
|-- README.md and the other root documents
|-- .env.example, .gitignore, Makefile
|-- docs/
|   |-- PRD.md                     specification
|   |-- file-explanations/         one document per source file, mirroring the source tree
|   |-- decisions/                 architecture decision records
|   |-- diagrams/, research/       empty so far
|-- data/
|   |-- raw/                       PaySim CSV (Git-ignored)
|   |-- processed/                 Parquet partitions (Git-ignored)
|   |-- sample/                    empty until a demo sample is needed
|-- experiments/
|   |-- experiment-configs/        split_v1.json
|   |-- results/                   validation, EDA and audit JSON
|   |-- figures/eda/               four PNG charts
|   |-- notebooks/                 empty; analysis lives in tested modules
|-- artifacts/
|   |-- metadata/                  preprocessing metadata, feature dictionary
|   |-- models/                    empty until Phase 2 (binaries Git-ignored)
|-- backend/
|   |-- pyproject.toml, uv.lock
|   |-- app/ml/                    data pipeline code
|   |-- app/{api,core,services,models,repositories,database,security,utils}/  empty until Phase 3
|   |-- migrations/                empty until Phase 3
|   |-- tests/{unit,integration}/  89 tests
|   |-- tests/api/                 empty until Phase 3
|-- frontend/
|   |-- package.json, vite.config.ts, tsconfig.json, index.html
|   |-- src/                       main.tsx, App.tsx, styles/tokens.css
|   |-- src/{components,pages,layouts,services,hooks,types,utils,assets}/ empty until Phase 4
|-- scripts/                       command-line entry points
|-- .github/workflows/             empty until Phase 5
```

## 4. Purpose of every major folder
| Folder | Purpose |
|---|---|
| `data/` | Input data and derived partitions; regenerated, never committed |
| `experiments/` | Configs and recorded evidence; committed so results can be reviewed without the dataset |
| `artifacts/` | What later stages consume: metadata now, models from Phase 2 |
| `backend/app/ml/` | Shared data and ML logic |
| `backend/tests/` | Automated tests |
| `scripts/` | Thin command-line wrappers around the library |
| `frontend/` | React application |
| `docs/` | Specification, decisions and file explanations |

## 5. Purpose of every source file
Each has a full document in [docs/file-explanations/](docs/file-explanations/).

| File | Responsibility |
|---|---|
| `backend/app/ml/schema.py` | Columns, leakage rules, feature dictionary and version |
| `backend/app/ml/pipeline_io.py` | Default paths, stable JSON, file hashing |
| `backend/app/ml/features.py` | The only feature computation |
| `backend/app/ml/dataset_validation.py` | Streaming, read-only validation |
| `backend/app/ml/splitting.py` | Chronological boundaries and masks |
| `backend/app/ml/dataset_preparation.py` | Parquet partitions and metadata; `load_partition` |
| `backend/app/ml/leakage_audit.py` | Schema and file checks; training-only signal measures |
| `backend/app/ml/eda.py` | Statistics and charts |
| `scripts/download_dataset.py` | Places the CSV |
| `scripts/validate_dataset.py` | Runs validation |
| `scripts/prepare_dataset.py` | Builds partitions |
| `scripts/run_eda.py` | Runs EDA |
| `scripts/audit_leakage.py` | Runs the audit |
| `scripts/check_explanations.py` | Enforces the documentation rule |
| `backend/tests/conftest.py` | Synthetic fixture and shared helpers |
| `backend/tests/unit/test_schema.py` | Schema rules |
| `backend/tests/unit/test_features.py` | Feature behaviour |
| `backend/tests/unit/test_dataset_validation.py` | Validation by corruption |
| `backend/tests/unit/test_splitting.py` | Split logic |
| `backend/tests/unit/test_scripts.py` | Documentation checker and dataset placement |
| `backend/tests/integration/test_data_pipeline.py` | Stages together, tamper tests |
| `backend/tests/integration/test_real_data.py` | Real outputs versus published figures |
| `frontend/index.html`, `frontend/src/main.tsx` | Page and React mount |
| `frontend/src/App.tsx` | Placeholder root component |
| `frontend/src/styles/tokens.css` | PRD colour tokens |
| `frontend/vite.config.ts` | Build tool config |
| `Makefile` | Command shortcuts |

Docstring-only `__init__.py` files are exempt from the explanation rule, as they have no behaviour.

## 6. Machine learning pipeline
**Implemented:** data preparation up to clean partitions. **Planned (Phase 2):** Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM and CatBoost, each compared under the original distribution, class weighting, SMOTE and ADASYN. Design constraints are in [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md).

## 7. Dataset flow (implemented)
```
data/raw/*.csv
  | validate_dataset.py    --> experiments/results/dataset_validation.json
  | prepare_dataset.py     --> data/processed/{train,validation,test}.parquet
  |                        --> artifacts/metadata/preprocessing_v1.json
  |                        --> artifacts/metadata/feature_dictionary_v1.json
  | run_eda.py             --> experiments/results/eda_summary.json, experiments/figures/eda/
  | audit_leakage.py       --> experiments/results/leakage_audit.json
```
All stages read in 500,000-row chunks, except that the audit holds training rows in memory to compute rank statistics. Order matters: EDA and the audit read boundaries from the preparation metadata.

## 8. Feature engineering flow (implemented)
```
Raw row (allow-listed columns only: step, type, amount, nameDest, isFraud, isFlaggedFraud)
  | raw_to_prediction_inputs: amount, transaction_type, step, destination_category
  | engineer_features: amount, amount_log1p, transaction_type, destination_category,
  |                    hour_of_day, hour_sin, hour_cos
  v
Features saved beside separate is_fraud, is_flagged_fraud, step and source_row columns
```
The Phase 3 API will start at `engineer_features` with the same four inputs.

## 9. Training and evaluation flow (planned: Phase 2)
Load with `load_partition`. Fit on train, with any oversampling inside the training pipeline only. Compare models and pick a threshold on validation. Evaluate the selected model on test once. Save everything under versioned names. Test results are reported overall and by low-volume regime.

## 10. Model saving and loading (planned: Phases 2 and 3)
Save the model, preprocessing pipeline, feature schema version, threshold, metrics and version together. The API verifies the schema version against `FEATURE_SCHEMA_VERSION` at startup and refuses a mismatch.

## 11. FastAPI architecture (planned: Phase 3)
Routes handle HTTP only, calling services for business logic, repositories for database access, and `app/ml` for inference, with configuration in `app/core` and authentication in `app/security`.

## 12. API request and response flow (planned: Phase 3)
Request, Pydantic validation, service, `engineer_features`, model, risk score and level, explanation, database save, response. Endpoints are listed in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## 13. React architecture (planned: Phase 4; toolchain implemented)
Implemented: Vite, TypeScript strict mode and colour tokens. Planned: ten pages, a shared layout, an API service layer and hooks, using custom CSS with the white theme.

## 14. Frontend-to-backend communication (planned: Phase 4)
Axios calls the REST API over HTTPS, using `VITE_API_BASE_URL`. No localhost URL is hardcoded for production.

## 15. Database architecture (planned: Phase 3)
PostgreSQL with the tables in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md), which also lists gaps the PRD's table list leaves open.

## 16. SQLAlchemy relationships (planned: Phase 3)
Transaction to predictions, prediction to investigations, investigation to notes, with users linked as assignee and note author.

## 17. Database migration process (planned: Phase 3)
Alembic, run as a controlled step at deployment rather than on application start.

## 18. Authentication flow (planned: Phase 3)
Hashed passwords, authentication and role-based permissions for analyst, investigator and administrator. Design is settled in Phase 3.

## 19. CSV upload processing (planned: Phase 3)
Validate extension, size, headers and types; process in batches; keep any `isFraud` column apart from prediction input; offer a downloadable error report and exported results. Must respect hosting limits.

## 20. Prediction storage (planned: Phase 3)
Every prediction stores its model version and threshold, so old results stay interpretable after a model change.

## 21. Investigation workflow (planned: Phase 3)
Statuses New, Under Review, Escalated, Closed and False Alarm, with notes and change history. These are workflow labels, not findings.

## 22. Explainability flow (planned: Phases 2 to 4)
SHAP global importance from Phase 2; per-prediction positive and negative contributions from the API; shown with stated limits. SHAP does not establish causality.

## 23. Deployment architecture (planned: Phase 6)
Independently deployed frontend, backend container, managed PostgreSQL and separately stored artefacts. See [DEPLOYMENT.md](DEPLOYMENT.md).

## 24. Environment configuration
Phase 1 code reads no environment variables: scripts use `pipeline_io.py` defaults and command-line arguments. `.env.example` lists what later phases will use.

## 25. Docker architecture (planned: Phases 3 and 6)
A backend Dockerfile, Compose with a PostgreSQL development service and persistent volume, and health checks. Docker is not installed on the development machine yet.

## 26. Local setup instructions
See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md).

## 27. Production deployment instructions (planned: Phase 6)
To be written and verified against a live deployment.

## 28. Troubleshooting
See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md#troubleshooting).

## 29. How to add another model (planned: Phase 2)
This will be written when the experiment framework exists. Any new model must use `load_partition` and the same partitions, with no feature changes unless the schema version is bumped.

## 30. How to update the model version (planned: Phases 2 and 3)
This will be written with the artefact format. In outline: train offline, evaluate, save to a new version folder, register it, and activate it without rebuilding the frontend.

## Rules connecting everything
| Rule | Enforced by |
|---|---|
| Balances never reach a model | `PIPELINE_RAW_COLUMNS`, `assert_processed_files_clean`, tests |
| Label never reaches features | `PartitionData`, `FORBIDDEN_FEATURE_COLUMNS`, tests |
| Future data never trains | `partition_masks`, `assert_processed_files_clean`, tests |
| Test partition stays out of feature decisions | EDA and audit scope, tests |
| Training and serving agree | One `engineer_features`, `test_stored_features_match_a_direct_serving_call` |
| Documentation stays synchronised | `scripts/check_explanations.py` |
