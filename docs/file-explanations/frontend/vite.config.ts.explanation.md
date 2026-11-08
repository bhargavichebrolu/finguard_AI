# vite.config.ts

Source: [frontend/vite.config.ts](../../../frontend/vite.config.ts)

## A. File Purpose
Configures the Vite development and preview servers: the React plugin, the `/api` proxy and the preview build's security headers.

## B. Why This File Exists
The web app calls the API on its own origin, so session cookies stay first-party (ADR 0004). These servers forward `/api` and `/health` to the backend. The preview server also serves the production Content Security Policy, which the browser tests check.

## C. Dependencies
- **Libraries:** Vite, `@vitejs/plugin-react`.
- **Internal modules:** none.
- **External services / database:** the API, at `FINGUARD_API_PROXY_TARGET`, default `http://127.0.0.1:8010`.
- **Depended on by:** `npm run dev`, `npm run build`, `npm run preview`, Playwright.

## D. Every Function Explained
No functions. `CONTENT_SECURITY_POLICY` is exported for the browser tests.

## E. Classes Explained
None.

## F. Execution Flow
Vite reads the file when a server or build starts.

## G. Input and Output
Input: the environment. Output: servers on ports 5173 (development) and 4173 (preview).

## H. Important Technical Concepts
- **The policy:** `default-src 'self'`, with no inline scripts or styles, `connect-src 'self'` because the API is same-origin, `frame-ancestors 'none'` and `object-src 'none'`.
- **The development server has no policy,** because hot reloading injects inline code. The policy is verified on the preview build, which is what deployment serves.
- **`changeOrigin: false`** keeps the browser's `Origin` header, which the API checks on cookie requests.
- **`host: "127.0.0.1"`:** on Windows, Vite's default `localhost` bound only the IPv6 address `[::1]`, so requests to `127.0.0.1` found nothing. This was found while verifying the preview server.

## I. Example
```powershell
$env:FINGUARD_API_PROXY_TARGET = "http://127.0.0.1:8011"; npm run preview
```

## J. Maintenance Notes
Phase 6 must set the same headers and `/api` rewrite on the chosen host.

## K. Related Files
- [vitest.config.ts](../../../frontend/vitest.config.ts.explanation.md): unit test settings.
- [ADR 0004](../../decisions/0004-phase-4-decisions.md): the same-origin decision.
