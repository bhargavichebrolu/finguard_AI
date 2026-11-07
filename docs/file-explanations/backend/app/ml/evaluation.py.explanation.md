# evaluation.py

Source: [backend/app/ml/evaluation.py](../../../../../backend/app/ml/evaluation.py)

## A. File Purpose
Calculates every metric, threshold rule and uncertainty estimate used in Phase 2.

## B. Why This File Exists
PRD 5.3 requires identical evaluation conditions. One module means every model is measured the same way, and the formulas are tested once.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `scikit-learn` metrics.
- **Internal modules:** `app.ml.regimes`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `experiments.py`, `experiment_stages.py`, `selection.py`, `final_evaluation.py`.

## D. Every Function Explained

### `_ratio`
- **Purpose:** divide safely.
- **Parameters / types:** `numerator`, `denominator`: numbers.
- **Returns / type:** `float | None`.
- **Internal processing:** returns `None` on a zero denominator.
- **Error handling:** this is the error handling: an undefined metric is reported as undefined, not as 0.
- **Calls:** nothing.
- **Used by:** the metric functions.

### `threshold_metrics`
- **Purpose:** compute the confusion matrix and threshold metrics.
- **Parameters / types:** `labels`, `scores`: arrays; `threshold: float`.
- **Returns / type:** `dict` with TP, FP, TN, FN, accuracy, precision, recall, F1, balanced accuracy, false positive rate, false negative rate, alerts and alert rate.
- **Internal processing:** a score equal to the threshold counts as an alert.
- **Error handling:** undefined metrics are `None`.
- **Calls:** `_ratio`.
- **Used by:** nearly everything here, plus `selection.py` and `final_evaluation.py`.

### `ranking_metrics`
- **Purpose:** compute threshold-free metrics.
- **Parameters / types:** `labels`, `scores`: arrays.
- **Returns / type:** `dict` with rows, fraud rows, prevalence, ROC-AUC, PR-AUC, PR-AUC lift and Brier score.
- **Internal processing:** PR-AUC uses `average_precision_score`. Lift is PR-AUC divided by prevalence, the score of a random ranking.
- **Error handling:** AUC values are `None` if only one class is present.
- **Calls:** sklearn metrics, `_ratio`.
- **Used by:** `evaluate_scores`, `final_evaluation.py`, `experiment_stages.py`.

### `threshold_for_fpr_cap`
- **Purpose:** find the threshold with the highest recall whose false positive rate stays within a cap.
- **Parameters / types:** `labels`, `scores`: arrays; `cap: float`.
- **Returns / type:** `float`.
- **Internal processing:** sorts legitimate rows' scores and takes the score at the allowed count. A tie crossing the cap is excluded whole, using `nextafter`.
- **Error handling:** `ValueError` for a cap outside (0, 1) or no negative rows.
- **Calls:** numpy.
- **Used by:** `evaluate_scores`, `selection.py`, `out_of_bag_threshold_behaviour`.

### `threshold_for_max_fbeta`
- **Purpose:** find the threshold that maximises F-beta.
- **Parameters / types:** `labels`, `scores`: arrays; `beta: float`, default 1.
- **Returns / type:** `float`.
- **Internal processing:** evaluates F-beta along the precision-recall curve.
- **Error handling:** a zero denominator gives F-beta 0.
- **Calls:** `precision_recall_curve`.
- **Used by:** `evaluate_scores`, `selection.py`.

### `prevalence_adjusted_pr_auc`
- **Purpose:** compare PR-AUC across windows with different base rates.
- **Parameters / types:** `labels`, `scores`: arrays; `target_prevalence: float`.
- **Returns / type:** `float | None`.
- **Internal processing:** weights negative rows so the weighted fraud rate equals the target.
- **Error handling:** `None` if one class is absent.
- **Calls:** `average_precision_score`.
- **Used by:** `final_evaluation.py`.

### `expected_precision`
- **Purpose:** state the precision implied by Bayes' rule.
- **Parameters / types:** `recall`, `false_positive_rate`, `prevalence`: floats.
- **Returns / type:** `float | None`.
- **Internal processing:** recall × prevalence over all alerts.
- **Error handling:** `None` when no alerts are implied.
- **Calls:** `_ratio`.
- **Used by:** `final_evaluation.py`, to separate prior shift from model behaviour.

### `decimated_curves`
- **Purpose:** save small PR and ROC curves.
- **Parameters / types:** `labels`, `scores`: arrays.
- **Returns / type:** `dict` of four lists.
- **Internal processing:** even spacing along recall, and log spacing along false positive rate.
- **Error handling:** none beyond sklearn's.
- **Calls:** `precision_recall_curve`, `roc_curve`.
- **Used by:** `selection.py`, `final_evaluation.py`.

### `build_slices`
- **Purpose:** define the row groups every result is broken down by.
- **Parameters / types:** `features: pd.DataFrame`; `steps: pd.Series`; `cutoff: int`.
- **Returns / type:** `dict[str, np.ndarray]`.
- **Internal processing:** sparse and normal regimes, CASH_OUT and TRANSFER, and amounts at or below the simulator cap.
- **Error handling:** `KeyError` if a column is absent.
- **Calls:** `row_regime_masks`.
- **Used by:** `experiment_stages.py`, `final_evaluation.py`.

### `evaluate_scores`
- **Purpose:** produce the standard result for one set of scores.
- **Parameters / types:** `labels`, `scores`: arrays; `slices: dict`; `fpr_cap: float`.
- **Returns / type:** `dict`.
- **Internal processing:** ranking metrics, the five PRD thresholds, the capped threshold, the best-F1 threshold, then each slice at the capped threshold.
- **Error handling:** inherited.
- **Calls:** `ranking_metrics`, `threshold_for_fpr_cap`, `threshold_for_max_fbeta`, `threshold_metrics`.
- **Used by:** `experiments.evaluate_candidate`, `experiment_stages.run_baselines`.

### `_prepare_ranking`
- **Purpose:** sort once so bootstrap replicates need no further sorting.
- **Parameters / types:** `labels`, `scores`: arrays.
- **Returns / type:** `(order, ends)` arrays.
- **Internal processing:** stable descending sort, then the end position of each tied group.
- **Error handling:** none needed.
- **Calls:** numpy.
- **Used by:** `bootstrap_pr_auc`, `paired_bootstrap_difference`.

### `_weighted_average_precision`
- **Purpose:** compute average precision with row weights.
- **Parameters / types:** sorted labels, sorted weights, tied group ends.
- **Returns / type:** `float`, NaN if the resample has no fraud.
- **Internal processing:** cumulative sums at group ends, then sum of recall gain × precision. This matches sklearn's definition, and a test checks that.
- **Error handling:** NaN results are dropped by `_interval`.
- **Calls:** numpy.
- **Used by:** the bootstrap functions.

### `_interval`
- **Purpose:** summarise replicates.
- **Parameters / types:** `values: np.ndarray`.
- **Returns / type:** `dict` with mean and 2.5th and 97.5th percentiles.
- **Internal processing:** ignores non-finite values.
- **Error handling:** returns `None` values if nothing is finite.
- **Calls:** numpy.
- **Used by:** the bootstrap functions.

### `bootstrap_pr_auc`
- **Purpose:** give PR-AUC a confidence interval.
- **Parameters / types:** `labels`, `scores`, `steps`: arrays; `replicates`, `seed`: ints.
- **Returns / type:** `dict`.
- **Internal processing:** resamples steps and reuses the sort.
- **Error handling:** inherited.
- **Calls:** `StepBootstrap`, `_prepare_ranking`, `_weighted_average_precision`, `_interval`.
- **Used by:** `selection.py`, `final_evaluation.py`.

### `paired_bootstrap_difference`
- **Purpose:** test whether two models differ, using the same resampled steps for both.
- **Parameters / types:** `labels`, `scores_a`, `scores_b`, `steps`: arrays; `replicates`, `seed`: ints.
- **Returns / type:** `dict` with interval and `includes_zero`.
- **Internal processing:** computes both models' PR-AUC per replicate and takes the difference.
- **Error handling:** inherited.
- **Calls:** `StepBootstrap`, `_prepare_ranking`, `_weighted_average_precision`, `_interval`.
- **Used by:** `selection.py`.

### `out_of_bag_threshold_behaviour`
- **Purpose:** estimate how a capped threshold behaves on unseen steps.
- **Parameters / types:** `labels`, `scores`, `steps`: arrays; `cap: float`; `replicates`, `seed`: ints.
- **Returns / type:** `dict` of intervals.
- **Internal processing:** sets the threshold on drawn steps and measures on undrawn steps.
- **Error handling:** skips degenerate replicates and reports how many were used.
- **Calls:** `StepBootstrap`, `threshold_for_fpr_cap`, `threshold_metrics`, `_interval`.
- **Used by:** `selection.py`.

## E. Classes Explained

### `StepBootstrap`
- **Purpose:** resample whole steps, because rows inside a step share conditions.
- **Attributes:** `unique_steps`, `row_step_index`, `generator`.
- **`__init__`:** finds the unique steps and creates the seeded generator.
- **`draw_step_counts`:** returns how many times each step is drawn.
- **`row_weights`:** turns step counts into per-row weights.

## F. Execution Flow
A caller builds slices once per partition. For each run it calls `evaluate_scores`. Finalists additionally go through the bootstrap functions.

## G. Input and Output
Input: arrays of labels and float scores. Output: plain dictionaries ready for JSON.

## H. Important Technical Concepts
**PR-AUC baseline:** a random ranking scores about the prevalence, so PR-AUC 0.05 is excellent at 0.06% prevalence and poor at 40%. That is why lift is always reported.

**Why resample steps:** bootstrapping rows would treat 973,000 validation rows as independent evidence. Validation has only 55 steps, and a sparse step can have 10% fraud while its neighbour has 0.05%. Resampling steps gives wider and more honest intervals.

**Prior shift:** `expected_precision` shows what precision should be if recall and false positive rate stayed fixed and only the base rate changed. A gap from observed precision indicates real change in score behaviour.

**A threshold chosen on the rows it is measured on is optimistic.** `at_max_f1` and `at_fpr_cap` in run records have this property. They allow fair comparison between models but are not generalisation estimates.

## I. Example
```python
result = evaluate_scores(labels, scores, build_slices(features, steps), fpr_cap=0.001)
print(result["ranking"]["pr_auc_lift"], result["at_fpr_cap"]["recall"])
```

## J. Maintenance Notes
Do not add reweighting or resampling to `evaluate_scores`: validation and test must keep their natural distribution (PRD 5.2). A change to any formula invalidates earlier results, so rerun them all.

## K. Related Files
- [experiments.py](experiments.py.explanation.md): applies this to each run.
- [selection.py](selection.py.explanation.md): uses the bootstrap to compare finalists.
- [final_evaluation.py](final_evaluation.py.explanation.md): applies it once to the test set.
- [regimes.py](regimes.py.explanation.md): defines two of the slices.
