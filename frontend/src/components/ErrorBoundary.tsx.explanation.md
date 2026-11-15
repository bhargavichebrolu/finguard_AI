# ErrorBoundary.tsx

Source: [frontend/src/components/ErrorBoundary.tsx](ErrorBoundary.tsx)

## A. File Purpose
Catches an error while a page is shown, so one failure never blanks the whole interface, and offers a reload.

## B. Why This File Exists
Phase 5 finding F7: a lazily loaded page whose code failed to download (after a redeploy renamed the files, or a dropped connection) unmounted the whole interface to a blank page.

## C. Dependencies
- **Libraries:** React, lucide-react.
- **Internal modules:** None.
- **External services / database:** None.
- **Depended on by:** `App.tsx`: one around each page, keyed by its path, and one around the whole application.

## D. Every Function Explained

### `isDownloadFailure`
True when an error is a failed module download, recognised by the messages Chromium ("Failed to fetch dynamically imported module"), Firefox ("error loading dynamically imported module") and WebKit ("Importing a module script failed") give.

### `getDerivedStateFromError`
Stores the error, so the next render shows the prompt.

### `render`
Shows the children, or an alert with a heading, an explanation and a Reload button. A download failure says the page could not be loaded and the application may have been updated; any other error gets a general message.

### `reload`
Inside `render`: the given `reload`, or `window.location.reload()`.

### `download`
Inside `render`: whether the error is a download failure.

## E. Classes Explained
### `ErrorBoundary`
A React error boundary; React requires a class for this. Props: `children`, optional `reload` for tests.

## F. Execution Flow
A page throws while rendering, or its lazy import rejects -> `getDerivedStateFromError` -> the prompt replaces that page only; the frame and navigation stay. Moving to another page mounts a new boundary (the key changes), so the error clears.

## G. Input and Output
Input: children. Output: the children, or the prompt.

## H. Important Technical Concepts
- **Why reload:** the browser remembers a failed module download for the rest of the visit, so retrying the import cannot work; only a full reload fetches the page's code again.
- **No error text shown:** an error message can contain anything; React already logs it to the browser console.
- **`DOWNLOAD_FAILURE`** is the regular expression for the three browsers' messages.

## I. Example
```tsx
<ErrorBoundary key={page.path}>
  <Suspense fallback={<LoadingState />}>{page.element}</Suspense>
</ErrorBoundary>
```

## J. Maintenance Notes
If a browser changes its message, add it to `DOWNLOAD_FAILURE` and to the test listing each browser's wording.

## K. Related Files
- [resilience.test.tsx](../../tests/unit/resilience.test.tsx.explanation.md): unit tests.
- [resilience.spec.ts](../../tests/e2e/resilience.spec.ts.explanation.md): the browser test with a real failed download.
