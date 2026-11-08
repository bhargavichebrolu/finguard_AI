# vitest.config.ts

Source: [frontend/vitest.config.ts](vitest.config.ts)

## A. File Purpose
Configures the unit and component tests.

## B. Why This File Exists
Tests run in jsdom, with a shared setup file and the mock API. They are kept apart from the browser tests, which run against the real API.

## C. Dependencies
- **Libraries:** Vitest, `@vitejs/plugin-react`.
- **Internal modules:** `tests/unit/setup.ts`.
- **External services / database:** none.
- **Depended on by:** `npm test`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Vitest loads this, runs the setup file, then the matching test files.

## G. Input and Output
Input: `tests/unit/**/*.test.ts(x)`. Output: test results.

## H. Important Technical Concepts
- **Separate from `vite.config.ts`:** Vite 8's types do not include a `test` section, so tests have their own file.
- **`css: false`:** styles are not processed in tests, which keeps them fast. Layout is checked in the browser tests instead.

## I. Example
```powershell
npm test
```

## J. Maintenance Notes
Browser tests are under `tests/e2e` and run with Playwright, not Vitest.

## K. Related Files
- [setup.ts](tests/unit/setup.ts.explanation.md): shared setup.
