# test_imbalance.py

Source: [backend/tests/unit/test_imbalance.py](../../../../../backend/tests/unit/test_imbalance.py)

## A. File Purpose
Tests that SMOTE and ADASYN produce valid rows, and that only one module can call them.

## B. Why This File Exists
PRD 5.2 requires meaningful synthetic samples, and oversampling inside the training pipeline only. A Phase 2 acceptance criterion is that no oversampling leakage exists.

## C. Dependencies
- **Libraries:** `ast`, `pathlib`, `numpy`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.features`, `app.ml.imbalance`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `method`
- **Purpose:** a fixture that repeats a test for SMOTE and ADASYN.
- **Parameters / types:** `request`. **Returns / type:** `str`.
- **Internal processing / errors:** returns the parameter; no special handling.
- **Calls:** nothing. **Used by:** the tests below.

### `result`
- **Purpose:** a fixture holding one oversampled fold.
- **Parameters / types:** `model_partition`, `method`. **Returns / type:** `OversampleResult`.
- **Internal processing / errors:** calls the function under test; no special handling.
- **Calls:** `oversample_training_fold`. **Used by:** the tests below.

### `synthetic_part`
- **Purpose:** return only the appended rows.
- **Parameters / types:** `result`, `original_rows: int`. **Returns / type:** `(features, labels)`.
- **Internal processing / errors:** slices past the original rows; no special handling.
- **Calls:** pandas. **Used by:** the tests below.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_original_rows_are_kept_unchanged_and_first` | `result`, `model_partition` | Real rows are untouched. |
| `test_only_fraud_rows_are_added` | `result`, `model_partition` | No synthetic legitimate rows. |
| `test_synthetic_rows_only_use_types_that_contain_fraud` | `result`, `model_partition` | No invented type or destination. |
| `test_synthetic_rows_obey_the_feature_rules` | `result`, `model_partition` | Whole hours, valid amounts, and features match the shared code. |
| `test_synthetic_amounts_stay_within_the_fraud_range` | `result`, `model_partition` | Interpolation, not extrapolation. |
| `test_target_ratio_is_reached_per_type` | `result`, `model_partition` | The requested ratio is achieved. |
| `test_same_seed_gives_the_same_rows_and_another_seed_does_not` | `model_partition`, `method` | Reproducibility. |
| `test_input_frame_is_not_modified` | `model_partition`, `method` | No side effects. |
| `test_type_with_too_little_fraud_is_skipped_and_reported` | `model_partition` | The skip is visible in the report. |
| `test_type_already_above_target_is_left_alone` | `model_partition` | No rows are added without need. |
| `test_unknown_method_is_rejected` | `model_partition` | Invalid method raises. |
| `test_mismatched_lengths_are_rejected` | `model_partition` | Invalid input raises. |
| `test_only_experiments_module_calls_the_oversampler` | none | A syntax-tree scan finds one caller only. |

## E. Classes Explained
None.

## F. Execution Flow
Fixtures build a synthetic fold, and each test checks one property.

## G. Input and Output
Input: the synthetic partition from `conftest.py`. Output: pass or fail.

## H. Important Technical Concepts
The final test reads source code rather than behaviour. It makes the containment rule break the build if someone later calls the oversampler from another module.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_imbalance.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Treat a failure of the last test as a leakage alarm.

## K. Related Files
- [imbalance.py](../../app/ml/imbalance.py.explanation.md): code under test.
- [conftest.py](../conftest.py.explanation.md): the fixture.
