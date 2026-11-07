# reports.py (repository)

Source: [backend/app/repositories/reports.py](reports.py)

## A. File Purpose
Holds the aggregate queries behind the summary report.

## B. Why This File Exists
PRD 6.1 lists the summary figures and forbids mixing ground-truth labels, model predictions and investigation outcomes. Separate functions keep those three apart in the code as well as the output.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.models`.
- **External services / database:** `transactions`, `predictions`, `investigations`, `ground_truth_labels`.
- **Depended on by:** `report_service.py`.

## D. Every Function Explained
Each takes `session` and `is_demo`, and filters to that scope.

### `_scoped_predictions`
Returns predictions joined to transactions in a scope.

### `model_flag_totals`
Returns total predictions, flags, total value and flagged value.

### `risk_distribution`
Returns a count per risk level.

### `type_distribution`
Returns analysed and flagged counts per transaction type.

### `flags_by_simulation_day`
Returns analysed and flagged counts per simulated day, for PRD 6.1's trend. A day is `step // 24`. Floor division matters: SQLAlchemy 2 turns `/` into true division, which put steps 5 and 12 in separate groups until a test caught it.

### `investigation_status_counts`
Returns a count per workflow status.

### `uploaded_label_totals`
Returns labelled rows, rows labelled fraud and their value. No metric is computed from these.

## E. Classes Explained
None.

## F. Execution Flow
`report_service` calls each one and puts the results in separate sections.

## G. Input and Output
Input: a scope. Output: plain dictionaries and lists.

## H. Important Technical Concepts
- **`func.count(case((condition, 1)))`:** counts rows meeting a condition in the same query, since `count` ignores nulls.
- **Trend is flags, not fraud.** PRD 6.1 says "fraud trends". These are counts of model flags, named accordingly.

## I. Example
```python
risk_distribution(session, False)  # {"LOW": 10, "MEDIUM": 2, "HIGH": 1}
```

## J. Maintenance Notes
These scan all rows in scope, which is fine at demonstration scale. Larger data would need pre-computed totals.

## K. Related Files
- [report_service.py](../services/report_service.py.explanation.md): the caller.
