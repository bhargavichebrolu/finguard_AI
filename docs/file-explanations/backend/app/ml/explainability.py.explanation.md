# explainability.py

Source: [backend/app/ml/explainability.py](../../../../../backend/app/ml/explainability.py)

## A. File Purpose
Produces SHAP explanations of the saved model: global importance, breakdowns by class and slice, and explanations of individual scores.

## B. Why This File Exists
PRD 5.7 requires global importance, individual contributions, positive and negative contributions, and stated limitations. The authorisation asks for SHAP on the selected model where supported.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `scikit-learn`, `shap` (imported inside `explain_rows`).
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `scripts/explain_model.py`, and the API from Phase 3.

## D. Every Function Explained

### `feature_group`
- **Purpose:** group columns that measure the same thing.
- **Parameters / types:** `name: str`.
- **Returns / type:** `str`: `amount`, `hour` or `transaction_type_and_destination`.
- **Internal processing:** checks the column prefix.
- **Error handling:** anything else falls into the type group.
- **Calls:** nothing.
- **Used by:** `summarise_explanations`, `reporting.py`.

### `explain_rows`
- **Purpose:** calculate SHAP values.
- **Parameters / types:** `pipeline: Pipeline`; `features: pd.DataFrame`; `family: str`.
- **Returns / type:** `dict` with values, base value, feature names and output scale.
- **Internal processing:** transforms the rows, picks `TreeExplainer` or `LinearExplainer`, and keeps class 1 values when a model returns both classes.
- **Error handling:** `ValueError` for an unsupported family.
- **Calls:** `shap`.
- **Used by:** `explain_validation_rows`.

### `additivity_error`
- **Purpose:** verify the explanation adds up to the real score.
- **Parameters / types:** `explanation: dict`; `scores: np.ndarray`.
- **Returns / type:** `float`, the largest gap.
- **Internal processing:** base value plus SHAP values, through the logistic function when the scale is log-odds.
- **Error handling:** none needed. A large value in the report signals a problem.
- **Calls:** numpy.
- **Used by:** `explain_validation_rows`.

### `_weighted_absolute_mean`
- **Purpose:** mean size of contributions, weighted.
- **Parameters / types:** `values`, `weights`: arrays.
- **Returns / type:** `np.ndarray`.
- **Internal processing:** `np.average` of absolute values.
- **Error handling:** none needed.
- **Calls:** numpy.
- **Used by:** `summarise_explanations`.

### `summarise_explanations`
- **Purpose:** produce global importance.
- **Parameters / types:** `explanation: dict`; `labels`, `weights`: arrays; `slices: dict`.
- **Returns / type:** `dict`.
- **Internal processing:** adds SHAP values within groups, then reports means for all rows, each class and each slice. The nested helper `describe` does this for one mask.
- **Error handling:** an empty mask gives `{"rows": 0}`.
- **Calls:** `feature_group`, `_weighted_absolute_mean`.
- **Used by:** `explain_validation_rows`.

### `describe`
A helper nested in `summarise_explanations`. It computes per-feature and per-group means for one row mask.

### `local_explanation`
- **Purpose:** explain one score.
- **Parameters / types:** `explanation: dict`; `position: int`; `score: float`; `threshold: float`.
- **Returns / type:** `dict` with score, alert status, and positive and negative contributions, largest first.
- **Internal processing:** sorts by size, then separates by sign.
- **Error handling:** none needed.
- **Calls:** nothing.
- **Used by:** `explain_validation_rows`, and the API from Phase 3.

### `sample_for_explanation`
- **Purpose:** choose rows to explain at an affordable cost.
- **Parameters / types:** `labels: np.ndarray`; `legitimate_rows: int`; `seed: int`.
- **Returns / type:** `(positions, weights)`.
- **Internal processing:** all fraud rows plus a random sample of legitimate rows, which are weighted back up.
- **Error handling:** the sample is capped at the available rows.
- **Calls:** numpy.
- **Used by:** `explain_validation_rows`.

### `explain_validation_rows`
- **Purpose:** build the saved report.
- **Parameters / types:** `pipeline`, `family`, `features`, `labels`, `scores`, `slices`, `threshold`, `legitimate_rows`, `seed`.
- **Returns / type:** `dict` with the JSON report and raw values for charts.
- **Internal processing:** samples, explains, verifies additivity, summarises, and picks three examples. The nested helper `example` picks one row.
- **Error handling:** an example with no matching row is `None`.
- **Calls:** the functions above.
- **Used by:** `scripts/explain_model.py`.

### `example`
A helper nested in `explain_validation_rows`. It picks the highest or lowest scoring row that meets a condition and describes it.

## E. Classes Explained
None.

## F. Execution Flow
Sample rows, transform, calculate SHAP values, verify additivity, summarise by feature, group, class and slice, and pick examples.

## G. Input and Output
Input: the frozen model and validation rows. Output: `experiments/results/phase2/shap_summary.json`.

## H. Important Technical Concepts
**SHAP values** split one score into a contribution per input, measured from a base value. They add up exactly to the model's output, which `additivity_error` verifies.

**Why groups:** `amount` and `amount_log1p` carry the same information, and the three hour columns describe one hour. A tree can use either, so credit is split arbitrarily. Adding values within a group is valid, because SHAP values are additive.

**Why validation rows:** they are what the threshold was chosen on, and using them keeps the test partition out of this analysis.

**Limitations:** see `LIMITATIONS`. SHAP does not establish causality. It describes what a model built on simulated data has learned.

## I. Example
```python
result = explain_validation_rows(pipeline, "lightgbm", features, labels, scores, slices,
                                 threshold, 20000, 42)
print(result["report"]["summary"]["all_rows"]["mean_absolute_by_group"])
```

## J. Maintenance Notes
Check `additivity_max_error` after a library upgrade: SHAP support for new booster versions is a common source of breakage. The API should reuse `explain_rows` and `local_explanation` in Phase 3.

## K. Related Files
- [explain_model.py](../../../scripts/explain_model.py.explanation.md): runs this.
- [model_artifacts.py](model_artifacts.py.explanation.md): loads the model.
- [test_explainability.py](../../tests/unit/test_explainability.py.explanation.md): tests.
