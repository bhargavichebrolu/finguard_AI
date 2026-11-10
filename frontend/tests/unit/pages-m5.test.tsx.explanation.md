# pages-m5.test.tsx

Source: [frontend/tests/unit/pages-m5.test.tsx](pages-m5.test.tsx)

## A. File Purpose
Tests the Investigation Centre against a stateful mock API.

## B. Why This File Exists
PRD 14.2 and 14.3 require investigation update and error tests, and PRD 7.5 requires confirmation of significant actions.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker.
- **Internal modules:** the page, `fixtures.ts`, `server.ts`, `render.tsx`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `openCase`
Renders the centre, opens the first case and returns its panel.

### `change`
A local value in the PATCH handler, not a function: the parsed change, which updates the mock case.

## E. Classes Explained
None.

## F. Execution Flow
The mock API keeps a case in memory, so changes, history and notes behave as they would on the server.

## G. Input and Output
| Test | Proves |
|---|---|
| lists the queue with the workflow statement | Queue and wording. |
| filters by status and by assignment to me | Filters reach the API. |
| opens a case directly from a link | `?open=` works. |
| changes status without confirmation when the review continues | Status change and history. |
| asks before closing a case, and does nothing if cancelled | Confirmation for false alarm, and cancel sends nothing. |
| adds a trimmed note and shows it | Notes. |
| assigns to me, to a colleague and to nobody | Assignment through the restricted list. |
| shows the API's refusal of an action | Errors. |
| is read-only for analysts | No controls without permission. |
| is not available to demo users | Permission guard. |

## H. Important Technical Concepts
- **Expected status (Phase 5 M7):** status changes now carry `expected_status`, the status shown when the change was made, so the expected PATCH bodies include it.
- **Stateful mock:** each PATCH updates the in-memory case and appends history, as the API does.

## I. Example
```powershell
npm test -- pages-m5
```

## J. Maintenance Notes
Add a test when a new action is added.

## K. Related Files
- [server.ts](server.ts.explanation.md): the base mock API.
