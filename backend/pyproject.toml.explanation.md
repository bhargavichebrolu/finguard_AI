# pyproject.toml

Source: [backend/pyproject.toml](pyproject.toml)

## A. File Purpose
Declares the backend's Python version, dependencies, test settings and lint rules.

## B. Why This File Exists
It is the single record of what the project needs. `uv.lock`, generated from it, pins exact versions so training, tests and the API image use the same ones.

## C. Dependencies
- **Libraries / tools:** `uv` and `hatchling`.
- **Internal files:** `backend/uv.lock`.
- **External services / database:** the Python package index, when locking.
- **Depended on by:** `backend/Dockerfile`, the `Makefile`, and every `uv run` command.

## D. Every Function Explained
No functions. The sections:

### `dependencies`
What the API image needs, covering the web framework, database access, authentication, and the libraries needed to load the frozen model.

### `dependency-groups`
- `training`: experiment libraries, never installed in the API image.
- `dev`: `pytest`, `ruff`, and `httpx`, which FastAPI's test client needs.

### `tool.uv`
`default-groups` installs training and dev tools on developer computers (the API image passes `--no-default-groups`). `override-dependencies` (Phase 6) gives `nvidia-nccl-cu12` a marker that matches no platform, so it is never installed. XGBoost's Linux wheel requires it, but it serves only multi-GPU training: the frozen model is scored on the CPU, and XGBoost itself stays at the exact version the model was saved with, which start-up checks. Removing it took 469 MB out of the API image; scores and explanations were identical without it.

### `tool.pytest.ini_options`
`--strict-markers` turns a mistyped marker into an error. `real_data` and `database` mark tests that need outside resources.

### `tool.ruff`
Line length 100 and lint rules for errors, imports, likely bugs and modern syntax.

## E. Classes Explained
None.

## F. Execution Flow
Read by `uv` when locking or syncing, and by `pytest` and `ruff` when they run.

## G. Input and Output
Not applicable.

## H. Important Technical Concepts
- **Phase 3 moved `scikit-learn`, `xgboost` and `joblib` into `dependencies`,** because the API now loads the model. The lock file kept them at 1.9.1, 3.2.0 and 1.6.0, the versions recorded in the model's metadata. `model_service.py` refuses to serve on a mismatch.
- **Ranges here, exact versions in the lock.** The Docker build uses `--frozen`, so the image cannot pick up a different version.

## I. Example
```powershell
uv sync --project backend
uv run --project backend pytest backend/tests -m "not real_data"
```

## J. Maintenance Notes
Upgrading `scikit-learn` or `xgboost` needs a retrained model, or a deliberate check that the frozen model behaves identically, followed by an update to the pin. Do not move training libraries into `dependencies`.

## K. Related Files
- [Dockerfile](Dockerfile.explanation.md): installs from the lock without training libraries.
- [model_service.py](app/services/model_service.py.explanation.md): checks versions at start-up.
