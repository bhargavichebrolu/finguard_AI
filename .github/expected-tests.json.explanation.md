# expected-tests.json

Source: [.github/expected-tests.json](expected-tests.json)

## A. File Purpose
The committed expectations CI checks each test run against: for the `backend` and `frontend` suites, the minimum number of passing tests, every test expected to skip on a clean checkout with its exact skip reason, and notes printed on every run.

## B. Why This File Exists
The Phase 5 approval (decision 6) requires "an explicit, fixed list of tests requiring the unavailable model binary", and that "unexpected changes to the skipped-test set must fail CI". This file is that list. A change to it shows up as a diff in review.

## C. Dependencies
- **Libraries:** none (JSON data).
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `scripts/check_test_run.py`; `backend/tests/unit/test_ci.py`.

## D. Every Function Explained
No functions. Keys per suite:
- **`minimum_passed`:** fewer passes fails CI (tests lost or not collected).
- **`skipped`:** pytest node id (relative to `backend/`) to skip reason. Must match the run exactly.
- **`notes`:** lines added to the job summary. The backend notes state that real-model inference, the API tests and the browser tests are not verified by CI.

## E. Classes Explained
None.

## F. Execution Flow
Read by `check_test_run.py` after each test step in CI.

## G. Input and Output
Written by `check_test_run.py --update` from a run on a fresh clone with a database, then committed.

## H. Important Technical Concepts
- **Only two reasons are allowed:** the frozen model binary is absent, or the dataset and processed partitions are absent. `test_ci.py` refuses any other reason, so a skip caused by a missing database or service can never be recorded as expected.
- **The deselected test** (`test_test_results_can_be_recalculated_from_the_saved_model`) is not listed: it is deselected, not skipped.
- **Frontend:** no skips are allowed.

## I. Example
```json
"tests/unit/test_model_service.py::test_altered_model_file_is_refused_before_loading": "frozen model file is absent"
```

## J. Maintenance Notes
Never edit counts or skips by hand to make CI pass. Rerun on a fresh clone, use `--update`, and explain the change in the commit.

## K. Related Files
- [ci.yml](workflows/ci.yml.explanation.md): the workflow.
- [check_test_run.py](../scripts/check_test_run.py.explanation.md): the comparison.
