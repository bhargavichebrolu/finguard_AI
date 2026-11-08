# foundation.test.tsx

Source: [frontend/tests/unit/foundation.test.tsx](foundation.test.tsx)

## A. File Purpose
Tests formatting rules, the score disclosure, shared error and confirmation states, and the System Information page.

## B. Why This File Exists
PRD 14.3 requires tests of navigation, API communication, loading and error states. The authorisation's cookie and wording rules need proof too.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker.
- **Internal modules:** the modules under test, `server.ts`, `fixtures.ts`, `render.tsx`.
- **External services / database:** none. The mock API answers.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Each test renders or calls code against the mock API, then checks the result.

## G. Input and Output
| Test | Proves |
|---|---|
| writes model scores as plain numbers, never as percentages | The central wording rule. |
| labels the risk score as not a percentage | Risk score wording. |
| writes measured rates as percentages | Rates are formatted correctly. |
| describes decisions without claiming fraud | Decision wording. |
| states what a score is and shows the API's measured limitations | The disclosure renders the API's notes. |
| warns when the limitations cannot be loaded | A failure is not hidden. |
| shows an error with its reference and a retry | The error state. |
| asks before acting and backs out on Escape | Confirmation, with focus on Cancel. |
| shows live service and frozen model details | The System Information page. |
| shows an error state when the status cannot load | Its error state. |

## H. Important Technical Concepts
- **Queries by role and label** test what users and assistive technology see, not implementation details.

## I. Example
```powershell
npm test
```

## J. Maintenance Notes
Add a test with each new behaviour, including its error case.

## K. Related Files
- [server.ts](server.ts.explanation.md): the mock API.
