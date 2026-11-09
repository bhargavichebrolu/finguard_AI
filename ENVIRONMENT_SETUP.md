# Environment Setup

Commands were verified on Windows 11 using PowerShell, from the repository root, unless noted otherwise.

## Prerequisites

| Tool | Version used | Needed for |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.11.3 | Python environment. It installs Python 3.11 itself if needed. |
| Node.js and npm | 24.22.1 and 11.19.1 | Frontend |
| Git | 2.56 | Version control |
| make | not installed here | Optional. Each `Makefile` recipe is one command that can be run directly. |
| Docker Desktop | 4.98.0 (Engine 29.9.2, Compose v5.6.1), WSL 2 | PostgreSQL and the API containers |

Disk space beyond the dataset: about 1.05 GB for the Python environment and 123 MB for processed partitions.

## Python

```powershell
uv sync --project backend
```

This creates `backend/.venv` with runtime, training and development dependencies, pinned by `backend/uv.lock`. To install runtime dependencies alone, as the API image does:

```powershell
uv sync --project backend --no-default-groups
```

## Dataset

See [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) for how to obtain the file. It must end up at `data/raw/PS_20174392719_1491204439457_log.csv`.

## Running the data pipeline

Run these in order.

```powershell
uv run --project backend python scripts/validate_dataset.py
uv run --project backend python scripts/prepare_dataset.py
uv run --project backend python scripts/run_eda.py
uv run --project backend python scripts/audit_leakage.py
```

Measured on the development machine (16 logical processors, 15.7 GB of RAM):

| Stage | Time | Peak memory |
|---|---:|---:|
| Validate | 53 s | 0.90 GB |
| Prepare | 30 s | 0.56 GB |
| EDA | 8 s | 0.20 GB |
| Leakage audit | 48 s | 2.01 GB |

The audit peaks highest because ROC-AUC needs all training rows in memory for ranking. Loading the whole CSV at once, by comparison, takes at least 1.27 GB for the data alone.

| Output | Location | In Git? |
|---|---|---|
| Raw dataset | `data/raw/` | No |
| Parquet partitions | `data/processed/` | No |
| Validation, EDA and audit reports | `experiments/results/` | Yes |
| Charts | `experiments/figures/eda/` | Yes |
| Preprocessing metadata, feature dictionary | `artifacts/metadata/` | Yes |

**To verify a reproduction**, rerun the pipeline and run `git diff artifacts/metadata/`. An empty diff means your partitions match exactly. Library versions are recorded in the metadata, so a dependency upgrade also shows there.

## Running the experiments

See [ML_EXPERIMENTS.md](ML_EXPERIMENTS.md#how-to-reproduce) for the commands, which run in order and need the data pipeline's outputs.

On the development machine, using 8 threads, recorded fitting time across all 125 runs was 68 minutes, and the selection step took over 10 minutes. Phase 2 peak memory was not measured. Per-run scores take about 400 MB of disk, and the selected model file is 57.5 KB.

| Output | Location | In Git? |
|---|---|---|
| Per-run validation scores | `experiments/scores/` | No |
| SHAP values for charts | `experiments/results/phase2/shap_sample.npz` | No |
| Selected model binary | `artifacts/models/fraud_detector_v1/model.joblib` | No |
| Run records, selection, thresholds, SHAP summary, test results, tables | `experiments/results/phase2/` | Yes |
| Charts | `experiments/figures/models/` | Yes |
| Model metadata and metrics bundle | `artifacts/metadata/model_v1*.json` | Yes |

## Backend and database

Docker Desktop installs per user under `%LOCALAPPDATA%\Programs\DockerDesktop`. A terminal opened before installation will not find `docker` until it is restarted.

```powershell
# 1. Create .env with new random secrets. Ports default to 5432 and 8000.
uv run --project backend python scripts/generate_env.py --api-port 8010

# 2. Start PostgreSQL. The first start creates the volume with SCRAM authentication.
docker compose up -d --wait db

# 3. Either run everything in Docker: migrations, then the API
docker compose up -d --build --wait

#    or run the API on Windows against the same database
cd backend; uv run alembic upgrade head; uv run uvicorn app.main:app --port 8010; cd ..

# 4. Create the first administrator. The password is prompted for and not shown.
uv run --project backend python scripts/create_admin.py --email you@example.com
```

Then open `http://127.0.0.1:8010/docs`, use **Authorize** with your email and password, and try the endpoints.

The API refuses to start if the frozen model file is missing, altered or under different library versions. `model.joblib` is not in Git, so a fresh clone needs it placed at `artifacts/models/fraud_detector_v1/model.joblib` (see `DEPLOYMENT.md`).

| Item | Value on the development computer |
|---|---|
| API image | `finguard-api:local`, 1.92 GB, of which 469 MB is NVIDIA libraries pulled in by XGBoost's Linux wheel |
| API port | 8010, because 8000 was in use by another project |
| Data volume | `finguard_finguard_pgdata`, kept by `docker compose down` and deleted by `docker compose down -v` |

## Frontend

```powershell
cd frontend
npm ci
npm run dev       # http://127.0.0.1:5173, forwarding /api to the API on 127.0.0.1:8010
npm test          # unit and component tests
npm run build     # type check and production bundle
npm run preview   # http://127.0.0.1:4173, the built app with its Content Security Policy
```

The app calls the API on its own origin. The Vite servers forward `/api` and `/health` to `FINGUARD_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8010`. Sign in with an account made by `scripts/create_admin.py`. After an API change, run `uv run --project backend python scripts/export_openapi.py`, then `npm run gen:api`.

### Worker processes and rate limits (Phase 5)

`WEB_CONCURRENCY` sets the API's worker processes (default 1). Each loads the model, about 170 MiB; two workers nearly doubled concurrent throughput in measurement, four were slower than two (`docs/performance/phase-5-m3-rate-limits-and-workers.md`). Rate limits are shared through PostgreSQL, so any number of workers or containers enforce one limit. `RATE_LIMIT_STORE=memory` exists only for comparison measurements and is refused in production.

### Batch queue (Phase 5)

Every API process runs one batch worker. `BATCH_LEASE_SECONDS` (60) is how long a crashed process holds a job before another resumes it, `BATCH_MAX_ATTEMPTS` (3) how many interrupted attempts a job gets, `BATCH_POLL_SECONDS` (2) how often an idle worker looks for work. A graceful stop gives the job back at once. Uploads are stored in the database until their job ends, so no shared disk is needed.

### Browser tests

```powershell
uv run --project backend python scripts/e2e_stack.py up   # API on 127.0.0.1:8011 using finguard_e2e_test
cd frontend
npx playwright install chromium                           # once
npm run test:e2e                                          # builds, serves on 127.0.0.1:4173, runs all projects
cd ..; uv run --project backend python scripts/e2e_stack.py down
```

`e2e_stack.py up` creates `finguard_e2e_test` if it is missing, and global setup reseeds it (refusing any name not ending in `_test`), so nothing in development data is touched. The backend suite uses `finguard_test` instead, so the two suites can run one after the other without restarting anything. Generated passwords, saved test sessions and screenshots go to `frontend/.e2e/`, which Git ignores. The browser-test API uses its own random signing key on each start and allows only `http://127.0.0.1:4173` as an origin.

## Environment variables

Run `scripts/generate_env.py` rather than copying `.env.example` by hand. It fills every secret with a random value and refuses to overwrite an existing `.env`. Each variable is described in [.env.example.explanation.md](.env.example.explanation.md). Use `127.0.0.1`, not `localhost`, in database addresses.

## Configuration files

From Phase 3, configuration files that are authored by hand have their own explanation documents beside them, for example `docker-compose.yml.explanation.md` ([why](docs/decisions/0003-phase-3-decisions.md)). The frontend configuration below is still described only here, because Phase 3 made no frontend changes.

| File | Purpose | Maintenance |
|---|---|---|
| `backend/pyproject.toml` | Python dependencies and groups; pytest and ruff settings | Add a dependency in the same change as the code that first imports it |
| `backend/uv.lock` | Generated exact Python versions | Commit it; never edit by hand |
| `frontend/package.json` | Frontend dependencies and scripts | Add dependencies only when used, or when the PRD requires them |
| `frontend/package-lock.json` | Generated exact Node versions | Commit it; never edit by hand |
| `frontend/tsconfig.json` | Strict TypeScript settings | Do not relax strictness to silence an error |
| `experiments/experiment-configs/split_v1.json` | Split fractions | Do not edit. Add a new version instead |
| `experiments/experiment-configs/experiments_v1.json` | Seeds, threads, model settings, search budgets, threshold objective, selection limits | Do not edit after results exist. Add a new version instead |
| `.gitignore` | Excludes secrets, data, model binaries and build output | Review before adding any new data location |
| `.env.example` | Placeholder configuration only | Never put a real value here |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Failed to build numba` | Resolver chose an old version | Keep the `numba>=0.61` floor in `pyproject.toml` |
| `ModuleNotFoundError: pyarrow` or similar | Environment synced without groups | Run `uv sync --project backend` |
| `Dataset not found` | CSV not in `data/raw/` | See [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) |
| `FileNotFoundError` for `preprocessing_v1.json` | EDA or audit run before preparation | Run `scripts/prepare_dataset.py` first |
| `exit code 255` in PowerShell around `uv` | PowerShell treats uv's progress on stderr as an error | Read the actual output; the command probably succeeded |
| `make` not recognised | Not installed on Windows by default | Run the recipe's command directly |
| `docker: command not found` | Terminal started before Docker Desktop was installed | Restart the terminal or editor |
| Database connection hangs | `localhost` tries IPv6 first, and Compose publishes IPv4 only | Use `127.0.0.1` in `DATABASE_URL` |
| `port is already allocated` | Another service uses the port | Change `POSTGRES_HOST_PORT` or `API_HOST_PORT` in `.env` |
| API exits with `ModelArtifactError` | Model file missing, altered or wrong library versions | Restore the frozen file. Do not edit the metadata or pins. |
| Password changes in `.env` have no effect | The volume kept the old password | Change it with `ALTER ROLE`, or recreate the volume (deletes data) |
