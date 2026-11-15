# test_summary_breakdown.py

Source: [backend/tests/api/test_summary_breakdown.py](test_summary_breakdown.py)

## A. File Purpose
Proves the one-pass dashboard breakdown gives exactly what the four original queries gave.

## B. Why This File Exists
Phase 5 M2 replaced four summary queries with one for speed. A performance change must not change any figure, so the original queries are kept here, verbatim, as the reference.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy.
- **Internal modules:** `app.repositories.reports`, API test fixtures.
- **External services / database:** PostgreSQL (`finguard_test`).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `reference_totals`
The pre-M2 totals query.

### `reference_risk`
The pre-M2 risk-level query.

### `reference_types`
The pre-M2 transaction-type query.

### `reference_days`
The pre-M2 per-day query.

### `stored`
Fixture: stores eight varied predictions for an analyst and three for a demo user, across types, risk levels and simulated days.

## E. Classes Explained
None.

## F. Execution Flow
Store predictions through the API, then compare the breakdown with each reference query.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_breakdown_equals_the_original_queries` (both scopes) | Totals, values, risk, type and day figures are identical, and the data was not empty. |
| `test_breakdown_of_an_empty_scope` | Zeros and empty collections. |
| `test_public_helpers_still_answer_from_the_breakdown` | The four helpers agree with the breakdown. |

## H. Important Technical Concepts
- **`INPUTS`** cover every transaction type, flagged and unflagged scores, and several simulated days.
- **`FLAGGED`** is the decision condition shared by the reference queries.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_summary_breakdown.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Never edit the reference queries to make a test pass; they define the expected figures.

## K. Related Files
- [reports.py](../../app/repositories/reports.py.explanation.md): the breakdown.
