# BatchAnalysisPage.tsx

Source: [frontend/src/pages/BatchAnalysisPage.tsx](BatchAnalysisPage.tsx)

## A. File Purpose
Page 3 of PRD 7.4, covering PRD 6.4: upload a CSV, watch it process, then review the results and download the results or error report.

## B. Why This File Exists
PRD 6.4 requires validation of extension and size, progress display, a downloadable error report, results and export. The browser checks what it can against the API's own limits from `/settings`, and the API checks everything again.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** components, `../hooks/useApiResource.ts`, `../services/api.ts`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET /settings`, `GET /batches`, `POST /batches/upload`, `GET /batches/{id}`, `/results`, `/export`, `/errors`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `checkFile`
Returns a message if the file is not `.csv`, is empty, or exceeds `max_upload_bytes`, and `null` if it may be uploaded.

### `BatchAnalysisPage`
Shows the limits, the file input, upload progress, a template download and recent uploads. Opening a recent upload shows its job.

### `chooseFile`
Stores the chosen file and checks it straight away, so problems show before uploading.

### `upload`
- **Purpose:** send the file.
- **Parameters / types:** none. **Returns / type:** `Promise<void>`.
- **Internal processing:** shows Axios upload progress, then opens the new job.
- **Error handling:** the API's refusal, such as missing columns or 413, appears as an error state. **Calls:** `batchesApi.upload`. **Used by:** the upload button.

### `downloadTemplate`
Creates a small CSV in the browser with the required columns and two example rows, then downloads it.

### `BatchJobView`
- **Purpose:** show one job.
- **Parameters / types:** `jobId`, `onFinished`. **Returns / type:** sections.
- **Internal processing:** polls every second while the job is pending or processing, slowing after 30 seconds. Shows processing progress, stored and refused counts, ignored columns, whether labels came with the file, and any failure message. When finished it offers downloads, refreshes the recent list once through an effect, and shows the results.
- **Error handling:** load and download errors show in error states. **Calls:** `usePolling`, `download`. **Used by:** the page.

### `download`
Nested in `BatchJobView`. Downloads results or the error report through `downloadFile`, showing any error.

### `BatchResults`
Pages through a job's stored results, highest score first.

## E. Classes Explained
None.

## F. Execution Flow
Choose a file, check it, upload with progress, poll the job until it finishes, then show results and downloads.

## G. Input and Output
Input: a CSV file. Output: progress, counts, results and two downloads.

## H. Important Technical Concepts
- **Two kinds of progress:** upload progress comes from the browser. Processing progress comes from the job's `processed_records`, because the API processes in chunks after accepting the file.
- **Labels are reported, not used:** an `isFraud` column is listed as ignored, and the page says labels were stored separately and never used to score.
- **Refreshing from an effect:** a first version refreshed the recent list during render, which React warns against when it updates another component, so the refresh moved into an effect.

## I. Example
```ts
checkFile(file, settings.max_upload_bytes);
```

## J. Maintenance Notes
Keep the required column list in the introduction in step with `batch_service.py`.

## K. Related Files
- [batch_service.py](../../../backend/app/services/batch_service.py.explanation.md): the server side.
- [useApiResource.ts](../hooks/useApiResource.ts.explanation.md): polling.
