# Caddyfile.production

Source: [docker/caddy/Caddyfile.production](Caddyfile.production)

## A. File Purpose
Configures Caddy for production: HTTPS with a public certificate obtained and renewed automatically, security headers, the interface's Content Security Policy, caching, compression of static files, the single-page fallback, and forwarding `/api` and `/health` to the API.

## B. Why This File Exists
Phase 6 deploys the same-origin shape that ADR 0004 requires and the production-like stack verified in Phase 5. Security finding S15 required a public certificate; this file obtains one from an ACME authority when `FINGUARD_TLS` is an email address.

## C. Dependencies
- **Libraries:** Caddy 2.11, from the image pinned in `docker/web/Dockerfile`.
- **Internal modules:** the built interface, copied to `/srv` by that Dockerfile.
- **External services / database:** `api:8000` on the `edge` network; an ACME authority (Let's Encrypt by default) for public certificates.
- **Depended on by:** the `web` service in `docker-compose.prod.yml`.

## D. Every Function Explained

No functions. The settings come from the environment: `FINGUARD_DOMAIN`, `FINGUARD_TLS`, `FINGUARD_HTTP_PORT` and `FINGUARD_HTTPS_PORT`.

## E. Classes Explained
None.

## F. Execution Flow
Plain HTTP redirects to HTTPS (Caddy's automatic redirect, which also answers certificate challenges). `/api/*` and `/health` go to the API uncompressed; everything else is a file from `/srv`, or `index.html` so interface routes load directly.

## G. Input and Output
Input: browser requests. Output: HTTPS responses with HSTS, `nosniff`, no referrer and no `Server` header.

## H. Important Technical Concepts
- **`tls {$FINGUARD_TLS}`:** an email address means a public certificate; `internal` means Caddy's own authority, for a local rehearsal only.
- **No compression for the API (BREACH):** `encode` is only inside the static-file handler.
- **Caching:** files under `/assets/` have content hashes in their names and are cached for a year; the page itself is `no-cache`, so a new release appears at once.
- **CSP:** must equal the production-like Caddyfile and `CONTENT_SECURITY_POLICY` in `frontend/vite.config.ts`; `test_deployment.py` compares the two Caddyfiles and `production.spec.ts` compares the live one with Vite's.
- **Redirect on other ports:** on a non-default HTTPS port, Caddy's automatic redirect omits the port. An explicit HTTP site would fix that, but turned off automatic HTTPS on the HTTP port, which certificate challenges rely on, so production keeps 80 and 443.

## I. Example
```powershell
docker build -f docker/web/Dockerfile -t finguard-web:production .
```

## J. Maintenance Notes
Change the CSP in all three places together. `admin off` keeps Caddy's admin interface closed.

## K. Related Files
- [Caddyfile](Caddyfile.explanation.md): the production-like stack.
- [docker/web/Dockerfile](../web/Dockerfile.explanation.md): builds the image containing this file.
- [docker-compose.prod.yml](../../docker-compose.prod.yml.explanation.md)
