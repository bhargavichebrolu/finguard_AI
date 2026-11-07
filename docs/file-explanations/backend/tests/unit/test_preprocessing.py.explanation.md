# test_preprocessing.py

Source: [backend/tests/unit/test_preprocessing.py](../../../../../backend/tests/unit/test_preprocessing.py)

## A. File Purpose
Tests the shared preprocessing step.

## B. Why This File Exists
A difference between training and serving inputs would silently degrade a deployed model. PRD 14.1 requires a preprocessing consistency test.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.features`, `app.ml.preprocessing`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `sample_features`
- **Purpose:** build three feature rows.
- **Parameters / types:** none. **Returns / type:** `pd.DataFrame`.
- **Internal processing / errors:** calls `engineer_features`; no special handling.
- **Calls:** `engineer_features`. **Used by:** tests in this file.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_output_columns_are_one_hot_then_numeric` | none | Column order is fixed and named. |
| `test_output_is_float32` | none | The matrix is single precision. |
| `test_one_hot_encodes_all_categories_even_if_absent_from_fit_rows` | none | Categories come from the schema, not the rows. |
| `test_serving_float64_matches_training_float32` | none | A served row becomes exactly what a training row became. |
| `test_unseen_category_raises` | none | An unknown type fails loudly. |
| `test_dropped_features_are_absent` | none | Sensitivity runs truly remove features. |
| `test_unknown_dropped_feature_raises` | none | A typo in a dropped name fails. |
| `test_scaling_is_centred_on_fit_rows_only` | none | The scaler is fixed by the fit rows. |
| `test_compact_features_leaves_the_input_unchanged` | none | Compacting does not alter the original frame. |
| `test_to_float32_does_not_copy_when_already_float32` | none | The cast saves memory on training data. |

## E. Classes Explained
None.

## F. Execution Flow
All tests run in memory.

## G. Input and Output
Input: three constructed rows. Output: pass or fail.

## H. Important Technical Concepts
`test_serving_float64_matches_training_float32` guards against training/serving skew arising from numeric precision.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_preprocessing.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
A change in column order breaks saved models, so treat a failure of the first test as a model-version change.

## K. Related Files
- [preprocessing.py](../../app/ml/preprocessing.py.explanation.md): code under test.
