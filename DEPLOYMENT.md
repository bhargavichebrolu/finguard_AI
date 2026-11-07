# Deployment

**Status: nothing is deployed. Deployment is Phase 6.** This file records the target and the constraints that earlier phases must respect. It will become step-by-step instructions, and only then will be verified against a live deployment.

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
- The API image uses `uv sync --no-default-groups` plus the chosen model's library. Training libraries are excluded, which matters for memory and image size.
- The container must not download or train on PaySim at startup.
- The deployed demonstration works on a manageable sample, not the full dataset.

## Open question for Phase 6

Where artefacts live depends on the chosen host. Options include a release asset, object storage, or copying them into the image at build time. The selected model file is 57.5 KB, so size does not limit the choice. It needs `xgboost` in the API image.
