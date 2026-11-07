# investigation_service.py

Source: [backend/app/services/investigation_service.py](investigation_service.py)

## A. File Purpose
Applies investigation status changes, assignments and notes.

## B. Why This File Exists
PRD 6.7 requires status updates, notes and a history of changes. PRD 9.2 requires related updates to share a transaction, so a change and its history can never disagree.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.api.schemas.investigations`, `app.core.errors`, `app.models`, `app.repositories.investigations`, `app.services.audit_service`.
- **External services / database:** the investigation tables and `audit_logs`.
- **Depended on by:** the investigations route.

## D. Every Function Explained

### `summary_view`
Builds one list row from an investigation, its prediction and its transaction.

### `_after_lock_time`
- **Purpose:** timestamp history rows and notes in the order they were applied.
- **Parameters / types:** none. **Returns / type:** a SQL function, `clock_timestamp()`.
- **Internal processing:** none; the database evaluates it when the row is inserted.
- **Error handling:** none needed. **Calls:** `func`. **Used by:** `update_investigation`, `add_note`.

### `_check_assignee`
Refuses an assignee who does not exist, is inactive, or lacks an investigating role. Raises `InvalidInputError`.

### `update_investigation`
- **Purpose:** apply a change.
- **Parameters / types:** `session`, `investigation_id`, `change: InvestigationUpdate`, `user`. **Returns / type:** `Investigation`.
- **Internal processing:** locks the row. A real status change adds a history row and an audit entry, while setting the same status adds nothing. It then applies any assignee change, commits, and reloads the row with notes and history.
- **Error handling:** `NotFoundError` or `InvalidInputError`, which leave everything unchanged.
- **Calls:** `lock_investigation`, `_check_assignee`, `record_event`, `get_investigation`. **Used by:** the route.

### `add_note`
- **Purpose:** add a note.
- **Parameters / types:** `session`, `investigation_id`, `text: str`, `user`. **Returns / type:** `InvestigationNote`.
- **Internal processing:** stores the note, updates `updated_at`, and records that a note was added. The text is not copied to the audit log, because notes may hold sensitive remarks.
- **Error handling:** `NotFoundError`.
- **Calls:** `lock_investigation`, `record_event`. **Used by:** the route.

## E. Classes Explained
None.

## F. Execution Flow
Permission check in the route, then lock, change, history, audit, commit.

## G. Input and Output
Input: a change or note. Output: the updated records.

## H. Important Technical Concepts
- **No feedback into the model.** Marking something `FALSE_ALARM` changes neither its stored score, its prediction nor any metric. Those are separate kinds of truth (PRD 6.1).
- **Why not `now()`:** PostgreSQL's `now()` is the start of the transaction, and a request starts its transaction before waiting for the row lock. A test with many simultaneous changes showed history rows ordered by start time rather than by when they took effect. `clock_timestamp()` is read after the lock is held, which fixed it.
- **Any status can move to any other.** The PRD lists statuses but no transitions, and investigators may need to reopen a closed case. The history records each move.

## I. Example
```python
update_investigation(session, item_id, InvestigationUpdate(status="ESCALATED"), user)
```

## J. Maintenance Notes
If transition rules are wanted later, add them to `update_investigation`.

## K. Related Files
- [investigations.py repository](../repositories/investigations.py.explanation.md): queries and locking.
- [investigations.py route](../api/routes/investigations.py.explanation.md): the entry points.
- [test_investigations.py](../../tests/api/test_investigations.py.explanation.md): tests.
