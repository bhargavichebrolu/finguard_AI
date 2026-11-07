# reports.py (schemas)

Source: [backend/app/api/schemas/reports.py](reports.py)

## A. File Purpose
Defines the shape of the summary report.

## B. Why This File Exists
PRD 6.1 says never to mix ground-truth labels, model predictions and investigation outcomes. Giving each its own section makes that structural.

## C. Dependencies
- **Libraries:** `pydantic`.
- **Internal modules:** `app.api.schemas.transactions`.
- **External services / database:** none.
- **Depended on by:** `report_service.py`, the reports route.

## D. Every Function Explained
No functions.

## E. Classes Explained
All inherit from `BaseModel`.

### `ModelFlagsSection`
Totals, flag rate, value, risk and type distributions, and flags per simulated day.

### `InvestigationWorkflowSection`
A count per workflow status.

### `UploadedLabelsSection`
Counts and value of labels supplied in uploads.

### `SummaryReport`
The three sections, plus scope, a separation note, performance notes and recent activity.

## F. Execution Flow
`report_service` builds a `SummaryReport`, and FastAPI serialises it.

## G. Input and Output
See `API_DOCUMENTATION.md`.

## H. Important Technical Concepts
- **`is_demo` and `scope`:** PRD 7.6 requires demo statistics to be distinguishable from real ones.
- **`flag_rate` is not a fraud rate.** It is the share of analysed records the model flagged. PRD 6.1's "fraud rate in analysed data" could only be measured from labels, so it is not presented from flags.

## I. Example
```python
summary.model_flags.flagged_for_review
```

## J. Maintenance Notes
Do not add a field combining counts from different sections.

## K. Related Files
- [report_service.py](../../services/report_service.py.explanation.md): builds this.
