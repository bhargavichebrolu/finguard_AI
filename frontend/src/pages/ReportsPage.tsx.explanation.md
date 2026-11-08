# ReportsPage.tsx

Source: [frontend/src/pages/ReportsPage.tsx](ReportsPage.tsx)

## A. File Purpose
Page 8 of PRD 7.4, covering PRD 6.9: download the four CSV reports.

## B. Why This File Exists
PRD 6.9 lists transaction predictions, a fraud summary, an investigation summary and the model evaluation. The fraud summary is named the flag summary here, because it counts model flags, which are not findings of fraud.

## C. Dependencies
- **Libraries:** React, `lucide-react`.
- **Internal modules:** `feedback.tsx`, `../services/api.ts`, `../services/endpoints.ts`.
- **External services / database:** `GET /api/v1/reports/export?report_type=...`.
- **Depended on by:** `registry.tsx`. Requires `export_reports`, so the demo role cannot open it.

## D. Every Function Explained

### `ReportsPage`
Shows a card for each report with a description and a download button. While one download runs, every button is disabled.

### `download`
Nested in `ReportsPage`. Calls `downloadFile` with the report's path and a fallback file name, and shows any error.

## E. Classes Explained
None.

## F. Execution Flow
Click a button, then the file is fetched through the signed-in client and saved by the browser.

## G. Input and Output
Output: a CSV file named by the API's `Content-Disposition` header.

## H. Important Technical Concepts
- **`REPORTS`** lists the four report types with their descriptions, so tests can check one button exists per type.
- **Downloads use the session:** a plain link would not send the CSRF header or reach the API's error messages, so files are fetched as Blobs and handed to the browser.

## I. Example
```ts
await downloadFile(downloadPaths.report("flag_summary"), "finguard-flag_summary.csv");
```

## J. Maintenance Notes
Add a report type here and in `ReportType` together.

## K. Related Files
- [reports.py](../../../backend/app/api/routes/reports.py.explanation.md): the export route.
- [endpoints.ts](../services/endpoints.ts.explanation.md): `downloadFile`.
