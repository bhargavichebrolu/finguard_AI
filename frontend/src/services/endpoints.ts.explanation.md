# endpoints.ts

Source: [frontend/src/services/endpoints.ts](endpoints.ts)

## A. File Purpose
Typed functions for every API route the interface uses, grouped by area, plus file downloads.

## B. Why This File Exists
Pages should not build URLs or guess response shapes. The types come from `api.generated.ts`, generated from the API's own schema, so a mismatch is a compile error rather than a runtime surprise.

## C. Dependencies
- **Libraries:** none directly. It uses the shared Axios instance.
- **Internal modules:** `api.ts`, `../types/api.generated.ts`.
- **External services / database:** the FinGuard API.
- **Depended on by:** hooks and pages.

## D. Every Function Explained

### `downloadFile`
- **Purpose:** download a CSV through the signed-in client.
- **Parameters / types:** `path: string`, `fallbackName: string`. **Returns / type:** `Promise<void>`.
- **Internal processing:** fetches the file as a blob, so the session cookie is sent, takes the file name from `Content-Disposition`, and saves it through a temporary link.
- **Error handling:** a failed request rejects with `ApiError`. **Calls:** `api.get`. **Used by:** batch, report and investigation pages.

### `response`
A local value in `downloadFile`, not a function: the successful response.

## E. Classes Explained
None.

## F. Execution Flow
A page calls, for example, `transactionsApi.predict(input)`. That calls `api.post`, and the typed data comes back.

## G. Input and Output
Input: arguments matching the API's request schemas. Output: the API's response types, re-exported under short names such as `Prediction` and `ModelReport`.

## H. Important Technical Concepts
- **Download errors (Phase 5 M7):** `readBlobError` and `blobText` moved into the client's response interceptor (`api.ts`). Here they never ran on a real failure: the interceptor had already turned the error into an `ApiError`, so downloads lost the API's message and reference. `downloadFile` now lets the client's `ApiError` through.
- **Groups:** `authApi`, `transactionsApi`, `batchesApi`, `investigationsApi`, `modelsApi`, `reportsApi`, `settingsApi`, `systemApi`, `usersApi` and `auditApi`. Each method maps to one route in `API_DOCUMENTATION.md`.
- **One module, not ten:** the plan proposed one module per area. They are grouped in one file instead, because each group is a few lines, and one document describes them better than ten thin ones.
- **`downloadPaths`:** builds the CSV export addresses, so pages never assemble them.
- **Upload progress:** `batchesApi.upload` passes Axios upload progress to the caller as a fraction from 0 to 1.

## I. Example
```ts
const report = await modelsApi.report();
report.families.length; // 6
```

## J. Maintenance Notes
When the API changes, regenerate `openapi.json` and the types, then fix any type errors here first.

## K. Related Files
- [api.ts](api.ts.explanation.md): the client.
- [export_openapi.py](../../../scripts/export_openapi.py.explanation.md): produces the schema behind the types.
