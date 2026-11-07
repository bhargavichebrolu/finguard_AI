# Environment Setup

Commands were verified on Windows 11 using PowerShell, from the repository root, unless noted otherwise.

## Prerequisites

| Tool | Version used | Needed for |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.11.3 | Python environment. It installs Python 3.11 itself if needed. |
| Node.js and npm | 24.22.1 and 11.19.1 | Frontend |
| Git | 2.56 | Version control |
| make | not installed here | Optional. Each `Makefile` recipe is one command that can be run directly. |
| Docker or PostgreSQL | not installed here | **Required from Phase 3** |

Disk space beyond the dataset: about 1.05 GB for the Python environment and 123 MB for processed partitions.

## Python

```powershell
uv sync --project backend
```

This creates `backend/.venv` with runtime, training and development dependencies, pinned by `backend/uv.lock`. To install runtime dependencies alone, as the future API image will:

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

## Frontend

```powershell
cd frontend
npm ci
npm run dev     # http://localhost:5173
npm run build   # type-check and production bundle
```

## Environment variables

Copy `.env.example` to `.env` and fill it in. `.env` is ignored by Git. Phase 1 code reads none of these variables; they document what Phases 3 and 4 will use.

## Configuration files

These declarative files are documented here rather than in individual explanation documents ([why](docs/decisions/0001-phase-1-decisions.md)).

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
