# registry.tsx

Source: [frontend/src/pages/registry.tsx](registry.tsx)

## A. File Purpose
Lists every page with its address, navigation label, icon and required permission, in PRD 7.4 order.

## B. Why This File Exists
Routes and navigation are both built from this list, so a page cannot appear in one and be missing from the other, or carry different permissions in each.

## C. Dependencies
- **Libraries:** React, `lucide-react`.
- **Internal modules:** the page components.
- **External services / database:** none.
- **Depended on by:** `App.tsx`, `AppLayout.tsx`.

## D. Every Function Explained

### `visiblePages`
Returns the pages whose permission the user holds, in order.

## E. Classes Explained
None.

## F. Execution Flow
Imported at start-up.

## G. Input and Output
Output: `PAGES`, an array of `PageDefinition`. Current entries, in order: Dashboard (`/dashboard`, `view_summary`), Transaction Analysis (`/analyse`, `predict`), CSV Batch Analysis (`/batches`, `upload_batch`), Transaction Explorer (`/transactions`, `view_transactions`), Explainable AI (`/explainability`, `view_models`), System Information (`/system`, `view_system_status`). Later milestones add the remaining PRD 7.4 pages in their places.

## H. Important Technical Concepts
- **`PageDefinition`** is an interface with `path`, `label`, `icon`, `permission` and `element`.

## I. Example
```tsx
{ path: "/system", label: "System Information", icon: Server, permission: "view_system_status", element: <SystemInformationPage /> }
```

## J. Maintenance Notes
Add each new page here and nowhere else.

## K. Related Files
- [AppLayout.tsx](../layouts/AppLayout.tsx.explanation.md): navigation.
- [App.tsx](../../../docs/file-explanations/frontend/src/App.tsx.explanation.md): routes.
