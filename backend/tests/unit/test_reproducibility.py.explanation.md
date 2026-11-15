# test_reproducibility.py

Source: [backend/tests/unit/test_reproducibility.py](test_reproducibility.py)

## A. File Purpose
Tests the Phase 5 M1 isolation and reproducibility measures.

## B. Why This File Exists
Pins and database guards protect against silent drift and against wiping the wrong database, so each has a test.

## C. Dependencies
- **Libraries:** pytest.
- **Internal modules:** `scripts/e2e_database.py`, `scripts/e2e_stack.py`, `scripts/test_report.py`, `scripts/verify_clean_clone.py` through `load_script`.
- **External services / database:** Git (for `check-ignore`).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Reads repository files and calls the scripts' functions with controlled environments.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_dockerfile_base_image_and_uv_are_pinned` | Every `FROM` has a digest; uv has an exact version. |
| `test_compose_images_are_pinned_or_built_locally` | Every Compose image is digest-pinned or the local build. |
| `test_browser_tests_use_their_own_database` | The seed script derives `finguard_e2e_test` from `TEST_DATABASE_URL`. |
| `test_browser_test_database_must_be_a_test_database` | A non-test name in either variable is refused. |
| `test_stack_refuses_unsafe_database_names` | Wrong case, injection-shaped and non-test names are refused before reaching SQL. |
| `test_stack_accepts_the_default_name` | The default is accepted. |
| `test_compose_points_browser_tests_at_their_database` | Compose uses the same default. |
| `test_junit_report_counts_and_names_skips` | Totals, skip reasons and node ids, including test classes. |
| `test_inputs_a_clean_clone_lacks_are_ignored_by_git` | The clean-clone check's expected absences are really ignored. |

## H. Important Technical Concepts
- **`DIGEST`** matches `@sha256:` followed by 64 hex characters.
- **`UNSAFE_NAMES`** are database names the stack must refuse.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_reproducibility.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
When a pinned digest is updated on purpose, these tests still pass; they check that a pin exists, not its value.

## K. Related Files
- [verify_clean_clone.py](../../../scripts/verify_clean_clone.py.explanation.md): the clean-clone check.
