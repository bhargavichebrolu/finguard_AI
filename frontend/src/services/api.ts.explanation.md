# api.ts

Source: [frontend/src/services/api.ts](api.ts)

## A. File Purpose
The single HTTP client the interface uses to reach the API, with CSRF handling and one error shape.

## B. Why This File Exists
The authorisation requires HttpOnly cookie sessions with CSRF protection, and forbids keeping tokens in browser storage. Putting the client in one place means every request follows those rules without each page having to remember them.

## C. Dependencies
- **Libraries:** `axios`.
- **Internal modules:** none.
- **External services / database:** the FinGuard API, reached on the page's own origin through `/api`.
- **Depended on by:** `endpoints.ts`, `useAuth.tsx`, `useApiResource.ts`, tests.

## D. Every Function Explained

### `readCookie`
- **Purpose:** read one readable cookie, used for the CSRF token.
- **Parameters / types:** `name: string`. **Returns / type:** `string | null`.
- **Internal processing:** splits `document.cookie` and matches the exact name. The session cookie is HttpOnly and never appears here.
- **Error handling:** returns `null` when absent. **Calls:** none. **Used by:** the request interceptor, tests.

### `toApiError`
- **Purpose:** convert anything Axios throws into an `ApiError`.
- **Parameters / types:** `error: unknown`. **Returns / type:** `ApiError`.
- **Internal processing:** takes the API's `detail`, `request_id`, field errors (dropping the `body` prefix) and `Retry-After`. A failure with no response becomes status 0 with a connection message.
- **Error handling:** never throws. **Calls:** `defaultMessage`. **Used by:** the response interceptor, hooks, pages.

### `defaultMessage`
Returns a plain message for a status when the API sent no `detail`, such as "Your role does not allow this action." for 403.

### `onUnauthorized`
Registers the function to call when a request is refused with 401, meaning the session ended. Only `AuthProvider` registers one.

### `createApiClient`
- **Purpose:** build a configured Axios instance.
- **Parameters / types:** `baseURL: string`, empty by default, so requests go to the page's own origin. **Returns / type:** `AxiosInstance`.
- **Internal processing:** sends cookies. On POST, PUT, PATCH and DELETE it copies the `finguard_csrf` cookie into `X-CSRF-Token`. Every error becomes an `ApiError`. A 401 calls the registered handler, except for a failed sign-in, which the form reports itself.
- **Error handling:** rejects with `ApiError`. **Calls:** `readCookie`, `toApiError`. **Used by:** the module's `api` instance, tests.

## E. Classes Explained
### `ApiError`
- **Purpose:** an API failure in one shape. **Attributes:** `status`, `requestId`, `fieldErrors`, `retryAfterSeconds`, and `message`. **Methods:** constructor only. **Inheritance:** `Error`.

## F. Execution Flow
Pages call `endpoints.ts`, which calls `api`. The request interceptor adds the CSRF header. The response interceptor normalises errors.

## G. Input and Output
Input: requests from `endpoints.ts`. Output: response data, or a rejected `ApiError`.

## H. Important Technical Concepts
- **Why the page can read the CSRF cookie but not the session cookie:** reading the CSRF token gives another site nothing it can use, because the browser will not send the session cookie with that site's requests (SameSite=Strict), and the server checks the token against this session.
- **Same origin:** with no base URL, requests go to `/api` on the page's origin, and the Vite server or the host forwards them. Cookies therefore stay first-party.
- **Request ID:** errors carry the server's `request_id`, which the error state shows as a reference for support.

## I. Example
```ts
const response = await api.post("/api/v1/transactions/predict", input);
```

## J. Maintenance Notes
Never add token storage here. A new header the API needs goes in the request interceptor, and must also be allowed in the API's CORS settings.

## K. Related Files
- [endpoints.ts](endpoints.ts.explanation.md): the typed calls.
- [useAuth.tsx](../hooks/useAuth.tsx.explanation.md): registers the 401 handler.
- [sessions.py](../../../backend/app/security/sessions.py.explanation.md): the server side of the cookies.
