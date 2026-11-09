# playwright.prodlike.config.ts

Source: [frontend/playwright.prodlike.config.ts](playwright.prodlike.config.ts)

## A. File Purpose
Configures the browser tests against the production-like HTTPS stack.

## B. Why This File Exists
The HTTPS path through Caddy needs its own address, certificate handling and seeding, separate from the main browser tests.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `tests/prodlike/`.
- **External services / database:** https://127.0.0.1:8443.
- **Depended on by:** `npm run test:prodlike`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Global setup reseeds `finguard_prodlike_test`, then the specs run in desktop Chromium.

## G. Input and Output
Output: list reporter results; failure screenshots only.

## H. Important Technical Concepts
- **`ignoreHTTPSErrors`:** Caddy's local certificate is not trusted by the test browser; cookies, HSTS and every other behaviour still work as under HTTPS.
- **No web server:** Caddy serves the built frontend.

## I. Example
```powershell
npm run test:prodlike
```

## J. Maintenance Notes
Start the stack first with `scripts/prodlike_stack.py up`.

## K. Related Files
- [production.spec.ts](tests/prodlike/production.spec.ts.explanation.md): the tests.
