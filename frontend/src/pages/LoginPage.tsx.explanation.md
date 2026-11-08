# LoginPage.tsx

Source: [frontend/src/pages/LoginPage.tsx](LoginPage.tsx)

## A. File Purpose
The sign-in form.

## B. Why This File Exists
Every page needs a session. The API sets HttpOnly cookies on sign-in, so this page sends credentials and never handles a token.

## C. Dependencies
- **Libraries:** React, React Router, `lucide-react`.
- **Internal modules:** `../hooks/useAuth.tsx`, `../services/api.ts`.
- **External services / database:** `POST /api/v1/auth/session`, through `signIn`.
- **Depended on by:** `App.tsx` at `/login`.

## D. Every Function Explained

### `LoginPage`
Shows the form, any notice (such as a session ending), and errors. Redirects when already signed in. `destination` is a local value, not a function: the page to return to after sign-in, taken from the router state, or `/`.

### `handleSubmit`
- **Purpose:** sign in.
- **Parameters / types:** the form event. **Returns / type:** `Promise<void>`.
- **Internal processing:** calls `signIn`, then returns to the page originally requested.
- **Error handling:** shows the API's message. A 429 shows the waiting time from `Retry-After`.
- **Calls:** `signIn`, `toApiError`. **Used by:** the form.

## E. Classes Explained
None.

## F. Execution Flow
Submit, sign in, then navigate to the saved destination.

## G. Input and Output
Input: email and password. Output: a session, or a message.

## H. Important Technical Concepts
- **`autoComplete`** hints let password managers work.
- **Research notice:** the page states up front that scores are not findings of fraud.

## I. Example
```ts
navigate(destination, { replace: true });
```

## J. Maintenance Notes
Do not add "remember me". Sessions are deliberately short.

## K. Related Files
- [useAuth.tsx](../hooks/useAuth.tsx.explanation.md): `signIn`.
- [auth.test.tsx](../../tests/unit/auth.test.tsx.explanation.md): tests.
