# audit.py

Source: [backend/app/api/routes/audit.py](audit.py)

## A. File Purpose
Lets administrators read the audit log.

## B. Why This File Exists
PRD 2.3 has administrators monitor application activity, and PRD section 10 requires audit logging. A log nobody can read has little value. This route is an addition to the PRD 8.2 list.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.security`, `app.services.audit_service`.
- **External services / database:** `audit_logs`, through the service.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `list_audit_logs`
- **Purpose:** `GET /api/v1/audit-logs`.
- **Parameters / types:** `_admin`, `db`, `limit`, `offset`. **Returns / type:** `Page[AuditLogView]`.
- **Internal processing:** calls `list_events` and wraps the result.
- **Error handling:** 401 without a token, 403 for other roles.
- **Calls:** `list_events`. **Used by:** clients.

## E. Classes Explained
None.

## F. Execution Flow
Permission check, then the query.

## G. Input and Output
Input: paging values. Output: entries, newest first.

## H. Important Technical Concepts
- **Read-only:** no route edits or deletes entries.

## I. Example
```powershell
curl.exe -H "Authorization: Bearer <token>" "http://127.0.0.1:8010/api/v1/audit-logs?limit=20"
```

## J. Maintenance Notes
Add filters here if the log grows large enough to need them.

## K. Related Files
- [audit_service.py](../../services/audit_service.py.explanation.md): the query.
- [permissions.py](../../security/permissions.py.explanation.md): who may read it.
