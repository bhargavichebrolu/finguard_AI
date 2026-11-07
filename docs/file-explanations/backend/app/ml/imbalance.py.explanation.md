# imbalance.py

Source: [backend/app/ml/imbalance.py](../../../../../backend/app/ml/imbalance.py)

## A. File Purpose
Generates synthetic fraud rows with SMOTE or ADASYN, in a form where each synthetic row is still a possible transaction.

## B. Why This File Exists
PRD 5.2 allows these methods only where the representation supports meaningful synthetic samples. Applied directly to the feature table they would produce impossible rows, such as 0.4 of a TRANSFER, hour 13.7, or an `amount_log1p` that disagrees with `amount`. This module avoids that.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `imbalanced-learn`, `scikit-learn`.
- **Internal modules:** `app.ml.features`, `app.ml.preprocessing`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `experiments.fit_candidate` only. A test enforces that.

## D. Every Function Explained

### `_build_sampler`
- **Purpose:** create the sampler.
- **Parameters / types:** `method: str`; `target_ratio: float`; `k_neighbors: int`; `seed: int`.
- **Returns / type:** an imbalanced-learn sampler.
- **Internal processing:** chooses `SMOTE` or `ADASYN`.
- **Error handling:** `ValueError` for an unknown method.
- **Calls:** imbalanced-learn constructors.
- **Used by:** `_synthesise_for_type`.

### `_reconstruct_rows`
- **Purpose:** turn interpolated values back into valid feature rows.
- **Parameters / types:** `latent_rows: np.ndarray` of log amount, sine and cosine; `transaction_type: str`; `destination_category: str`.
- **Returns / type:** `pd.DataFrame` of features.
- **Internal processing:** recovers the hour with `arctan2` and rounds it to a whole hour, recovers the amount with `expm1`, then calls `engineer_features`.
- **Error handling:** amounts are floored at 0. `engineer_features` validates the rest.
- **Calls:** `engineer_features`.
- **Used by:** `_synthesise_for_type`.

### `_synthesise_for_type`
- **Purpose:** generate rows for one transaction type.
- **Parameters / types:** `features`, `labels` for one type; `method`, `target_ratio`, `k_neighbors`, `seed`.
- **Returns / type:** `pd.DataFrame` holding only the new rows.
- **Internal processing:** standardises the three continuous values so that distances are meaningful, runs the sampler, takes the rows appended after the originals, reverses the scaling, and rebuilds them.
- **Error handling:** errors from the sampler, such as ADASYN finding no eligible neighbours, propagate. `experiments.run_candidate` records them as a failed run, so a failure stays visible.
- **Calls:** `_build_sampler`, `_reconstruct_rows`.
- **Used by:** `oversample_training_fold`.

### `oversample_training_fold`
- **Purpose:** the module's public entry point.
- **Parameters / types:** `features: pd.DataFrame`; `labels: np.ndarray`; `method: str`; `target_ratio: float`; `k_neighbors: int`; `seed: int`.
- **Returns / type:** `OversampleResult`.
- **Internal processing:** loops over transaction types and skips any with too little fraud or already at target. Original rows stay first, in their original order.
- **Error handling:** `ValueError` if lengths differ.
- **Calls:** `_synthesise_for_type`, `compact_features`.
- **Used by:** `experiments.fit_candidate`.

## E. Classes Explained

### `OversampleResult`
A dataclass holding `features`, `labels` and `report`. The report states how many rows were added per type, so the result can be checked.

## F. Execution Flow
Split by transaction type, skip types without enough fraud, standardise, generate rows, reconstruct through `engineer_features`, append to the originals.

## G. Input and Output
Input: rows from one training fold. Output: the same rows plus synthetic fraud rows. No legitimate rows are created or removed.

## H. Important Technical Concepts
**SMOTE** creates a new fraud row on the line between a fraud row and a nearby fraud row. **ADASYN** does the same, but generates more rows around fraud that has many legitimate neighbours, which are the harder cases.

**Why per type:** a line between a TRANSFER and a CASH_OUT has no meaning. Within one type, only amount and hour vary, and both can be interpolated.

**Why a target ratio of 0.1 rather than full balance:** full balance would add over 1.9 million synthetic rows, far outnumbering the 3,633 real fraud rows they derive from, and would cost memory the machine does not have. The ratio is in the config, and sensitivity runs try others.

**Limitations:** interpolating between two opposite hours, such as 06:00 and 18:00, passes near the centre of the clock, so the recovered hour is not meaningful. Synthetic rows also cannot contain information that the real rows lack: they reshape the training distribution but add no new evidence.

**Leakage rule:** this runs after the split, on the training rows of one fold only (PRD 5.2). Validation and test rows never reach it.

## I. Example
```python
result = oversample_training_fold(features, labels, "smote", 0.1, 5, seed=42)
print(result.report["synthetic_rows"])
```

## J. Maintenance Notes
Do not import this anywhere except `experiments.py`. If the feature schema gains a value that cannot be rebuilt from amount and hour, `_reconstruct_rows` must change with it.

## K. Related Files
- [experiments.py](experiments.py.explanation.md): the only caller.
- [features.py](features.py.explanation.md): enforces valid rows.
- [test_imbalance.py](../../tests/unit/test_imbalance.py.explanation.md): proves validity and containment.
