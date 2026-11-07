# Deployment

**Status: nothing is deployed. Deployment is Phase 6.** Phase 3 runs the API and database locally through `docker-compose.yml`. This file records the target and the constraints that earlier phases must respect. It will become step-by-step instructions, and only then will be verified against a live deployment.

## Target

| Part | Platform options | Requirement |
|---|---|---|
| Frontend | Netlify or Vercel | API URL from environment; routes survive refresh; HTTPS |
| Backend | Render, Railway or AWS | Container, health endpoint, structured logs, correct CORS |
| Database | Managed PostgreSQL | No dependency on a laptop; controlled migrations |
| Model artefacts | Stored apart from source | Loaded at startup, never trained in production |

The frontend and backend deploy independently, and the design stays portable between providers.

## Constraints to respect from now on

- Free hosting may lack persistent disk, always-on service, background workers and large memory, so batch processing must fit within those limits.
- The API image uses `uv sync --frozen --no-default-groups --no-install-project`. Training libraries are excluded, which a check confirmed in the built image.
- The image is 1.92 GB, of which 469 MB is `nvidia-nccl-cu12`, which XGBoost's Linux wheel requires but this CPU-only model never uses. Switching to the `xgboost-cpu` package would shrink it, but start-up checks the `xgboost` package version against the model's metadata, so that switch needs a deliberate check and a pin change.
- The database must be initialised with `POSTGRES_INITDB_ARGS="--auth-local=scram-sha-256 --auth-host=scram-sha-256"` or its managed equivalent, and the API must connect as a role without superuser rights.
- Batch processing runs inside the API process and is lost on restart. Interrupted jobs are marked failed at start-up.
- The container must not download or train on PaySim at startup.
- The deployed demonstration works on a manageable sample, not the full dataset.

## Open question for Phase 6

Where artefacts live depends on the chosen host. Options include a release asset, object storage, or copying them into the image at build time. The selected model file is 57.5 KB, so size does not limit the choice. Locally, Compose mounts `artifacts/` read-only. Whatever the host, the file must match the hash pinned in `backend/app/core/frozen_model.py`, or the API will not start.
