# playwright.config.ts

Source: [frontend/playwright.config.ts](playwright.config.ts)

## A. File Purpose
Configures the browser tests: where they live, the preview server they run against, the three viewport projects and the reporting.

## B. Why This File Exists
Authorisation decision 4 requires browser tests against the real backend, with desktop, mobile and accessibility coverage. This file wires those runs to the real API rather than a mock.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `tests/e2e/global-setup.ts`, the specs.
- **External services / database:** The API at `FINGUARD_E2E_API` (default http://127.0.0.1:8011).
- **Depended on by:** `npm run test:e2e`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Global setup reseeds the test database; the web server builds the app and runs `vite preview` on 127.0.0.1:4173 with `FINGUARD_API_PROXY_TARGET` pointing at the test API; the `setup` project signs each role in; then `desktop` runs every spec, and `tablet` and `mobile` run the responsive spec.

## G. Input and Output
Input: the running test API. Output: the list reporter's results, failure screenshots in `test-results/`, and page screenshots in `.e2e/screenshots/` (both Git-ignored).

## H. Important Technical Concepts
- **Projects:** `desktop` 1440 x 900, `tablet` 768 x 1024 with touch, `mobile` 390 x 844 with touch and mobile emulation. All use Chromium.
- **One worker:** the tests share one database and some change settings others read, so they run in order.
- **No credentials in reports:** traces, video and the HTML report are off, because they record typed values, including generated passwords. Failure screenshots show password fields masked.
- **`BASE_URL`** is exported for reference; the specs use the copy in `support.ts`.
- **Production CSP:** the preview server sends the same Content Security Policy as production builds (`vite.config.ts`), so violations appear in the tests.

## I. Example
```powershell
python scripts/e2e_stack.py up
cd frontend
npm run test:e2e
```

## J. Maintenance Notes
Keep the viewport sizes equal to those the Phase 4 authorisation lists. Do not turn on traces or the HTML report without first removing typed passwords from them.

## K. Related Files
- [support.ts](tests/e2e/support.ts.explanation.md): shared helpers.
- [e2e_stack.py](../scripts/e2e_stack.py.explanation.md): starts the test API.
