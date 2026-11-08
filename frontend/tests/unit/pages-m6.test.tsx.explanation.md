# pages-m6.test.tsx

Source: [frontend/tests/unit/pages-m6.test.tsx](pages-m6.test.tsx)

## A. File Purpose
Tests Model Performance, Reports and Settings, including account management, and the full page order.

## B. Why This File Exists
PRD 14.2 requires component tests for each page, and PRD 7.5 requires confirmation of significant actions. Authorisation decision 5 is checked by showing that values come from the report response.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker, Axios.
- **Internal modules:** the pages, `registry.tsx`, `endpoints.ts`, `fixtures.ts`, `server.ts`, `render.tsx`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `body`
A local value, not a function: in the blob test, a JSON error body wrapped in a Blob; in the user handlers, the parsed request body.

### `caught`
A local value, not a function: a constructed `AxiosError` with a Blob body.

### `error`
A local value, not a function: the mapped `ApiError`.

### `unreadable`
A local value, not a function: an error whose Blob body is not JSON.

### `input`
A local value, not a function: the boundary field.

### `dialog`
A local value, not a function: the open confirmation.

### `comparison`
A local value, not a function: the model comparison table.

### `card`
A local value, not a function: the chart card under test.

### `submit`
A local value, not a function: the Create account button.

## E. Classes Explained
None.

## F. Execution Flow
Each test sets a role, replaces the handlers it needs and renders the page through the real routes.

## G. Input and Output
| Test | Proves |
|---|---|
| lists every page in PRD 7.4 order | Registry order. |
| names families and threshold rules readably | `familyName`, `ruleName`. |
| shows the saved results from the report, with the disclosure | Values come from the response; selected and tied badges; confusion counts; thresholds; sources; disclosure. |
| filters the experiment history by stage | Stage filter. |
| shows a chart as a table on request | Table view. |
| reports a failure to load the report | Error state. |
| downloads each report type from its path | One button per type and the right query. |
| shows an error when a download fails | Error state and buttons re-enabled. |
| reads the API's message out of a blob error body | `readBlobError`, including a non-JSON body. |
| is closed to the demo role | Permission guard. |
| checks the high risk boundary against the frozen threshold | `checkBoundary`. |
| shows settings read-only to an analyst | No edit or account controls. |
| lets an administrator change the boundary after confirming | Validation, confirmation and the PATCH body. |
| deactivates another account only after confirming, and never your own | Confirmation and self-protection. |
| changes a role | Role PATCH. |
| creates an account once the password is long enough | Disabled until valid, then the POST body. |

## H. Important Technical Concepts
- **Blob error bodies:** jsdom's XMLHttpRequest returns no body for blob requests, so the page test can only see the status message. `readBlobError` is therefore tested directly, and the browser tests in M7 cover the real path.

## I. Example
```powershell
npm test -- pages-m6
```

## J. Maintenance Notes
Fixture values are invented; do not copy saved Phase 2 figures into them.

## K. Related Files
- [fixtures.ts](fixtures.ts.explanation.md): `reportFixture`.
