# test_splitting.py

Source: [backend/tests/unit/test_splitting.py](../../../../../backend/tests/unit/test_splitting.py)

## A. File Purpose
Tests chronological boundary selection and partition assignment.

## B. Why This File Exists
A boundary error would silently put future data in the training set. Temporal leakage like that inflates scores and is invisible in the output.

## C. Dependencies
- **Libraries:** `json`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `uniform_counts`
- **Purpose:** build per-step counts where rows equal steps in share.
- **Parameters / types:** `steps: int`, `rows: int`. **Returns / type:** `pd.Series`.
- **Internal processing / errors:** constructs the series; no special handling.
- **Calls:** pandas. **Used by:** tests in this file.

**Common to every test below:** the return is `None`, failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_boundaries_follow_cumulative_row_share` | none | 100 equal steps split at 70 and 85. |
| `test_boundaries_reflect_rows_not_step_numbers` | none | Boundaries follow rows: 70% of 10,900 rows ends at step 7. |
| `test_boundary_includes_a_step_landing_exactly_on_the_share` | none | The floating-point case `0.6 + 0.3` still includes step 3. This found a real bug. |
| `test_invalid_fractions_are_rejected` | `train`, `validation` | Impossible fractions raise `ValueError`. |
| `test_too_few_steps_is_rejected` | none | Three steps cannot make three valid partitions here. |
| `test_first_step_too_large_is_rejected` | none | A dominant first step raises `ValueError`. |
| `test_masks_cover_every_row_exactly_once` | none | Partitions neither overlap nor miss rows. |
| `test_masks_are_strictly_chronological` | none | Each partition starts right after the previous one ends. |
| `test_count_rows_per_step_handles_chunks` | `raw_csv` | Counting is correct when steps cross chunk boundaries. |
| `test_config_loads_from_json` | `tmp_path` | A valid config loads. |
| `test_config_missing_key_raises` | `tmp_path` | A missing key raises `KeyError`. |

## E. Classes Explained
None.

## F. Execution Flow
Most tests are in-memory. Three use files through fixtures.

## G. Input and Output
Input: constructed counts, a fixture CSV and config files. Output: pass or fail.

## H. Important Technical Concepts
Expected boundaries are worked out by hand in comments, so a test states the rule independently of the code.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_splitting.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If the boundary rule changes, update these tests deliberately, publish a new split config version, and rerun all later stages.

## K. Related Files
- [splitting.py](../../app/ml/splitting.py.explanation.md): code under test.
