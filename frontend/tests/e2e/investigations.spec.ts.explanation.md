# investigations.spec.ts

Source: [frontend/tests/e2e/investigations.spec.ts](investigations.spec.ts)

## A. File Purpose
Tests the investigation workflow against the real API: queue filters, assignment, status changes with confirmation, notes, history, and concurrent updates.

## B. Why This File Exists
PRD 6.7 and PRD 7.5 require status updates, notes, history and confirmation before concluding. The brief also requires that concurrent updates do not corrupt event ordering.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `openNewCase`
Creates a flagged prediction and returns its investigation.

### `panel`
The open investigation region.

### `me`
The signed-in user, from `/auth/me`.

### `analystId`
The analyst's id, read in a separate signed-in context.

### `id`
A local value, not a function: the analyst's id inside `analystId`.

### `detail`
A local value, not a function: the case read back after the concurrent updates.

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| filters the queue by status and by assignment | Status filter and "Assigned to me". |
| assigns a case to a colleague, to me and to nobody | Assignment persists; only investigators and administrators are offered, and the API refuses an analyst. |
| changes status, asks before concluding, and keeps the history | No dialog for Under review; dialogs for Closed and False alarm; Cancel and Escape change nothing; history in order after reload. |
| adds trimmed notes that persist | Blank notes blocked, trimming, counter, reload. |
| keeps history in order under concurrent updates from two people | 8 status changes and 8 notes sent at once by two users: every history entry starts where the previous ended, times never go backwards, the last entry matches the status, all notes kept. |

## H. Important Technical Concepts
- **Why ordering holds:** the service locks the investigation row and stamps entries with `clock_timestamp()` after taking the lock (`investigation_service.py`).

## I. Example
```powershell
npm run test:e2e -- tests/e2e/investigations.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
If statuses change, update the confirmation labels.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [investigation_service.py](../../../backend/app/services/investigation_service.py.explanation.md): locking and history.
