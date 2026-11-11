# Deployment

**Status: nothing is deployed. Deployment is Phase 6.** The API and database run locally through `docker-compose.yml`, and Phase 5 added a local HTTPS production-like stack (`scripts/prodlike_stack.py`) that shows the intended shape. This file records the target and the constraints that earlier phases must respect. It will become step-by-step instructions, and only then will be verified against a live deployment.

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
- Batch processing runs inside the API processes as a PostgreSQL queue (Phase 5, ADR 0005 D1). It needs no separate worker or persistent disk: upload bytes are held in the database until the job ends, and a job interrupted by a restart or host sleep resumes from its last committed chunk once its 60-second lease expires.
- Rate limits are counted in PostgreSQL, so any number of API processes share them; production refuses the per-process memory store.
- Each API process loads the model: about 170 MB idle per process in Phase 5 measurements. `WEB_CONCURRENCY` defaults to 1; two processes suit hosts with at least 1 GB.
- The browser must reach the API on the frontend's own origin (ADR 0004): the frontend host forwards `/api` and `/health` to the API (Netlify `_redirects` with status 200, or Vercel `rewrites`). Production cookies are `__Secure-` and `__Host-` prefixed and need HTTPS.
- `TRUSTED_PROXY_IPS` must list the host's proxy addresses, or the sign-in limit becomes per email only (security finding S14).
- `python -m app.commands.retention --apply` should be scheduled by the host (sessions 7 days, audit 365 days).
- The container must not download or train on PaySim at startup.
- The deployed demonstration works on a manageable sample, not the full dataset.

## Open question for Phase 6

Where artefacts live depends on the chosen host. Options include a release asset, object storage, or copying them into the image at build time. The selected model file is 57.5 KB, so size does not limit the choice. Locally, Compose mounts `artifacts/` read-only. Whatever the host, the file must match the hash pinned in `backend/app/core/frozen_model.py`, or the API will not start.
