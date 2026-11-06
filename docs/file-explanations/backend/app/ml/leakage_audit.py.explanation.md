# leakage_audit.py

Source: [backend/app/ml/leakage_audit.py](../../../../../backend/app/ml/leakage_audit.py)

## A. File Purpose
Proves that excluded information cannot reach the model, and measures why those exclusions matter.

## B. Why This File Exists
Phase 1's acceptance criteria require a leakage audit. Published PaySim results often report near-perfect scores by using balance columns, so this project needs a repeatable check instead of a promise. Separating the audit from preparation means it inspects the actual output files rather than trusting the code that wrote them.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `pyarrow`, `scikit-learn` (`roc_auc_score`), `pathlib`, `typing`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.features`, `app.ml.pipeline_io`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** `scripts/audit_leakage.py`, `test_data_pipeline.py`.

## D. Every Function Explained

### `assert_feature_schema_clean`
- **Purpose:** enforce the declared schema rules.
- **Parameters / types:** none.
- **Returns / type:** `dict[str, Any]` with `passed` and the feature list.
- **Internal processing:** intersects features with the forbidden set; checks each feature's availability flag.
- **Error handling:** raises `LeakageError`.
- **Calls:** none. **Used by:** `run_leakage_audit`, tests.

### `assert_processed_files_clean`
- **Purpose:** inspect the real files on disk.
- **Parameters / types:** `processed_dir: Path`, `boundaries: SplitBoundaries`.
- **Returns / type:** `dict[str, Any]` with observed step ranges.
- **Internal processing:** reads each Parquet schema and step column, then compares ranges with the boundaries.
- **Error handling:** raises `LeakageError` for a leaky column or a time overlap.
- **Calls:** `partition_path`, `pyarrow.parquet`. **Used by:** `run_leakage_audit`, tests.

### `_separation`
- **Purpose:** measure how well one column separates the classes.
- **Parameters / types:** `labels: np.ndarray`, `scores: np.ndarray`.
- **Returns / type:** `dict[str, float]` with `roc_auc` and `separation`, `max(auc, 1 - auc)`.
- **Internal processing / errors:** direct calculation; scikit-learn raises if only one class is present.
- **Calls:** `roc_auc_score`. **Used by:** `measure_training_signal`.

### `_rate_by_class`
- **Purpose:** compare how often a condition holds for each class.
- **Parameters / types:** `flag: pd.Series`, `labels: pd.Series`.
- **Returns / type:** `dict[str, float]` with `fraud` and `legitimate`.
- **Internal processing / errors:** means per class; no special handling.
- **Calls:** pandas. **Used by:** `measure_training_signal`.

### `measure_training_signal`
- **Purpose:** gather evidence for the exclusions without touching validation or test labels.
- **Parameters / types:** `raw_path: Path`, `boundaries: SplitBoundaries`, `chunk_size: int`.
- **Returns / type:** `dict[str, Any]`.
- **Internal processing:** keeps only training rows, then measures each balance column, two derived balance errors, each selected feature and three balance behaviours.
- **Error handling:** propagates read and metric errors.
- **Calls:** `engineer_features`, `raw_to_prediction_inputs`, `_separation`, `_rate_by_class`, `label_values_by_category`. **Used by:** `run_leakage_audit`, tests.

### `label_values_by_category`
- **Purpose:** turn a category into a score, by its in-sample fraud rate.
- **Parameters / types:** `categories: pd.Series`, `labels: pd.Series`.
- **Returns / type:** `dict[str, float]`.
- **Internal processing:** groups labels by category and averages them.
- **Error handling:** none needed.
- **Calls:** pandas. **Used by:** `measure_training_signal`. This is descriptive only and is not suitable for model features.

### `run_leakage_audit`
- **Purpose:** run everything and return one report.
- **Parameters / types:** `raw_path: Path`, `processed_dir: Path`, `boundaries: SplitBoundaries`, `chunk_size: int`.
- **Returns / type:** `dict[str, Any]`.
- **Internal processing:** calls the three checks in order.
- **Error handling:** a broken rule raises `LeakageError`.
- **Calls:** the three checks above. **Used by:** `scripts/audit_leakage.py`, tests.

## E. Classes Explained

### `LeakageError`
- **Responsibility:** a distinct exception for a broken hard rule, so scripts can exit with a clear failure.
- **Constructor / attributes / methods:** inherited from `RuntimeError`.
- **Usage:** raised by the two assert functions, caught in `scripts/audit_leakage.py`.

## F. Execution Flow
Schema check, then file check, then training-only signal measurement. A failed check raises before any signal is computed.

## G. Input and Output
Input: raw CSV, processed folder, boundaries. Output: `experiments/results/leakage_audit.json`.

## H. Important Technical Concepts
- **Hard rules versus evidence:** the first two checks are pass or fail. Signal numbers explain the decisions and do not decide anything automatically.
- **What the evidence shows on real training rows:** a derived origin balance error reaches a separation of 0.919, and the balance reconciles exactly in 99.1% of fraud rows against 20.3% of legitimate rows. That pattern describes the simulator's bookkeeping, not anything knowable before a transaction completes.
- **High separation does not mean leakage:** `transaction_type` scores 0.849 but is genuinely known at request time. Leakage concerns when information becomes available, not how strong it is.
- **Single-column numbers are not model estimates.** Combined performance is measured in Phase 2.

## I. Example
```python
report = run_leakage_audit(RAW_CSV_PATH, PROCESSED_DIR, boundaries)
report["processed_file_check"]["passed"]  # True
```

## J. Maintenance Notes
Add a new forbidden source to `schema.py` so this audit picks it up. Keep signal measurement restricted to training rows; `test_signal_audit_uses_training_rows_only` protects this.

## K. Related Files
- [schema.py](schema.py.explanation.md): rules.
- [audit_leakage.py](../../../scripts/audit_leakage.py.explanation.md): command-line wrapper.
- [test_data_pipeline.py](../../tests/integration/test_data_pipeline.py.explanation.md): tests, including tampered files.
