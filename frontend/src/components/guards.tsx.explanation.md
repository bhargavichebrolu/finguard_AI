# guards.tsx

Source: [frontend/src/components/guards.tsx](guards.tsx)

## A. File Purpose
Route guards that require a session or a permission, and the not-found and not-permitted pages.

## B. Why This File Exists
Pages a role cannot use should not be offered. The API remains the authority and refuses such actions anyway.

## C. Dependencies
- **Libraries:** React, React Router.
- **Internal modules:** `../hooks/useAuth.tsx`, `feedback.tsx`.
- **External services / database:** none.
- **Depended on by:** `App.tsx`.

## D. Every Function Explained

### `RequireAuth`
While the session is being checked it shows a loading state. When signed out it redirects to `/login`, remembering the requested path.

### `RequirePermission`
Renders its children only if `can(permission)`, and otherwise shows `ForbiddenPage`.

### `ForbiddenPage`
Explains that the page is not available for this role.

### `NotFoundPage`
Explains that the address does not exist.

## E. Classes Explained
None.

## F. Execution Flow
Routes wrap pages in these guards.

## G. Input and Output
Input: children and a permission. Output: the page, a redirect or a message.

## H. Important Technical Concepts
- **Mirroring, not enforcing:** a hidden page is a usability choice, and the security rule lives in the API.

## I. Example
```tsx
<RequirePermission permission="view_investigations"><InvestigationCentre /></RequirePermission>
```

## J. Maintenance Notes
New pages get their permission through `registry.tsx`, not by wrapping them by hand.

## K. Related Files
- [App.tsx](../../../docs/file-explanations/frontend/src/App.tsx.explanation.md): routes.
- [registry.tsx](../pages/registry.tsx.explanation.md): page permissions.
