# resilience.spec.ts

Source: [frontend/tests/e2e/resilience.spec.ts](resilience.spec.ts)

## A. File Purpose
Browser tests of the interface against a real API that is slow, stopped, restarted or without its database, and against a page whose code cannot be downloaded.

## B. Why This File Exists
Phase 5 M7: frontend behaviour on API outages, session expiry during a task, database loss and recovery, report download failures and duplicate submissions, all on the real stack.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`: `stopApiContainer`, `startApiContainer`, `restartApiContainer`, `waitForApi`, `setDatabaseAvailable`, `createAccount`, `signInWith`, `runDatabaseScript`.
- **External services / database:** The browser-test API container, PostgreSQL (`finguard_e2e_test`), Docker.
- **Depended on by:** `npm run test:e2e` (desktop, Firefox and WebKit projects).

## D. Every Function Explained

### `expectSafeAlert`
Waits for an alert with the given text and a `Reference:`, and checks its text matches nothing in `INTERNALS`.

### `fillScoringForm`
Fills the Transaction Analysis form with a fixed valid transaction and an identifier.

### `ensureATransaction`
Stores one transaction through the API, so the explorer shows a table whatever ran before; without it two tests depended on test order.

### `storedCount`
Counts stored transactions whose identifier contains the given text.

### `totalBefore`
Inside the double-press test: the number of stored transactions before.

### `totalAfter`
The number after, once the network is quiet.

## E. Classes Explained
None.

## F. Execution Flow
Each test causes a real fault (or injects a network one), checks what the user sees, ends the fault in a `finally` block, and checks recovery without signing in again or restarting anything.

## G. Input and Output
| Test | Proves |
|---|---|
| a page whose code fails to download offers a reload, and the frame stays usable | F7: the prompt, navigation still works, Reload recovers |
| a slow answer shows the loading state, then the page | A 2-second delay shows Loading, then content, no error |
| a request with no answer says so, and Try again recovers | Dropped connection: plain message, retry works |
| while the API is stopped the app says it is unavailable, not signed out, and continues after | Real stop and start; same session afterwards |
| a session survives an API restart in the middle of a task | Form filled, API restarted, submit stores once |
| a database outage gives an actionable message, keeps the session, and recovers without a restart | Report download and explorer show the 503 message with a reference; no file; still signed in; works again after |
| returns to the same page after signing in again, and stores nothing meanwhile | Session expired on the server mid-form: sign-in notice, back to the form, nothing stored |
| pressing Score twice stores one transaction | One request, one record |

## H. Important Technical Concepts
- **Real outages:** the API container is really stopped or restarted, and the database really refuses connections (`e2e_stack.py database off`), for the browser-test database only.
- **Injected faults:** a failed chunk download, a delayed response and a reset connection cannot be produced on demand otherwise, so `page.route` injects them; the API behind them is real.
- **`INTERNALS`:** words an error shown to users must not contain.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/resilience.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
Always end an outage in `finally`. If a run is stopped mid-outage, `python scripts/e2e_stack.py database on` (or `up`) ends it.

## K. Related Files
- [support.ts](support.ts.explanation.md): the outage helpers.
- [e2e_stack.py](../../../scripts/e2e_stack.py.explanation.md): the database switch.
