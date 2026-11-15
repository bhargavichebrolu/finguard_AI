# Dockerfile.dockerignore

Source: [docker/web/Dockerfile.dockerignore](Dockerfile.dockerignore)

## A. File Purpose
Limits what the web image build can see: only `frontend/` (without installed packages, build output or test results) and the production Caddyfile.

## B. Why This File Exists
The web image is built with the repository root as context, because it needs both the frontend and a file under `docker/`. The root also holds `data/` (the PaySim dataset), `artifacts/` (the frozen model) and local `.env` files with secrets. Without this file all of it would be sent to the builder, which is slow and risks secrets ending up in an image layer.

## C. Dependencies
- **Libraries / tools:** Docker BuildKit, which reads `<Dockerfile name>.dockerignore` next to the Dockerfile.
- **Internal files:** `docker/web/Dockerfile`.
- **External services / database:** none.
- **Depended on by:** `docker build -f docker/web/Dockerfile .` and the `web` service.

## D. Every Function Explained

No functions. `*` excludes everything; `!` lines bring back what the build needs; the last lines exclude large or local folders inside `frontend/`.

## E. Classes Explained
None.

## F. Execution Flow
Docker applies the patterns in order before sending the context to the builder.

## G. Input and Output
Input: the repository root. Output: a build context of the frontend sources and one Caddyfile.

## H. Important Technical Concepts
An allow-list is safer than a deny-list here: a new secret or data folder added later is excluded automatically. `test_deployment.py` checks that only the two expected paths are allowed.

## I. Example
```powershell
docker build -f docker/web/Dockerfile -t finguard-web:production .
```

## J. Maintenance Notes
If the build needs another file, add one `!` line for it, never a wider pattern.

## K. Related Files
- [docker/web/Dockerfile](Dockerfile.explanation.md)
- [test_deployment.py](../../backend/tests/unit/test_deployment.py.explanation.md)
