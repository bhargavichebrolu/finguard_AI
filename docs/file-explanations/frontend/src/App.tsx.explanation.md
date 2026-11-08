# App.tsx

Source: [frontend/src/App.tsx](../../../../frontend/src/App.tsx)

## A. File Purpose
The root component: providers, the router and every route.

## B. Why This File Exists
One place defines which addresses exist, which need a session, and which need a permission. Phase 1 used it as a placeholder. Phase 4 made it the application's root.

## C. Dependencies
- **Libraries:** React, React Router.
- **Internal modules:** `hooks/useAuth.tsx`, `hooks/useModelLimits.tsx`, `layouts/AppLayout.tsx`, `pages/LoginPage.tsx`, `pages/registry.tsx`, `components/guards.tsx`.
- **External services / database:** none directly.
- **Depended on by:** `main.tsx`, and `tests/unit/render.tsx` through `AppRoutes`.

## D. Every Function Explained

### `HomeRedirect`
Sends `/` to the first page the role may open, or shows the not-permitted page if there is none.

### `AppRoutes`
- **Purpose:** define all routes.
- **Parameters / types:** none. **Returns / type:** `<Routes>`.
- **Internal processing:** `/login` is public. Everything else sits inside `RequireAuth`, `ModelLimitsProvider` and `AppLayout`. Each page from `PAGES` is wrapped in `RequirePermission`. Unknown addresses show `NotFoundPage`.
- **Error handling:** guards handle missing sessions and permissions.
- **Calls:** `visiblePages`. **Used by:** `App`, tests.

### `App`
Wraps `AppRoutes` in `AuthProvider` and `BrowserRouter`.

## E. Classes Explained
None.

## F. Execution Flow
`main.tsx` renders `App`. `AuthProvider` checks the session. The router renders the login page or the layout with the requested page.

## G. Input and Output
Input: the browser address. Output: the matching page.

## H. Important Technical Concepts
- **Separated for tests:** `AppRoutes` is exported apart from `App`, so tests can use a memory router.
- **Limitations load after sign-in:** `ModelLimitsProvider` sits inside `RequireAuth`, because the metrics route needs a session.

## I. Example
```tsx
<AuthProvider><BrowserRouter><AppRoutes /></BrowserRouter></AuthProvider>
```

## J. Maintenance Notes
Add pages in `pages/registry.tsx`, not here.

## K. Related Files
- [registry.tsx](../../../../frontend/src/pages/registry.tsx.explanation.md): the page list.
- [guards.tsx](../../../../frontend/src/components/guards.tsx.explanation.md): route guards.
