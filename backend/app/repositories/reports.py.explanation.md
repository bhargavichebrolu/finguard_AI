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

### `model_flag_breakdown`
- **Purpose:** every model-flag figure on the dashboard from one pass over predictions.
- **Parameters / types:** `session`, `is_demo`. **Returns / type:** `FlagBreakdown`.
- **Internal processing:** one query groups by risk level, transaction type and simulated day (floor of step / 24), counting rows and flags and summing amounts. Python adds the small result (at most a few hundred groups) into totals, a risk distribution, a type distribution and a per-day list, each in sorted order.
- **Error handling:** an empty scope gives zeros and empty collections. **Calls:** none. **Used by:** `build_summary`, and the four helpers below.

### `model_flag_totals`
Returns total predictions, flags, total value and flagged value, from `model_flag_breakdown`.

### `risk_distribution`
Returns a count per risk level, from `model_flag_breakdown`.

### `type_distribution`
Returns analysed and flagged counts per transaction type, from `model_flag_breakdown`. Also used by the flag-summary CSV.

### `flags_by_simulation_day`
Returns analysed and flagged counts per simulated day, for PRD 6.1's trend. A day is `step // 24`. Floor division matters: SQLAlchemy 2 turns `/` into true division, which put steps 5 and 12 in separate groups until a test caught it.

### `investigation_status_counts`
Returns a count per workflow status.

### `uploaded_label_totals`
Returns labelled rows, rows labelled fraud and their value. No metric is computed from these.

## E. Classes Explained
### `FlagBreakdown`
A frozen dataclass: `total`, `flagged`, `total_value`, `flagged_value`, `by_risk`, `by_type`, `by_day`.

None.

## F. Execution Flow
`report_service` calls each one and puts the results in separate sections.

## G. Input and Output
Input: a scope. Output: plain dictionaries and lists.

## H. Important Technical Concepts
- **One pass (Phase 5 M2):** four separate queries each scanned the same 500,000-row join for about 150 ms; one grouped query halved the dashboard summary (862 ms to 434 ms median, `docs/performance/phase-5-baseline.md`). `test_summary_breakdown.py` proves the results equal the original queries.
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
