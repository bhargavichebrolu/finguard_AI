# ADR 0002: Phase 2 decisions, fixed before any candidate was scored

**Status:** accepted for Phase 2. Date: 2026-11-07.

This record and [experiments_v1.json](../../experiments/experiment-configs/experiments_v1.json) were committed before any model was scored on validation or test. The commit order in Git is the evidence. Later sections, if any, are labelled as added after results existed.

**What had been seen when this was written:** Phase 1's published counts (rows and fraud per step in every partition) and training-only EDA. A timing probe fitted models on a random 10% of training rows to size the search. It measured time and memory only, read no validation or test rows, and computed no quality metric.

## 1. Correction to the PRD

PRD 1.3 mentions selecting a model on "measured test performance". PRD 5.5 and section 16 require an untouched test set. The Phase 2 authorisation settles this: **model selection must never be based on test performance.** Fit on train; tune, select and set thresholds on validation; evaluate on test once after the freeze.

The final model is fitted on the training partition only, as instructed. It is not refitted on train plus validation, because the threshold is set on validation, and a refit would invalidate it.

## 2. Selection rule

Applied by [selection.py](../../backend/app/ml/selection.py) to each family's best run, by validation PR-AUC, from the matrix and tuning stages. Sensitivity and stability runs cannot win.

**Gates.** A candidate is rejected if it:
1. Does not beat the transaction-type baseline's PR-AUC on validation.
2. Does not beat that baseline in every rolling-origin fold inside training, using the baseline fitted on that fold's fit rows.
3. Varies by more than 10% across seeds (coefficient of variation of PR-AUC), or has a failed seed or fold run.

**Ranking.** Among those that pass:
1. Take the highest mean PR-AUC across seeds as the top candidate. Keep candidates whose paired step-bootstrap 95% interval for the PR-AUC difference from the top includes 0.
2. Among those, take the highest recall at the operational threshold, treating values within 1 percentage point as tied.
3. Among those, take the lowest median single-row prediction time.

**If nothing passes the gates,** the ranking is applied to all candidates, and the result must be reported as failing them.

**Why this order.** PR-AUC is the threshold-free measure that fits severe imbalance. Validation has only 55 steps and 570 fraud rows, so small differences may be noise. Where the data cannot separate two models, it is more sensible to decide on what matters in use, then on cost. This covers PRD 5.6: precision and recall through PR-AUC and the operational recall, false-positive burden through the cap, computational cost, stability and threshold behaviour.

## 3. Threshold objective

**The highest recall with a false positive rate of at most 0.1% on validation.** It is calculated from the frozen model's own scores.

**Why:**
- The false positive rate is defined on legitimate rows alone, so its meaning does not change with prevalence, which shifts sevenfold between validation and test. A threshold tuned for F1 or precision depends on the prevalence where it was chosen.
- It fixes the false-positive burden directly: about 1 in 1,000 legitimate transactions goes to review.
- It is always achievable, whereas a precision target might not be.

**The value 0.1% is a judgement.** No review capacity or cost figures exist for a simulated dataset. Other caps, the PRD candidates (0.30 to 0.70), and best-F1 and best-F2 thresholds are all reported, so a different choice can be made with the evidence available. The threshold is stored with the model. Changing it would not need retraining, but it would be a new operating point that the test set has not measured independently.

## 4. Sparse and normal steps

**Definition:** a step is sparse if it has fewer than 1,000 rows in total. Otherwise it is normal. No label is read.

The cut-off was fixed in Phase 1 from row counts alone, and it is not tuned here. Results are repeated at 500 and 2,000 to check for dependence on this value. Fraud rows do count towards the row total, so the definition uses no label values but is not statistically unrelated to fraud. A live request cannot know its step's final row count, so the regime is an analysis slice only, never a feature.

## 5. Oversampling

SMOTE and ADASYN from imbalanced-learn run **per transaction type**, on a three-value continuous representation (log amount, and the sine and cosine of the hour), standardised on that type's rows within the fold. Each synthetic row is rebuilt through `engineer_features`, so it obeys the same rules as a real row. This meets PRD 5.2's requirement for meaningful samples: running these methods on the full table would produce fractional types, impossible hours and inconsistent amount columns.

- **Applied only to training rows.** The call is inside `fit_candidate`, and the saved pipeline contains no sampler. This holds for rolling folds too.
- **Target ratio 0.1**, fraud to legitimate within each type, rather than full balance. Full balance would add about 1.9 million synthetic rows derived from 3,633 real ones, and would strain the memory available. Ratios of 0.02 and 0.3 are tested as sensitivity, on LightGBM.
- **Types with no fraud** receive no synthetic rows.

## 6. Comparison design

- **Same inputs:** all families receive the same one-hot and numeric matrix. CatBoost's own categorical handling is not used, so it can't be a difference between families.
- **Same conditions:** 8 threads, one run at a time, on one machine.
- **Matrix:** 6 families and 4 strategies at fixed baseline settings, giving 24 runs.
- **Tuning:** random samples per family, on the family's best matrix strategy, keeping validation PR-AUC as the objective. A strategy that would only do well with different hyperparameters would be missed. That is an accepted limitation.
- **Sensitivity (informational):** oversampling ratios, and the leading model with hour features or amount features removed.
- **Stability:** seeds 42, 7 and 2024, and three rolling-origin folds inside training.
- **No early stopping:** the number of boosting rounds is a tuned setting.

## 7. Temporal evaluation

Rolling-origin anchors at 55%, 70%, 85% and 100% of training rows, using row counts only. Intervals come from a bootstrap over whole steps, because rows within a step are not independent.

## 8. Test partition controls

1. `load_development_partition` refuses anything except train and validation.
2. Only `final_evaluation.py` reads the test file. Tests scan the source to enforce this.
3. An integration test runs training and selection with no test file on disk.
4. `evaluate_final_test.py` refuses to start unless the freeze files are committed and unchanged.
5. The evaluation refuses to run if a result already exists. There is no force option.
6. Only the selected model is evaluated on test, along with non-learning baselines.

## 9. Honest limits of this design

- About 90 runs share one validation window, so the winner's validation score is optimistic. The test result is the unbiased figure, for this window.
- Test prevalence was already known from Phase 1 when the threshold objective was chosen, and it is part of the reason given in section 3. It was not used to tune any value.
- Timing was measured with other applications open, so small differences are noise.
- The test window is one period of one simulation. It does not show how a model would behave on real transactions.

## 10. Added files beyond PRD 13

`scripts/analyse_temporal_drift.py`, `explain_model.py` and `evaluate_final_test.py` give their steps a command. Section 13 permits additions.

## 11. Added after results existed

Everything in this section was written after validation results were seen and before test was opened. None of it changes the rule, the candidates or the threshold objective above.

- **Run count.** 125 runs were recorded, not 126. One Logistic Regression tuning sample matched its baseline, so the run store reused that result.
- **Sensitivity runs added to the report.** They were always saved, but the generated tables left them out. They now appear with the range of each family's search.
- **LightGBM diagnostic.** `scripts/diagnose_lightgbm.py` explains why LightGBM collapsed on two strategies. It is marked ineligible, stays out of the run store, and did not affect selection. Its best fit would not automatically have won, and was not bootstrapped.
- **Freeze evidence strengthened.** The test report field `frozen_at_commit` was renamed `model_fitted_at_commit`, because it records the commit the model was fitted from. Tests now check the Git history of the freeze files directly.
- **Comparison precision.** The frozen threshold sits one float64 step above a float32 score, so scores must be compared as float64. All scoring paths already did, and a test now guards this.
