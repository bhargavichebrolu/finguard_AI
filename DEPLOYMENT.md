# Deployment

**Status (Phase 6): the production configuration is complete and was verified in a full local rehearsal. Nothing is deployed to a public host, and no public URL exists.**

A public deployment needs a server and a DNS name, which this project does not have. Every step below was run on the development computer with the same files, using Caddy's own certificate authority in place of a public one (section 6). The steps that only a public host can show are listed in section 7.

## 1. What runs

One Docker host runs `docker-compose.prod.yml`:

```
browser --HTTPS--> web (Caddy: certificate, headers, built interface)
                     |  /api/*, /health only, uncompressed
                     v
                   api (FastAPI, APP_ENV=production, frozen model mounted read-only)
                     |                          retention (daily, same image)
                     v                                  |
                   db (PostgreSQL 17, volume pgdata) <--+
```

| Service | Image | Published | Notes |
|---|---|---|---|
| `web` | `finguard-web`, built by `docker/web/Dockerfile` (92.7 MB) | 80 and 443 only | Public certificate from an ACME authority, renewed automatically, stored in the `caddy_data` volume |
| `api` | `finguard-api`, built by `backend/Dockerfile` (979 MB) | Nothing | Trusts forwarded headers only from Caddy's fixed address, 172.30.240.10 |
| `db` | `postgres:17-alpine`, pinned by digest | Nothing | SCRAM authentication; the API connects as a role without superuser rights; no test database |
| `migrate` | `finguard-api` | Nothing | `alembic upgrade head`, then exits; the API starts only after it succeeds |
| `retention` | `finguard-api` | Nothing | `python -m app.commands.retention --apply` once a day (sessions 7 days, audit 365 days) |

The database is on its own network, which Caddy cannot reach. Image sizes are as `docker image ls` reports them.

## 2. Requirements

- A Linux host with Docker Engine and Compose v2, at least 1 GB of memory for one API process (each process loads the model, about 170 MB idle).
- For a public certificate: a DNS name pointing at the host, and ports 80 and 443 reachable from the internet.
- The frozen model files. `model.joblib` is not in Git. Copy the repository's `artifacts/` folder (with `artifacts/models/fraud_detector_v1/model.joblib`) to the host. The API refuses to start unless the file matches the SHA-256 pinned in `backend/app/core/frozen_model.py` (`69813c17…`), the metadata matches, and scikit-learn and XGBoost are the versions the model was saved with.

## 3. First deployment

```bash
git clone <repository> finguard && cd finguard
# The frozen model (section 2). Git keeps only artifacts/models/.gitkeep, so create the folder.
mkdir -p artifacts/models/fraud_detector_v1
cp /path/to/model.joblib artifacts/models/fraud_detector_v1/model.joblib
sha256sum artifacts/models/fraud_detector_v1/model.joblib   # must start 69813c17

# 1. Settings with new secrets. Never commit .env.production (Git ignores it).
python3 scripts/generate_production_env.py --domain finguard.example.com --tls ops@example.com

# 2. Build and start. --wait returns when every service is healthy.
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build --wait

# 3. The first administrator. The password is prompted for and not shown.
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec api python -m app.commands.create_admin --email admin@example.com

# 4. Verify the deployment from any computer.
python3 scripts/verify_deployment.py --origin https://finguard.example.com --email admin@example.com
```

`--tls` takes an email address for a public certificate, or `internal` for Caddy's own authority, which browsers do not trust (rehearsals only). Other options: `--http-port`, `--https-port`, `--bind-address` and `--artifacts-dir`.

## 4. Operating it

| Task | Command (prefix: `docker compose -f docker-compose.prod.yml --env-file .env.production`) |
|---|---|
| Status and health | `ps` |
| Logs (structured JSON from the API) | `logs -f api` |
| Stop, keeping data | `down` |
| Start again | `up -d --wait` |
| Upgrade to a new commit | `git pull`, then `up -d --build --wait` (migrations run first) |
| Keep the previous images | set `FINGUARD_RELEASE=<name>` in `.env.production` before building |
| Back up the database | `exec -T db sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > finguard.dump` |
| Restore (replaces the current data) | `exec -T db sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < finguard.dump`, then `restart api` |

Backup and restore pass the administrator password even inside the container, because the database uses SCRAM on its local socket as well. Both commands were run in the rehearsal (section 6).

**Restarts and failures.** Every long-running service has `restart: unless-stopped`. The API's health check calls `/health`, which answers only after start-up has verified the model and registered it in the database. If the database becomes unavailable, requests that need it get 503 with `Retry-After`, the session is kept, and the pool reconnects when the database returns, without restarting the API. A batch job interrupted by a stop or crash resumes from its last stored chunk after its 60-second lease expires, in any API process.

**Secrets.** All secrets are in `.env.production`, which `generate_production_env.py` writes with new random values and Git ignores. Compose refuses to start if one is missing. Changing a database password in the file after the first start does not change the database; use `ALTER ROLE` as well. To rotate the signing key, change `SECRET_KEY` and run `up -d`; every session ends.

## 5. Security settings in force

| Control | Setting |
|---|---|
| HTTPS | Caddy, public certificate (S15), HSTS one year, HTTP redirected |
| Cookies | `__Secure-` session cookie (HttpOnly, Secure, SameSite=Strict, Path=/api) and `__Host-` CSRF cookie |
| CSRF and origin | Every change needs the CSRF token and an `Origin` equal to `FINGUARD_PUBLIC_ORIGIN` |
| Proxy trust (S14) | `TRUSTED_PROXY_IPS=172.30.240.10`; production refuses to start without a trusted proxy, and refuses entries such as `0.0.0.0/0` |
| API documentation (S13) | Off: `/docs`, `/redoc` and `/openapi.json` do not exist in production, and cannot be turned on there. The contract is [API_DOCUMENTATION.md](API_DOCUMENTATION.md) and `frontend/openapi.json` |
| Headers | CSP for the interface (same as the browser tests), `default-src 'none'` for the API, `nosniff`, no referrer, no `Server` header |
| Compression | Static files only; API responses are never compressed (BREACH) |
| Rate limits | Stored in PostgreSQL, shared by all processes; production refuses the per-process store |
| Database | No published port; SCRAM; non-superuser role; separate network |

## 6. Local rehearsal (what was verified)

Run on Windows 11 with Docker Desktop, on 2026-11-15, from a **fresh clone**. The model file was copied in as in section 3, images were built with `--no-cache`, and volumes were new:

```bash
python scripts/generate_production_env.py --domain 127.0.0.1 --tls internal     --http-port 9080 --https-port 9443 --bind-address 127.0.0.1 --output <outside the repo>/env.production
docker compose -f docker-compose.prod.yml --env-file <...>/env.production build --no-cache
docker compose -f docker-compose.prod.yml --env-file <...>/env.production up -d --wait
docker exec -e FINGUARD_ADMIN_PASSWORD=... finguard-prod-api-1 python -m app.commands.create_admin --email admin@finguard.example
docker cp finguard-prod-web-1:/data/caddy/pki/authorities/local/root.crt <...>/root.crt
python scripts/verify_deployment.py --origin https://127.0.0.1:9443 --ca-file <...>/root.crt --email admin@finguard.example --write
```

| Check | Result |
|---|---|
| Without the model file (first attempt, before the folder was created) | The API refused to start; `up --wait` failed |
| Build without cache and start | All services healthy 20 s after `up`; API image 979 MB, web image 92.7 MB |
| Database state | Migration 0004; databases `postgres` and `finguard` only (no test database); `finguard_app` is not a superuser and cannot create databases; no API or database port published |
| `verify_deployment.py --write` | 26 of 26 checks passed, with the certificate verified against Caddy's root (not skipped) |
| The README demonstration, in Chromium | 13 of 13 steps passed: dashboard, flagged and unflagged scoring, a 40-row batch, the explorer, an investigation reviewed, noted and closed, model pages showing the 0.282% false positive rate, a report download, a new analyst who can view but not change |
| Documentation routes, asked of the API inside its container | 404 for `/docs`, `/redoc`, `/openapi.json` |
| API process killed with SIGKILL (outside Docker, as a crash) | Restarted by its restart policy, healthy again, every check passed |
| Caddy restarted | Every check passed |
| Database stopped while the API ran | Sign-in answered 503 with `Retry-After: 5`; `/health` stayed up; after the database returned, every check passed without restarting the API |
| Every container restarted at once (a host restart) | Every check passed |
| Full stop (`down`) and start | Transactions, predictions, investigations, users and batches identical |
| Backup, data loss, restore (section 4 commands) | 89 transactions and all dependent rows truncated, then restored with identical counts in every table and the same table owner; every check passed after an API restart |
| Logs of all four services | No signing key, database password or administrator password; no tracebacks |
| Request body over 11 MB, chunked, signed in | 413 from Caddy; a 9 MB file reached the API, which applied its own row limit |

Two defects were found and fixed by this rehearsal: the backup commands lacked the database password (the database uses SCRAM on its local socket too), and the model step did not say that the folder must be created in a fresh clone.

On a non-default HTTPS port such as 9443, Caddy's automatic HTTP redirect omits the port. An explicit HTTP site fixed that, but it turned off automatic HTTPS on the HTTP port, which certificate challenges use, so it was reverted. Production uses 80 and 443, where this does not arise.

## 7. Not verified

- **A public host and certificate.** Obtaining and renewing a public certificate needs a reachable DNS name; it was not done. Caddy's ACME handling is standard, but it is untested here.
- **A managed database.** The configuration runs PostgreSQL in a container. A managed service would replace the `db` service and `DATABASE_URL`, with the same requirements: SCRAM, a non-superuser role, and no public access.
- **Platform hosts** (Render, Railway, Netlify, Vercel). The single-host Compose deployment was chosen because it keeps the same-origin rule (ADR 0004) and the batch queue without platform-specific settings. On a platform, the API image and the Caddyfile rules still apply, and `TRUSTED_PROXY_IPS` must list the platform's proxies.
- **Load beyond the Phase 5 measurements.** See [docs/performance/](docs/performance/phase-5-baseline.md).

## 8. Image size

The API image went from 1.92 GB to 979 MB in Phase 6:
- NVIDIA NCCL (469 MB) is no longer installed. XGBoost's Linux wheel requires it, but it serves only multi-GPU training, and a `uv` override removes it.
- uv is used in a build stage only.

XGBoost stays at 3.2.0 and scikit-learn at 1.9.1, the versions the model was saved with. A fixed grid of 550 synthetic inputs gave byte-for-byte identical scores and explanations in both images.

The remaining size is mostly XGBoost's own library (227 MB, built with GPU support), SciPy, pandas and NumPy. The `xgboost-cpu` package, built without GPU support, would make XGBoost's part smaller; the saving was not measured. It was not used, because start-up checks the installed `xgboost` package version against the model's metadata, and changing that check is not worth the saving.
