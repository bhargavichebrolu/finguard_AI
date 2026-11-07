# drift.py

Source: [backend/app/ml/drift.py](../../../../../backend/app/ml/drift.py)

## A. File Purpose
Measures how prevalence, volume and feature distributions change across the simulation.

## B. Why This File Exists
Test prevalence is about seven times validation prevalence. Without understanding why, a test result could be misread as model skill or failure. This module explains the shift. It reads published counts first, so the investigation does not open the test file before the model is frozen.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`.
- **Internal modules:** `app.ml.features`, `app.ml.regimes`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** `scripts/analyse_temporal_drift.py`, `final_evaluation.py`.

## D. Every Function Explained

### `step_table_from_eda`
- **Purpose:** build one table of rows, fraud and partition per step.
- **Parameters / types:** `eda_summary: dict`; `boundaries: SplitBoundaries`.
- **Returns / type:** `pd.DataFrame` indexed by step.
- **Internal processing:** reads the Phase 1 report and applies `partition_masks`.
- **Error handling:** `KeyError` if the report has the wrong shape.
- **Calls:** `partition_masks`.
- **Used by:** `build_prevalence_report`.

### `_group_summary`
- **Purpose:** summarise a set of steps.
- **Parameters / types:** `group: pd.DataFrame`.
- **Returns / type:** `dict` of counts, prevalence and per-step rates.
- **Internal processing:** sums and divides.
- **Error handling:** rates are `None` for an empty group.
- **Calls:** pandas.
- **Used by:** `partition_prevalence`.

### `partition_prevalence`
- **Purpose:** summarise each partition overall and by regime.
- **Parameters / types:** `table: pd.DataFrame`; `cutoff: int`.
- **Returns / type:** nested `dict`.
- **Internal processing:** classifies steps, then summarises each partition and regime, with shares of its rows and fraud.
- **Error handling:** inherited.
- **Calls:** `classify_steps`, `_group_summary`.
- **Used by:** `build_prevalence_report`, `cutoff_sensitivity`.

### `decompose_prevalence_change`
- **Purpose:** attribute a prevalence change to regime mix or to within-regime rates.
- **Parameters / types:** `reference`, `target`: partition summaries.
- **Returns / type:** `dict` with total, mix and rate effects.
- **Internal processing:** the Kitagawa decomposition, in which the effects sum exactly to the total.
- **Error handling:** a regime with no rows counts as a rate of 0.
- **Calls:** nothing.
- **Used by:** `build_prevalence_report`.

### `prevalence_at_reference_volume`
- **Purpose:** ask what target prevalence would be at another window's legitimate volume.
- **Parameters / types:** `reference`, `target`: partition summaries.
- **Returns / type:** `float`.
- **Internal processing:** target fraud per step over that plus the reference's legitimate rows per step.
- **Error handling:** none needed; partitions always have rows.
- **Calls:** nothing.
- **Used by:** `build_prevalence_report`.

### `daily_profile`
- **Purpose:** provide a per-day series for charting.
- **Parameters / types:** `table: pd.DataFrame`.
- **Returns / type:** `list[dict]`.
- **Internal processing:** groups steps into 24-step blocks.
- **Error handling:** `prevalence` is `None` if a day has no rows.
- **Calls:** pandas.
- **Used by:** `build_prevalence_report`.

### `regime_by_hour`
- **Purpose:** show when sparse steps occur.
- **Parameters / types:** `table: pd.DataFrame`; `cutoff: int`.
- **Returns / type:** `dict` of 24-element lists per partition.
- **Internal processing:** for each hour, the share of that hour's steps that are sparse.
- **Error handling:** `None` for an hour with no steps.
- **Calls:** `classify_steps`.
- **Used by:** `build_prevalence_report`.

### `cutoff_sensitivity`
- **Purpose:** test whether conclusions depend on the value 1,000.
- **Parameters / types:** `table: pd.DataFrame`; `cutoffs: list[int]`.
- **Returns / type:** `dict` keyed by cut-off.
- **Internal processing:** repeats the regime summary.
- **Error handling:** inherited.
- **Calls:** `partition_prevalence`.
- **Used by:** `build_prevalence_report`.

### `population_stability_index`
- **Purpose:** measure drift in a numeric column.
- **Parameters / types:** `reference`, `target`: arrays.
- **Returns / type:** `float`.
- **Internal processing:** deciles from the reference, then compares the shares.
- **Error handling:** duplicate bin edges collapse. The tails extend to infinity.
- **Calls:** `_psi`.
- **Used by:** `_frame_drift`.

### `categorical_stability_index`
- **Purpose:** measure drift in a categorical column.
- **Parameters / types:** `reference`, `target`: arrays; `categories: list`.
- **Returns / type:** `float`.
- **Internal processing:** compares the share of each category.
- **Error handling:** see `_psi`.
- **Calls:** `_psi`.
- **Used by:** `_frame_drift`.

### `_psi`
- **Purpose:** the formula itself.
- **Parameters / types:** `expected`, `actual`: share arrays.
- **Returns / type:** `float`.
- **Internal processing:** Σ (actual − expected) × ln(actual / expected).
- **Error handling:** shares are floored so an empty bin cannot produce infinity.
- **Calls:** numpy.
- **Used by:** the two index functions.

### `_frame_drift`
- **Purpose:** compute PSI for amount, type and hour.
- **Parameters / types:** `reference`, `target`: `pd.DataFrame`.
- **Returns / type:** `dict[str, float]`.
- **Internal processing:** calls the index functions on the three underlying columns. The redundant destination and hour encodings are left out.
- **Error handling:** inherited.
- **Calls:** `population_stability_index`, `categorical_stability_index`.
- **Used by:** `feature_drift`.

### `feature_drift`
- **Purpose:** compare two windows' features overall and within each class.
- **Parameters / types:** `reference`, `target`: frames; `reference_labels`, `target_labels`: arrays.
- **Returns / type:** `dict`.
- **Internal processing:** applies `_frame_drift` to all rows, then to legitimate and fraud rows.
- **Error handling:** inherited.
- **Calls:** `_frame_drift`.
- **Used by:** `scripts/analyse_temporal_drift.py` for train and validation; `final_evaluation.py` for test, after the freeze.

### `build_prevalence_report`
- **Purpose:** assemble the analysis that needs only published counts.
- **Parameters / types:** `eda_summary: dict`; `boundaries`; `cutoff: int`; `sensitivity_cutoffs: list[int]`.
- **Returns / type:** `dict`, ready for JSON.
- **Internal processing:** calls everything above and records the regime definition.
- **Error handling:** inherited.
- **Calls:** the functions above.
- **Used by:** `scripts/analyse_temporal_drift.py`.

## E. Classes Explained
None.

## F. Execution Flow
EDA report, then step table, then partition and regime summaries, then decomposition, counterfactual, hour profile and sensitivity.

## G. Input and Output
Input: `experiments/results/eda_summary.json`, plus feature rows for `feature_drift`. Output: `experiments/results/phase2/temporal_drift.json`.

## H. Important Technical Concepts
**Prior shift** means the base rate changes. **Covariate shift** means feature distributions change. **Concept shift** means the feature-to-fraud relationship changes. They have different consequences, so they are measured separately.

**Kitagawa decomposition:** the prevalence change is split into how much is due to more rows falling in the sparse regime, and how much is due to rates changing within a regime.

**PSI** is the population stability index. A common rule of thumb calls below 0.1 stable and above 0.25 a large shift. These are conventions, not statistical tests.

**Test boundary:** the prevalence functions use only counts already published in Phase 1. `feature_drift` reads values, so it must not receive test rows before the freeze. The drift script only gives it train and validation.

## I. Example
```python
report = build_prevalence_report(eda_summary, boundaries, 1000, [500, 2000])
print(report["decomposition"]["validation_to_test"])
```

## J. Maintenance Notes
Do not pass test rows to `feature_drift` outside `final_evaluation.py`. A test of the drift script enforces this.

## K. Related Files
- [regimes.py](regimes.py.explanation.md): the sparse definition.
- [analyse_temporal_drift.py](../../../scripts/analyse_temporal_drift.py.explanation.md): runs this.
- [final_evaluation.py](final_evaluation.py.explanation.md): completes the feature drift on test.
