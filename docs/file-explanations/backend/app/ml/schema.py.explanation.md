# schema.py

Source: [backend/app/ml/schema.py](../../../../../backend/app/ml/schema.py)

## A. File Purpose
Declares what the data pipeline may read and what the model may see: raw PaySim columns, excluded columns, the four prediction inputs, the feature dictionary, rejected feature candidates and the feature schema version.

## B. Why This File Exists
Leakage rules only hold if there is one definition of them. Validation, feature engineering, partitioning, the leakage audit and (from Phase 3) the API all import these constants, so no module carries its own copy of a column list.

## C. Dependencies
- **Libraries:** `dataclasses` (standard library).
- **Internal modules:** none. This is the bottom of the dependency graph on purpose.
- **External services / database:** none.
- **Depended on by:** `features.py`, `dataset_validation.py`, `dataset_preparation.py`, `leakage_audit.py`, `eda.py`, `scripts/prepare_dataset.py`, and the tests.

## D. Every Function Explained

### `feature_dictionary_records`
- **Purpose:** produce the machine-readable feature dictionary saved to `artifacts/metadata/feature_dictionary_v1.json`.
- **Parameters / types:** none.
- **Returns / type:** `dict` with `feature_schema_version`, `features` and `rejected_features`.
- **Internal processing:** converts each frozen dataclass to a plain dictionary with `asdict`.
- **Error handling:** none needed; the input is constant data.
- **Calls:** `dataclasses.asdict`.
- **Used by:** `scripts/prepare_dataset.py`, `test_schema.py`.

## E. Classes Explained

### `FeatureSpec`
- **Responsibility:** one row of the feature dictionary required by PRD 4.4.
- **Constructor / attributes:** `name`, `source_columns`, `transformation`, `data_type`, `kind` ("numeric" or "categorical"), `business_meaning`, `rationale`, `available_before_completion`.
- **Methods:** none (frozen dataclass).
- **Dependencies / usage:** instances populate `FEATURE_DICTIONARY`; `leakage_audit.py` reads `available_before_completion`.

### `RejectedFeature`
- **Responsibility:** records a candidate feature and why it was left out, so the decision is not re-litigated later.
- **Constructor / attributes:** `name`, `reason`.
- **Methods:** none (frozen dataclass).
- **Dependencies / usage:** populates `REJECTED_FEATURES`, exported with the feature dictionary.

## F. Execution Flow
Importing the module evaluates the constants. `FEATURE_COLUMNS`, `NUMERIC_FEATURES` and `CATEGORICAL_FEATURES` are derived from `FEATURE_DICTIONARY`, so adding a `FeatureSpec` updates all three.

## G. Input and Output
No runtime input. Output is constants plus the dictionary returned by `feature_dictionary_records`.

## H. Important Technical Concepts
- **`PIPELINE_RAW_COLUMNS` is an allow-list.** Balances and `nameOrig` are absent, so `read_csv(usecols=...)` never loads them. That is stronger than dropping them afterwards.
- **`FORBIDDEN_FEATURE_COLUMNS`** also includes processed tracking columns such as `step`: the raw step is stored for time-window evaluation but must not be a feature.
- **`step` is both an input and a forbidden feature.** Callers supply it, but only the derived hour features reach the model.
- **`destination_category` is redundant in PaySim.** Merchant occurs if and only if the type is PAYMENT (measured in `experiments/results/dataset_validation.json`). It stays because PRD 4.4 and 6.2 require it.

## I. Example
```python
from app.ml.schema import FEATURE_COLUMNS, FORBIDDEN_FEATURE_COLUMNS
assert not set(FEATURE_COLUMNS) & FORBIDDEN_FEATURE_COLUMNS
```

## J. Maintenance Notes
To add a feature: add a `FeatureSpec`, compute it in `features.py`, bump `FEATURE_SCHEMA_VERSION`, update the dictionary table in `DATASET_DOCUMENTATION.md`, rerun `scripts/prepare_dataset.py`, and retrain. Saved models are tied to the schema version, so any change here invalidates them.

## K. Related Files
- [features.py](features.py.explanation.md): computes the features declared here.
- [leakage_audit.py](leakage_audit.py.explanation.md): enforces the rules declared here.
- [test_schema.py](../../tests/unit/test_schema.py.explanation.md): tests them.
- `DATASET_DOCUMENTATION.md`: human-readable feature dictionary.
