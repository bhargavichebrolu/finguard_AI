# Project Connections

How FinGuard AI fits together, from raw data to the screen. **Each section states whether it describes implemented code or a plan.** Current state: Phase 1 is implemented, the Phase 2 experiment code is implemented, and Phases 3 to 6 are planned. Results are recorded in [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md).

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
|   |-- pyproject.toml, uv.lock
|   |-- app/ml/                    data pipeline code
|   |-- app/{api,core,services,models,repositories,database,security,utils}/  empty until Phase 3
|   |-- migrations/                empty until Phase 3
|   |-- tests/{unit,integration}/  unit and integration tests
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
| `frontend/src/App.tsx` | Placeholder root component |
| `frontend/src/styles/tokens.css` | PRD colour tokens |
| `frontend/vite.config.ts` | Build tool config |
| `Makefile` | Command shortcuts |

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
The Phase 3 API will start at `engineer_features` with the same four inputs.

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

## 10. Model saving and loading (implemented; API use planned for Phase 3)
`save_model_artifact` writes one sklearn pipeline (preprocessing and model together) to `artifacts/models/<version>/model.joblib`, and metadata to `artifacts/metadata/model_v1.json`. The metadata records the feature schema version, preprocessing hash, threshold, score meaning, library versions and the file's SHA-256. `load_model_artifact` checks the schema, columns and hash before opening the file, and imports no experiment code. `LoadedModel.predict_scores` starts from the four prediction inputs and returns float64 scores, which the frozen threshold must be compared with. The Phase 3 API will use this directly.

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

## 22. Explainability flow (Phase 2 implemented; Phases 3 and 4 planned)
Implemented: `explainability.py` produces global importance by feature and group, breakdowns by class and regime, and per-prediction positive and negative contributions, with a check that they add up to the score. Planned: the API serves `explain_rows` and `local_explanation`, and the interface shows them with the stated limits. SHAP does not establish causality.

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

## 29. How to add another model (implemented)
1. Add the family to `MODEL_FAMILIES` and a branch to `build_estimator` in `candidates.py`.
2. Add it to `TREE_FAMILIES` or a new branch in `explainability.py`, or accept that it has no explanations.
3. In a **new** config version, add its baseline settings and tuning grid. Add small settings to `small_experiment_config` in `conftest.py`.
4. Add a colour and label in `reporting.py`.
5. Run `train_models.py`, then the later stages.

Use the same partitions through `load_development_partition`, and change no features unless the schema version is bumped. Note that the current test partition has been used once, so a model selected later needs a new untouched window, or its test result must be labelled as not independent.

## 30. How to update the model version (saving implemented; activation planned for Phase 3)
Change `MODEL_VERSION` in `selection.py` and the metadata path, train offline, and run `evaluate_models.py`, which saves to a new version folder with its own metadata. Registration and activation without rebuilding the frontend arrive with the Phase 3 API.

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
