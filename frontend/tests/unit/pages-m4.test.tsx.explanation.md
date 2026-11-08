# pages-m4.test.tsx

Source: [frontend/tests/unit/pages-m4.test.tsx](pages-m4.test.tsx)

## A. File Purpose
Tests CSV Batch Analysis and the Transaction Explorer against the mock API.

## B. Why This File Exists
PRD 14.3 requires tests of upload validation, filtering, loading and error states.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker.
- **Internal modules:** the pages, `fixtures.ts`, `server.ts`, `render.tsx`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `page`
Wraps rows in the API's paging shape.

### `csv`
Builds a CSV `File` for upload tests.

## E. Classes Explained
None.

## F. Execution Flow
Each test sets mock responses, renders a page, then acts and checks.

## G. Input and Output
| Test | Proves |
|---|---|
| checks type, emptiness and size against the API's limit | Client file checks. |
| refuses an oversized file without uploading it | No request is sent. |
| uploads, follows processing to the end, and shows counts, ignored columns and results | Upload, polling through PROCESSING to finished, counts, `isFraud` reported as ignored, results and downloads. |
| downloads the error report through the signed-in client | Downloads use the authenticated client. |
| shows the API's refusal of a bad file | API messages. |
| shows a failed job's message | Failure state. |
| turns filters into API parameters and leaves blanks out | Query building. |
| sends the chosen filters to the API and shows matching rows | The real request carries the filters. |
| pages through results | Paging. |
| shows an empty state when nothing matches | Empty state. |
| opens the full detail with investigation history, notes and explanation | PRD 6.6 fields and the link onward. |

## H. Important Technical Concepts
- **Browser download functions are stubbed,** because jsdom has no `URL.createObjectURL`.

## I. Example
```powershell
npm test -- pages-m4
```

## J. Maintenance Notes
Polling tests wait up to three seconds for the second poll.

## K. Related Files
- [fixtures.ts](fixtures.ts.explanation.md): data.
