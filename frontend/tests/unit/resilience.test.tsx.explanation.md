# resilience.test.tsx

Source: [frontend/tests/unit/resilience.test.tsx](resilience.test.tsx)

## A. File Purpose
Unit tests of the interface when the API is slow, unreachable or failing, and when a page fails while shown.

## B. Why This File Exists
Phase 5 M7 asked for the frontend's behaviour on unavailable, slow and failing APIs to be tested, with messages that are actionable and reveal nothing internal.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, MSW, axios.
- **Internal modules:** `ErrorBoundary`, `services/api`, `render.tsx`, `server.ts`.
- **External services / database:** None: MSW answers.
- **Depended on by:** `npm test`.

## D. Every Function Explained

### `failure`
Awaits a request expected to fail and returns its `ApiError`.

### `timedOut`
Builds the `AxiosError` axios raises when its timeout passes (code `ECONNABORTED`).

### `Throws`
A component that throws the error it is given.

### `Missing`
A lazy component whose import rejects as a failed download does.

### `reload`
A spy standing in for reloading the page.

## E. Classes Explained
None.

## F. Execution Flow
Each test arranges an answer (or none) with MSW, makes the request or renders the app, and checks what the user would see.

## G. Input and Output
| Test | Proves |
|---|---|
| says a slow request timed out | A timeout has its own message; for a change, the may-have-saved warning |
| keeps a slow answer that arrives within the timeout | Slow is not failure |
| warns that a change with no answer may still have been saved | Unsafe methods with no answer |
| gives a read with no answer no such warning, nor a failed sign-in | No false warning |
| shows the API's own message for a database outage | 503 detail and reference reach the user |
| explains a proxy's bad-gateway answer | 502 gets a plain message; the proxy's HTML is not shown |
| does not send a signed-in user to the sign-in page, and recovers on Try again | Start-up with a 503 shows "unavailable", then continues |
| treats no answer at all the same way | Start-up with no answer |
| offers a reload when a page's code could not be downloaded | The boundary's prompt and button |
| gives any other error a general message without its text | Nothing internal shown |
| recognises how each browser reports a failed page download | Chromium, Firefox and WebKit wording |

## H. Important Technical Concepts
- **Timeouts:** MSW's interception in jsdom does not enforce XHR timeouts, so the timeout test builds the error axios documents; the real path is covered by the message mapping it tests.

## I. Example
```powershell
npm test -- tests/unit/resilience.test.tsx
```

## J. Maintenance Notes
Add a case here for every new message the client can show.

## K. Related Files
- [api.ts](../../src/services/api.ts.explanation.md): the client.
- [ErrorBoundary.tsx](../../src/components/ErrorBoundary.tsx.explanation.md): the boundary.
