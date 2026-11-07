# investigations.py (repository)

Source: [backend/app/repositories/investigations.py](investigations.py)

## A. File Purpose
Holds the database queries for investigations.

## B. Why This File Exists
PRD 8.1 separates database operations from business logic.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.models`.
- **External services / database:** `investigations`, `predictions`, `transactions`, `investigation_notes`, `investigation_status_history`.
- **Depended on by:** `investigation_service.py`, reports.

## D. Every Function Explained

### `_rows_query`
Joins an investigation to its prediction and transaction.

### `list_investigations`
- **Purpose:** return a page.
- **Parameters / types:** `session`, `status`, `assigned_user_id`, `limit`, `offset`. **Returns / type:** `tuple[list[Row], int]`.
- **Internal processing:** filters, then orders newest first, with the identifier breaking ties.
- **Error handling:** none needed. **Calls:** `_rows_query`. **Used by:** `investigation_service`.

### `get_investigation`
Returns one investigation with notes and history loaded, or `None`.

### `lock_investigation`
- **Purpose:** read an investigation for changing.
- **Parameters / types:** `session`, `investigation_id`. **Returns / type:** `Investigation | None`.
- **Internal processing:** `SELECT ... FOR UPDATE` holds a row lock until commit.
- **Error handling:** a waiting request continues after the lock is released.
- **Calls:** `select`. **Used by:** `investigation_service`.

## E. Classes Explained
None.

## F. Execution Flow
Services call these inside a request's session.

## G. Input and Output
Input: identifiers and filters. Output: rows.

## H. Important Technical Concepts
- **Why lock:** without it, two investigators changing the status at once could both read `NEW`, and the history's `from_status` would then be wrong for one of them.

## I. Example
```python
list_investigations(session, InvestigationStatus.NEW, None, 50, 0)
```

## J. Maintenance Notes
Keep lock durations short, by committing promptly after `lock_investigation`.

## K. Related Files
- [investigation_service.py](../services/investigation_service.py.explanation.md): the caller.
