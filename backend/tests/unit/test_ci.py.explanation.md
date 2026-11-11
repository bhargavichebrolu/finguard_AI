# test_ci.py

Source: [backend/tests/unit/test_ci.py](test_ci.py)

## A. File Purpose
Tests for Phase 5 M8: the skip comparison in `check_test_run.py`, the committed expectations, and safety rules for the CI workflow.

## B. Why This File Exists
The workflow cannot run until it is pushed. What can be checked locally is checked here: that the comparison fails in every case the approval names (unexpected skips, missing test execution), that the expectations file holds only acceptable skip reasons, and that the workflow is pinned, read-only and runs every required check.

## C. Dependencies
- **Libraries:** pytest, standard library.
- **Internal modules:** `scripts/check_test_run.py` and `scripts/verify_clean_clone.py`, loaded with the `load_script` fixture.
- **External services / database:** none.
- **Depended on by:** the backend suite (and therefore CI itself).

## D. Every Function Explained

### `checker`
Fixture: a freshly loaded `check_test_run` module.

### `write_junit`
Writes a small JUnit file and an empty `tests/unit/test_x.py`, so node ids resolve as in a real run.

### `run_compare`
Reads a written report and compares it with the given expectations.

### `test_the_expected_run_passes_and_states_what_was_not_verified`
A run matching the list passes, and its summary counts skips by reason and includes the note about real-model inference.

### `test_an_unexpected_skip_fails`
A database test skipping because `TEST_DATABASE_URL` is unset fails the check, naming the test and reason.

### `test_an_expected_skip_that_ran_or_disappeared_fails`
A listed skip that did not happen fails.

### `test_a_skip_for_a_different_reason_fails`
The same test skipping for another reason fails.

### `test_failures_and_errors_fail`
Failures are reported as problems.

### `test_fewer_passing_tests_than_recorded_fails`
Fewer passes than `minimum_passed` fails.

### `test_missing_or_empty_results_fail`
No result file, or a file with no tests, fails.

### `test_main_fails_without_results_and_writes_the_summary`
The command line exits 1 without results and still writes the job summary.

### `test_update_records_the_run_but_refuses_failures`
`--update` records skips and passes, keeps the notes, and refuses a run with an error.

### `test_committed_expectations_are_consistent`
The committed file has both suites, positive minimums, no frontend skips, only the three exact skip reasons in `ACCEPTABLE_SKIP_REASONS` (model binary absent, in two wordings, or dataset absent; an earlier pattern match would have accepted "TEST_DATABASE_URL is not set", so exact strings are used), node ids whose files exist, not the deselected test, and the "NOT verified in CI" note.

### `test_workflow_pins_actions_and_keeps_permissions_read_only`
Every action is pinned to a 40-character commit hash; permissions are `contents: read`; no repository secret is used; credentials are not persisted; nothing mentions `trust` authentication.

### `test_workflow_runs_every_required_check`
Each required command appears in the workflow, and the checks after the tests still run when an earlier step fails.

### `test_workflow_and_clean_clone_check_agree_on_absent_inputs`
The workflow checks the same absent inputs as `verify_clean_clone.py`.

## E. Classes Explained
None.

## F. Execution Flow
Ordinary pytest unit tests; no database.

## G. Input and Output
Inputs are hand-written JUnit fragments and the committed workflow and expectations.

## H. Important Technical Concepts
- **Text checks on YAML:** the project has no YAML parser dependency, so the workflow is checked as text. These tests catch removed checks and unpinned actions; they do not prove the workflow runs, which only GitHub can.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_ci.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
When a check is added to or removed from the workflow, update the command list in `test_workflow_runs_every_required_check`.

## K. Related Files
- [check_test_run.py](../../../scripts/check_test_run.py.explanation.md)
- [ci.yml](../../../.github/workflows/ci.yml.explanation.md)
- [expected-tests.json](../../../.github/expected-tests.json.explanation.md)
