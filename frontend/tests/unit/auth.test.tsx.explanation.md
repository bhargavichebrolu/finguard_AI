# auth.test.tsx

Source: [frontend/tests/unit/auth.test.tsx](auth.test.tsx)

## A. File Purpose
Tests sign-in, session restore, sign-out, session ending, the demo banner, role-based content and navigation.

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
| restores a session from the cookie on load | Reload keeps you signed in. |
| sends a signed-out visitor to the login page | Guards redirect. |
| signs in and returns to the page that was asked for | The full sign-in flow. |
| shows the API's message for wrong credentials | Errors are shown clearly. |
| explains a rate limit with the waiting time | 429 handling. |
| signs out through the API and returns to login | Logout calls `DELETE /auth/session`. |
| returns to login with a message when the API ends the session | A 401 during use signs out. |
| shows the demo banner only to demo users | PRD 7.6 labelling. |
| does not show the demo banner to other roles | No false labelling. |
| shows the audit log only to administrators | Role-based content. |
| lists navigation entries and marks the current page | Navigation works. |
| collapses and expands the navigation | PRD 7.3 collapsible navigation, with `aria-expanded`. |
| shows a not-found page for an unknown address | Unknown routes. |

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
