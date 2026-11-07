# final_evaluation.py

Source: [backend/app/ml/final_evaluation.py](../../../../../backend/app/ml/final_evaluation.py)

## A. File Purpose
Runs the single evaluation of the frozen model on the test partition, and separates prior shift from real changes in model behaviour.

## B. Why This File Exists
The authorisation requires the test partition to stay untouched until the model and threshold are frozen. This is the only module that reads it, so the rule can be checked by a test and enforced at run time.

## C. Dependencies
- **Libraries:** `numpy`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.drift`, `app.ml.evaluation`, `app.ml.experiment_stages`, `app.ml.model_artifacts`, `app.ml.pipeline_io`, `app.ml.preprocessing`, `app.ml.regimes`.
- **External services / database:** none.
- **Depended on by:** `scripts/evaluate_final_test.py`.

## D. Every Function Explained

### `assert_ready_for_test`
- **Purpose:** enforce the one-time rule.
- **Parameters / types:** `metadata: dict`; `output_path: Path`.
- **Returns / type:** `None`.
- **Internal processing:** checks the frozen status and that no result file exists.
- **Error handling:** raises `ModelNotFrozenError` or `TestAlreadyEvaluatedError`.
- **Calls:** nothing.
- **Used by:** `evaluate_frozen_model`.

### `_score_partition`
- **Purpose:** score a partition with the frozen model.
- **Parameters / types:** `model: LoadedModel`; `partition: PartitionData`.
- **Returns / type:** `np.ndarray`.
- **Internal processing:** compacts features, then calls `predict_proba`.
- **Error handling:** inherited.
- **Calls:** `compact_features`.
- **Used by:** `evaluate_frozen_model`.

### `_regime_comparison`
- **Purpose:** report sparse and normal steps on test, next to validation.
- **Parameters / types:** test and validation labels, scores and slices; `threshold: float`.
- **Returns / type:** `dict` by regime.
- **Internal processing:** ranking and threshold metrics for each regime, for both partitions.
- **Error handling:** inherited.
- **Calls:** `threshold_metrics`, `ranking_metrics`.
- **Used by:** `evaluate_frozen_model`.

### `_prior_shift_check`
- **Purpose:** ask whether prevalence alone explains the change in precision.
- **Parameters / types:** test and validation labels and scores; `threshold: float`.
- **Returns / type:** `dict`.
- **Internal processing:** computes expected precision from validation's recall and false positive rate at test prevalence, and PR-AUC reweighted to validation's prevalence.
- **Error handling:** inherited.
- **Calls:** `threshold_metrics`, `expected_precision`, `prevalence_adjusted_pr_auc`, `ranking_metrics`.
- **Used by:** `evaluate_frozen_model`.

### `_alerts_by_day`
- **Purpose:** show how alerts and recall move over time.
- **Parameters / types:** `labels`, `scores`, `steps`: arrays; `threshold: float`.
- **Returns / type:** `list[dict]`.
- **Internal processing:** groups steps into 24-step days.
- **Error handling:** undefined metrics are `None`.
- **Calls:** `threshold_metrics`.
- **Used by:** `evaluate_frozen_model`.

### `evaluate_frozen_model`
- **Purpose:** run the evaluation and save it.
- **Parameters / types:** `model: LoadedModel`; `processed_dir: Path`; `output_path: Path`; `config: dict`; `source_commit: str`.
- **Returns / type:** `dict`; also written to JSON.
- **Internal processing:** checks readiness; loads all three partitions; scores test and validation; computes overall, regime, slice, baseline, prior-shift, drift and daily results.
- **Error handling:** see `assert_ready_for_test`. No threshold or model setting is an argument, so neither can be changed here.
- **Calls:** the helpers above, `feature_drift`, `type_rate_scores`, `bootstrap_pr_auc`, `build_slices`, `decimated_curves`.
- **Used by:** `scripts/evaluate_final_test.py`.

## E. Classes Explained

### `TestAlreadyEvaluatedError`
Raised on a second attempt. `__test__ = False` stops pytest collecting it because of its name.

### `ModelNotFrozenError`
Raised if the metadata does not record a freeze.

## F. Execution Flow
Check readiness, load partitions, score, compute all sections, save once.

## G. Input and Output
Input: the frozen model and all three partitions. Output: `experiments/results/phase2/test_evaluation.json`.

## H. Important Technical Concepts
**Prior shift check:** suppose validation gives recall R and false positive rate F. If only prevalence changes to p, Bayes' rule predicts precision R×p / (R×p + F×(1−p)). Precision higher than validation's is not in itself model skill, so this expected value is the fair comparison.

**Prevalence-adjusted PR-AUC:** reweights test's legitimate rows so its effective fraud rate matches validation's. It assumes the score distribution within each class is unchanged.

**Report only:** the PRD threshold candidates are listed for information. They cannot affect the threshold, which is frozen already.

**Only the selected model is evaluated.** Scoring the other finalists on test would invite choosing after the fact.

## I. Example
```python
model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
report = evaluate_frozen_model(model, PROCESSED_DIR, output_path, config, commit)
print(report["overall"]["at_frozen_threshold"])
```

## J. Maintenance Notes
Never delete `test_evaluation.json` to rerun with changes to the model or threshold. After this evaluation, the test set is no longer untouched for this project: a later model needs a new evaluation window, or its test result must be clearly labelled as such.

## K. Related Files
- [evaluate_final_test.py](../../../scripts/evaluate_final_test.py.explanation.md): runs this, with the Git check.
- [model_artifacts.py](model_artifacts.py.explanation.md): the verified model.
- [evaluation.py](evaluation.py.explanation.md): metrics.
- [drift.py](drift.py.explanation.md): feature drift.
