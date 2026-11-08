# feedback.tsx

Source: [frontend/src/components/feedback.tsx](feedback.tsx)

## A. File Purpose
The loading, empty, error and confirmation states, and the page header, that every page uses.

## B. Why This File Exists
PRD 7.5 requires loading states, empty states, clear API errors and confirmation of significant actions. Shared components make those consistent and accessible.

## C. Dependencies
- **Libraries:** React, `lucide-react`.
- **Internal modules:** `../services/api.ts` (the `ApiError` type).
- **External services / database:** none.
- **Depended on by:** pages and `DataTable.tsx`.

## D. Every Function Explained

### `LoadingState`
Shows a spinner and a label in a polite live region, so screen readers announce it.

### `EmptyState`
Shows a title and an optional explanation when there is nothing to list.

### `ErrorState`
Shows the API's message, any field errors, the request reference and an optional retry button, inside `role="alert"`.

### `PageHeader`
Shows the page title and an introduction.

### `ConfirmDialog`
- **Purpose:** ask before a significant action.
- **Parameters / types:** `open`, `title`, `message`, `confirmLabel`, `onConfirm`, `onCancel`. **Returns / type:** a dialog or nothing.
- **Internal processing:** focuses Cancel when opened, so the safe choice is the default, and closes on Escape.
- **Error handling:** none needed. **Calls:** `onKey`. **Used by:** the investigation and settings pages.

### `onKey`
Nested in `ConfirmDialog`. Calls `onCancel` when Escape is pressed.

## E. Classes Explained
None.

## F. Execution Flow
Pages render one of these according to `useApiResource` state.

## G. Input and Output
Input: props. Output: accessible markup.

## H. Important Technical Concepts
- **`role="alert"` and `role="status"`** let assistive technology announce errors and progress without moving focus.

## I. Example
```tsx
{resource.error ? <ErrorState error={resource.error} onRetry={resource.reload} /> : null}
```

## J. Maintenance Notes
Keep error messages from the API as they are. They are written to be safe to show.

## K. Related Files
- [useApiResource.ts](../hooks/useApiResource.ts.explanation.md): the state these show.
- [components.css](../styles/components.css.explanation.md): styles.
