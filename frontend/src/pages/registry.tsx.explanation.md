# registry.tsx

Source: [frontend/src/pages/registry.tsx](registry.tsx)

## A. File Purpose
Lists every page with its address, navigation label, icon and required permission, in PRD 7.4 order. Each page is loaded lazily on first visit.

## B. Why This File Exists
Routes and navigation are both built from this list, so a page cannot appear in one and be missing from the other, or carry different permissions in each.

## C. Dependencies
- **Libraries:** React (`lazy`), `lucide-react`.
- **Internal modules:** the page components.
- **External services / database:** none.
- **Depended on by:** `App.tsx`, `AppLayout.tsx`.

## D. Every Function Explained

### `page`
- **Purpose:** turn one named export of a page module into a lazy component.
- **Parameters / types:** `load`, a dynamic import; `name`, the export's name. **Returns / type:** a `React.lazy` component.
- **Internal processing:** `React.lazy` needs a default export, so this maps the named export to `default`. The type parameter makes a misspelt name a type error.
- **Error handling:** a failed import throws into the nearest error boundary. **Calls:** `lazy`. **Used by:** the page constants.

### `visiblePages`
Returns the pages whose permission the user holds, in order.

## E. Classes Explained
None.

## F. Execution Flow
Imported at start-up.

## G. Input and Output
Output: `PAGES`, an array of `PageDefinition`. Current entries, in order: Dashboard (`/dashboard`, `view_summary`), Transaction Analysis (`/analyse`, `predict`), CSV Batch Analysis (`/batches`, `upload_batch`), Transaction Explorer (`/transactions`, `view_transactions`), Investigation Centre (`/investigations`, `view_investigations`), Model Performance (`/models`, `view_models`), Explainable AI (`/explainability`, `view_models`), Reports (`/reports`, `export_reports`), Settings (`/settings`, `view_settings`), System Information (`/system`, `view_system_status`). This is the full PRD 7.4 list.

## H. Important Technical Concepts
- **Code-splitting:** each page and the chart library load as separate files, so the first download stays small. Before this the build warned that one file was over 500 kB.
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
