# features.py

Source: [backend/app/ml/features.py](../../../../../backend/app/ml/features.py)

## A. File Purpose
Turns the four prediction inputs (amount, transaction type, step, destination category) into model features. It also converts raw PaySim rows into those same four inputs.

## B. Why This File Exists
Training/serving skew, where a model sees features computed differently in production, is a classic ML failure. With one function used by both paths, the two cannot diverge. The signature itself is a safeguard: only prediction inputs are read, so training cannot use a value serving will not have.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`.
- **Internal modules:** `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `dataset_preparation.py`, `leakage_audit.py`, `eda.py` (for `HOURS_PER_DAY`), tests, and the Phase 3 prediction service.

## D. Every Function Explained

### `destination_category_from_account`
- **Purpose:** map identifiers such as `C123` or `M456` to `customer` or `merchant`.
- **Parameters / types:** `accounts: pd.Series` of strings.
- **Returns / type:** `pd.Series` of category names.
- **Internal processing:** takes the first character and maps it through `DESTINATION_PREFIX_TO_CATEGORY`.
- **Error handling:** raises `ValueError` with examples if a prefix is unknown; it never guesses.
- **Calls:** pandas string and map operations.
- **Used by:** `raw_to_prediction_inputs`, tests.

### `raw_to_prediction_inputs`
- **Purpose:** express raw PaySim rows in the same shape as an API request.
- **Parameters / types:** `raw: pd.DataFrame` with `amount`, `type`, `step`, `nameDest`.
- **Returns / type:** `pd.DataFrame` with `PREDICTION_INPUT_COLUMNS`, same index.
- **Internal processing:** renames `type`, derives the destination category, copies the others.
- **Error handling:** a missing column raises `KeyError`; a bad prefix raises `ValueError`.
- **Calls:** `destination_category_from_account`.
- **Used by:** `dataset_preparation.py`, `leakage_audit.py`, tests.

### `_validate_inputs`
- **Purpose:** stop inputs that would silently produce wrong features.
- **Parameters / types:** `inputs: pd.DataFrame`.
- **Returns / type:** `None`.
- **Internal processing:** checks for missing columns, nulls, negative amounts or steps, and unknown categories.
- **Error handling:** raises `ValueError` naming the problem.
- **Calls:** pandas checks.
- **Used by:** `engineer_features`.

### `engineer_features`
- **Purpose:** the single implementation of feature computation.
- **Parameters / types:** `inputs: pd.DataFrame` containing `PREDICTION_INPUT_COLUMNS`; extra columns are ignored.
- **Returns / type:** `pd.DataFrame` with exactly `FEATURE_COLUMNS`, same index.
- **Internal processing:** computes `log1p(amount)`, `hour = step % 24`, sine and cosine of the hour angle, and fixed-category columns.
- **Error handling:** through `_validate_inputs`.
- **Calls:** `_validate_inputs`, `numpy.log1p`, `numpy.sin`, `numpy.cos`.
- **Used by:** `dataset_preparation.py`, `leakage_audit.py`, tests, and the Phase 3 prediction service.

## E. Classes Explained
None.

## F. Execution Flow
Offline: raw chunk, then `raw_to_prediction_inputs`, then `engineer_features`, then Parquet. Online from Phase 3: validated API request, then a one-row DataFrame, then `engineer_features`, then the model.

## G. Input and Output
Input row: `{amount: 100.0, transaction_type: "TRANSFER", step: 25, destination_category: "customer"}`.
Output columns: `amount`, `amount_log1p`, `transaction_type`, `destination_category`, `hour_of_day`, `hour_sin`, `hour_cos`.

## H. Important Technical Concepts
- **Statelessness:** one row's features never depend on other rows, so single and batch predictions agree. A test proves this.
- **Cyclical encoding:** as a plain number, hour 23 looks far from hour 0. Sine and cosine keep them adjacent, which matters for linear models and SMOTE's nearest-neighbour step.
- **Fixed categories:** a category absent from a chunk still has the same encoding, so partition files and one-row requests stay compatible.
- **Hour phase is an assumption:** PaySim defines one step as one hour but not which clock hour step 1 is. The trough at hours 3 to 5 looks like night, but the name is a convention.
- **Zero amounts:** accepted here because 16 real rows have them, and `log1p(0)` is defined. Whether the API accepts them is decided in Phase 3.

## I. Example
```python
inputs = pd.DataFrame({"amount": [100.0], "transaction_type": ["TRANSFER"],
                       "step": [25], "destination_category": ["customer"]})
engineer_features(inputs)["hour_of_day"].iloc[0]  # 1
```

## J. Maintenance Notes
Never add a feature that needs another row, a fitted statistic or an account history here. Fitted transforms belong in the Phase 2 pipeline. Any change here requires a schema version bump, a rerun of `prepare_dataset.py` and retraining.

## K. Related Files
- [schema.py](schema.py.explanation.md): declares the columns.
- [dataset_preparation.py](dataset_preparation.py.explanation.md): offline caller.
- [test_features.py](../../tests/unit/test_features.py.explanation.md): tests.
