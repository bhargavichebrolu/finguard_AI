### Temporal drift

#### Prevalence by partition

| Partition | Steps | Rows | Fraud | Fraud rate | Fraud/step | Legit/step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 322 | 4,433,703 | 3,633 | 0.082% | 11.28 | 13758 |
| validation | 55 | 973,173 | 570 | 0.059% | 10.36 | 17684 |
| test | 366 | 955,744 | 4,010 | 0.420% | 10.96 | 2600 |

#### Sparse and normal steps

| Partition | Regime | Steps | Rows | Fraud | Fraud rate | % rows | % fraud |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | sparse | 139 | 9,957 | 1,486 | 14.924% | 0.22% | 40.9% |
| train | normal | 183 | 4,423,746 | 2,147 | 0.049% | 99.78% | 59.1% |
| validation | sparse | 15 | 1,479 | 160 | 10.818% | 0.15% | 28.1% |
| validation | normal | 40 | 971,694 | 410 | 0.042% | 99.85% | 71.9% |
| test | sparse | 246 | 25,746 | 2,812 | 10.922% | 2.69% | 70.1% |
| test | normal | 120 | 929,998 | 1,198 | 0.129% | 97.31% | 29.9% |

#### What drives the prevalence change

| Change | Total | Regime mix effect | Within-regime rate effect |
| --- | ---: | ---: | ---: |
| train to test | 0.338% | 0.317% | 0.021% |
| train to validation | -0.023% | -0.009% | -0.014% |
| validation to test | 0.361% | 0.274% | 0.087% |

Test prevalence if its fraud per step stayed the same but legitimate volume matched training: **0.080%**; validation: **0.062%**.

#### Feature drift, train to validation (PSI)

| Rows | Amount | Type | Hour |
| --- | ---: | ---: | ---: |
| all_rows | 0.0152 | 0.0004 | 0.0860 |
| legitimate | 0.0152 | 0.0004 | 0.1053 |
| fraud | 0.0289 | 0.0000 | 0.1473 |

### Imbalance matrix

#### Baselines on validation

| Baseline | PR-AUC | ROC-AUC | Recall | Precision |
| --- | ---: | ---: | ---: | ---: |
| Random ranking | 0.00059 | 0.5000 | n/a | n/a |
| Transaction type rate | 0.00239 | 0.8487 | 0.0000 | n/a |
| Existing rule (`isFlaggedFraud`) | n/a | n/a | 0.0000 | n/a |

#### Validation PR-AUC, baseline settings

| Model | Original | Class weight | SMOTE | ADASYN |
| --- | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.0830 | 0.0094 | 0.0313 | 0.0697 |
| Decision Tree | 0.2500 | 0.2356 | 0.2874 | 0.2662 |
| Random Forest | 0.3203 | 0.2989 | 0.3159 | 0.2836 |
| XGBoost | 0.3362 | 0.3269 | 0.3278 | 0.3160 |
| LightGBM | 0.0618 | 0.0011 | 0.3136 | 0.3038 |
| CatBoost | 0.3425 | 0.3481 | 0.3378 | 0.3222 |

#### Validation recall at a 0.1% false positive rate

| Model | Original | Class weight | SMOTE | ADASYN |
| --- | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.2018 | 0.0228 | 0.1456 | 0.1351 |
| Decision Tree | 0.3439 | 0.3526 | 0.3684 | 0.3526 |
| Random Forest | 0.3754 | 0.3456 | 0.3737 | 0.3702 |
| XGBoost | 0.3965 | 0.3649 | 0.3877 | 0.3930 |
| LightGBM | 0.1526 | 0.0000 | 0.3754 | 0.3754 |
| CatBoost | 0.3947 | 0.4000 | 0.4070 | 0.3912 |

#### Training time in seconds, including resampling

| Model | Original | Class weight | SMOTE | ADASYN |
| --- | ---: | ---: | ---: | ---: |
| Logistic Regression | 3.0 | 4.4 | 5.0 | 6.3 |
| Decision Tree | 22.6 | 15.7 | 18.5 | 18.2 |
| Random Forest | 42.6 | 50.0 | 40.9 | 41.1 |
| XGBoost | 33.6 | 32.4 | 33.5 | 34.4 |
| LightGBM | 17.3 | 15.6 | 16.9 | 17.8 |
| CatBoost | 55.2 | 57.4 | 58.9 | 59.9 |

### Search and sensitivity

#### Hyperparameter search on validation

| Model | Strategy | Settings tried | Failed | Lowest PR-AUC | Highest PR-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| Logistic Regression | Original | 3 | 0 | 0.0540 | 0.0829 |
| Decision Tree | SMOTE | 12 | 0 | 0.0765 | 0.3160 |
| Random Forest | Original | 8 | 0 | 0.2451 | 0.3158 |
| XGBoost | Original | 16 | 0 | 0.3230 | 0.3499 |
| LightGBM | SMOTE | 16 | 0 | 0.3078 | 0.3448 |
| CatBoost | Class weight | 10 | 0 | 0.3305 | 0.3527 |

#### Sensitivity runs on validation

| Change | Model | Strategy | PR-AUC before | PR-AUC after | ROC-AUC after | Recall at 0.1% FPR after |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Without amount, amount_log1p | CatBoost | Class weight | 0.3527 | 0.2327 | 0.9148 | 0.2947 |
| Without hour_of_day, hour_sin, hour_cos | CatBoost | Class weight | 0.3527 | 0.1592 | 0.9123 | 0.1895 |
| Oversampling ratio 0.02 | LightGBM | ADASYN | 0.3038 | 0.2983 | 0.8985 | 0.3544 |
| Oversampling ratio 0.3 | LightGBM | ADASYN | 0.3038 | 0.3044 | 0.8977 | 0.3719 |
| Oversampling ratio 0.02 | LightGBM | SMOTE | 0.3136 | 0.2895 | 0.9065 | 0.3667 |
| Oversampling ratio 0.3 | LightGBM | SMOTE | 0.3136 | 0.3122 | 0.9045 | 0.3667 |

#### LightGBM diagnostic on validation

These fits ran after selection and were not eligible for it.

| Strategy | Settings | Trees built | Largest split gain | Distinct scores | PR-AUC | ROC-AUC | Recall at 0.1% FPR |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | baseline | 300 of 300 | 6.57e+09 | 5,198 | 0.0618 | 0.6979 | 0.1526 |
| Original | tuned | 200 of 200 | 2.51e+05 | 3,882 | 0.2867 | 0.9225 | 0.3509 |
| Original | baseline, boost_from_average off | 300 of 300 | 8.81e+02 | 16,207 | 0.3052 | 0.9280 | 0.3649 |
| Original | tuned, boost_from_average off | 200 of 200 | 1.64e+03 | 3,005 | 0.3480 | 0.9460 | 0.4035 |
| Class weight | baseline | 108 of 300 | 1.16e+15 | 5 | 0.0011 | 0.6954 | 0.0000 |
| Class weight | tuned | 5 of 200 | 6.82e+15 | 2 | 0.0006 | 0.4998 | 0.0000 |
| Class weight | baseline, boost_from_average off | 300 of 300 | 1.61e+06 | 16,144 | 0.3246 | 0.9156 | 0.3719 |
| Class weight | tuned, boost_from_average off | 200 of 200 | 1.61e+06 | 9,635 | 0.3409 | 0.9421 | 0.4053 |

### Model comparison

#### Best run per family on validation

| Model | Strategy | PR-AUC | 95% interval (steps resampled) | ROC-AUC | Precision | Recall | F1 | Balanced acc. |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| CatBoost | Class weight | 0.3527 | 0.2572 to 0.4612 | 0.9394 | 0.2097 | 0.4018 | 0.2756 | 0.7004 |
| XGBoost | Original | 0.3499 | 0.2598 to 0.4533 | 0.9461 | 0.2121 | 0.4123 | 0.2801 | 0.7057 |
| LightGBM | SMOTE | 0.3448 | 0.2513 to 0.4485 | 0.9346 | 0.2072 | 0.4123 | 0.2758 | 0.7057 |
| Random Forest | Original | 0.3203 | 0.2304 to 0.4213 | 0.9439 | 0.1815 | 0.3754 | 0.2447 | 0.6872 |
| Decision Tree | SMOTE | 0.3160 | 0.2285 to 0.4145 | 0.9209 | 0.2198 | 0.3895 | 0.2810 | 0.6943 |
| Logistic Regression | Original | 0.0830 | 0.0364 to 0.1589 | 0.8845 | 0.1058 | 0.2018 | 0.1388 | 0.6004 |

#### Confusion matrices, error rates and cost

| Model | TP | FP | FN | TN | FPR | FNR | Train (s) | Batch (us/row) | Single row (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CatBoost | 229 | 863 | 341 | 971,740 | 0.089% | 59.8% | 61.1 | 0.35 | 2.01 |
| XGBoost | 235 | 873 | 335 | 971,730 | 0.090% | 58.8% | 18.4 | 0.56 | 2.06 |
| LightGBM | 235 | 899 | 335 | 971,704 | 0.092% | 58.8% | 11.8 | 1.08 | 2.13 |
| Random Forest | 214 | 965 | 356 | 971,638 | 0.099% | 62.5% | 42.6 | 0.80 | 5.76 |
| Decision Tree | 222 | 788 | 348 | 971,815 | 0.081% | 61.1% | 16.6 | 0.27 | 1.74 |
| Logistic Regression | 115 | 972 | 455 | 971,631 | 0.100% | 79.8% | 3.0 | 0.31 | 2.14 |

### Stability and selection gates

| Model | Mean PR-AUC across seeds | Seed variation | Rolling fold PR-AUC | Type baseline per fold | PR-AUC gap to top (95%) | Gates |
| --- | ---: | ---: | --- | --- | --- | --- |
| Logistic Regression | 0.0830 | 0.0% | 0.0868, 0.0841, 0.0145 | 0.0025, 0.0031, 0.0029 | 0.1990 to 0.3383 | passed |
| Decision Tree | 0.3164 | 1.0% | 0.1876, 0.2814, 0.1927 | 0.0025, 0.0031, 0.0029 | 0.0101 to 0.0657 | passed |
| Random Forest | 0.3211 | 0.2% | 0.1708, 0.1910, 0.1062 | 0.0025, 0.0031, 0.0029 | 0.0061 to 0.0620 | passed |
| XGBoost | 0.3474 | 0.7% | 0.2260, 0.3427, 0.3805 | 0.0025, 0.0031, 0.0029 | -0.0110 to 0.0151 | passed |
| LightGBM | 0.3457 | 0.2% | 0.2193, 0.3389, 0.2378 | 0.0025, 0.0031, 0.0029 | -0.0124 to 0.0318 | passed |
| CatBoost | 0.3522 | 0.6% | 0.2168, 0.3452, 0.3709 | 0.0025, 0.0031, 0.0029 | top | passed |

### Threshold behaviour

#### Thresholds on validation

| Rule | Threshold | Precision | Recall | F1 | FPR | Alerts | Recall (sparse) | Recall (normal) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Selected (FPR at most 0.1%)** | 0.0284191 | 0.2121 | 0.4123 | 0.2801 | 0.090% | 1,108 | 0.9563 | 0.2000 |
| PRD candidate 0.30 | 0.3 | 0.8846 | 0.2421 | 0.3802 | 0.002% | 156 | 0.5062 | 0.1390 |
| PRD candidate 0.40 | 0.4 | 0.8939 | 0.2070 | 0.3362 | 0.001% | 132 | 0.4250 | 0.1220 |
| PRD candidate 0.50 | 0.5 | 0.9068 | 0.1877 | 0.3110 | 0.001% | 118 | 0.3563 | 0.1220 |
| PRD candidate 0.60 | 0.6 | 0.9882 | 0.1474 | 0.2565 | 0.000% | 85 | 0.2687 | 0.1000 |
| PRD candidate 0.70 | 0.7 | 0.9863 | 0.1263 | 0.2240 | 0.000% | 73 | 0.2000 | 0.0976 |
| fpr cap 0.0001 | 0.0712455 | 0.6690 | 0.3404 | 0.4512 | 0.010% | 290 | 0.7937 | 0.1634 |
| fpr cap 0.0005 | 0.0342728 | 0.4184 | 0.3912 | 0.4044 | 0.032% | 533 | 0.9125 | 0.1878 |
| fpr cap 0.001 | 0.0284191 | 0.2121 | 0.4123 | 0.2801 | 0.090% | 1,108 | 0.9563 | 0.2000 |
| fpr cap 0.005 | 0.0118244 | 0.0704 | 0.4596 | 0.1220 | 0.356% | 3,724 | 0.9750 | 0.2585 |
| fpr cap 0.01 | 0.0106894 | 0.0280 | 0.4912 | 0.0530 | 0.999% | 9,996 | 0.9750 | 0.3024 |
| max f1 | 0.0763189 | 0.6807 | 0.3404 | 0.4538 | 0.009% | 285 | 0.7937 | 0.1634 |
| max f2 | 0.0343454 | 0.4184 | 0.3912 | 0.4044 | 0.032% | 533 | 0.9125 | 0.1878 |

#### Does the rule hold on steps it did not see?

| Check | Recall | FPR | Precision |
| --- | ---: | ---: | ---: |
| Set on early steps, measured on late | 0.4338 | 0.094% | 0.2310 |
| Set on late steps, measured on early | 0.3881 | 0.086% | 0.1922 |
| Out-of-bag steps, mean (95% interval) | 0.4163 (0.2594 to 0.5557) | 0.118% (0.008% to 0.327%) | 0.2368 |

#### Do scores behave like probabilities?

| Score bin | Rows | Fraud | Mean score | Observed fraud rate |
| --- | ---: | ---: | ---: | ---: |
| 0.0 to 0.1 | 972,921 | 393 | 0.0006 | 0.0004 |
| 0.1 to 0.2 | 68 | 21 | 0.1319 | 0.3088 |
| 0.2 to 0.3 | 28 | 18 | 0.2527 | 0.6429 |
| 0.3 to 0.4 | 24 | 20 | 0.3421 | 0.8333 |
| 0.4 to 0.5 | 14 | 11 | 0.4480 | 0.7857 |
| 0.5 to 0.6 | 33 | 23 | 0.5467 | 0.6970 |
| 0.6 to 0.7 | 12 | 12 | 0.6677 | 1.0000 |
| 0.7 to 0.8 | 10 | 10 | 0.7407 | 1.0000 |
| 0.8 to 0.9 | 37 | 36 | 0.8582 | 0.9730 |
| 0.9 to 1.0 | 26 | 26 | 0.9659 | 1.0000 |

### SHAP

#### Mean absolute SHAP value by group (log-odds)

| Group | All rows (reweighted) | Fraud rows | Legitimate rows | Sparse steps | Normal steps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Type and destination | 2.3020 | 1.3594 | 2.3026 | 3.2782 | 2.3007 |
| Amount | 0.5167 | 1.4620 | 0.5161 | 0.6745 | 0.5165 |
| Hour of day | 0.3536 | 1.4755 | 0.3530 | 2.6921 | 0.3503 |

#### Explained examples

| Example | Transaction | Score | Pushed score up | Pushed score down |
| --- | --- | --- | --- | --- |
| most missed fraud | CASH_OUT, 161,859.16, hour 19 | 0.0003002 | transaction_type_CASH_OUT +0.34, transaction_type_PAYMENT +0.20, transaction_type_CASH_IN +0.18 | amount -0.60, hour_of_day -0.32, hour_sin -0.31 |
| strongest false alert | TRANSFER, 2,821,973.25, hour 2 | 0.5698 | hour_of_day +3.32, amount +2.29, amount_log1p +0.80 | transaction_type_CASH_OUT -0.44, hour_sin -0.01 |
| strongest true alert | CASH_OUT, 3,244,067.25, hour 5 | 0.9928 | amount +3.65, hour_of_day +3.15, transaction_type_CASH_OUT +1.54 | none |

Largest additivity error across explained rows: 5.36e-07.
