# Caddyfile

Source: [docker/caddy/Caddyfile](Caddyfile)

## A. File Purpose
Configures Caddy for the production-like stack: HTTPS, security headers, the frontend's Content Security Policy, the single-page fallback, and forwarding `/api` and `/health` to the API.

## B. Why This File Exists
Phase 5 M5 verifies the same-origin HTTPS deployment that ADR 0004 requires, including proxy trust. A Phase 6 host can reproduce these rules.

## C. Dependencies
- **Libraries:** Caddy 2.11 (official image, pinned by digest in `docker-compose.yml`).
- **Internal modules:** the built frontend in `frontend/dist`.
- **External services / database:** `api-prodlike:8000`.
- **Depended on by:** `caddy-prodlike` in `docker-compose.yml`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
HTTP on 8082 redirects to HTTPS on 8443; `/api/*` and `/health` go to the API; anything else is a file from `/srv`, or `index.html` so routes load directly.

## G. Input and Output
Input: browser requests. Output: HTTPS responses with HSTS, `nosniff`, no referrer and no `Server` header.

## H. Important Technical Concepts
- **`tls internal` and `local_certs`:** a certificate from Caddy's own authority, untrusted by browsers; tests ignore the certificate error, and a real host uses a public certificate.
- **`default_sni 127.0.0.1`:** clients send no server name for an IP address, so without it the handshake failed with an internal-error alert.
- **Forwarded headers:** Caddy replaces any client-sent `X-Forwarded-For` with the real address; the API trusts only Caddy's fixed address (172.30.250.10).
- **CSP:** must equal `CONTENT_SECURITY_POLICY` in `frontend/vite.config.ts`; `production.spec.ts` compares them on a live response.
- **HSTS** is one year, set here because a host's proxy, not the API, terminates HTTPS.

## I. Example
```powershell
python scripts/prodlike_stack.py up
```

## J. Maintenance Notes
Change the CSP in both places together. `admin off` keeps Caddy's admin interface closed.

## K. Related Files
- [prodlike_stack.py](../../scripts/prodlike_stack.py.explanation.md): starts it.
- [production.spec.ts](../../frontend/tests/prodlike/production.spec.ts.explanation.md): tests it.
