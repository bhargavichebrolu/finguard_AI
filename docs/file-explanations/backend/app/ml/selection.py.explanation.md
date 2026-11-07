# selection.py

Source: [backend/app/ml/selection.py](../../../../../backend/app/ml/selection.py)

## A. File Purpose
Selects the model and threshold from validation evidence, using a rule fixed in advance, then refits and saves the winner.

## B. Why This File Exists
The authorisation for Phase 2 requires that selection never uses test performance, and PRD 5.6 requires a justified choice beyond one metric. Writing the rule as code, committed before any result existed, prevents the rule from being adjusted to fit the outcome.

## C. Dependencies
- **Libraries:** `numpy`, standard library `json`, `statistics`, `platform`, `importlib.metadata`.
- **Internal modules:** `app.ml.candidates`, `app.ml.evaluation`, `app.ml.experiment_stages`, `app.ml.experiments`, `app.ml.model_artifacts`, `app.ml.pipeline_io`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `scripts/evaluate_models.py`.

## D. Every Function Explained

### `_same_settings`
- **Purpose:** decide whether two runs differ only in their seed.
- **Parameters / types:** `spec_a`, `spec_b`: dicts.
- **Returns / type:** `bool`.
- **Internal processing:** compares every field except the seed.
- **Error handling:** `KeyError` if a field is missing.
- **Calls:** nothing.
- **Used by:** `summarise_family`.

### `summarise_family`
- **Purpose:** gather what the rule needs about a family's best run.
- **Parameters / types:** `family: str`; `runs: dict`; `fold_reports: list[dict]`.
- **Returns / type:** `dict | None`.
- **Internal processing:** finds the best search run, its seed repeats and its rolling folds.
- **Error handling:** `None` if the family has no successful run. Failed seed runs are counted.
- **Calls:** `best_run`, `_same_settings`.
- **Used by:** `family_summaries`.

### `apply_gates`
- **Purpose:** reject candidates that lack minimum skill or stability.
- **Parameters / types:** `candidates: list[dict]`; `type_rate_pr_auc: float`; `rule: dict`.
- **Returns / type:** `(passed, rejected)`, with reasons for each rejection.
- **Internal processing:** must beat the type baseline on validation and in every rolling fold, and seed variation must be within the limit.
- **Error handling:** a failed fold or seed run is a rejection reason.
- **Calls:** nothing.
- **Used by:** `freeze_selected_model`.

### `choose_candidate`
- **Purpose:** apply the three ranking steps.
- **Parameters / types:** `passed: list[dict]`; `differences: dict`; `rule: dict`.
- **Returns / type:** `dict` naming the outcome of each step.
- **Internal processing:** see the rule in section H.
- **Error handling:** `ValueError` for an empty list.
- **Calls:** nothing.
- **Used by:** `freeze_selected_model`.

### `_threshold_grid`
- **Purpose:** provide thresholds to sweep.
- **Parameters / types:** none.
- **Returns / type:** `np.ndarray`.
- **Internal processing:** log spacing near 0 and near 1, even spacing between, plus the PRD candidates. Different strategies concentrate scores at different ends of the scale.
- **Error handling:** none needed.
- **Calls:** numpy.
- **Used by:** `analyse_thresholds`.

### `reliability_table`
- **Purpose:** check whether scores behave like probabilities.
- **Parameters / types:** `labels`, `scores`: arrays.
- **Returns / type:** `list[dict]`.
- **Internal processing:** ten equal-width bins, each with mean score and observed fraud rate.
- **Error handling:** an empty bin has `None` values.
- **Calls:** numpy.
- **Used by:** `analyse_thresholds`.

### `_with_slices`
- **Purpose:** report one threshold overall and on each slice.
- **Parameters / types:** `labels`, `scores`, `threshold`, `slices`.
- **Returns / type:** `dict`.
- **Internal processing:** calls `threshold_metrics` per slice.
- **Error handling:** inherited.
- **Calls:** `threshold_metrics`.
- **Used by:** `analyse_thresholds`.

### `analyse_thresholds`
- **Purpose:** study threshold behaviour on validation and choose the threshold.
- **Parameters / types:** `labels`, `scores`, `steps`: arrays; `slices: dict`; `settings: dict`.
- **Returns / type:** `dict`.
- **Internal processing:** the fixed objective, the PRD candidates, alternative rules, a full sweep, an early-versus-late check, out-of-bag behaviour, reliability and curves.
- **Error handling:** inherited.
- **Calls:** the threshold and metric functions in `evaluation.py`.
- **Used by:** `freeze_selected_model`.

### `compare_with_top`
- **Purpose:** compare each candidate with the top candidate.
- **Parameters / types:** `candidates`, `scores_by_family`, `labels`, `steps`, `bootstrap`.
- **Returns / type:** `dict` by family.
- **Internal processing:** paired step bootstrap of the PR-AUC difference.
- **Error handling:** inherited.
- **Calls:** `paired_bootstrap_difference`.
- **Used by:** `freeze_selected_model`.

### `family_summaries`
- **Purpose:** summarise all families.
- **Parameters / types:** `runs`, `fold_reports`.
- **Returns / type:** `(summaries, missing)`.
- **Internal processing:** calls `summarise_family` for each.
- **Error handling:** families without results are listed, not hidden.
- **Calls:** `summarise_family`.
- **Used by:** `freeze_selected_model`, `reporting.py`.

### `spec_from_summary`
- **Purpose:** rebuild the exact spec of a run.
- **Parameters / types:** `summary: dict`.
- **Returns / type:** `CandidateSpec`.
- **Internal processing:** copies the fields.
- **Error handling:** validation in `CandidateSpec`.
- **Calls:** `CandidateSpec`.
- **Used by:** `freeze_selected_model`.

### `score_semantics`
- **Purpose:** state honestly what the score means.
- **Parameters / types:** `strategy: str`.
- **Returns / type:** `str`.
- **Internal processing:** chooses a description by strategy.
- **Error handling:** none needed.
- **Calls:** nothing.
- **Used by:** `freeze_selected_model`.

### `_library_versions`
- **Purpose:** record versions needed to load the model.
- **Parameters / types:** `family: str`.
- **Returns / type:** `dict[str, str]`.
- **Internal processing:** reads installed package versions.
- **Error handling:** `PackageNotFoundError` if a package is absent.
- **Calls:** `importlib.metadata.version`.
- **Used by:** `freeze_selected_model`.

### `freeze_selected_model`
- **Purpose:** run the whole selection and save the result.
- **Parameters / types:** `data`, `config`, `store`, `results_dir`, `models_dir`, `metadata_path`, `preprocessing_metadata_path`, `source_commit`.
- **Returns / type:** `dict`, the selection report.
- **Internal processing:** applies gates and ranking, refits the winner on training rows, compares its score hash with the recorded run, analyses thresholds, then saves the reports and model.
- **Error handling:** if no candidate passes the gates, selection continues among all candidates and sets `no_candidate_passed`, which must be reported. A refit mismatch is recorded in `refit_matches_recorded_run`, not hidden.
- **Calls:** the functions above, `fit_candidate`, `score_rows`, `save_model_artifact`.
- **Used by:** `scripts/evaluate_models.py`.

## E. Classes Explained
None.

## F. Execution Flow
Summaries, gates, paired comparison, ranking steps, refit, threshold analysis, save.

## G. Input and Output
Input: `runs.json`, `baselines.json`, `rolling_folds.json`, saved scores, train and validation rows. Output: `selection.json`, `threshold_analysis.json`, `artifacts/models/fraud_detector_v1/model.joblib`, `artifacts/metadata/model_v1.json`.

## H. Important Technical Concepts
**The rule, fixed in advance:**
1. **Gates:** beat the transaction-type baseline on validation and in every rolling fold, and keep seed variation at or below 10%.
2. Keep candidates whose PR-AUC cannot be distinguished from the top candidate's (the paired bootstrap interval includes 0).
3. Among those, take the highest recall at the 0.1% false positive cap, treating values within 1 percentage point as tied.
4. Among those, take the lowest single-row prediction time.

**Why statistical ties go to the operational metric:** validation has 55 steps, so a small PR-AUC lead may be noise. In that case it is more sensible to decide on what matters in use.

**Why a false positive cap:** precision and F1 change with prevalence, which shifts greatly over time. The false positive rate is defined on legitimate rows alone, so a threshold set this way has a stable meaning. It also sets the review burden directly.

**Selected from family winners only:** sensitivity runs cannot win. They were not part of the planned search.

## I. Example
```python
report = freeze_selected_model(data, config, store, results_dir, models_dir,
                               metadata_path, preprocessing_path, commit)
print(report["decision"]["selected_family"], report["selected_threshold"])
```

## J. Maintenance Notes
Do not change the rule after seeing results for a given model version. A new rule needs a new model version and a new, untouched evaluation window, because the current test set will already have been used.

## K. Related Files
- [0002-phase-2-decisions.md](../../../../decisions/0002-phase-2-decisions.md): the rule and why.
- [evaluate_models.py](../../../scripts/evaluate_models.py.explanation.md): runs this.
- [model_artifacts.py](model_artifacts.py.explanation.md): saves and loads.
- [evaluation.py](evaluation.py.explanation.md): metrics and bootstrap.
