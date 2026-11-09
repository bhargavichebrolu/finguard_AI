# Project Connections

How FinGuard AI fits together, from raw data to the screen. **Each section states whether it describes implemented code or a plan.** Current state: Phases 1 to 3 are implemented. The model is frozen and evaluated, and the API and database run locally in Docker. Phases 4 to 6 are planned. Results are recorded in [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md).

## 1. Project introduction
FinGuard AI analyses simulated mobile-money transactions, gives each an uncalibrated model score and a review decision, explains it and supports investigation through a dashboard. It uses the synthetic PaySim dataset and is for research and demonstration only. The point of the project is the connected system rather than any one model.

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
Model training and experiments              [implemented] app/ml/experiments.py, experiment_stages.py, scripts/train_models.py
    |
    v
Model evaluation                            [implemented] app/ml/evaluation.py
    |
    v
Model selection                             [implemented] app/ml/selection.py, scripts/evaluate_models.py
    |
    v
Model artefact persistence                  [implemented] app/ml/model_artifacts.py
    |
    v
Final test evaluation, once, after freeze   [implemented] app/ml/final_evaluation.py, scripts/evaluate_final_test.py
    |
    v
FastAPI model loading, after hash checks   [implemented] app/services/model_service.py
    |
    v
Prediction and batch endpoints              [implemented] app/api/routes/transactions.py, batches.py
    |
    v
React application                           [planned: Phase 4]
    |
    v
User sees prediction and explanation        [planned: Phase 4]
    |
    v
PostgreSQL stores prediction history        [implemented] app/models/records.py, migrations/
    |
    v
Dashboard and reports retrieve stored results [planned: Phase 4]
```

**Model training and live inference are separate processes.** Training runs offline on the full dataset and produces artefacts. The API only loads those artefacts. The one thing they share is `engineer_features`, which keeps feature calculations identical in both.

## 3. Complete directory structure
```
finguard-ai/
|-- README.md and the other root documents
|-- .env.example, .gitignore, .gitattributes, Makefile, docker-compose.yml
|-- docker/postgres/init/          first-start SQL: application role and test database
|-- docs/
|   |-- PRD.md                     specification
|   |-- file-explanations/         Phase 1 and 2 documents, mirroring the source tree
|   |-- decisions/                 architecture decision records
|   |-- diagrams/, research/       empty so far
|-- data/
|   |-- raw/                       PaySim CSV (Git-ignored)
|   |-- processed/                 Parquet partitions (Git-ignored)
|   |-- sample/                    empty until a demo sample is needed
|-- experiments/
|   |-- experiment-configs/        split_v1.json, experiments_v1.json
|   |-- results/                   validation, EDA and audit JSON
|   |-- results/phase2/            runs, selection, thresholds, SHAP and test results
|   |-- figures/eda/               four PNG charts
|   |-- figures/models/            experiment charts
|   |-- scores/                    per-run validation scores (Git-ignored)
|   |-- notebooks/                 empty; analysis lives in tested modules
|-- artifacts/
|   |-- metadata/                  preprocessing metadata, feature dictionary, model metadata and metrics
|   |-- models/fraud_detector_v1/  the selected model (binary Git-ignored)
|-- backend/
|   |-- pyproject.toml, uv.lock, Dockerfile, .dockerignore, alembic.ini
|   |-- app/main.py                application factory and start-up checks
|   |-- app/ml/                    data pipeline and ML code
|   |-- app/api/{routes,schemas}/  HTTP routes and request and response shapes
|   |-- app/core/                  settings, frozen pins, errors, logging, middleware, rate limits
|   |-- app/services/              business rules
|   |-- app/repositories/          multi-table queries
|   |-- app/models/                SQLAlchemy tables and enums
|   |-- app/database/              engine, sessions, base class
|   |-- app/security/              passwords, tokens, permissions, dependencies
|   |-- app/utils/                 CSV safety
|   |-- migrations/                Alembic environment and revision 0001
|   |-- tests/{unit,integration,api}/
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
Phase 1 and 2 files have documents in [docs/file-explanations/](docs/file-explanations/). Phase 3 files have a document beside them, named `<file>.explanation.md`.

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
| `backend/app/ml/regimes.py` | Label-independent definition of sparse and normal steps |
| `backend/app/ml/drift.py` | Prevalence, regime and feature drift analysis |
| `backend/app/ml/preprocessing.py` | The matrix every model family receives; used in training and serving |
| `backend/app/ml/imbalance.py` | SMOTE and ADASYN producing valid rows |
| `backend/app/ml/candidates.py` | Model families and the description of one experiment |
| `backend/app/ml/evaluation.py` | Metrics, threshold rules, step bootstrap |
| `backend/app/ml/experiments.py` | Fit, time and evaluate one candidate; test partition guard; run storage |
| `backend/app/ml/experiment_stages.py` | Baselines, matrix, tuning, sensitivity, stability |
| `backend/app/ml/selection.py` | The pre-registered selection rule, threshold analysis, freeze |
| `backend/app/ml/model_artifacts.py` | Save and independently load the model |
| `backend/app/ml/explainability.py` | SHAP explanations |
| `backend/app/ml/final_evaluation.py` | The only code that reads the test partition |
| `backend/app/ml/reporting.py` | Charts and tables from saved results |
| `scripts/download_dataset.py` | Places the CSV |
| `scripts/validate_dataset.py` | Runs validation |
| `scripts/prepare_dataset.py` | Builds partitions |
| `scripts/run_eda.py` | Runs EDA |
| `scripts/audit_leakage.py` | Runs the audit |
| `scripts/analyse_temporal_drift.py` | Runs the drift analysis, without test feature values |
| `scripts/train_models.py` | Runs the experiment stages |
| `scripts/evaluate_models.py` | Selects and freezes the model and threshold |
| `scripts/explain_model.py` | Produces SHAP results on validation |
| `scripts/diagnose_lightgbm.py` | Explains LightGBM's collapse in the matrix; its fits are not eligible for selection |
| `scripts/evaluate_final_test.py` | Runs the one test evaluation, after checking the freeze is committed |
| `scripts/export_metrics.py` | Generates charts, tables and the metrics bundle |
| `scripts/check_explanations.py` | Enforces the documentation rule |
| `backend/tests/conftest.py` | Synthetic fixture and shared helpers |
| `backend/tests/unit/test_schema.py` | Schema rules |
| `backend/tests/unit/test_features.py` | Feature behaviour |
| `backend/tests/unit/test_dataset_validation.py` | Validation by corruption |
| `backend/tests/unit/test_splitting.py` | Split logic |
| `backend/tests/unit/test_scripts.py` | Documentation checker and dataset placement |
| `backend/tests/integration/test_data_pipeline.py` | Stages together, tamper tests |
| `backend/tests/integration/test_real_data.py` | Real outputs versus published figures |
| `backend/tests/integration/test_phase2_pipeline.py` | The whole Phase 2 flow, with no test file on disk until the freeze |
| `backend/tests/unit/test_regimes.py`, `test_preprocessing.py`, `test_imbalance.py`, `test_candidates.py`, `test_evaluation.py`, `test_experiments.py`, `test_selection.py`, `test_drift.py`, `test_model_artifacts.py`, `test_explainability.py`, `test_reporting.py` | One Phase 2 module each |
| `frontend/index.html`, `frontend/src/main.tsx` | Page and React mount |
| `frontend/src/App.tsx`, `pages/registry.tsx` | Routes, guards and the PRD 7.4 page list, each page lazily loaded |
| `frontend/src/pages/*.tsx` | The ten pages and the sign-in page |
| `frontend/src/services/`, `hooks/`, `components/`, `layouts/`, `types/`, `utils/` | API client, state, shared components, layout, typed contracts, formatting |
| `frontend/tests/unit/*` | Component tests against a mock API |
| `frontend/playwright.config.ts`, `frontend/tests/e2e/*` | Browser tests against the real API and `finguard_e2e_test` at three viewports |
| `scripts/e2e_stack.py`, `scripts/e2e_database.py` | Start the browser-test API; create, seed and adjust its database (refuses non-`_test` names) |
| `scripts/verify_clean_clone.py`, `scripts/test_report.py` | Clean-clone reproducibility check and pytest report reading |
| `scripts/measure_performance.py`, `frontend/playwright.perf.config.ts`, `frontend/tests/perf/*` | Measured performance against the browser-test stack; results in `docs/performance/` |
| `frontend/src/styles/tokens.css` | PRD colour tokens |
| `frontend/vite.config.ts` | Build tool config |
| `Makefile` | Command shortcuts |
| `docker-compose.yml`, `docker/postgres/init/01_app_role.sql` | Local stack, SCRAM from first initialisation, application role |
| `backend/Dockerfile`, `backend/.dockerignore` | API image without training libraries |
| `backend/alembic.ini`, `backend/migrations/env.py`, `script.py.mako`, `versions/20261107_0001_initial_schema.py` | Migrations |
| `.env.example`, `.gitattributes`, `.gitignore`, `backend/pyproject.toml` | Configuration |
| `backend/app/main.py` | Application factory and start-up |
| `backend/app/core/config.py`, `frozen_model.py` | Settings, and the pinned model, hash and threshold |
| `backend/app/core/errors.py`, `logging.py`, `middleware.py`, `rate_limit.py` | Safe errors, JSON logs, request context, limits |
| `backend/app/database/base.py`, `session.py` | Base class and sessions |
| `backend/app/models/enums.py`, `records.py` | Vocabularies and tables |
| `backend/app/security/passwords.py`, `tokens.py`, `permissions.py`, `dependencies.py` | Authentication and authorisation |
| `backend/app/services/model_service.py`, `risk.py` | Verified model loading, scoring, explanations, risk bands |
| `backend/app/services/prediction_service.py`, `batch_service.py`, `export_service.py` | Prediction storage, CSV processing, exports |
| `backend/app/services/investigation_service.py`, `settings_service.py`, `auth_service.py`, `audit_service.py` | Workflow, settings, accounts, audit |
| `backend/app/services/metrics_service.py`, `report_service.py` | Saved Phase 2 results, summaries and reports |
| `backend/app/repositories/transactions.py`, `investigations.py`, `reports.py` | Queries |
| `backend/app/api/router.py`, `routes/*.py`, `schemas/*.py` | Routes and schemas |
| `backend/app/utils/csv_safety.py` | Formula-safe CSV and file names |
| `scripts/generate_env.py`, `scripts/create_admin.py` | Local secrets and the first administrator |
| `backend/tests/unit/test_config.py`, `test_model_service.py` | Settings and model verification |
| `backend/tests/integration/test_migrations.py` | Migrations and constraints on PostgreSQL |
| `backend/tests/api/conftest.py`, `test_auth.py`, `test_transactions.py`, `test_batches.py`, `test_investigations.py`, `test_models_and_reports.py` | The API end to end |

Docstring-only `__init__.py` files are exempt from the explanation rule, as they have no behaviour.

## 6. Machine learning pipeline
**Implemented:** data preparation, then experiments on Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM and CatBoost, each compared under the original distribution, class weighting, SMOTE and ADASYN. Selection and threshold rules are in [ADR 0002](docs/decisions/0002-phase-2-decisions.md), and results are in [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md).

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
The API starts at `engineer_features` with the same four inputs, through `prediction_service.inputs_frame`.

## 9. Training and evaluation flow (implemented)
```
experiments_v1.json, train.parquet, validation.parquet
  | analyse_temporal_drift.py  --> results/phase2/temporal_drift.json
  | train_models.py            --> results/phase2/{baselines,runs,rolling_folds}.json, scores/
  |     baselines, 24-cell matrix, tuning, sensitivity, seeds, rolling folds
  | evaluate_models.py         --> results/phase2/{selection,threshold_analysis}.json
  |                            --> artifacts/models/fraud_detector_v1/model.joblib
  |                            --> artifacts/metadata/model_v1.json (frozen)
  | explain_model.py           --> results/phase2/shap_summary.json
  | diagnose_lightgbm.py       --> results/phase2/lightgbm_diagnostic.json (outside selection)
  | git commit (the freeze)
  | evaluate_final_test.py     --> results/phase2/test_evaluation.json (once; reads test.parquet)
  | export_metrics.py          --> figures/models/, all_runs.csv, ML_EXPERIMENTS.md, model_v1_metrics.json
```
Partitions are read through `load_development_partition`, which refuses the test partition. Oversampling happens only inside `fit_candidate`, on the rows of the fold being fitted. Every result is reported overall and for sparse and normal steps.

## 10. Model saving and loading (implemented)
`save_model_artifact` writes one sklearn pipeline (preprocessing and model together) to `artifacts/models/<version>/model.joblib`, and metadata to `artifacts/metadata/model_v1.json`. The metadata records the feature schema version, preprocessing hash, threshold, score meaning, library versions and the file's SHA-256. `load_model_artifact` checks the schema, columns and hash before opening the file, and imports no experiment code. `LoadedModel.predict_scores` starts from the four prediction inputs and returns float64 scores, which the frozen threshold must be compared with. The API wraps this in `load_verified_model`, which first checks the metadata against the pins in `frozen_model.py`, the installed `scikit-learn` and `xgboost` versions, the preprocessing hash and the metrics file. Any failure stops start-up.

## 11. FastAPI architecture (implemented)
Routes handle HTTP only: a permission dependency, schema validation and one service call. Services hold rules and commit. Repositories hold multi-table queries, and `app/ml` provides inference. Configuration is in `app/core`, and authentication in `app/security`. See [ARCHITECTURE.md](ARCHITECTURE.md#backend-layers-phase-3).

Start-up (`lifespan` in `app/main.py`): verify and load the model, register it as the only active row in `model_versions`, mark interrupted batch jobs as failed, then accept requests. Nothing trains, and migrations run separately.

## 12. API request and response flow (implemented)
```
POST /api/v1/transactions/predict
  | RequestContextMiddleware   request ID, size limit, security headers, one log line
  | get_current_user           token signature and expiry, user active, token version current
  | rate_limited(PREDICT)      role allowed, per-user limit
  | TransactionInput           four inputs, merchant only with PAYMENT, extra fields refused
  | prediction_service         get_high_risk_boundary, score_inputs:
  |                              inputs_frame -> ServingModel.score -> assess_score -> explain
  |                            store Transaction, Prediction, Investigation + history, AuditLog
  |                            one commit
  v
PredictionView: model_score, score_is_calibrated false, risk level, FLAG_FOR_REVIEW,
                model_version, threshold_used, explanation with limitations
```
Endpoints are listed in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## 13. React architecture (Phase 4, implemented)
```
main.tsx -> App.tsx (AuthProvider, BrowserRouter)
  /login                      LoginPage
  everything else             RequireAuth -> ModelLimitsProvider -> AppLayout
                                -> RequirePermission(page.permission) -> Suspense -> lazy page
pages/registry.tsx            one list drives routes and navigation, in PRD 7.4 order:
                              Dashboard, Transaction Analysis, CSV Batch Analysis,
                              Transaction Explorer, Investigation Centre, Model Performance,
                              Explainable AI, Reports, Settings, System Information
types/report.ts               typed sections of GET /models/report (saved Phase 2 outputs only)
services/api.ts               one Axios client: cookies, CSRF header, ApiError, 401 signal
services/endpoints.ts         typed calls, using types/api.generated.ts from frontend/openapi.json
hooks/                        useAuth, useApiResource and usePolling, useModelLimits
components/                   feedback states, ScoreDisclosure, badges, DataTable, guards
styles/                       tokens, layout, components, pages (custom CSS, white theme)
```
Navigation shows only pages whose permission `/auth/me` reports. The API still enforces every rule.

## 14. Frontend-to-backend communication (Phase 4)
```
browser -> same origin /api/...    (Vite dev :5173 or preview :4173 locally; host rewrite in Phase 6)
        -> proxy -> FastAPI         (FINGUARD_API_PROXY_TARGET, default http://127.0.0.1:8010)
cookies: finguard_session (HttpOnly, Path=/api)  finguard_csrf (readable, sent back as X-CSRF-Token)
```
No token is kept in browser storage. `VITE_API_BASE_URL` stays empty unless the API must be reached on another origin, which would break SameSite=Strict cookies. Contract: `scripts/export_openapi.py` writes `frontend/openapi.json`, and `npm run gen:api` regenerates the types. Tests on both sides fail if either is stale.

### Browser tests (Phase 4)
```
scripts/e2e_stack.py up        compose profile "e2e": migrate-e2e -> api-e2e  127.0.0.1:8011
                               same image as api; APP_ENV=test; DATABASE_URL -> finguard_e2e_test;
                               CORS only http://127.0.0.1:4173; new E2E_SECRET_KEY each start
frontend/playwright.config.ts  global-setup.ts -> scripts/e2e_database.py seed (refuses non-*_test)
                                                -> frontend/.e2e/accounts.json (Git-ignored)
                                                -> sign-in proof against :8011
                               webServer: npm run build + vite preview :4173 -> proxy -> :8011
                               sessions.setup.ts -> .e2e/state-<role>.json
                               specs (tests/e2e/*.spec.ts) -> support.ts (apiCall adds X-CSRF-Token
                               and Origin; repoBytes refuses data/)
                               model-performance.spec.ts also reads artifacts/metadata/*.json and
                               experiments/results/phase2/* to compare with the page
```
Since Phase 5 M1 the browser tests have their own database, `finguard_e2e_test`, created by `e2e_stack.py up`; the backend suite keeps `finguard_test`, which it empties. The seed step still stops with an instruction if the browser-test API has not registered the model.

### Reproducibility (Phase 5)
```
scripts/verify_clean_clone.py   git clone --no-local -> temp folder; confirm .env, model binary, dataset absent
                                uv sync --frozen; pytest (JUnit -> scripts/test_report.py); repository checks;
                                npm ci, typecheck, test, build
backend/Dockerfile, compose     base images pinned by digest; uv pinned exactly
export_model_report.py          source hashes over content with line endings normalised
```

### Performance measurement (Phase 5)
```
scripts/measure_performance.py run      reseed finguard_e2e_test -> 40 synthetic analysts (admin API)
                                        -> predict latency (cookie path, direct to :8011) -> batches
                                        -> populate 100k / 500k via batch uploads -> query timings
                                        -> docker stats memory -> docs/performance/*.json
npm run perf:pages                      playwright.perf.config.ts (no reseed) -> page readiness JSON
measure_performance.py render           Markdown tables only from saved JSON
```
Dashboard summary: `report_service.build_summary` -> `repositories/reports.model_flag_breakdown` (one grouped pass). CSV exports: `utils/csv_safety.csv_lines` (64 KB pieces) fed by server-side-cursor queries.

## 15. Database architecture (implemented)
PostgreSQL 17 with the tables, constraints and indexes in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md). Two roles: a superuser for administration, and `finguard_app` without superuser rights for the API, migrations and tests. SCRAM applies to every connection, set by `POSTGRES_INITDB_ARGS` at first initialisation.

## 16. SQLAlchemy relationships (implemented)
Transaction one-to-one prediction, prediction to at most one investigation, investigation to notes and status history in time order. Users are linked as creator, assignee, note author and audit actor, and those links are cleared rather than deleted if a user is removed. Labels sit in `ground_truth_labels`, linked to transactions but read by no scoring code.

## 17. Database migration process (implemented)
`docker compose up` runs the `migrate` service, which runs `alembic upgrade head`, before the API starts. On the host, run `cd backend; uv run alembic upgrade head`. `test_migrations.py` checks upgrade, downgrade and that models and migrations agree.

## 18. Authentication flow (implemented)
```
scripts/create_admin.py   ->  first admin (Argon2id hash)
Web application (Phase 4):
POST /auth/session (JSON) ->  origin check, rate limit, verify, user_sessions row,
                              Set-Cookie finguard_session (HttpOnly, SameSite=Strict, /api)
                              Set-Cookie finguard_csrf (readable, SameSite=Strict, /)
each request              ->  cookie token -> live session row -> user active, token_version
                              POST/PATCH/DELETE also: allowed Origin + X-CSRF-Token
DELETE /auth/session      ->  revoke this row, clear cookies
API clients and Swagger:
POST /auth/login (form)   ->  bearer token {sub, ver, iat, exp}, no CSRF needed
Both                      ->  role permission check for the route
POST /users (admin)       ->  further accounts. There is no self-registration.
```
Roles: demo, analyst, investigator and admin, from PRD section 2. The table is in `app/security/permissions.py`.

## 19. CSV upload processing (implemented)
```
POST /batches/upload
  | extension, streaming size limit, NUL check -> temporary file under a random name
  | header: required columns, leaky columns refused, isFraud and isFlaggedFraud ignored
  | row count limit -> BatchJob PENDING -> 202
background: process_batch
  | chunks of 1,000 rows: TransactionInput per row, score, insert with ON CONFLICT DO NOTHING,
  |   predictions, investigations for flags, labels to ground_truth_labels, row errors, commit
  | final status, audit entry; the temporary file is always deleted
```
Results, export and the error report are separate routes. A restart marks unfinished jobs as failed.

## 20. Prediction storage (implemented)
Every prediction stores `model_version`, `threshold_used` and `high_risk_boundary_used`, so old results stay interpretable after a model or setting change. The database refuses a stored decision that contradicts the score and threshold.

## 21. Investigation workflow (implemented)
A flagged prediction outside demo mode opens an investigation with status `NEW`. Investigators and admins change status and assignee, and add notes. Each status change is a new history row, stamped after the row lock is held, so the order is right even under simultaneous changes. Statuses are workflow labels: they never change a score, a decision or a metric.

## 22. Explainability flow (implemented)
Phase 2: `explainability.py` produced global importance, saved in the metrics bundle. Phase 3: `ServingModel.explain` uses XGBoost's own TreeSHAP values (`pred_contribs`), which tests show match the `shap` library and add up to the score on the log-odds scale. They are stored for every single prediction and for flagged batch rows, and returned with Phase 2's limitations. SHAP does not establish causality. The interface that shows them is Phase 4.

## 23. Deployment architecture (planned: Phase 6)
Independently deployed frontend, backend container, managed PostgreSQL and separately stored artefacts. See [DEPLOYMENT.md](DEPLOYMENT.md).

## 24. Environment configuration (implemented)
The API reads `app/core/config.py` settings from the environment and `.env`. `scripts/generate_env.py` creates `.env` with random secrets. Phase 1 and 2 scripts still use `pipeline_io.py` defaults and command-line arguments. The frozen model's version, hash and threshold are deliberately not settings.

## 25. Docker architecture (implemented locally; deployment in Phase 6)
```
docker-compose.yml
  db       postgres:17-alpine, SCRAM from first start, named volume, port on 127.0.0.1 only
  migrate  finguard-api:local, alembic upgrade head, then exits
  api      finguard-api:local, non-root, ./artifacts mounted read-only, health check on /health
  migrate-e2e, api-e2e   profile "e2e" only: the same image against finguard_e2e_test on 127.0.0.1:8011
```

## 26. Local setup instructions
See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md).

## 27. Production deployment instructions (planned: Phase 6)
To be written and verified against a live deployment.

## 28. Troubleshooting
See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md#troubleshooting).

## 29. How to add another model (implemented)
1. Add the family to `MODEL_FAMILIES` and a branch to `build_estimator` in `candidates.py`.
2. Add it to `TREE_FAMILIES` or a new branch in `explainability.py`, or accept that it has no explanations.
3. In a **new** config version, add its baseline settings and tuning grid. Add small settings to `small_experiment_config` in `conftest.py`.
4. Add a colour and label in `reporting.py`.
5. Run `train_models.py`, then the later stages.

Use the same partitions through `load_development_partition`, and change no features unless the schema version is bumped. Note that the current test partition has been used once, so a model selected later needs a new untouched window, or its test result must be labelled as not independent.

## 30. How to update the model version (implemented)
1. Change `MODEL_VERSION` in `selection.py` and the metadata path, train offline, and run `evaluate_models.py`, which saves to a new version folder with its own metadata.
2. Evaluate it on data it has never seen. PaySim's test window has already been used.
3. Update the pins in `backend/app/core/frozen_model.py`, and the metadata paths in settings.
4. Restart the API. `register_active_model` makes the new version the only active row, and earlier predictions keep their recorded version and threshold. The one-prediction-per-transaction rule (ADR 0003, decision 8) means re-scoring old transactions needs a migration first.

## Rules connecting everything
| Rule | Enforced by |
|---|---|
| Balances never reach a model | `PIPELINE_RAW_COLUMNS`, `assert_processed_files_clean`, tests |
| Label never reaches features | `PartitionData`, `FORBIDDEN_FEATURE_COLUMNS`, tests |
| Future data never trains | `partition_masks`, `assert_processed_files_clean`, tests |
| Test partition stays out of feature decisions | EDA and audit scope, tests |
| Test partition stays out of selection | `load_development_partition`, source scan tests, `test_phase2_pipeline.py`, `evaluate_final_test.py` commit check |
| Oversampling touches training rows only | `fit_candidate` as the only caller, no sampler in saved pipelines, tests |
| Test set is used once | `assert_ready_for_test` |
| Reports match the results | `reporting.py` renders tables from saved files |
| Training and serving agree | One `engineer_features`, `test_stored_features_match_a_direct_serving_call` |
| Documentation stays synchronised | `scripts/check_explanations.py` |
| The served model is the frozen one | `frozen_model.py` pins, `load_verified_model`, `test_model_service.py` |
| Labels never reach scoring | `inputs_frame`, `TransactionInput` refusing extra fields, `test_batches.py`, `test_model_service.py` |
| Decisions match the threshold | `assess_score`, `ck_predictions_decision_matches_threshold`, tests |
| Flags, workflow and labels stay apart | Separate tables and report sections, `test_models_and_reports.py` |
| Every route needs a token | `require_permission`, `test_every_api_route_requires_authentication` |
| Phase 2 metrics are served unchanged | `read_metrics`, `test_metrics_endpoint_serves_saved_values_exactly` |
