# test_evaluation.py

Source: [backend/tests/unit/test_evaluation.py](../../../../../backend/tests/unit/test_evaluation.py)

## A. File Purpose
Tests metric formulas, threshold rules and the step bootstrap.

## B. Why This File Exists
Every Phase 2 result depends on these calculations. PRD 14.1 requires a threshold behaviour test. A subtle error here would be invisible in the results.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `pytest`, `sklearn.metrics`.
- **Internal modules:** `app.ml.evaluation`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `_block_data`
- **Purpose:** build labels and scores grouped into 40 steps.
- **Parameters / types:** `seed: int`. **Returns / type:** `(labels, scores, steps)`.
- **Internal processing / errors:** seeded random data, where fraud rows score higher; no special handling.
- **Calls:** numpy. **Used by:** the bootstrap and `evaluate_scores` tests.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_threshold_metrics_by_hand` | none | Every metric matches a hand calculation. |
| `test_a_score_equal_to_the_threshold_alerts` | none | The boundary rule. |
| `test_higher_threshold_cannot_raise_recall_or_alerts` | none | Threshold behaviour is monotonic. |
| `test_undefined_metrics_are_none_not_zero` | none | Undefined is reported as undefined. |
| `test_ranking_metrics_report_baseline_and_lift` | none | PR-AUC comes with its baseline. |
| `test_ranking_metrics_with_one_class_are_none` | none | No AUC with one class. |
| `test_fpr_cap_gives_highest_recall_within_the_cap` | none | Within the cap, and the next lower threshold breaks it. |
| `test_fpr_cap_excludes_a_tie_that_would_cross_it` | none | Tied scores are handled as a whole. |
| `test_fpr_cap_too_small_for_any_alert_on_negatives` | none | A tiny cap allows no false alerts. |
| `test_invalid_fpr_cap_is_rejected` | `cap` | Caps outside (0, 1) raise. |
| `test_max_f1_threshold_is_the_best_among_all_scores` | none | Nothing beats the returned threshold. |
| `test_f2_favours_recall_over_f1` | none | F2's threshold is not above F1's. |
| `test_prevalence_adjustment_at_same_prevalence_changes_nothing` | none | The weights reduce to 1. |
| `test_prevalence_adjustment_lowers_pr_auc_at_lower_prevalence` | none | Correct direction. |
| `test_expected_precision_by_hand` | none | The Bayes formula. |
| `test_expected_precision_with_no_alerts_is_none` | none | Undefined case. |
| `test_weighted_average_precision_matches_sklearn_with_ties` | none | The fast calculation equals sklearn's, including ties and weights. |
| `test_bootstrap_draws_whole_steps` | none | Rows in a step share a weight. |
| `test_bootstrap_is_reproducible_and_brackets_the_estimate` | none | Same seed, same interval, around the point estimate. |
| `test_paired_difference_of_a_model_with_itself_is_exactly_zero` | none | Pairing works. |
| `test_paired_difference_detects_a_clearly_better_model` | none | The comparison can detect a difference. |
| `test_out_of_bag_behaviour_reports_how_many_replicates_were_used` | none | The count is reported and the rate is plausible. |
| `test_slices_describe_regime_type_and_cap` | none | Slice masks are correct. |
| `test_evaluate_scores_keeps_natural_distribution_and_applies_one_threshold` | none | Row counts are unchanged, and one threshold applies to all slices. |
| `test_curves_are_small_and_within_range` | none | Curves are compact and valid. |

## E. Classes Explained
None.

## F. Execution Flow
All tests run in memory.

## G. Input and Output
Input: small constructed arrays. Output: pass or fail.

## H. Important Technical Concepts
Hand-calculated expectations are written in comments, so a test states the rule independently of the code. The comparison with sklearn proves that the faster bootstrap calculation is the same metric.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_evaluation.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If an expected value needs changing, re-derive it by hand first. Then rerun all experiments, because earlier results were produced by the old formula.

## K. Related Files
- [evaluation.py](../../app/ml/evaluation.py.explanation.md): code under test.
