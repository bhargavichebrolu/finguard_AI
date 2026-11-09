# retention.py

Source: [backend/app/commands/retention.py](retention.py)

## A. File Purpose
An administrative command that deletes records past their retention period, as a dry run unless told to apply.

## B. Why This File Exists
Phase 5 found that expired sessions, audit entries and rate-limit rows were never removed (finding F8). The approval asked for an explicit command, not a background job, with dry-run and apply modes, counts and cutoff dates: 7 days for ended sessions and 365 days for audit records.

## C. Dependencies
- **Libraries:** SQLAlchemy, Python standard library.
- **Internal modules:** `app.models.records`, `app.services.audit_service`, `app.database.session`.
- **External services / database:** PostgreSQL.
- **Depended on by:** Administrators: `python -m app.commands.retention [--apply]`, inside the API image or with the backend environment.

## D. Every Function Explained

### `run`
- **Purpose:** count, and if applying delete, each category's records older than its cutoff.
- **Parameters / types:** `session`, `apply: bool`, optional `now`. **Returns / type:** a list of `Outcome`.
- **Internal processing:** cutoffs are `now` minus each period, with `now` from the database clock unless given. Deletes use a strict `<`, so a record exactly at its cutoff is kept. Applying records one `retention.applied` audit entry with every count and cutoff, then commits; a dry run rolls back.
- **Error handling:** errors propagate and nothing is committed. **Calls:** `record_event`. **Used by:** `main`, tests.

### `report`
Formats the outcomes as one line per category, then whether anything was deleted.

### `main`
Parses `--apply` (default: dry run), runs, prints the report.

## E. Classes Explained
### `Category`
One kind of record: name, model, period kept and the time it is judged by.

### `Outcome`
One category's cutoff and count.

## F. Execution Flow
Compute cutoffs, count or delete per category, record and commit only when applying.

## G. Input and Output
Output, for example: `Would delete 2 expired_sessions older than 2026-11-02T12:00:00+00:00`.

## H. Important Technical Concepts
- **Sessions** are judged by when they ended: `LEAST(expires_at, revoked_at)`, so a session revoked eight days ago goes even though its expiry was later; a live session is never removed.
- **`SESSION_DAYS`, `AUDIT_DAYS`, `RATE_LIMIT_DAYS`** are 7, 365 and 1. One day is far beyond any rate-limit window, so no current count changes.
- **`CATEGORIES`** lists the four record kinds.

## I. Example
```powershell
python -m app.commands.retention          # dry run
python -m app.commands.retention --apply  # delete
```

## J. Maintenance Notes
Change a period only with the owner's approval and update the tests' boundaries.

## K. Related Files
- [test_retention.py](../../tests/integration/test_retention.py.explanation.md): boundary tests.
