# ML Experiments

**Status: no model has been trained yet.** Phase 2 fills in model comparisons, thresholds and the selected model. This file currently records the experimental design and the data findings that constrain it.

All results must come from executed runs and saved files. No figure may be written here by hand from memory.

## Design fixed by Phase 1

| Element | Decision |
|---|---|
| Features | Seven features in schema `1.0.0`, derived only from the four prediction inputs |
| Excluded | Balances, identifiers, `isFraud`, `isFlaggedFraud`, raw `step` |
| Training | Steps 1 to 322 (3,633 fraud rows, 0.0819%) |
| Validation | Steps 323 to 377 (570 fraud rows, 0.0586%) |
| Test | Steps 378 to 743 (4,010 fraud rows, 0.4196%). No model has seen it. |

## What the data implies for Phase 2

### 1. Expect far lower scores than published PaySim results
Many public PaySim notebooks report near-perfect scores using balance columns, which this project excludes. Without them the task is much harder. No estimate is given here: Phase 2 measures it. A modest honest score should be expected and is not a failure, and any near-perfect score should be treated as a leakage alarm.

### 2. Base rates differ strongly across partitions
Test prevalence is about 7 times validation prevalence, for a structural reason: fraud stays near 11 rows per step while legitimate volume collapses late in the simulation.

Consequences:
- **PR-AUC and precision cannot be compared directly across partitions**, because both depend on prevalence. Report each alongside its baseline, which for PR-AUC is the partition's fraud rate.
- **A validation-chosen threshold may behave differently on test.** Precision is likely to look better on test simply because fraud is more common there. This should be reported as prior shift, not as model skill.
- **ROC-AUC is less affected by prevalence** and is a useful cross-partition comparison, though it can look flattering at this imbalance, so it does not replace PR-AUC.

### 3. Report test results by regime
Steps with fewer than 1,000 rows behave like a different population, with a fraud rate of 10% to 15% against under 0.13% elsewhere. They hold 70% of test fraud but only 28% of validation fraud. Phase 2 should report test metrics overall and separately for low-volume and normal steps, using the stored `step` column.

### 4. Hour features may not transfer fully
In training, overnight hours are low-volume and fraud-heavy. Late in the simulation, low volume also occurs in daytime hours. A model that learned "overnight means fraud" may therefore lose signal in that period. Comparing regimes will show whether this happens.

### 5. Validation has few positives
570 fraud rows limit how precisely validation can rank similar models. Stability across seeds and comparison of confidence intervals should inform selection, as PRD 5.6 asks for stability. Time-ordered folds within training are an option if validation proves too noisy.

### 6. SMOTE and ADASYN need care
PRD 5.2 allows these only where the representation supports meaningful synthetic samples. Interpolating one-hot categories produces values that do not correspond to real transactions. Planned approach: SMOTENC or restricting oversampling to continuous features within each type, always inside the training pipeline only. If neither is defensible for a model, the reason will be documented rather than the experiment being forced.

### 7. Most of the data is trivially legitimate
All training fraud is in two types. Models will learn this quickly, so overall ROC-AUC will partly reflect that easy split. Reporting metrics within TRANSFER and CASH_OUT will show whether a model does more than recognise the type.

### 8. Rule baseline
`isFlaggedFraud` flags 3, 0 and 13 rows across train, validation and test, and every flagged row is fraud. It serves as the existing-rule baseline: perfect precision and almost no recall.

### 9. Compute constraints
The development machine has 16 logical processors and 15.7 GB of RAM, and training has about 4.4 million rows. Any adjustment to the model list or search budget will be documented here.

## Results
None yet.
