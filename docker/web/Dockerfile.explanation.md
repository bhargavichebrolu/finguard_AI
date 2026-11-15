# docker/web/Dockerfile

Source: [docker/web/Dockerfile](Dockerfile)

## A. File Purpose
Builds the production web image: the interface built from source, served by Caddy with the production Caddyfile.

## B. Why This File Exists
Phase 6 needs the interface deployed from a clean checkout, not from a `frontend/dist` folder built on someone's computer. Building inside the image runs the same `npm run build` (type check, then Vite) as CI, from the lockfile.

## C. Dependencies
- **Libraries:** Node.js 24.22.1 and Caddy 2.11 base images, both pinned by digest.
- **Internal files:** `frontend/` and `docker/caddy/Caddyfile.production`; everything else is excluded by `Dockerfile.dockerignore`.
- **External services / database:** the npm registry during the build.
- **Depended on by:** the `web` service in `docker-compose.prod.yml`, the CI `images` job.

## D. Every Function Explained

No functions. Two stages:
- **`build`:** `npm ci` from `package-lock.json`, then `npm run build`.
- **final:** Caddy, with `dist` copied to `/srv` and the Caddyfile to `/etc/caddy/Caddyfile`.

## E. Classes Explained
None.

## F. Execution Flow
Copy the lockfile and install, so dependencies are cached while sources change; copy the sources; build; copy the output into the Caddy image.

## G. Input and Output
Input: the repository root as build context. Output: an image of 92.7 MB (as Docker reports it) containing only Caddy, the built files and the Caddyfile.

## H. Important Technical Concepts
- **Context and ignore file:** the context is the repository root, which also holds the dataset, model and secrets. BuildKit reads `Dockerfile.dockerignore` beside this file, which excludes everything except what is needed.
- **No Node.js at run time:** only the final stage is shipped.

## I. Example
```powershell
docker build -f docker/web/Dockerfile -t finguard-web:production .
```

## J. Maintenance Notes
Update the Node.js digest with the version CI uses (`.github/workflows/ci.yml`).

## K. Related Files
- [Dockerfile.dockerignore](Dockerfile.dockerignore.explanation.md)
- [Caddyfile.production](../caddy/Caddyfile.production.explanation.md)
- [docker-compose.prod.yml](../../docker-compose.prod.yml.explanation.md)
