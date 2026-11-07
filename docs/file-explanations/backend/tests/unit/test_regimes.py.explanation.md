# test_regimes.py

Source: [backend/tests/unit/test_regimes.py](../../../../../backend/tests/unit/test_regimes.py)

## A. File Purpose
Tests the sparse and normal step definition.

## B. Why This File Exists
The authorisation requires a label-independent definition. These tests pin the rule and prove that it takes no label as input.

## C. Dependencies
- **Libraries:** `inspect`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.regimes`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

**Common to every test below:** the return is `None`, and failures surface as `AssertionError`. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_cutoff_is_strict` | none | 999 is sparse, while 1,000 and 1,001 are not. |
| `test_invalid_cutoff_is_rejected` | none | A zero cut-off raises `ValueError`. |
| `test_rows_per_step_counts_in_step_order` | none | Counts are correct and sorted by step. |
| `test_masks_cover_every_row_exactly_once` | none | A row is in exactly one regime. |
| `test_definition_takes_no_label_input` | none | No function has a label parameter. |
| `test_default_cutoff_matches_phase_1` | none | The cut-off still equals the value fixed in Phase 1. |

## E. Classes Explained
None.

## F. Execution Flow
All tests run in memory.

## G. Input and Output
Input: constructed step numbers. Output: pass or fail.

## H. Important Technical Concepts
Inspecting function signatures turns the label-independence requirement into something a test can fail on.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_regimes.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Changing the cut-off should fail `test_default_cutoff_matches_phase_1`, which prompts a deliberate decision and a full rerun.

## K. Related Files
- [regimes.py](../../app/ml/regimes.py.explanation.md): code under test.
