# Dockerfile

Source: [backend/Dockerfile](Dockerfile)

## A. File Purpose
Builds the API image, which the `migrate` and `api` services in `docker-compose.yml` both use.

## B. Why This File Exists
PRD 11.6 requires a backend Dockerfile. An image also proves the API works with only its declared dependencies, without the training libraries that happen to be installed on the development computer.

## C. Dependencies
- **Libraries / tools:** Docker, `uv`.
- **Internal files:** `pyproject.toml`, `uv.lock`, `alembic.ini`, `migrations/`, `app/`.
- **External services / database:** the `python:3.11-slim` base image and the package index, at build time only.
- **Depended on by:** `docker-compose.yml`.

## D. Every Function Explained
No functions. The steps:

### System package
`libgomp1` is the OpenMP runtime XGBoost needs. Without it, loading the model fails inside the container.

### Dependency install
`uv sync --frozen --no-default-groups --no-install-project` installs exactly what `uv.lock` records, and leaves out the `training` and `dev` groups. Copying the lock file before the code means dependency layers are rebuilt only when dependencies change.

### Non-root user
The process runs as `finguard`, which cannot change `/app`.

### Proxy trust
`--no-proxy-headers` stops Uvicorn trusting `X-Forwarded-For` from 127.0.0.1, which it does by default. Proxy trust is then controlled only by `TRUSTED_PROXY_IPS`.

### Health check
Uses Python's standard library, so `curl` is not needed in the image.

## E. Classes Explained
None.

## F. Execution Flow
Build: install system packages, install Python dependencies, copy code, create the user. Run: `uvicorn` starts `app.main:app`.

## G. Input and Output
Build input: the `backend/` folder, filtered by `.dockerignore`. Output: an image serving port 8000.

## H. Important Technical Concepts
- **The model is not in the image.** It is mounted read-only at run time, so the image stays small and the model stays out of the build. PRD 5.8 and `DEPLOYMENT.md` keep model artefacts apart from source.
- **Same versions as training.** The lock pins `scikit-learn` 1.9.1 and `xgboost` 3.2.0, and start-up refuses any other versions.
- **Python is pinned to 3.11,** matching the version that saved the model.

## I. Example
```powershell
docker compose build api
```

## J. Maintenance Notes
The base image is pinned by digest and `uv` to an exact version (Phase 5 M1), so a rebuild uses exactly what was tested; `test_reproducibility.py` checks both pins exist. To update, resolve the new digest with `docker buildx imagetools inspect python:3.11-slim`, rebuild and rerun the tests. If the lock file format changes, update this pin. New top-level backend folders the API needs must be copied here.

## K. Related Files
- [.dockerignore](.dockerignore.explanation.md): what stays out of the build.
- [docker-compose.yml](../docker-compose.yml.explanation.md): how the image is run.
- [pyproject.toml](pyproject.toml.explanation.md): the dependencies installed.
