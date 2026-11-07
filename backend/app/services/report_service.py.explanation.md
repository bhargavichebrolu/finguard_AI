# report_service.py

Source: [backend/app/services/report_service.py](report_service.py)

## A. File Purpose
Builds the summary report and the downloadable reports.

## B. Why This File Exists
PRD 6.1 lists the summary figures, and PRD 6.9 lists the exports. PRD 6.1 also requires labels, predictions and investigation outcomes to stay apart.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.api.schemas`, `app.database.session`, `app.models.records`, `app.repositories`, `app.services`, `app.utils.csv_safety`.
- **External services / database:** the application tables.
- **Depended on by:** the reports route.

## D. Every Function Explained

### `build_summary`
- **Purpose:** build the summary.
- **Parameters / types:** `session`, `model: ServingModel`, `is_demo: bool`. **Returns / type:** `SummaryReport`.
- **Internal processing:** fills separate sections from separate queries, plus recent activity and notes from saved metrics.
- **Error handling:** zero records gives a flag rate of 0.
- **Calls:** `queries.*`, `list_transactions`, `performance_notes`. **Used by:** the route.

### `_flag_summary_lines`
Returns analysed and flagged counts by type, as CSV.

### `_investigation_rows`
Yields investigation rows for export. It has its own session, because it runs while the response is sent.

### `_model_evaluation_lines`
Returns the saved metrics as CSV rows.

### `report_lines`
- **Purpose:** choose the report.
- **Parameters / types:** `report_type: ReportType`, `is_demo: bool`, `model`. **Returns / type:** an iterator of strings.
- **Internal processing:** dispatches on the type.
- **Error handling:** invalid types are refused by the route's `Literal`.
- **Calls:** the functions above, `prediction_csv_lines`. **Used by:** the route.

## E. Classes Explained
None. `ReportType` lists the four reports.

## F. Execution Flow
A route calls `build_summary`, or wraps `report_lines` in a streaming response.

## G. Input and Output

| PRD 6.9 report | `report_type` | Content |
|---|---|---|
| Transaction prediction CSV | `predictions` | Each stored prediction |
| Fraud summary CSV | `flag_summary` | Model flags by type |
| Investigation summary | `investigations` | Each investigation |
| Model evaluation report | `model_evaluation` | Saved Phase 2 metrics |

## H. Important Technical Concepts
- **"Fraud summary" is named `flag_summary`,** because it counts model flags, and calling them fraud would misstate them.
- **The evaluation report uses saved results only,** and no test data is read.
- **The summary's figures describe stored records,** not model quality. `model_performance_notes` carries the frozen evaluation.

## I. Example
```python
"".join(report_lines("model_evaluation", False, model))
```

## J. Maintenance Notes
Keep the three kinds of information in their own sections.

## K. Related Files
- [reports.py repository](../repositories/reports.py.explanation.md): queries.
- [reports.py schemas](../api/schemas/reports.py.explanation.md): shapes.
- [metrics_service.py](metrics_service.py.explanation.md): saved results.
