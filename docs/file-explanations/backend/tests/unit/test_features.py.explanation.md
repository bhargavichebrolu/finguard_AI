# test_features.py

Source: [backend/tests/unit/test_features.py](../../../../../backend/tests/unit/test_features.py)

## A. File Purpose
Tests feature calculations, input rejection, and the guarantees training and serving rely on.

## B. Why This File Exists
The same feature code runs offline and online, so a bug here affects every model and every prediction.

## C. Dependencies
- **Libraries:** `math`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.features`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `make_inputs`
- **Purpose:** build a valid one-row input, overridable per test.
- **Parameters / types:** `**overrides` of column values. **Returns / type:** `pd.DataFrame`.
- **Internal processing / errors:** merges overrides into defaults; no special handling.
- **Calls:** pandas. **Used by:** tests in this file.

**Common to every test below:** parameters are pytest fixtures or parametrised values, the return is `None`, failures surface as `AssertionError`, and each calls `engineer_features` or `destination_category_from_account`. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_output_has_exact_columns_in_schema_order` | `raw_frame` | Output columns equal `FEATURE_COLUMNS`, with one row per input row. |
| `test_hour_wraps_at_24` | none | Steps 0, 23, 24, 25, 743 give hours 0, 23, 0, 1, 23. |
| `test_cyclical_encoding_places_hour_on_the_unit_circle` | none | Hour 6 has sine 1 and cosine 0. |
| `test_amount_log_transform_handles_zero` | none | `log1p(0)` is 0, and `log1p(e - 1)` is 1. |
| `test_labels_and_balances_cannot_change_features` | `raw_frame` | Changing labels, flags, origin account and all balances leaves the features identical. This is the key leakage test. |
| `test_extra_input_columns_are_ignored` | none | Extra columns such as `isFraud` have no effect. |
| `test_single_row_matches_the_same_row_in_a_batch` | `raw_frame` | Single and batch predictions get the same features. |
| `test_invalid_inputs_are_rejected` | `overrides`, `message` | Negative values, nulls and unknown categories raise `ValueError`. |
| `test_missing_input_column_is_rejected` | none | A missing column raises `ValueError`. |
| `test_destination_category_mapping` | none | C maps to customer, and M to merchant. |
| `test_unknown_destination_prefix_is_rejected` | none | An unknown prefix raises `ValueError`. |

## E. Classes Explained
None.

## F. Execution Flow
pytest runs each test; `test_invalid_inputs_are_rejected` runs once per parameter set.

## G. Input and Output
Input: small hand-built frames and the shared fixture. Output: pass or fail.

## H. Important Technical Concepts
Behavioural leakage tests are stronger than checking column names: tampering with the forbidden values and comparing outputs proves they have no influence at all.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_features.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Add a test for each new feature with a hand-calculated expected value. If stored features change intentionally, also bump the schema version.

## K. Related Files
- [features.py](../../app/ml/features.py.explanation.md): code under test.
- [conftest.py](../conftest.py.explanation.md): `raw_frame` fixture.
