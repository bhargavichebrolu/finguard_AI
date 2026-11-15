# pages.perf.ts

Source: [frontend/tests/perf/pages.perf.ts](pages.perf.ts)

## A. File Purpose
Times every page from navigation start until it is usable, cold and warm, and writes the figures to JSON.

## B. Why This File Exists
Phase 5 M2 asks for measured page navigation timings, taken against a realistic data volume.

## C. Dependencies
- **Libraries:** Playwright Test, Node `fs`, `path`, `url`.
- **Internal modules:** none.
- **External services / database:** The preview server and browser-test API.
- **Depended on by:** `playwright.perf.config.ts`.

## D. Every Function Explained

### `signedInState`
Signs in once as the seeded administrator through the form and saves the state. The password is read from the Git-ignored accounts file and never logged.

### `measure`
Opens a page, waits for its level-one heading and for no loading state, then reads `performance.now()`, the navigation entry and transferred bytes.

### `median`
The median of a list.

## E. Classes Explained
### `Sample`
An interface: ready time, DOMContentLoaded time and transferred bytes for one load.

## F. Execution Flow
For each page: 3 cold loads in new contexts, one cache-filling load, then 5 warm loads.

## G. Input and Output
Output: medians and maxima per page.

## H. Important Technical Concepts
- **Ready** means the heading is visible and no loading status remains, which is what a person waits for in this client-rendered app.

## I. Example
```powershell
npm run perf:pages
```

## J. Maintenance Notes
Keep `PAGES` equal to the registry.

## K. Related Files
- [measure_performance.py](../../../scripts/measure_performance.py.explanation.md): renders the results.
