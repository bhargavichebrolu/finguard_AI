# FinGuard AI
## Product Requirements Document (PRD)

**Project:** FinGuard AI – Intelligent Financial Transaction Fraud Detection and Risk Monitoring Platform

**Version:** 1.0

**Project Type:** Full-Stack Machine Learning Application

**Primary Domain:** Financial Technology / Artificial Intelligence / Machine Learning

**Project Status:** Development Planned

**Target:** Portfolio-quality, production-minded, deployable software application

---

# 1. Project Overview

## 1.1 Introduction

FinGuard AI is an intelligent financial transaction monitoring and fraud detection platform that uses machine learning to identify potentially fraudulent financial transactions.

The platform will analyse transaction data, predict fraud probabilities, assign risk scores, explain prediction outcomes and provide an interactive dashboard for monitoring financial activity.

The application will combine:

- Supervised machine learning.
- Imbalanced classification techniques.
- Ensemble learning.
- Explainable AI.
- Data engineering.
- REST API development.
- Full-stack web development.
- Relational database management.
- Cloud deployment and production configuration.

The system will use the publicly available PaySim synthetic mobile-money transaction dataset.

The primary objective is to create a working end-to-end financial fraud detection application rather than a standalone machine learning experiment.

## 1.2 Problem Statement

Financial transaction platforms process large numbers of transactions, making manual identification of fraudulent activity impractical.

Fraudulent transactions represent a very small proportion of overall transactions. Consequently, conventional classification models may achieve high accuracy while failing to identify fraudulent activity.

FinGuard AI addresses this challenge through:

1. Comparative evaluation of multiple machine learning algorithms.
2. Appropriate handling of extreme class imbalance.
3. Fraud probability estimation.
4. Configurable risk thresholds.
5. Explainable prediction outputs.
6. Transaction-level investigation.
7. Interactive monitoring and reporting.

The system is a research and demonstration platform. Its predictions must not be represented as verified financial crime findings or used to automatically block real customer transactions.

## 1.3 Project Objectives

The project must:

1. Build a reproducible fraud detection training pipeline.
2. Evaluate multiple classification algorithms.
3. Compare class imbalance handling strategies.
4. prevent data leakage.
5. Select a model based on measured test performance.
6. Build a FastAPI backend.
7. Build a React frontend.
8. Integrate PostgreSQL.
9. Provide real-time-style individual transaction analysis.
10. Support CSV batch analysis.
11. Display model performance and evaluation results.
12. Provide explainable AI predictions.
13. Store prediction history.
14. Provide Docker-based deployment.
15. Deploy the application using independently configurable frontend, backend and database services.
16. Maintain detailed documentation for every authored source file.

---

# 2. Target Users

## 2.1 Financial Analyst

Can:
- Upload transaction datasets.
- View fraud detection summaries.
- Investigate suspicious transactions.
- Export reports.
- Filter transactions by risk.

## 2.2 Fraud Investigation Analyst

Can:
- Inspect individual flagged transactions.
- View fraud probability.
- Examine contributing features.
- Record investigation notes.
- Update investigation status.

## 2.3 System Administrator

Can:
- View system statistics.
- Monitor application activity.
- Review model versions.
- Inspect system health.
- Manage permitted users.

## 2.4 Portfolio Demonstration User

Can:
- Explore the dashboard.
- Test individual transactions.
- Upload a sample CSV.
- Review model performance.
- Explore explainability results.

---

# 3. Technology Stack

The following stack is mandatory unless a documented technical limitation requires a change.

## 3.1 Machine Learning

| Technology | Purpose |
|---|---|
| Python | Main ML language |
| Pandas | Data manipulation |
| NumPy | Numerical processing |
| Scikit-learn | Preprocessing and evaluation |
| XGBoost | Gradient boosting |
| LightGBM | Gradient boosting |
| CatBoost | Gradient boosting |
| imbalanced-learn | SMOTE and ADASYN |
| SHAP | Model explainability |
| Matplotlib | Evaluation visualisations |
| Joblib | Model persistence |

## 3.2 Backend

| Technology | Purpose |
|---|---|
| Python | Backend language |
| FastAPI | REST API |
| Pydantic | Request validation |
| SQLAlchemy | ORM |
| Alembic | Database migrations |
| PostgreSQL | Persistent database |
| Uvicorn | ASGI server |
| Pytest | Backend testing |
| HTTPX | API testing |

## 3.3 Frontend

| Technology | Purpose |
|---|---|
| React | Frontend framework |
| TypeScript | Type safety |
| Vite | Build tooling |
| CSS3 | Styling |
| Recharts | Data visualisation |
| React Router | Navigation |
| Axios | API communication |
| Lucide React | Icons |

Use custom CSS for the application design. Do not introduce unnecessary UI frameworks.

## 3.4 Deployment

| Technology | Purpose |
|---|---|
| Docker | Containerisation |
| Docker Compose | Local multi-service development |
| Netlify or Vercel | Frontend hosting |
| Render, Railway or AWS | Backend hosting |
| Managed PostgreSQL | Production database |
| GitHub | Version control and CI/CD |
| GitHub Actions | Automated checks |

The architecture must remain portable between hosting providers.

---

# 4. Dataset Requirements

## 4.1 Primary Dataset

Dataset: PaySim – Synthetic Financial Datasets for Fraud Detection.

Source:

https://www.kaggle.com/datasets/ealaxi/paysim1

Expected original dataset characteristics:

- Approximately 6.36 million transactions.
- 8,213 fraudulent transactions.
- Five transaction categories.
- Eleven original columns.
- Approximately 30 days of simulated transaction activity.

The exact downloaded dataset must be inspected and verified before processing.

## 4.2 Dataset Columns

| Column | Description |
|---|---|
| step | Simulation time step |
| type | Transaction category |
| amount | Transaction amount |
| nameOrig | Originating account identifier |
| oldbalanceOrg | Original sender balance |
| newbalanceOrig | New sender balance |
| nameDest | Destination account identifier |
| oldbalanceDest | Original recipient balance |
| newbalanceDest | New recipient balance |
| isFraud | Fraud target |
| isFlaggedFraud | Existing rule-based flag |

## 4.3 Critical Data Leakage Requirements

The following columns must be excluded from the primary predictive feature set:

- oldbalanceOrg
- newbalanceOrig
- oldbalanceDest
- newbalanceDest

These values are affected by the simulation's fraud cancellation behaviour.

The target column `isFraud` must never be included in model inputs.

The existing `isFlaggedFraud` column must not be treated as a predictive feature in the primary model. It may be evaluated separately as an existing rule-based baseline.

Account identifiers must not be used as arbitrary numeric features.

## 4.4 Feature Engineering

Create meaningful transaction-time features, including:

- Transaction amount.
- Transaction type.
- Hour derived from step.
- Destination account category.
- Other defensible features derived exclusively from information available at assessment time.

Every engineered feature must have a documented rationale and availability-time classification.

Maintain a feature dictionary explaining:
- Feature name.
- Original source column.
- Transformation.
- Data type.
- Business meaning.
- Whether it is available before transaction completion.

## 4.5 Dataset Processing

The system must:

1. Validate the downloaded dataset.
2. Check column names and data types.
3. Check missing values.
4. Check duplicate records.
5. Check invalid amounts.
6. Check target distribution.
7. Generate exploratory data analysis.
8. Save preprocessing metadata.
9. Process large datasets in memory-conscious batches.
10. Produce reproducible train, validation and test partitions.

Do not silently discard records or modify labels.

---

# 5. Machine Learning Architecture

## 5.1 Models

Implement and compare:

1. Logistic Regression as a baseline.
2. Decision Tree as a simple nonlinear baseline.
3. Random Forest as an ensemble baseline.
4. XGBoost.
5. LightGBM.
6. CatBoost.

The model list can be adjusted if computational constraints are documented.

## 5.2 Imbalance Handling Experiments

Evaluate:

1. Original imbalanced training distribution.
2. Class weighting.
3. SMOTE.
4. ADASYN.

Oversampling must happen only inside the training pipeline.

Never apply oversampling before splitting the dataset.

Validation and test datasets must retain their natural class distribution.

SMOTE and ADASYN must only be used where the chosen feature representation supports meaningful synthetic samples.

## 5.3 Experimental Design

Use:

- Chronological training, validation and test partitions.
- An untouched final test set.
- Reproducible random seeds.
- Identical evaluation conditions for comparable models.
- Versioned preprocessing configurations.
- Training-time measurements.
- Inference-time measurements.

Because PaySim contains time steps, do not rely exclusively on random splitting. Earlier transactions should be used for training and later transactions for validation and testing.

## 5.4 Model Evaluation

Calculate:

- Accuracy.
- Precision.
- Recall.
- F1-score.
- ROC-AUC.
- PR-AUC / Average Precision.
- Balanced Accuracy.
- Confusion Matrix.
- False Positive Rate.
- False Negative Rate.
- Training Time.
- Inference Time.

PR-AUC, Precision, Recall and F1-score are particularly important because of the severe class imbalance.

Accuracy must never be presented as the only measure of model quality.

## 5.5 Threshold Optimisation

The system must allow fraud classification thresholds to be evaluated.

For example:

- 0.30
- 0.40
- 0.50
- 0.60
- 0.70

These are experimental threshold candidates, not predetermined optimal values.

Select a threshold using validation data and a documented operational objective.

The final test set must not be repeatedly used to tune thresholds.

## 5.6 Model Selection

Do not automatically select the model with the highest accuracy.

The selected model must be justified using:

- Precision.
- Recall.
- F1-score.
- PR-AUC.
- False-positive burden.
- Computational cost.
- Stability.
- Threshold behaviour.

Record the selected model, feature schema, preprocessing version, threshold and evaluation metrics.

## 5.7 Explainable AI

Implement SHAP explanations where supported.

The application must display:

- Global feature importance.
- Important contributing features for an individual prediction.
- Positive and negative feature contributions.
- Explanation limitations.

Do not claim that SHAP establishes causality.

## 5.8 Model Persistence

Save:

- Trained model.
- Preprocessing pipeline.
- Feature schema.
- Model metadata.
- Selected threshold.
- Evaluation results.
- Model version.

Store artefacts using versioned filenames or model version directories.

The backend must load a validated trained model rather than retraining the entire model whenever the application starts.

---

# 6. Functional Requirements

## 6.1 Dashboard

The landing dashboard must display:

- Total analysed transactions.
- Fraudulent predictions.
- Legitimate predictions.
- High-risk transactions.
- Fraud rate in analysed data.
- Total transaction value.
- Fraud value among known labelled records, where labels are available.
- Recent transaction activity.
- Risk distribution.
- Transaction type distribution.
- Fraud trends over simulation time.
- Model performance summary.

Important:

Distinguish between:
- Actual ground-truth fraud labels in the experimental dataset.
- Model-generated fraud predictions.
- User-investigation outcomes.

Never mix these three categories.

## 6.2 Transaction Analysis

Users must be able to enter:

- Transaction amount.
- Transaction type.
- Simulation time step.
- Destination account category.

The system must:

1. Validate the input.
2. Apply the exact saved preprocessing pipeline.
3. Generate a prediction.
4. Return a probability.
5. Generate a risk score.
6. Display the classification.
7. Explain the prediction where supported.
8. Save the prediction record.

The application must not ask users for unavailable post-transaction balance fields.

## 6.3 Risk Classification

Display:

- Low Risk.
- Medium Risk.
- High Risk.

Risk boundaries must be configurable and documented.

The score must be derived from the model probability and must not be presented as a calibrated financial risk percentage unless calibration has been measured and validated.

## 6.4 CSV Upload

Users must be able to upload a CSV file containing supported transaction columns.

Requirements:

- Validate file extension.
- Validate file size.
- Validate headers.
- Validate data types.
- Detect missing values.
- Reject unsupported formats.
- Provide a downloadable error report.
- Process records in batches.
- Display progress.
- Generate prediction results.
- Allow results to be exported.

The application must not require the target `isFraud` column for prediction.

If the target is present in an experimental dataset, it may be retained separately for post-prediction evaluation. It must never enter the prediction pipeline.

## 6.5 Transaction Explorer

Provide a searchable transaction table.

Filters:

- Transaction ID.
- Risk level.
- Prediction status.
- Transaction type.
- Amount range.
- Simulation time.
- Investigation status.

Support pagination and sorting.

## 6.6 Transaction Details

Each transaction must have a detail view containing:

- Transaction identifier.
- Transaction attributes.
- Predicted fraud probability.
- Risk score.
- Risk classification.
- Model version.
- Prediction timestamp.
- Explainability information.
- Investigation status.
- Investigation notes.

## 6.7 Investigation Management

Support statuses:

- New.
- Under Review.
- Escalated.
- Closed.
- False Alarm.

Users must be able to update statuses and add notes.

Maintain a history of status changes.

These are investigation workflow labels, not verified criminal findings.

## 6.8 Model Performance Page

Provide:

- Model comparison table.
- Metric comparison charts.
- Precision-Recall curve.
- ROC curve.
- Confusion matrices.
- Threshold comparison.
- Training-time comparison.
- Inference-time comparison.
- Feature importance.
- Experiment history.

All displayed evaluation metrics must originate from saved experiment outputs.

## 6.9 Reports

Allow users to export:

- Transaction prediction CSV.
- Fraud summary CSV.
- Investigation summary.
- Model evaluation report.

## 6.10 Application Settings

Provide:

- Risk threshold settings.
- API connection status.
- Current model version.
- Dataset information.
- Application version.
- System health.

---

# 7. User Interface Requirements

## 7.1 Design Direction

Use a professional, modern, white/light fintech dashboard.

The entire application must use a consistent white theme.

Do not use a dark dashboard theme.

## 7.2 Colour Palette

| Element | Colour |
|---|---|
| Main background | #F8FAFC |
| Main card | #FFFFFF |
| Primary text | #172033 |
| Secondary text | #64748B |
| Primary blue | #2563EB |
| Secondary blue | #DBEAFE |
| Success | #16A34A |
| Warning | #D97706 |
| Danger | #DC2626 |
| Borders | #E2E8F0 |

Use colours consistently and ensure accessibility.

## 7.3 Layout

Use:

- Fixed or collapsible left navigation.
- Top navigation bar.
- Main content area.
- Consistent spacing.
- Rounded cards.
- Subtle shadows.
- Clean typography.
- Responsive layouts.

## 7.4 Navigation

Create the following pages:

1. Dashboard.
2. Transaction Analysis.
3. CSV Batch Analysis.
4. Transaction Explorer.
5. Investigation Centre.
6. Model Performance.
7. Explainable AI.
8. Reports.
9. Settings.
10. System Information.

## 7.5 UX Requirements

- Display loading states.
- Display empty states.
- Display API errors clearly.
- Display upload progress.
- Confirm destructive actions.
- Avoid unnecessary animations.
- Ensure mobile and desktop responsiveness.
- Do not use hardcoded fake statistics in production mode.

## 7.6 Demo Mode

Provide a clearly labelled demo mode.

Demo mode may use a small, curated sample dataset.

All demo records must be identified as synthetic sample records.

The application must distinguish demo statistics from actual model inference and experimental evaluation.

---

# 8. Backend Architecture

## 8.1 Architecture

Use a modular FastAPI backend.

Separate:

- API routing.
- Business logic.
- ML inference.
- Data validation.
- Database operations.
- Authentication.
- Configuration.
- Logging.

Routes must not contain all the business logic.

## 8.2 API Endpoints

### Health

GET /health

GET /api/v1/system/status

### Transactions

POST /api/v1/transactions/predict

GET /api/v1/transactions

GET /api/v1/transactions/{transaction_id}

### Batch Analysis

POST /api/v1/batches/upload

GET /api/v1/batches/{batch_id}

GET /api/v1/batches/{batch_id}/results

GET /api/v1/batches/{batch_id}/export

### Investigation

GET /api/v1/investigations

PATCH /api/v1/investigations/{investigation_id}

POST /api/v1/investigations/{investigation_id}/notes

### Model

GET /api/v1/models

GET /api/v1/models/active

GET /api/v1/models/metrics

GET /api/v1/models/feature-importance

### Reports

GET /api/v1/reports/summary

GET /api/v1/reports/export

### Configuration

GET /api/v1/settings

PATCH /api/v1/settings

All endpoints must have request and response schemas.

Provide Swagger/OpenAPI documentation through FastAPI.

---

# 9. Database Design

Use PostgreSQL.

The database must store application information and prediction history.

## 9.1 Tables

### users

- id
- email
- password_hash
- role
- is_active
- created_at

### transactions

- id
- external_transaction_id
- transaction_type
- amount
- simulation_step
- destination_category
- created_at

### predictions

- id
- transaction_id
- model_version
- fraud_probability
- risk_score
- risk_level
- prediction
- threshold_used
- created_at

### investigations

- id
- prediction_id
- status
- assigned_user_id
- created_at
- updated_at

### investigation_notes

- id
- investigation_id
- user_id
- note
- created_at

### model_versions

- id
- version
- algorithm
- model_path_or_artifact_reference
- feature_schema_version
- metrics_json
- is_active
- created_at

### batch_jobs

- id
- filename
- status
- total_records
- processed_records
- failed_records
- created_at
- completed_at

### audit_logs

- id
- user_id
- action
- entity_type
- entity_id
- created_at

## 9.2 Database Requirements

- Use SQLAlchemy models.
- Use Alembic migrations.
- Add appropriate indexes.
- Enforce foreign keys.
- Use transactions for related updates.
- Validate inputs.
- Avoid storing unnecessary personal information.
- Never store plaintext passwords.
- Keep database credentials outside source code.

Large batch uploads should not be stored as unbounded raw database blobs.

Use controlled temporary storage and store only the necessary records and results.

---

# 10. Security Requirements

Implement:

- Environment-based configuration.
- Secure password hashing.
- Authentication.
- Role-based permissions.
- Input validation.
- File upload restrictions.
- CORS restrictions.
- Rate limiting where supported.
- Safe error responses.
- Secret management.
- Database access controls.
- Audit logging.

Use separate development and production configuration.

Never commit:
- .env
- API secrets.
- Database passwords.
- Private keys.
- Real user data.
- Trained private data exports.

Create a .env.example file containing placeholders only.

---

# 11. Deployment Requirements

Deployment is a core project requirement, not an optional future enhancement.

## 11.1 Deployment Architecture

The system must support this deployment architecture:

React frontend
        |
        | HTTPS REST API
        |
FastAPI backend
        |
        +---- ML model artefacts
        |
        +---- PostgreSQL database
        |
        +---- Temporary batch file storage

The frontend and backend must be independently deployable.

## 11.2 Frontend Deployment

Support deployment to:

- Netlify.
- Vercel.

Requirements:

- Production build must succeed.
- API base URL must come from environment configuration.
- No localhost API URL may be hardcoded in production.
- Frontend routing must work after page refresh.
- HTTPS must be used.

## 11.3 Backend Deployment

Support container-based deployment.

Suitable platforms include:

- Render.
- Railway.
- AWS.

Requirements:

- Dockerfile.
- Production startup command.
- Health endpoint.
- Environment-based settings.
- Database connection configuration.
- Model artefact loading.
- Structured logs.
- Correct CORS configuration.

## 11.4 Database Deployment

Use managed PostgreSQL for production.

The database must not depend on a local laptop.

Run database migrations during controlled deployment.

## 11.5 Model Deployment

Train models outside the production web request lifecycle.

Store the selected model artefacts separately from source code.

The backend must load the selected model during application startup.

The production container must not download or train the entire PaySim dataset on every restart.

Document the model artefact storage strategy and how a new model version is released.

## 11.6 Docker Requirements

Provide:

- Backend Dockerfile.
- Frontend Dockerfile if required for self-hosting.
- Docker Compose configuration.
- PostgreSQL development service.
- Health checks.
- Environment variables.
- Persistent development database volume.

A developer must be able to start the local application using documented commands.

## 11.7 Deployment Constraints

Do not assume that free hosting provides:

- Persistent local storage.
- Unlimited memory.
- Always-on services.
- Unlimited execution time.
- Background processing.
- Unlimited database capacity.

Batch processing must account for hosting resource limits.

The deployed demonstration must work with a manageable sample even if the complete dataset cannot be processed on the hosting platform.

---

# 12. Documentation Requirements – Mandatory

Documentation is a core engineering requirement.

This is one of the most important requirements of the project.

## 12.1 Individual File Explanation

Every manually authored source-code file must have a corresponding explanation Markdown file.

Use this naming convention:

source_file.py
source_file.explanation.md

Examples:

details.py
details.py.explanation.md

prediction_service.py
prediction_service.py.explanation.md

database.py
database.py.explanation.md

For frontend:

Dashboard.tsx
Dashboard.tsx.explanation.md

api.ts
api.ts.explanation.md

Each explanation file must contain the following sections.

### A. File Purpose

Explain what the file is responsible for.

### B. Why This File Exists

Explain the architectural reason for creating it separately.

### C. Dependencies

List:

- Imported libraries.
- Internal modules imported.
- External services used.
- Database dependencies.
- Other files that depend on it.

### D. Every Function Explained

For every function:

1. Function name.
2. Purpose.
3. Parameters.
4. Parameter types.
5. Return value.
6. Return type.
7. Internal processing.
8. Error handling.
9. Functions or modules it calls.
10. Which other parts of the project use it.

### E. Classes Explained

For every class:

- Class responsibility.
- Constructor.
- Attributes.
- Methods.
- Dependencies.
- Usage.

### F. Execution Flow

Explain what happens when the file executes or when one of its functions is called.

### G. Input and Output

Explain the expected inputs and outputs.

### H. Important Technical Concepts

Explain any important technical concepts used in the implementation.

### I. Example

Provide a small practical example where appropriate.

### J. Maintenance Notes

Explain what should be changed if the file needs modification.

### K. Related Files

Provide relative paths to connected files and their responsibilities.

## 12.2 Documentation Synchronisation

The coding agent must follow this workflow:

1. Create or modify a source file.
2. Immediately create or update its explanation Markdown file.
3. Verify that the explanation matches the implementation.
4. Run the relevant tests.
5. Update central architecture documentation if the file changes system connections.

Do not postpone all documentation until the end.

If a source file changes, its explanation must be reviewed and updated in the same task.

Do not create empty explanation files or generic explanations.

Generated binaries, dataset files, dependency lockfiles, compiled build outputs and automatically generated files do not require individual explanation documents. Their purpose and management must instead be documented in the relevant project documentation.

## 12.3 Whole Project Connected Documentation

Create a mandatory central file:

PROJECT_CONNECTIONS.md

This must explain the entire project from beginning to end.

It must be detailed enough for a developer to understand the complete system without reading every source file first.

Include:

1. Project introduction.
2. Full project architecture.
3. Complete directory structure.
4. Purpose of every major folder.
5. Purpose of every source file.
6. Machine learning pipeline.
7. Dataset flow.
8. Feature engineering flow.
9. Training and evaluation flow.
10. Model saving and loading.
11. FastAPI architecture.
12. API request/response flow.
13. React architecture.
14. Frontend-to-backend communication.
15. Database architecture.
16. SQLAlchemy relationships.
17. Database migration process.
18. Authentication flow.
19. CSV upload processing.
20. Prediction storage.
21. Investigation workflow.
22. Explainability flow.
23. Deployment architecture.
24. Environment configuration.
25. Docker architecture.
26. Local setup instructions.
27. Production deployment instructions.
28. Troubleshooting.
29. How to add another model.
30. How to update the model version.

### Required architecture flow

The document must explain the following connected process:

PaySim CSV
    |
    v
Dataset validation
    |
    v
Data cleaning
    |
    v
Feature engineering
    |
    v
Chronological dataset splitting
    |
    v
Model training and experiments
    |
    v
Model evaluation
    |
    v
Model selection
    |
    v
Model artefact persistence
    |
    v
FastAPI model loading
    |
    v
Prediction endpoint
    |
    v
React application
    |
    v
User sees prediction and explanation
    |
    v
PostgreSQL stores prediction history
    |
    v
Dashboard and reports retrieve stored results

The document must also explain that model training and live inference are separate processes.

## 12.4 Additional Documentation Files

Create:

README.md
PROJECT_CONNECTIONS.md
ARCHITECTURE.md
DATABASE_SCHEMA.md
API_DOCUMENTATION.md
ML_EXPERIMENTS.md
DATASET_DOCUMENTATION.md
DEPLOYMENT.md
ENVIRONMENT_SETUP.md
TESTING_GUIDE.md
SECURITY.md
CHANGELOG.md
CONTRIBUTING.md

Maintain a documentation index in README.md.

---

# 13. Required Project Directory Structure

The following is the target structure. The implementation agent may add files where necessary, but must not remove required responsibilities without documenting the reason.

FinGuard-AI/
|
|-- README.md
|-- PROJECT_CONNECTIONS.md
|-- ARCHITECTURE.md
|-- DATABASE_SCHEMA.md
|-- API_DOCUMENTATION.md
|-- ML_EXPERIMENTS.md
|-- DATASET_DOCUMENTATION.md
|-- DEPLOYMENT.md
|-- ENVIRONMENT_SETUP.md
|-- TESTING_GUIDE.md
|-- SECURITY.md
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- .gitignore
|-- .env.example
|-- docker-compose.yml
|-- Makefile
|
|-- docs/
|   |-- file-explanations/
|   |-- diagrams/
|   |-- research/
|   |-- decisions/
|
|-- data/
|   |-- raw/
|   |-- processed/
|   |-- sample/
|
|-- experiments/
|   |-- notebooks/
|   |-- results/
|   |-- figures/
|   |-- experiment-configs/
|
|-- artifacts/
|   |-- models/
|   |-- metadata/
|
|-- backend/
|   |-- Dockerfile
|   |-- pyproject.toml
|   |-- alembic.ini
|   |-- migrations/
|   |
|   |-- app/
|   |   |-- main.py
|   |   |
|   |   |-- api/
|   |   |   |-- routes/
|   |   |   |-- schemas/
|   |   |
|   |   |-- core/
|   |   |-- services/
|   |   |-- models/
|   |   |-- repositories/
|   |   |-- database/
|   |   |-- ml/
|   |   |-- security/
|   |   |-- utils/
|   |
|   |-- tests/
|       |-- unit/
|       |-- integration/
|       |-- api/
|
|-- frontend/
|   |-- Dockerfile
|   |-- package.json
|   |-- vite.config.ts
|   |-- src/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- layouts/
|   |   |-- services/
|   |   |-- hooks/
|   |   |-- types/
|   |   |-- utils/
|   |   |-- styles/
|   |   |-- assets/
|   |   |-- App.tsx
|   |   |-- main.tsx
|   |
|   |-- tests/
|
|-- scripts/
|   |-- download_dataset.py
|   |-- validate_dataset.py
|   |-- train_models.py
|   |-- evaluate_models.py
|   |-- export_metrics.py
|
|-- .github/
    |-- workflows/
        |-- ci.yml

All manually authored source files must have matching explanation documents using the convention in Section 12.

Do not commit the full PaySim dataset or unnecessary generated model binaries to GitHub.

---

# 14. Testing Requirements

## 14.1 Machine Learning Tests

Test:

- Dataset validation.
- Feature schema.
- Target separation.
- Leakage prevention.
- Train/test temporal boundaries.
- Preprocessing consistency.
- Model loading.
- Prediction output.
- Probability range.
- Threshold behaviour.
- Reproducibility.

## 14.2 Backend Tests

Test:

- Health endpoint.
- Input validation.
- Prediction endpoint.
- Invalid requests.
- CSV upload.
- Database integration.
- Investigation updates.
- Authentication.
- Error responses.

## 14.3 Frontend Tests

Test:

- Navigation.
- Dashboard rendering.
- API communication.
- Upload validation.
- Prediction results.
- Filtering.
- Loading states.
- Error states.
- Responsive layout.

## 14.4 Integration Tests

Verify:

1. Frontend can communicate with backend.
2. Backend can load the model.
3. Backend can connect to PostgreSQL.
4. Predictions can be stored.
5. Stored predictions can be retrieved.
6. Investigation updates persist.
7. Reports reflect database records.

## 14.5 Deployment Tests

Verify:

- Docker image builds.
- Application starts.
- Health endpoint responds.
- Database migrations execute.
- Frontend connects to deployed API.
- Model artefacts are available.
- Environment variables are configured.
- No localhost URLs are used in production.

---

# 15. GitHub and Engineering Standards

The repository must contain:

- Meaningful commit messages.
- Clean source code.
- Type annotations where appropriate.
- Consistent naming.
- No committed secrets.
- No unnecessary generated files.
- No unexplained hardcoded values.
- No fabricated results.
- No duplicated business logic.
- No unnecessary dependencies.

Use GitHub Actions to run relevant tests and build checks.

Every completed milestone must be committed separately.

Do not push untested changes or claim a feature is complete before verifying it.

---

# 16. Six-Phase Implementation Plan

The entire project must be divided into six independently verifiable phases.

The implementation agent must not jump ahead without satisfying the previous phase's acceptance criteria.

## PHASE 1 – Project Foundation and Data Engineering

Deliverables:

- Repository structure.
- Python environment.
- Frontend environment.
- Dependency management.
- Environment configuration.
- Dataset download instructions.
- Dataset validation.
- Data dictionary.
- Exploratory data analysis.
- Feature engineering.
- Leakage audit.
- Chronological dataset splitting.
- Initial documentation.

Acceptance criteria:

- The dataset is correctly loaded.
- The dataset structure is verified.
- The fraud distribution is reported.
- Leakage-prone fields are excluded from the primary feature set.
- All preprocessing steps are reproducible.
- Individual file explanations are present.
- PROJECT_CONNECTIONS.md is started and accurate.

## PHASE 2 – Machine Learning Experiments

Deliverables:

- Baseline models.
- XGBoost.
- LightGBM.
- CatBoost.
- Imbalance handling experiments.
- Hyperparameter tuning.
- Threshold evaluation.
- SHAP explanations.
- Confusion matrices.
- PR and ROC curves.
- Saved experiment results.
- Selected model.
- Model metadata.

Acceptance criteria:

- All selected experiments execute successfully.
- No oversampling leakage exists.
- The final test partition remains untouched during model selection.
- Metrics are calculated directly from executed experiments.
- Model artefacts can be loaded independently.
- Experiment findings are documented.

## PHASE 3 – Backend and Database

Deliverables:

- FastAPI project.
- PostgreSQL integration.
- SQLAlchemy models.
- Alembic migrations.
- Prediction service.
- Transaction endpoints.
- Batch upload endpoints.
- Investigation endpoints.
- Model performance endpoints.
- Authentication and permissions.
- Backend tests.
- Individual file explanations.

Acceptance criteria:

- API starts successfully.
- Model loads successfully.
- Individual prediction works.
- Database persistence works.
- API documentation works.
- Backend tests pass.

## PHASE 4 – React Frontend

Deliverables:

- Application layout.
- White/light UI theme.
- Dashboard.
- Transaction analysis page.
- CSV upload page.
- Transaction explorer.
- Investigation centre.
- Model performance page.
- Explainability page.
- Reports.
- Settings.
- API integration.
- Responsive styling.
- Frontend tests.
- Individual file explanations.

Acceptance criteria:

- All navigation works.
- All pages use actual backend data.
- Prediction results are displayed correctly.
- CSV upload works.
- Error and loading states work.
- Frontend tests pass.

## PHASE 5 – Full Integration and Quality Assurance

Deliverables:

- Complete frontend/backend integration.
- Complete database integration.
- End-to-end workflows.
- Error handling.
- Security review.
- Performance optimisation.
- Batch processing verification.
- Documentation review.
- CI pipeline.

Acceptance criteria:

- All major user journeys work.
- No critical integration errors remain.
- All important tests pass.
- Documentation matches implementation.
- No production secrets are committed.
- No fabricated application metrics exist.

## PHASE 6 – Deployment and Portfolio Release

Deliverables:

- Production Docker configuration.
- Frontend deployment.
- Backend deployment.
- Managed PostgreSQL.
- Environment setup.
- Production API URL.
- Model artefact deployment.
- Health monitoring.
- Production verification.
- README.
- Screenshots.
- Architecture diagrams.
- Portfolio description.
- GitHub release.

Acceptance criteria:

- Public frontend URL works.
- Backend URL works.
- Database connection works.
- Model inference works.
- Prediction history persists.
- CSV demonstration works within hosting limits.
- Application can be accessed independently of the developer's laptop.
- Deployment instructions are complete.

---

# 17. Final Acceptance Criteria

The project will only be considered complete when all of the following are satisfied.

[ ] Full dataset processing is reproducible.

[ ] ML experiments have actual recorded results.

[ ] Leakage prevention is verified.

[ ] Models have been compared fairly.

[ ] Final model selection is justified.

[ ] Individual transaction prediction works.

[ ] CSV batch analysis works.

[ ] Risk scores are displayed.

[ ] Explainability is available.

[ ] PostgreSQL persistence works.

[ ] Investigation workflow works.

[ ] Dashboard reflects actual application data.

[ ] Model performance page reflects real experiment results.

[ ] White/light UI is consistent.

[ ] Backend API documentation exists.

[ ] Every authored source file has a detailed explanation Markdown file.

[ ] PROJECT_CONNECTIONS.md explains the complete architecture.

[ ] All required documentation exists.

[ ] Automated tests pass.

[ ] Docker configuration works.

[ ] Public deployment works.

[ ] No secrets are exposed.

[ ] GitHub repository is clean and professional.

[ ] Portfolio documentation is complete.

---

# 18. Instructions to the AI Coding Agent

Treat this PRD as the authoritative specification.

Follow these instructions throughout implementation.

1. Work in the six defined phases.
2. Do not implement the entire application in one uncontrolled code-generation operation.
3. Before creating files, inspect the existing repository.
4. Never overwrite existing work without inspecting it.
5. Use modular, maintainable architecture.
6. Create files only where their responsibilities are clear.
7. Every authored source file must have a detailed matching explanation Markdown file.
8. Update explanations immediately after modifying the corresponding source.
9. Maintain PROJECT_CONNECTIONS.md throughout development.
10. Keep the project documentation synchronised with the implementation.
11. Never fabricate experimental metrics.
12. Never hardcode production dashboard statistics.
13. Never use target labels as model features.
14. Never introduce data leakage.
15. Never expose credentials.
16. Do not assume that a local application is production-ready.
17. Test each milestone before proceeding.
18. Report exactly what has been completed and what remains.
19. Record commands executed and test outcomes.
20. Commit completed milestones separately.
21. Do not push to GitHub without explicit authorisation.
22. Do not claim deployment is complete until the deployed application has been tested.

At the end of every phase, provide:

- Files created.
- Files modified.
- Explanation documents created or updated.
- Technical implementation summary.
- Tests executed.
- Test results.
- Outstanding issues.
- Git commit information, if committed.
- Confirmation that acceptance criteria have been met.

If any requirement is technically impossible or inappropriate, explain the reason and propose an alternative before silently changing the architecture.

---

# 19. Final Product Vision

FinGuard AI must demonstrate the ability to build a complete machine learning product.

It should not be merely a fraud detection notebook, a static dashboard or a frontend demonstration.

It must connect the entire engineering lifecycle:

Data acquisition → Data engineering → Machine learning → Model evaluation → Explainability → Model persistence → Backend API → Database → React frontend → Deployment.

The final result should be understandable, reproducible, testable, maintainable and publicly demonstrable.

**Definition of success:** A developer or recruiter should be able to open the deployed application, submit a transaction, receive an actual model prediction, inspect its explanation, view the stored prediction and explore the model's genuine evaluation results.

The repository should also contain enough technical documentation for another developer to understand how the system works and reproduce its major components.

End of PRD.
