# test_retention.py

Source: [backend/tests/integration/test_retention.py](test_retention.py)

## A. File Purpose
Tests the retention command's cutoffs, boundaries, dry run, exact deletion and audit record.

## B. Why This File Exists
The approval required tests for boundary dates and deletion correctness, and that active sessions and records within their periods are preserved.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy.
- **Internal modules:** `app.commands.retention`, `app.models.records`.
- **External services / database:** PostgreSQL (`finguard_test`).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `db`
Fixture: an empty test database session.

### `add_session`
Adds a session with chosen expiry and revocation times.

### `records`
Fixture: sessions, audit entries and rate-limit rows one second either side of each cutoff and exactly at it, plus a live and a recently revoked session.

### `counts`
Counts the rows the tests created.

## E. Classes Explained
None.

## F. Execution Flow
Create rows at known times relative to a fixed `NOW`, then run the command.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_dry_run_reports_counts_and_cutoffs_and_deletes_nothing` | Counts and cutoffs, nothing deleted. |
| `test_apply_deletes_exactly_what_the_dry_run_reported` | Only rows before their cutoff go; rows at the cutoff, live sessions and recent records stay. |
| `test_applying_is_recorded_and_running_again_deletes_nothing` | Audit entry with counts and cutoffs; a second run deletes nothing. |
| `test_the_command_is_a_dry_run_unless_told_to_apply` | The command line defaults to a dry run. |

## H. Important Technical Concepts
- **`NOW`, `SECOND` and the three cutoffs** pin every boundary.
- **`EXPECTED`** is the per-category count both modes must report.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_retention.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Keep a row at, just before and just after every cutoff.

## K. Related Files
- [retention.py](../../app/commands/retention.py.explanation.md): the command.
