# playwright.perf.config.ts

Source: [frontend/playwright.perf.config.ts](playwright.perf.config.ts)

## A. File Purpose
Configures the page-timing measurement, separate from the browser tests.

## B. Why This File Exists
Page timings must be taken with the measured data volume in place, so this configuration has no global setup and never reseeds the database.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `tests/perf/`.
- **External services / database:** The browser-test API on 127.0.0.1:8011.
- **Depended on by:** `npm run perf:pages`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Build and serve the app with the production Content Security Policy, then run `tests/perf/*.perf.ts`.

## G. Input and Output
Output: `docs/performance/phase-5-pages.json`, or `FINGUARD_PERF_OUT`.

## H. Important Technical Concepts
- **Desktop Chromium at 1440 x 900**, one worker, traces and video off.

## I. Example
```powershell
npm run perf:pages
```

## J. Maintenance Notes
Run it after `measure_performance.py run`, against the same stack.

## K. Related Files
- [pages.perf.ts](tests/perf/pages.perf.ts.explanation.md): the measurement.
