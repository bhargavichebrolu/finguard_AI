# FinGuard AI

An end-to-end machine learning application for monitoring simulated financial transactions: a reproducible data and training pipeline, a FastAPI service, a PostgreSQL database and a React dashboard.

> **Research and demonstration only.** FinGuard AI is built on the synthetic PaySim dataset. Its predictions are not verified financial crime findings and must not be used to block real customer transactions.

## Project status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation and data engineering | Complete |
| 2 | Machine learning experiments | Complete, awaiting review |
| 3 | Backend and database | Not started |
| 4 | React frontend | Not started (toolchain only) |
| 5 | Integration and quality assurance | Not started |
| 6 | Deployment and portfolio release | Not started |

**What works today:** dataset validation, EDA, feature engineering, a leakage audit, chronological partitioning, model experiments and a frozen model that can be loaded and verified, all from the command line. There is no API or usable interface yet.

## Key findings so far

- The dataset matches its published profile: 6,362,620 rows and 8,213 fraud rows (0.129%).
- Balance columns are excluded as leaky: an origin balance that reconciles exactly appears in 99.1% of fraud rows against 20.3% of legitimate rows.
- Fraud prevalence shifts sharply over time: 0.082% in training, 0.059% in validation and 0.420% in test. Fraud per step stays stable while legitimate volume collapses.
- The selected model is XGBoost on the original class distribution. Without balance columns, on the test window it reaches PR-AUC 0.4242 against 0.0042 for random ranking, with 45.9% recall and 40.7% precision.
- XGBoost, LightGBM and CatBoost were statistically tied on validation, so a pre-registered rule made the choice.
- Results differ greatly by regime: recall is 56.1% in low-volume steps and 21.9% in normal steps. The model missed its false positive target on test (0.282% against 0.1%). See [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md#test-results).

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and Node.js 20 or later.

```powershell
uv sync --project backend
uv run --project backend python scripts/download_dataset.py --from-file <path to PaySim csv>
uv run --project backend python scripts/validate_dataset.py
uv run --project backend python scripts/prepare_dataset.py
uv run --project backend python scripts/run_eda.py
uv run --project backend python scripts/audit_leakage.py
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml
```

Full instructions are in [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md).

## Documentation index

| Document | Contents |
|---|---|
| [PROJECT_CONNECTIONS.md](PROJECT_CONNECTIONS.md) | How the entire system connects, start to finish |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, boundaries and design rules |
| [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) | Dataset, data dictionary, feature dictionary, leakage audit, EDA |
| [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md) | Experimental design and results |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database design (planned) |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | API contract (planned) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment plan |
| [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) | Local setup and configuration |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | How to run tests, and what they cover |
| [SECURITY.md](SECURITY.md) | Security rules and status |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and documentation rules |
| [CHANGELOG.md](CHANGELOG.md) | Project history |
| [docs/PRD.md](docs/PRD.md) | Product requirements (the specification) |
| [docs/decisions/](docs/decisions/) | Architecture decision records |
| [docs/file-explanations/](docs/file-explanations/) | One explanation document per source file |
