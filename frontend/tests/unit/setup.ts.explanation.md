# setup.ts

Source: [frontend/tests/unit/setup.ts](setup.ts)

## A. File Purpose
Runs before each unit test file. It adds DOM matchers, starts the mock API and resets state between tests.

## B. Why This File Exists
Every test should start from the same clean state.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `@testing-library/jest-dom`.
- **Internal modules:** `server.ts`.
- **External services / database:** none.
- **Depended on by:** `vitest.config.ts`.

## D. Every Function Explained

No functions.

## E. Classes Explained
### `TestResizeObserver`
A do-nothing stand-in for `ResizeObserver`, which jsdom lacks and Recharts' responsive container needs. It is installed only when missing, and only in unit tests. Browsers provide the real one, and the Playwright tests check chart rendering.
None.

## F. Execution Flow
Start the server before all tests. After each test, clean up, reset handlers, restore the analyst role and clear the CSRF cookie. Close the server at the end.

## G. Input and Output
None.

## H. Important Technical Concepts
- **Async wait of 5 seconds (Phase 5 M1):** pages load lazily, and on a cold start (a fresh clone or CI) compiling a page the first time took longer than Testing Library's one-second default, so the first test in three files failed there. Waiting longer changes no assertion.
- **`onUnhandledRequest: "error"`** makes unexpected API calls fail loudly.

## I. Example
```ts
setupFiles: ["./tests/unit/setup.ts"]
```

## J. Maintenance Notes
Reset any new shared state here.

## K. Related Files
- [vitest.config.ts](../../vitest.config.ts.explanation.md): loads this.
