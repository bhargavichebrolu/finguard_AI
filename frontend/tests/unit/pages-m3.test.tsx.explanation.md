# pages-m3.test.tsx

Source: [frontend/tests/unit/pages-m3.test.tsx](pages-m3.test.tsx)

## A. File Purpose
Tests the Dashboard, Transaction Analysis and Explainable AI pages against the mock API.

## B. Why This File Exists
PRD 14.3 requires dashboard rendering, prediction results, loading and error states. The authorisation's wording and disclosure rules need checking on these pages too.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker.
- **Internal modules:** the pages, `fixtures.ts`, `server.ts`, `render.tsx`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `useSummary`
Makes the mock API return a chosen summary. Despite the name it is a test helper, not a React hook.

### `fillAndSubmit`
Types an amount, chooses a type, types a step and submits the form.

## E. Classes Explained
None.

## F. Execution Flow
Each test sets mock responses, renders a page and checks what is shown or sent.

## G. Input and Output
| Test | Proves |
|---|---|
| shows the three kinds of information in separate sections, with API figures | PRD 6.1 separation, and figures from the API. |
| shows the disclosure from the API on the dashboard | Limitations are shown. |
| shows the model performance summary from the metrics response | Saved figures, with the target. |
| offers each chart as a table | Table view and `aria-pressed`. |
| explains an empty scope instead of drawing empty charts | Empty states. |
| labels demo statistics as demo | PRD 7.6. |
| shows an error state when the summary cannot load | Error state. |
| ties the destination to the type, as in PaySim | Combination rule. |
| validates amount, step and identifier before sending | Client checks. |
| sends exactly the four inputs and shows the result with its explanation | No extra fields, no percent sign on scores, the causality warning shown. |
| sends merchant for PAYMENT | Combination sent correctly. |
| shows field errors without calling the API | Invalid input is stopped. |
| shows the API's message for a repeated identifier | 409 handling. |
| is not offered to roles without the predict permission | Permission guard. |
| shows saved importance with its limits, and explains a chosen prediction | Explainable AI. |
| says so when a prediction has no stored explanation | Missing explanation. |

## H. Important Technical Concepts
- **`tile` and `card`** are local values in tests, not functions: the stat tile found by its label, and the card holding a heading.

## I. Example
```powershell
npm test -- pages-m3
```

## J. Maintenance Notes
Add tests for new sections with their empty and error cases.

## K. Related Files
- [fixtures.ts](fixtures.ts.explanation.md): data.
