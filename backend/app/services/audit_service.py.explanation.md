# audit_service.py

Source: [backend/app/services/audit_service.py](audit_service.py)

## A. File Purpose
Writes and reads audit log entries.

## B. Why This File Exists
PRD section 10 requires audit logging, and PRD 2.3 lets administrators monitor activity. A single function keeps entries consistent.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.models.records`.
- **External services / database:** the `audit_logs` table.
- **Depended on by:** auth, prediction, batch, investigation and settings services, and the audit route.

## D. Every Function Explained

### `record_event`
- **Purpose:** add one entry.
- **Parameters / types:** `session`, `user_id`, `action: str`, `entity_type: str`, optional `entity_id`, optional `details`. **Returns / type:** `None`.
- **Internal processing:** adds to the session and does not commit.
- **Error handling:** database errors surface at the caller's commit.
- **Calls:** `session.add`. **Used by:** services.

### `list_events`
- **Purpose:** read a page of entries.
- **Parameters / types:** `session`, `limit: int`, `offset: int`. **Returns / type:** `tuple[list[AuditLog], int]`.
- **Internal processing:** counts, then fetches newest first.
- **Error handling:** none needed. **Calls:** `session`. **Used by:** the audit route.

## E. Classes Explained
None.

## F. Execution Flow
A service calls `record_event` while doing its work, then commits both together.

## G. Input and Output
Input: who did what to which record. Output: rows in `audit_logs`.

## H. Important Technical Concepts
- **Same transaction:** an action and its audit entry succeed or fail together, so there is neither unlogged work nor a log entry for work that did not happen.
- **No secrets, no amounts:** details hold identifiers and counts. Failed logins store no email, since people sometimes type a password into the email box.

## I. Example
```python
record_event(session, user.id, "investigation.status_changed", "investigation", item.id,
             {"from": "NEW", "to": "UNDER_REVIEW"})
```

## J. Maintenance Notes
Keep action names in `area.verb` form. Rows are not pruned at this stage, so a retention policy will be needed for long-running use.

## K. Related Files
- [records.py](../models/records.py.explanation.md): the table.
- [audit.py](../api/routes/audit.py.explanation.md): the route.
