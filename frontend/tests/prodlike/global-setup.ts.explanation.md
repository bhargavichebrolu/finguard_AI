# global-setup.ts

Source: [frontend/tests/prodlike/global-setup.ts](global-setup.ts)

## A. File Purpose
Before the production-like tests: checks the HTTPS site answers, reseeds its database, and proves the API behind Caddy reads it.

## B. Why This File Exists
As for the main browser tests: tests must start from known data in a test database and never run against the wrong one.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `prodlike.ts`, `../e2e/support.ts` (`runDatabaseScript`).
- **External services / database:** The production-like stack.
- **Depended on by:** `playwright.prodlike.config.ts`.

## D. Every Function Explained

### `globalSetup`
Health check over HTTPS, `e2e_database.py seed` with `E2E_DB_NAME=finguard_prodlike_test`, then a sign-in with the freshly generated administrator password.

## E. Classes Explained
None.

## F. Execution Flow
Health, seed, proof.

## G. Input and Output
Output: `.e2e/prodlike-accounts.json` (Git-ignored).

## H. Important Technical Concepts
- **Fails closed:** if the proof fails, no test runs.

## I. Example
```powershell
npm run test:prodlike
```

## J. Maintenance Notes
Keep the proof step.

## K. Related Files
- [prodlike.ts](prodlike.ts.explanation.md): shared values.
