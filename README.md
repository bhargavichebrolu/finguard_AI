# FinGuard AI

An end-to-end machine learning application for monitoring simulated financial transactions: a reproducible data and training pipeline, a FastAPI service, a PostgreSQL database and a React dashboard.

> **Research and demonstration only.** FinGuard AI is built on the synthetic PaySim dataset. Its predictions are not verified financial crime findings and must not be used to block real customer transactions.

## Project status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation and data engineering | Complete |
| 2 | Machine learning experiments | Complete |
| 3 | Backend and database | Complete |
| 4 | React frontend | Complete |
| 5 | Integration hardening, quality assurance and reliability | Complete: accepted on 2026-11-13 with its documented residual risks ([completion record](docs/plans/phase-5-completion.md), [Firefox investigation](docs/plans/phase-5-firefox-investigation.md)) |
| 6 | Deployment and portfolio release | Implemented: production configuration built and verified in a local rehearsal ([DEPLOYMENT.md](DEPLOYMENT.md), [completion record](docs/plans/phase-6-completion.md)). **Not deployed to a public host** |

Phases 5 and 6 are on branch `phase-5-hardening`, which is not merged into `main` and not pushed.

**What works today:** the data pipeline and experiments from the command line, and a FastAPI service backed by PostgreSQL. The service runs locally in Docker. It verifies and loads the frozen model, scores single transactions and CSV batches, stores predictions and investigations, and serves the saved evaluation. A React interface covers all ten PRD pages: dashboard, single and CSV batch scoring, the transaction explorer, investigations, model performance, explanations, reports, settings and system information. It signs in with HttpOnly cookie sessions, shows each role only what it may use, and states the model's measured shortfalls beside every score. Browser tests run it against the real API and PostgreSQL at desktop, tablet and mobile sizes, with automated accessibility checks, in Chromium, Firefox and WebKit. Since Phase 5, batch jobs survive restarts and run across several API processes, rate limits are shared between processes, the production settings are tested over HTTPS behind a proxy, outages give clear messages and recover without a restart, and a CI workflow is written (it has not yet run on GitHub). Phase 6 added a production deployment on one Docker host (HTTPS through Caddy, no API documentation in production, proxy trust enforced, daily retention), halved the API image without changing a single score, and sped up deep explorer pages. Safari itself and screen readers have not been tested.

`model_score` is not a calibrated probability, and `FLAG_FOR_REVIEW` is a request for human review.

## Key findings so far

- The dataset matches its published profile: 6,362,620 rows and 8,213 fraud rows (0.129%).
- Balance columns are excluded as leaky: an origin balance that reconciles exactly appears in 99.1% of fraud rows against 20.3% of legitimate rows.
- Fraud prevalence shifts sharply over time: 0.082% in training, 0.059% in validation and 0.420% in test. Fraud per step stays stable while legitimate volume collapses.
- The selected model is XGBoost on the original class distribution. Without balance columns, on the test window it reaches PR-AUC 0.4242 against 0.0042 for random ranking, with 45.9% recall and 40.7% precision.
- XGBoost, LightGBM and CatBoost were statistically tied on validation, so a pre-registered rule made the choice.
- Results differ greatly by regime: recall is 56.1% in low-volume steps and 21.9% in normal steps. The model missed its false positive target on test (0.282% against 0.1%). See [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md#test-results).

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and Node.js 20 or later (24.22.1 is the version tested and used in CI).

```powershell
uv sync --project backend
uv run --project backend python scripts/download_dataset.py --from-file <path to PaySim csv>
uv run --project backend python scripts/validate_dataset.py
uv run --project backend python scripts/prepare_dataset.py
uv run --project backend python scripts/run_eda.py
uv run --project backend python scripts/audit_leakage.py
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml
```

The pipeline commands need the PaySim CSV; the application does not. To run the application, with Docker Desktop installed and the frozen model at `artifacts/models/fraud_detector_v1/model.joblib` (not in Git):

```powershell
uv run --project backend python scripts/generate_env.py --api-port 8010
docker compose up -d --build --wait
uv run --project backend python scripts/create_admin.py --email you@example.com
cd frontend; npm ci; npm run dev
```

Then open `http://127.0.0.1:5173` and sign in; the API's interactive documentation is at `http://127.0.0.1:8010/docs`. Full instructions are in [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md).

To run the production configuration (HTTPS, Caddy, no API documentation), see [DEPLOYMENT.md](DEPLOYMENT.md): `scripts/generate_production_env.py`, then `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build --wait`.

## Demonstration

A five-minute walk through the whole workflow, as an administrator:

1. **Dashboard:** totals, flag rate and risk distribution of stored predictions, with the model's measured limitations.
2. **Transaction Analysis:** score `CASH_OUT`, 5,000,000.00, step 50, customer. The result is `FLAG_FOR_REVIEW` with an uncalibrated `model_score`, a risk level and a SHAP explanation, and an investigation opens as New. For contrast, `TRANSFER`, 1,000,000.00, step 400 is `NOT_FLAGGED` (both inputs are used by the browser tests).
3. **CSV Batch Analysis:** upload a CSV with the columns `external_transaction_id,amount,transaction_type,step,destination_category`. Watch progress, page through results, and download the results and errors (formula-safe).
4. **Transaction Explorer:** filter by decision, risk or type; sort by score; open a transaction.
5. **Investigation Centre:** open the new case, move it to Under review, add a note, then close it (a confirmation explains that statuses never change scores); the history keeps every step.
6. **Model Performance and Explainable AI:** the saved evaluation of the frozen model (PR curves by regime, the 0.282% false positive rate against its 0.1% target) and global feature importance.
7. **Reports and Settings:** export predictions as CSV; change the high-risk boundary (the decision threshold stays frozen); add an analyst account and sign in as them to see the restricted navigation.

## Documentation index

| Document | Contents |
|---|---|
| [PROJECT_CONNECTIONS.md](PROJECT_CONNECTIONS.md) | How the entire system connects, start to finish |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, boundaries and design rules |
| [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) | Dataset, data dictionary, feature dictionary, leakage audit, EDA |
| [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md) | Experimental design and results |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Tables, constraints, roles and migrations |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Endpoints, roles, inputs, errors and score meaning |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment: configuration, commands, verification |
| [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) | Local setup and configuration |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | How to run tests, and what they cover |
| [SECURITY.md](SECURITY.md) | Security rules and status |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and documentation rules |
| [CHANGELOG.md](CHANGELOG.md) | Project history |
| [docs/PRD.md](docs/PRD.md) | Product requirements (the specification) |
| [docs/decisions/](docs/decisions/) | Architecture decision records |
| [docs/file-explanations/](docs/file-explanations/) | Explanation documents for Phase 1 and 2 files. From Phase 3, each file's document sits beside it. |
