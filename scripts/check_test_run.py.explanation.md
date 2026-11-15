# check_test_run.py

Source: [scripts/check_test_run.py](check_test_run.py)

## A. File Purpose
Compares one test run's JUnit report with the committed expectations in `.github/expected-tests.json`, and fails when tests are missing, failing, or skipped differently from the list.

## B. Why This File Exists
The Phase 5 approval requires CI to run every test that does not need the missing model binary, keep an explicit expected-skip list, and fail on unexpected skips or missing test execution. pytest itself treats a skip as a success, so a database outage in CI, a broken import or a deleted test file could turn hundreds of tests into silent skips. This script makes those cases fail.

## C. Dependencies
- **Libraries:** Python standard library only (`argparse`, `json`, `collections`, `dataclasses`), so the frontend CI job can run it with the runner's own Python.
- **Internal modules:** `test_report.py` (`TestReport`, `read_junit`).
- **External services / database:** none.
- **Depended on by:** `.github/workflows/ci.yml` (both jobs); `backend/tests/unit/test_ci.py`.

## D. Every Function Explained

### `passed`
A property of `Outcome`: true when no problem was found.

### `load_expectations`
- **Purpose:** read one suite's entry from the expectations file.
- **Parameters / types:** `path: Path`, `suite: str`. **Returns / type:** `dict` with `minimum_passed`, `skipped` and `notes`.
- **Error handling:** an unknown suite stops the script with a message. **Used by:** `main`.

### `compare`
- **Purpose:** the check itself.
- **Parameters / types:** `report: TestReport | None` (None when no result file exists), `expected: dict`. **Returns / type:** `Outcome`.
- **Internal processing:** records a problem for: no result file; no tests; any failure or error; each skip not in the list; each listed skip that did not happen (the test ran, or no longer exists); each skip whose reason differs from the recorded one; fewer passes than `minimum_passed`. It also writes summary lines: totals, a count per skip reason, and the suite's notes.
- **Calls:** none. **Used by:** `main`, tests.

### `updated_expectations`
Builds a suite entry from a run (passes become the new minimum, skips sorted by node id), keeping the existing notes.

### `render_summary`
Formats an `Outcome` as Markdown for the GitHub job summary (`$GITHUB_STEP_SUMMARY`) and the log.

### `main`
- **Parameters / types:** `suite` (`backend` or `frontend`), the JUnit file, `--expected` (defaults to the committed file), `--summary FILE`, `--update`. **Returns / type:** exit code.
- **Internal processing:** reads the report with the suite's root folder (`SUITE_ROOTS`), then either compares and prints the summary (exit 1 on any problem), or with `--update` rewrites the suite's entry.
- **Error handling:** `--update` refuses a missing run or one with failures or errors, so a broken run can never become the expectation.

## E. Classes Explained
### `Outcome`
A dataclass holding `problems` (each makes the check fail) and `lines` (reported either way).

## F. Execution Flow
CI runs the tests with JUnit output, then this script with `--summary`. A deliberate change to the skipped set is made locally with `--update`, then reviewed as a diff of the expectations file.

## G. Input and Output
Input: a JUnit XML report (pytest or Vitest). Output: a printed and optionally appended Markdown summary; exit 0 or 1; with `--update`, a rewritten expectations file.

## H. Important Technical Concepts
- **Exact match, not a subset:** a listed test that stops skipping also fails. Otherwise the list would go stale, and a later, unrelated skip of that test would pass unnoticed.
- **Reasons are compared:** the same test skipping for a different reason means something else is wrong, for example a database test skipping because `TEST_DATABASE_URL` is unset rather than because the model is absent.
- **Minimum passed:** catches tests that disappear without skipping, such as a file pytest can no longer collect. Adding tests is fine; removing them needs `--update` and a reviewed change.
- **Vitest reports:** Vitest names test cases by file path, which `node_id` keeps as `file::name`. The frontend list expects no skips.

## I. Example
```powershell
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml --junitxml=pytest.xml --deselect tests/integration/test_real_models.py::test_test_results_can_be_recalculated_from_the_saved_model
python scripts/check_test_run.py backend pytest.xml
```

## J. Maintenance Notes
Record a new expectation only from a clean checkout with a database (TESTING_GUIDE.md, "Continuous integration (Phase 5 M8)"), never from a working copy that holds the model or dataset, which would run tests CI cannot.

## K. Related Files
- [test_report.py](test_report.py.explanation.md): report reading.
- [ci.yml](../.github/workflows/ci.yml.explanation.md): the workflow that runs it.
- [expected-tests.json](../.github/expected-tests.json.explanation.md): the expectations.
- [test_ci.py](../backend/tests/unit/test_ci.py.explanation.md): its tests.
