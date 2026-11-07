# test_investigations.py

Source: [backend/tests/api/test_investigations.py](test_investigations.py)

## A. File Purpose
Tests the investigation workflow through the real API: statuses, history, notes, assignment, access and simultaneous changes.

## B. Why This File Exists
PRD 14.2 requires tests of investigation updates, and PRD 6.7 requires a history of changes. These tests also prove that the workflow never alters model output.

## C. Dependencies
- **Libraries:** `pytest`, `sqlalchemy`, `concurrent.futures`.
- **Internal modules:** `app.models`, `app.security.tokens`, API fixtures.
- **External services / database:** PostgreSQL and the frozen model.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `investigator`
Fixture returning headers for an investigator.

### `case`
Fixture that stores a flagged prediction, which opens an investigation, and returns the response.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_flag_opens_a_new_investigation_listed_with_its_score` | A flag opens one `NEW` investigation, listed with the workflow statement. |
| `test_every_prd_status_can_be_set` | Each PRD 6.7 status works. |
| `test_prd_statuses_are_exactly_these` | The list matches the PRD. |
| `test_invalid_status_is_refused` | `CONFIRMED_FRAUD` and null are refused. |
| `test_empty_update_is_refused` | An empty body gives 422. |
| `test_status_history_records_each_change_in_order` | The full chain, including who made each change. |
| `test_setting_the_same_status_adds_no_history` | No noise in the history. |
| `test_status_change_is_audited` | An audit entry is written. |
| `test_workflow_status_never_changes_the_prediction` | `FALSE_ALARM` leaves the score and decision as they were. |
| `test_notes_are_saved_with_author_and_shown_on_the_transaction` | Notes reach the PRD 6.6 detail view. |
| `test_note_text_is_not_copied_to_the_audit_log` | Note content stays out of the log. |
| `test_invalid_notes_are_refused` | Blank and over-long notes give 422. |
| `test_note_changes_updated_at` | The timestamp moves. |
| `test_assignment_and_unassignment` | Both directions, and the filter. |
| `test_assignee_must_be_an_active_investigator` | Other roles and inactive users are refused. |
| `test_unknown_assignee_is_refused_and_nothing_changes` | A failed update also leaves the status alone. |
| `test_list_filters_by_status` | The status filter. |
| `test_analyst_can_view_but_not_change` | PRD 2.1 and 2.2 access. |
| `test_demo_user_has_no_access` | 403 throughout. |
| `test_admin_can_update` | Administrators can act. |
| `test_unknown_investigation_is_not_found` | 404 on each route. |
| `test_simultaneous_changes_keep_the_history_consistent` | With many parallel changes, each history row starts from the status the previous one left, which row locking guarantees. |

## E. Classes Explained
None.

## F. Execution Flow
The `case` fixture creates an investigation, and the test acts on it.

## G. Input and Output
Input: HTTP requests. Output: pass or fail.

## H. Important Technical Concepts
- **Atomicity test:** `test_unknown_assignee_is_refused_and_nothing_changes` sends a valid status together with a bad assignee, and proves neither is applied.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_investigations.py
```

## J. Maintenance Notes
If transition rules are added, `test_every_prd_status_can_be_set` and the history test need updating.

## K. Related Files
- [investigation_service.py](../../app/services/investigation_service.py.explanation.md): the rules.
- [investigations.py repository](../../app/repositories/investigations.py.explanation.md): locking.
