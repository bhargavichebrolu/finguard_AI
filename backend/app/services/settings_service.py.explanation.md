# settings_service.py

Source: [backend/app/services/settings_service.py](settings_service.py)

## A. File Purpose
Reads and changes the high risk boundary, the one setting administrators can change.

## B. Why This File Exists
PRD 6.3 and 6.10 require configurable risk settings. Keeping the rule here makes it clear that this can never change the frozen threshold.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.core`, `app.models.records`, `app.services.audit_service`.
- **External services / database:** `app_settings`, `audit_logs`.
- **Depended on by:** `prediction_service.py`, `batch_service.py`, the settings route.

## D. Every Function Explained

### `get_high_risk_boundary`
- **Purpose:** return the boundary in force.
- **Parameters / types:** `session`. **Returns / type:** `float`.
- **Internal processing:** the stored row, or `default_high_risk_boundary` (0.30).
- **Error handling:** none needed. **Calls:** `session.get`. **Used by:** services and the settings route.

### `set_high_risk_boundary`
- **Purpose:** change the boundary.
- **Parameters / types:** `session`, `value: float`, `changed_by`. **Returns / type:** `float`.
- **Internal processing:** validates, inserts or updates the row, writes an audit entry with old and new values, and commits.
- **Error handling:** raises `InvalidInputError` unless the value is above the threshold and at most 1.
- **Calls:** `get_high_risk_boundary`, `record_event`. **Used by:** the settings route.

## E. Classes Explained
None.

## F. Execution Flow
Each prediction reads the boundary once and stores it on the prediction row.

## G. Input and Output
Input: a number. Output: the new boundary, a row and an audit entry.

## H. Important Technical Concepts
- **History is not rewritten.** Earlier predictions keep their stored risk level and `high_risk_boundary_used`.
- **Why 0.30 by default:** on validation it gives 88.5% precision and 24.2% recall. See ADR 0003, decision 4.

## I. Example
```python
set_high_risk_boundary(session, 0.5, admin.id)
```

## J. Maintenance Notes
Do not add the threshold here. Changing it means releasing a new model through `frozen_model.py`.

## K. Related Files
- [risk.py](risk.py.explanation.md): uses the boundary.
- [frozen_model.py](../core/frozen_model.py.explanation.md): the threshold.
