# global-setup.ts

Source: [frontend/tests/e2e/global-setup.ts](global-setup.ts)

## A. File Purpose
Runs once before the browser tests: checks the test API answers, reseeds the test database, and proves the API reads that database.

## B. Why This File Exists
Tests must start from known data and must never run against development records. A freshly generated password can only work if the API on port 8011 uses the database just seeded, so a successful sign-in proves it.

## C. Dependencies
- **Libraries:** Playwright Test (`request`).
- **Internal modules:** `support.ts`, `scripts/e2e_database.py`.
- **External services / database:** The test API.
- **Depended on by:** `playwright.config.ts`.

## D. Every Function Explained

### `globalSetup`
- **Purpose:** prepare a clean, proven test environment.
- **Parameters / types:** none. **Returns / type:** `Promise<void>`.
- **Internal processing:** checks `/health`, runs the seed command, then signs in as the seeded administrator directly against the API.
- **Error handling:** throws with an instruction if the API is down or not using the seeded database. **Calls:** `runDatabaseScript`, `account`. **Used by:** Playwright.

## E. Classes Explained
None.

## F. Execution Flow
Health check, seed, sign-in proof.

## G. Input and Output
Output: `.e2e/accounts.json` and a one-line seed message.

## H. Important Technical Concepts
- **Fail closed:** if the check fails, no test runs.

## I. Example
```powershell
npx playwright test
```

## J. Maintenance Notes
Keep the proof step: it is what stops tests running against the wrong database.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
