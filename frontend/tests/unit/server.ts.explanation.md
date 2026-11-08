# server.ts

Source: [frontend/tests/unit/server.ts](server.ts)

## A. File Purpose
A mock API for component tests, answering the real API paths with fixtures.

## B. Why This File Exists
Component tests need fast, repeatable responses, including errors, without a running backend. The browser tests use the real backend instead.

## C. Dependencies
- **Libraries:** Mock Service Worker (`msw`).
- **Internal modules:** `fixtures.ts`.
- **External services / database:** none.
- **Depended on by:** `setup.ts`, tests.

## D. Every Function Explained

### `errorBody`
Returns a JSON error in the API's format, with `detail` and `request_id`, and a status.

### `body`
A local value in the sign-in handler, not a function: the parsed JSON request. Only the fixture password signs in.

## E. Classes Explained
None.

## F. Execution Flow
`setup.ts` starts the server. Tests override handlers with `server.use(...)`.

## G. Input and Output
Input: requests from the client. Output: mock responses.

## H. Important Technical Concepts
- **`state`** lets a test change the signed-in role or sign the user out.
- **Unhandled requests fail the test,** so a page calling an unexpected route is noticed.

## I. Example
```ts
server.use(http.get("/api/v1/system/status", () => errorBody("Internal server error.", 500)));
```

## J. Maintenance Notes
Add a handler for each new route a page calls.

## K. Related Files
- [setup.ts](setup.ts.explanation.md): starts it.
- [fixtures.ts](fixtures.ts.explanation.md): the data.
