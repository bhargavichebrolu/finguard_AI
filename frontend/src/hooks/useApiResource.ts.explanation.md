# useApiResource.ts

Source: [frontend/src/hooks/useApiResource.ts](useApiResource.ts)

## A. File Purpose
Loads data from the API with loading, error and reload handling, and provides a polling helper.

## B. Why This File Exists
PRD 7.5 requires loading, empty and error states everywhere. One hook means every page behaves the same, and handles the case where a slow earlier request finishes after a newer one.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `../services/api.ts`.
- **External services / database:** whatever the `load` function calls.
- **Depended on by:** pages and `useModelLimits.tsx`.

## D. Every Function Explained

### `useApiResource`
- **Purpose:** run a loader and expose its state.
- **Parameters / types:** `load: () => Promise<T>`, `deps`. **Returns / type:** `{ data, error, loading, reload }`.
- **Internal processing:** each run gets a number, and only the latest run may set state, so stale responses are ignored. `reload` runs it again.
- **Error handling:** errors become `ApiError`. **Calls:** `toApiError`. **Used by:** pages.

### `usePolling`
- **Purpose:** repeat a callback while a condition holds.
- **Parameters / types:** `callback`, `intervalMs`, `active`, `slowAfterMs`. **Returns / type:** `void`.
- **Internal processing:** schedules with `setTimeout`, and triples the interval after `slowAfterMs` so a long job does not keep the API busy.
- **Error handling:** none needed. **Calls:** the callback. **Used by:** the batch page.

### `tick`
Nested in `usePolling`. Runs the callback and schedules the next run.

## E. Classes Explained
None.

## F. Execution Flow
On mount, and when `deps` change, `load` runs and the state updates. While a batch is processing, `usePolling` calls `reload` repeatedly.

## G. Input and Output
Input: a loader function. Output: data, error and loading state.

## H. Important Technical Concepts
- **`deps` decide when to reload.** `load` is a new function on every render, so it is deliberately not a dependency.
- **Back-off:** polling every second for 30 seconds, then every three seconds, follows the approved plan.

## I. Example
```ts
const status = useApiResource(() => systemApi.status(), []);
```

## J. Maintenance Notes
Keep stale-response protection. Without it, quick filter changes can show results for an older filter.

## K. Related Files
- [feedback.tsx](../components/feedback.tsx.explanation.md): renders the states.
- [api.ts](../services/api.ts.explanation.md): error shape.
