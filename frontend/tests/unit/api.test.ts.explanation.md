# api.test.ts

Source: [frontend/tests/unit/api.test.ts](api.test.ts)

## A. File Purpose
Tests the API client: the CSRF header, no browser storage, error normalisation, rate-limit timing, network failures and the session-ended signal.

## B. Why This File Exists
PRD 14.3 requires tests of navigation, API communication, loading and error states. The authorisation's cookie and wording rules need proof too.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`, Mock Service Worker.
- **Internal modules:** the modules under test, `server.ts`, `fixtures.ts`, `render.tsx`.
- **External services / database:** none. The mock API answers.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `captureHeaders`
Installs a handler that records the CSRF header seen by each method, and returns the record.

### `error`
A local value in two tests, not a function: the rejected value from a failed request, checked to be an `ApiError`.

## E. Classes Explained
None.

## F. Execution Flow
Each test renders or calls code against the mock API, then checks the result.

## G. Input and Output
Phase 5 M5 added a test that the prefixed CSRF cookie is preferred, read from a supplied cookie string because jsdom will not store a `__Host-` cookie on an insecure origin.

| Test | Proves |
|---|---|
| sends the CSRF cookie as a header on requests that change data | POST, PATCH and DELETE carry the token, and GET does not. |
| never reads or stores a token in browser storage | `localStorage` and `sessionStorage` are never touched. |
| turns error responses into ApiError with message, reference and field errors | The API's error format is preserved. |
| reads Retry-After on rate limits | Waiting time reaches the interface. |
| reports a network failure in plain words | Status 0, with a connection message. |
| signals a session ending on 401, except for a failed sign-in | The global sign-out fires only when it should. |
| reads cookies by exact name | A similarly named cookie is not mistaken for the CSRF cookie. |

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
