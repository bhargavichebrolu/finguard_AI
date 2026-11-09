# support.ts

Source: [frontend/tests/e2e/support.ts](support.ts)

## A. File Purpose
Shared helpers for the browser tests: seeded accounts, saved sessions, API calls with the CSRF header, the test-database script, a problem watcher, and known inputs.

## B. Why This File Exists
Every spec needs the same careful handling of credentials and CSRF, so it lives in one place.

## C. Dependencies
- **Libraries:** Node `child_process`, `fs`, `path`, `url`; Playwright Test.
- **Internal modules:** `scripts/e2e_database.py`.
- **External services / database:** The test API through the preview server.
- **Depended on by:** Every spec and the setup files.

## D. Every Function Explained

### `account`
Returns a seeded account (email, password, role) from the Git-ignored `.e2e/accounts.json`. Passwords are never printed.

### `statePath`
Where the setup project saves a role's signed-in browser state.

### `repoBytes`
Reads a repository file as bytes, and refuses anything under `data/`, so no test can read the dataset.

### `repoFile`
Reads a repository file as text, through `repoBytes`.

### `pythonPath`
The backend virtual environment's Python, or `FINGUARD_PYTHON` if set.

### `runDatabaseScript`
Runs `scripts/e2e_database.py` with `-I`, which refuses any database not named *_test.

### `changeHeaders`
Returns the `X-CSRF-Token` header (read from the `finguard_csrf` cookie) and the allowed `Origin`, as the interface sends them.

### `csrf`
A local value in `changeHeaders`, not a function: the CSRF cookie.

### `apiCall`
Calls the API with the page's own session cookie, adding the change headers for anything but GET.

### `signInThroughForm`
Signs in through the real form and waits for the Sign out button.

### `startSession`
Starts a session through `POST /api/v1/auth/session` with the allowed origin, returning the response.

### `watchForProblems`
Collects Content Security Policy violations (reported through a `securitypolicyviolation` listener), uncaught errors and console errors. Tests that provoke failing responses on purpose can allow "Failed to load resource" messages.

### `uniqueId`
A valid, unique transaction identifier for this run.

### `predictThroughApi`
Scores one transaction through the API and returns the stored prediction, checking it was created.

### `restartApiContainer`
Restarts the browser-test API container gracefully with `docker restart`, as a deploy would. Needs the Docker CLI on `PATH`; the container keeps its environment, so sessions stay valid.

### `signInWith`
Signs in through the form with an email and password given directly, for accounts a test created itself.

### `createAccount`
- **Purpose:** create a fresh account through the administrator API.
- **Parameters / types:** `browser`, optional `role` (default analyst). **Returns / type:** `Account` with a generated email and password.
- **Why:** tests that use an account up (changing its password, deactivating it) need one per run of each browser project. With Firefox and WebKit added, the seeded accounts were used up by the first engine (Phase 5 M6).
- **Error handling:** fails unless the API answers 201.

## E. Classes Explained
### `Account, Problems, StoredPrediction`
Interfaces describing a seeded account, the problem list and the prediction fields the tests read.

## F. Execution Flow
Imported by the specs.

## G. Input and Output
Input: the accounts file and the running stack. Output: helpers.

## H. Important Technical Concepts
- **`FLAGGED_INPUT` and `UNFLAGGED_INPUT`** were found by scoring through the test API: CASH_OUT 5,000,000 at step 50 is flagged High, and TRANSFER 1,000,000 at step 400 is not flagged. Tests read the score from the API rather than hard-coding it.
- **`NO_SESSION`** is an empty browser state for tests that start signed out.
- **Cookie paths:** the session cookie is scoped to `/api`, so it is read with an `/api` URL; the CSRF cookie is on `/`.

## I. Example
```ts
const stored = await predictThroughApi(page, FLAGGED_INPUT);
```

## J. Maintenance Notes
Never log `account(...).password`. Keep `repoBytes` refusing `data/`.

## K. Related Files
- [e2e_database.py](../../../scripts/e2e_database.py.explanation.md): the database script.
