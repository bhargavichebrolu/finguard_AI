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
| 5 | Integration hardening, quality assurance and reliability | Implemented on branch `phase-5-hardening` (milestones M1–M9 committed); acceptance pending the reviewer's decision on the Firefox reliability investigation ([completion record](docs/plans/phase-5-completion.md), [investigation](docs/plans/phase-5-firefox-investigation.md)) |
| 6 | Deployment and portfolio release | Not started |

**What works today:** the data pipeline and experiments from the command line, and a FastAPI service backed by PostgreSQL. The service runs locally in Docker. It verifies and loads the frozen model, scores single transactions and CSV batches, stores predictions and investigations, and serves the saved evaluation. A React interface covers all ten PRD pages: dashboard, single and CSV batch scoring, the transaction explorer, investigations, model performance, explanations, reports, settings and system information. It signs in with HttpOnly cookie sessions, shows each role only what it may use, and states the model's measured shortfalls beside every score. Browser tests run it against the real API and PostgreSQL at desktop, tablet and mobile sizes, with automated accessibility checks, in Chromium, Firefox and WebKit. Since Phase 5, batch jobs survive restarts and run across several API processes, rate limits are shared between processes, the production settings are tested over HTTPS behind a proxy, outages give clear messages and recover without a restart, and a CI workflow is written (it has not yet run on GitHub). Safari itself and screen readers have not been tested.

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

To run the API, with Docker Desktop installed:

```powershell
uv run --project backend python scripts/generate_env.py --api-port 8010
docker compose up -d --build --wait
uv run --project backend python scripts/create_admin.py --email you@example.com
```

Then open `http://127.0.0.1:8010/docs`. Full instructions are in [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md).

## Documentation index

| Document | Contents |
|---|---|
| [PROJECT_CONNECTIONS.md](PROJECT_CONNECTIONS.md) | How the entire system connects, start to finish |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, boundaries and design rules |
| [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) | Dataset, data dictionary, feature dictionary, leakage audit, EDA |
| [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md) | Experimental design and results |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Tables, constraints, roles and migrations |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Endpoints, roles, inputs, errors and score meaning |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment plan |
| [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) | Local setup and configuration |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | How to run tests, and what they cover |
| [SECURITY.md](SECURITY.md) | Security rules and status |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and documentation rules |
| [CHANGELOG.md](CHANGELOG.md) | Project history |
| [docs/PRD.md](docs/PRD.md) | Product requirements (the specification) |
| [docs/decisions/](docs/decisions/) | Architecture decision records |
| [docs/file-explanations/](docs/file-explanations/) | Explanation documents for Phase 1 and 2 files. From Phase 3, each file's document sits beside it. |
