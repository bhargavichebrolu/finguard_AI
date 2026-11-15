# production.spec.ts

Source: [frontend/tests/prodlike/production.spec.ts](production.spec.ts)

## A. File Purpose
Tests the complete HTTPS path through Caddy with production settings.

## B. Why This File Exists
The approval required HTTPS through Caddy to be tested end to end: cookie flags and prefixes, CSRF, CORS, proxy forwarding and trusted-proxy restrictions, never trusting arbitrary forwarded headers.

## C. Dependencies
- **Libraries:** Playwright Test, Node `child_process`.
- **Internal modules:** `prodlike.ts`, `../e2e/support.ts`, `../../vite.config.ts`.
- **External services / database:** The production-like stack; Docker (`docker inspect`).
- **Depended on by:** none; run by `npm run test:prodlike`.

## D. Every Function Explained

### `signIn`
Signs in through the form on the HTTPS site.

### `csrfToken`
Reads the `__Host-finguard_csrf` cookie.

### `post`
A local value, not a function: posts a prediction with chosen headers.

### `attempt`
A local value, not a function: one failed sign-in with a spoofed `X-Forwarded-For`.

### `preflight`
A local value, not a function: the CORS preflight response.

### `inspect`
A local value, not a function: reads a container's details with `docker inspect`.

### `cookie`
A local value in `csrfToken`, not a function: the CSRF cookie found.

## E. Classes Explained
None.

## F. Execution Flow
Each test talks to https://127.0.0.1:8443, and one also to the API directly.

## G. Input and Output
| Test | Proves |
|---|---|
| plain HTTP is redirected to HTTPS | 308 to the HTTPS address, path and query kept. |
| production serves no interactive API documentation or schema | Phase 6, S13: the API answers 404 for `/docs`, `/redoc` and `/openapi.json`; through Caddy, `/openapi.json` is the interface's page, not the schema. |
| signs in over HTTPS with Secure, prefixed cookies and production headers | HSTS, the CSP equal to Vite's, no `Server`; `__Secure-` and `__Host-` cookies with their required attributes and no plain-named cookies; a prediction through the interface; sign-out clears cookies; no CSP or page errors. |
| refuses changes without the CSRF token, from another origin, or over the wrong scheme | 403 for each; 201 when correct. |
| gives other origins no cross-origin access | No `Access-Control-Allow-Origin`. |
| spoofed forwarded addresses cannot dodge the sign-in limit, through the proxy or around it | Five failures with five invented addresses reach the limit, via Caddy and directly. |
| the API trusts forwarded headers only from the proxy's fixed address | Caddy's only address equals `TRUSTED_PROXY_IPS`; production settings in force. |

## H. Important Technical Concepts
- **`PREDICT`, `INPUT`:** the prediction address and an unflagged synthetic input.
- **Positive proxy trust** (a configured proxy's header is believed) is tested at the code level in `test_phase4_backend.py`; here the deployed configuration is checked.

## I. Example
```powershell
npm run test:prodlike
```

## J. Maintenance Notes
If a test here fails, a production security control regressed.

## K. Related Files
- [Caddyfile](../../../docker/caddy/Caddyfile.explanation.md): the proxy.
