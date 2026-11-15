# docker-compose.prod.yml

Source: [docker-compose.prod.yml](docker-compose.prod.yml)

## A. File Purpose
Runs FinGuard in production on one Docker host: PostgreSQL, the migration job, the API, Caddy (HTTPS and the built interface) and a daily retention job, with persistent volumes and health checks.

## B. Why This File Exists
Phase 6 needs a deployment configuration that is complete, secure and portable. `docker-compose.yml` is the development and test stack (published local ports, test databases, test profiles); this file is separate so production carries none of that.

## C. Dependencies
- **Libraries / tools:** Docker Compose v2 with BuildKit.
- **Internal files:** `backend/Dockerfile`, `docker/web/Dockerfile`, `docker/postgres/init/`, the frozen model folder (`FINGUARD_ARTIFACTS_DIR`), and `.env.production` from `scripts/generate_production_env.py`.
- **External services / database:** for a public certificate, a DNS name pointing at the host and ports 80 and 443 reachable.
- **Depended on by:** `DEPLOYMENT.md`, the CI `images` job, `test_deployment.py`.

## D. Every Function Explained

No functions. The services:
- **`db`:** PostgreSQL 17 pinned by digest, SCRAM authentication from first start, data in the `pgdata` volume, no published port, only on the `data` network. `TEST_DB_NAME` is empty, so no test database is created.
- **`migrate`:** `alembic upgrade head` once, after the database is healthy. The image's HTTP health check is disabled because it is a one-off job.
- **`api`:** `APP_ENV=production`; the model folder mounted read-only; on `data` and `edge`; no published port. It trusts forwarded headers only from Caddy's fixed address.
- **`web`:** Caddy with the built interface; the only published ports. Certificates persist in `caddy_data`. Its health check fetches `/health` over HTTPS through Caddy to the API.
- **`retention`:** `python -m app.commands.retention --apply` once a day.

## E. Classes Explained
None.

## F. Execution Flow
`db` healthy → `migrate` completes → `api` and `retention` start → `api` healthy (model verified and registered) → `web` starts. `up --wait` returns when all are healthy. `restart: unless-stopped` brings services back after a crash or reboot.

## G. Input and Output
Input: `.env.production`. Output: the site on `FINGUARD_HTTPS_PORT`, with HTTP on `FINGUARD_HTTP_PORT` redirecting to it.

## H. Important Technical Concepts
- **Required values:** `${NAME:?message}` stops Compose before anything starts if a secret is missing; no secret has a default.
- **Two networks:** `data` (database traffic) and `edge` (Caddy and the API, subnet 172.30.240.0/24). Caddy cannot reach the database.
- **Proxy trust (S14):** `TRUSTED_PROXY_IPS: 172.30.240.10` is Caddy's fixed address, so sign-in limits see each client's real address.
- **API documentation (S13):** not configured, so production serves none.
- **Release tags:** `FINGUARD_RELEASE` names the images, so a previous release can be started again.

## I. Example
```powershell
python scripts/generate_production_env.py --domain finguard.example.com --tls ops@example.com
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build --wait
```

## J. Maintenance Notes
Changing database passwords in `.env.production` after the first start does not change the volume; use `ALTER ROLE`. If the edge subnet changes, change `TRUSTED_PROXY_IPS` too (`test_deployment.py` checks they agree).

## K. Related Files
- [Caddyfile.production](docker/caddy/Caddyfile.production.explanation.md)
- [docker/web/Dockerfile](docker/web/Dockerfile.explanation.md)
- [generate_production_env.py](scripts/generate_production_env.py.explanation.md)
- [verify_deployment.py](scripts/verify_deployment.py.explanation.md)
- [docker-compose.yml](docker-compose.yml.explanation.md): the development stack.
