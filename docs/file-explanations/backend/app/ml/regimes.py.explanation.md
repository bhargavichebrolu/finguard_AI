# regimes.py

Source: [backend/app/ml/regimes.py](../../../../../backend/app/ml/regimes.py)

## A. File Purpose
Defines sparse and normal simulation steps, using row counts alone.

## B. Why This File Exists
Phase 1 found that steps with very few rows behave like a different population. Phase 2 reports every result for both groups, so the definition needs one home. Keeping it here also means EDA, experiments and the final test cannot drift apart.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `eda.py`, `evaluation.py`, `drift.py`, `final_evaluation.py`.

## D. Every Function Explained

### `rows_per_step`
- **Purpose:** count rows per step.
- **Parameters / types:** `steps: pd.Series`, one step number per row.
- **Returns / type:** `pd.Series` of integer counts indexed by step, in step order.
- **Internal processing:** `value_counts`, then sort by step.
- **Error handling:** none needed; an empty input gives an empty result.
- **Calls:** pandas only.
- **Used by:** `row_regime_masks`, `experiment_stages.py`.

### `classify_steps`
- **Purpose:** label each step sparse or normal.
- **Parameters / types:** `step_rows: pd.Series`; `cutoff: int`, default `SPARSE_STEP_MAX_ROWS`.
- **Returns / type:** `pd.Series` of regime names indexed by step.
- **Internal processing:** a step is sparse when its row count is strictly below the cutoff.
- **Error handling:** raises `ValueError` for a non-positive cutoff.
- **Calls:** numpy `where`.
- **Used by:** `row_regime_masks`, `drift.py`.

### `row_regime_masks`
- **Purpose:** turn the step definition into row masks for slicing metrics.
- **Parameters / types:** `steps: pd.Series`; `cutoff: int`.
- **Returns / type:** `dict[str, np.ndarray]`, one boolean mask per regime.
- **Internal processing:** counts rows per step, classifies steps, maps each row to its step's regime.
- **Error handling:** inherits `classify_steps`.
- **Calls:** `rows_per_step`, `classify_steps`.
- **Used by:** `evaluation.build_slices`.

## E. Classes Explained
None.

## F. Execution Flow
Count rows per step, compare each count with the cutoff, map the result back to rows.

## G. Input and Output
Input: step numbers. Output: regime per step, or a boolean mask per regime.

## H. Important Technical Concepts
**Label independence:** no label is read. One nuance remains: fraud rows are counted like any other row, and in a sparse step about one row in ten is fraud. So the definition uses no label values, but the count is not statistically unrelated to fraud. The fixed cutoff is what stops this mattering: it is not fitted to any model or fraud rate.

**Not a feature:** a live request cannot know how many rows its step will end up with. Using the regime as an input would be leakage from the future.

**Sensitivity:** `drift.py` repeats the analysis at other cutoffs, so the conclusions can be checked against the choice of 1,000.

## I. Example
```python
masks = row_regime_masks(partition.steps)
sparse_labels = partition.labels[masks["sparse"]]
```

## J. Maintenance Notes
Do not tune `SPARSE_STEP_MAX_ROWS` using model results. If it ever changes, rerun EDA, experiments and the final evaluation, and record why.

## K. Related Files
- [drift.py](drift.py.explanation.md): cut-off sensitivity and prevalence analysis.
- [evaluation.py](evaluation.py.explanation.md): metric slices.
- [eda.py](eda.py.explanation.md): uses the same cut-off.
