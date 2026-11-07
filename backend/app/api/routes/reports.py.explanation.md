# reports.py (routes)

Source: [backend/app/api/routes/reports.py](reports.py)

## A. File Purpose
Exposes the summary report and report downloads.

## B. Why This File Exists
These are the PRD 8.2 report endpoints, implementing PRD 6.1 and 6.9.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas.reports`, `app.security`, `app.services.report_service`, `app.models`.
- **External services / database:** through the service.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `read_summary`
`GET /api/v1/reports/summary`. Needs `VIEW_SUMMARY`, and returns `SummaryReport` for the user's scope.

### `export_report`
`GET /api/v1/reports/export?report_type=...`. Needs `EXPORT_REPORTS`, and streams CSV. An unknown type gives 422. The file name uses a validated value, so a client cannot inject into the header.

## E. Classes Explained
None.

## F. Execution Flow
Permission check, then the service.

## G. Input and Output
See `API_DOCUMENTATION.md`.

## H. Important Technical Concepts
- **Demo users see a demo summary and cannot export reports,** matching PRD 2.4.

## I. Example
```powershell
curl.exe -H "Authorization: Bearer <token>" "http://127.0.0.1:8010/api/v1/reports/export?report_type=model_evaluation" -o evaluation.csv
```

## J. Maintenance Notes
A new report needs a value in `ReportType`, and a branch in `report_lines`.

## K. Related Files
- [report_service.py](../../services/report_service.py.explanation.md): the logic.
