# useAuth.tsx

Source: [frontend/src/hooks/useAuth.tsx](useAuth.tsx)

## A. File Purpose
Holds who is signed in and what they may do, and provides sign-in and sign-out.

## B. Why This File Exists
The session is in an HttpOnly cookie the page cannot read, so the interface has to ask the API whether a session exists. Permissions are taken from the API, so the interface never keeps its own copy of the role table.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `../services/api.ts`, `../services/endpoints.ts`.
- **External services / database:** `GET /auth/me`, `POST` and `DELETE /auth/session`.
- **Depended on by:** `App.tsx`, the layout, guards and pages.

## D. Every Function Explained

### `AuthProvider`
- **Purpose:** provide the auth state.
- **Parameters / types:** `children`. **Returns / type:** a React element.
- **Internal processing:** asks `/auth/me` on start-up. It registers a 401 handler that signs the user out with a message, and sets a timer that ends the session at `session_expires_at`.
- **Error handling:** a failed `/auth/me` means signed out. Sign-out clears local state even if the request fails.
- **Calls:** `authApi`, `onUnauthorized`. **Used by:** `App.tsx`, tests.

### `useAuth`
Returns the auth state. It throws if used outside `AuthProvider`, which catches a wiring mistake at once.

## E. Classes Explained
None.

## F. Execution Flow
On start-up the status is `checking`. If `/auth/me` succeeds it becomes `signedIn`, otherwise `signedOut`. Sign-in sets the user from the response. A 401 later, or the expiry timer, returns to `signedOut` with a notice.

## G. Input and Output
Output: `status`, `user` (email, role, permissions and session expiry), `notice`, `signIn`, `signOut` and `can(permission)`.

## H. Important Technical Concepts
- **`unavailable` (Phase 5 M7):** only a 401 from the start-up check means signed out. Any other failure sets status `unavailable` with `checkError`, and `recheck` repeats the check. Before, an API restart or database outage sent a user with a valid session to the sign-in page.
- **Reloading keeps the session:** the cookie survives a reload, so `/auth/me` restores it. Nothing is read from browser storage.
- **`can` mirrors the server.** Hiding a button is a convenience, and the API refuses the action anyway.
- **The expiry timer** prevents a user working on a page whose session has already lapsed, then losing the work at the next request.

## I. Example
```ts
const { can } = useAuth();
if (can("update_investigations")) { /* show the status control */ }
```

## J. Maintenance Notes
Keep permission names exactly as the API returns them, and never compute permissions from the role here.

## K. Related Files
- [api.ts](../services/api.ts.explanation.md): the 401 signal.
- [guards.tsx](../components/guards.tsx.explanation.md): uses the status and permissions.
- [LoginPage.tsx](../pages/LoginPage.tsx.explanation.md): calls `signIn`.
