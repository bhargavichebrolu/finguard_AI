# experiment_stages.py

Source: [backend/app/ml/experiment_stages.py](../../../../../backend/app/ml/experiment_stages.py)

## A. File Purpose
Defines the experiment plan: baselines, the imbalance matrix, hyperparameter tuning, sensitivity runs and stability runs.

## B. Why This File Exists
The authorisation asks for a comparison of six families across four imbalance strategies, tuned on validation, with reproducible configuration. This file turns `experiments_v1.json` into those runs.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `scikit-learn` (`ParameterSampler`).
- **Internal modules:** `app.ml.candidates`, `app.ml.dataset_preparation`, `app.ml.evaluation`, `app.ml.experiments`, `app.ml.imbalance`, `app.ml.pipeline_io`, `app.ml.regimes`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** `scripts/train_models.py`, `selection.py`, `scripts/evaluate_models.py`.

## D. Every Function Explained

### `load_experiment_config`
- **Purpose:** read and check the config.
- **Parameters / types:** `path: Path`.
- **Returns / type:** `dict`.
- **Internal processing:** checks required keys, family coverage, the seed list and the false positive cap.
- **Error handling:** `ValueError` naming the problem.
- **Calls:** `json`.
- **Used by:** every Phase 2 script.

### `load_development_data`
- **Purpose:** load the two partitions experiments may use.
- **Parameters / types:** `processed_dir: Path`; `config: dict`.
- **Returns / type:** `ExperimentData`.
- **Internal processing:** loads train and validation, and builds validation's slices once.
- **Error handling:** inherited.
- **Calls:** `load_development_partition`, `build_slices`.
- **Used by:** `train_models.py`, `evaluate_models.py`, `analyse_temporal_drift.py`.

### `type_rate_scores`
- **Purpose:** the baseline that only recognises the transaction type.
- **Parameters / types:** `train_features`, `train_labels`, `target_features`.
- **Returns / type:** `np.ndarray`.
- **Internal processing:** gives each row its type's fraud rate in the fit rows.
- **Error handling:** a type absent from the fit rows gets 0.
- **Calls:** numpy, pandas.
- **Used by:** `run_baselines`, `run_stability`, `final_evaluation.py`.

### `run_baselines`
- **Purpose:** evaluate non-learning references.
- **Parameters / types:** `data`, `config`, `output_path`.
- **Returns / type:** `dict`; also written to JSON.
- **Internal processing:** a random ranking, the type-rate baseline and the existing `isFlaggedFraud` rule.
- **Error handling:** inherited.
- **Calls:** `type_rate_scores`, `evaluate_scores`, `ranking_metrics`, `threshold_metrics`.
- **Used by:** `train_models.py`.

### `_matrix_spec`
- **Purpose:** build the spec for one matrix cell.
- **Parameters / types:** `family: str`; `strategy: str`; `config: dict`.
- **Returns / type:** `CandidateSpec`.
- **Internal processing:** baseline settings, with the target ratio only for oversampling.
- **Error handling:** validated by `CandidateSpec`.
- **Calls:** `CandidateSpec`.
- **Used by:** `run_matrix`.

### `_run_on_validation`
- **Purpose:** fit on train and evaluate on validation, once.
- **Parameters / types:** `spec`, `stage`, `data`, `config`, `store`.
- **Returns / type:** the run record.
- **Internal processing:** wraps `evaluate_candidate` in `run_candidate`.
- **Error handling:** failures become saved records.
- **Calls:** `run_candidate`, `evaluate_candidate`.
- **Used by:** all search stages.

### `run_matrix`
- **Purpose:** compare six families across four strategies at fixed settings.
- **Parameters / types:** `data`, `config`, `store`.
- **Returns / type:** `None`.
- **Internal processing:** two nested loops.
- **Error handling:** inherited.
- **Calls:** `_matrix_spec`, `_run_on_validation`.
- **Used by:** `train_models.py`.

### `best_run`
- **Purpose:** find a family's best run.
- **Parameters / types:** `runs: dict`; `family: str`; `stages: tuple`.
- **Returns / type:** `(run_id, run) | None`.
- **Internal processing:** highest validation PR-AUC among successful runs in the given stages. Sorting by id first makes ties deterministic.
- **Error handling:** `None` if nothing is eligible.
- **Calls:** nothing.
- **Used by:** `run_tuning`, `overall_top_family`, `run_sensitivity`, `run_stability`, `selection.py`.

### `tuning_specs`
- **Purpose:** sample hyperparameters around the baseline.
- **Parameters / types:** `family`, `winner`, `config`.
- **Returns / type:** `list[CandidateSpec]`.
- **Internal processing:** `ParameterSampler` with the primary seed, keeping the family's best strategy.
- **Error handling:** an unknown setting raises when the model is built, and is recorded as a failed run.
- **Calls:** `ParameterSampler`, `CandidateSpec`.
- **Used by:** `run_tuning`.

### `run_lightgbm_diagnostic`
- **Purpose:** find out why LightGBM collapsed in the matrix on the original distribution and with class weighting.
- **Parameters / types:** `data: ExperimentData`, `config: dict`, `tuned_hyperparameters: dict`.
- **Returns / type:** `dict`: the settings tried and one result per strategy and setting, marked `eligible_for_selection: False`.
- **Internal processing:** fits each of the two strategies under four settings on training rows, and scores validation.
- **Error handling:** a crash in one fit is recorded as that cell's result, because a crash is itself evidence.
- **Calls:** `fit_candidate`, `score_rows`, `ranking_metrics`, `threshold_for_fpr_cap`, `threshold_metrics`.
- **Used by:** `diagnose_lightgbm.py`. It does not use `RunStore`, so these fits cannot enter selection.

### `run_tuning`
- **Purpose:** search hyperparameters for each family.
- **Parameters / types:** `data`, `config`, `store`.
- **Returns / type:** `None`.
- **Internal processing:** takes the family's best matrix strategy and runs its samples.
- **Error handling:** a family with only failed runs is skipped with a message.
- **Calls:** `best_run`, `tuning_specs`, `_run_on_validation`.
- **Used by:** `train_models.py`.

### `overall_top_family`
- **Purpose:** find the leading family, for the feature sensitivity runs.
- **Parameters / types:** `runs: dict`.
- **Returns / type:** `str`.
- **Internal processing:** the maximum over family winners.
- **Error handling:** `ValueError` if there are no successful runs.
- **Calls:** `best_run`.
- **Used by:** `run_sensitivity`.

### `run_sensitivity`
- **Purpose:** check the oversampling ratio and which features carry the signal.
- **Parameters / types:** `data`, `config`, `store`.
- **Returns / type:** `None`.
- **Internal processing:** LightGBM at other ratios for both oversamplers, then the leading model without hour features and without amount features.
- **Error handling:** inherited.
- **Calls:** `best_run`, `overall_top_family`, `_spec_from_record`, `_run_on_validation`.
- **Used by:** `train_models.py`.

### `_subset`
- **Purpose:** select rows of a partition.
- **Parameters / types:** `partition`, `mask`.
- **Returns / type:** `PartitionData`.
- **Internal processing:** `.loc` on each field.
- **Error handling:** none needed.
- **Calls:** pandas.
- **Used by:** `run_stability`.

### `_spec_from_record`
- **Purpose:** rebuild a spec from a saved run.
- **Parameters / types:** `fields: dict`; optional `seed`, `dropped`.
- **Returns / type:** `CandidateSpec`.
- **Internal processing:** copies fields, overriding the seed or dropped features if given.
- **Error handling:** validated by `CandidateSpec`.
- **Calls:** `CandidateSpec`.
- **Used by:** `run_sensitivity`, `run_stability`.

### `_run_fold`
- **Purpose:** run one rolling fold.
- **Parameters / types:** `spec`, `fold_index`, `fit`, `evaluation`, `config`, `store`.
- **Returns / type:** the run record.
- **Internal processing:** builds the fold's slices, then fits and evaluates. Scores are not kept.
- **Error handling:** failures become saved records.
- **Calls:** `build_slices`, `run_candidate`, `evaluate_candidate`.
- **Used by:** `run_stability`.

### `run_stability`
- **Purpose:** test each family winner against other seeds and other time windows.
- **Parameters / types:** `data`, `config`, `store`, `folds_path`.
- **Returns / type:** `None`.
- **Internal processing:** builds forward folds inside the training partition, saves the fold baselines, then repeats each winner with other seeds and on each fold.
- **Error handling:** a family with no successful run is skipped with a message.
- **Calls:** `rolling_origin_folds`, `type_rate_scores`, `_run_on_validation`, `_run_fold`.
- **Used by:** `train_models.py`.

## E. Classes Explained

### `ExperimentData`
A dataclass holding `train`, `validation` and `validation_slices`.

## F. Execution Flow
Baselines, then matrix, tuning, sensitivity and stability. Each stage skips runs that already exist, so an interrupted experiment resumes.

## G. Input and Output
Input: `experiments_v1.json`, train and validation Parquet files. Output: `experiments/results/phase2/{baselines,runs,rolling_folds}.json` and score files.

## H. Important Technical Concepts
**Rolling-origin folds** fit on earlier rows and evaluate on later rows within the training partition. Random k-fold would train on the future. Each fold's oversampling is applied to that fold's fit rows only, because it happens inside `fit_candidate`.

**Tuning on one validation window:** about 66 tuning runs share 570 validation fraud rows. The winner's validation score is therefore somewhat optimistic, which is why seeds, folds and an untouched test set also matter.

**Type-rate baseline:** every model can recognise that fraud occurs in two types, so a model has only shown skill if it beats this baseline.

**Why tuning keeps one strategy per family:** searching every strategy would multiply the runs by four for little gain. The matrix identifies each family's strategy at fixed settings, and tuning then refines it. A strategy that needed different hyperparameters to shine would be missed, which is a known limitation.

## I. Example
```python
data = load_development_data(PROCESSED_DIR, config)
run_matrix(data, config, RunStore(results_path, SCORES_DIR))
```

## J. Maintenance Notes
A config change produces new run ids, so old results stay in `runs.json` under old ids. Start a new config version rather than editing `experiments_v1.json` after results exist.

## K. Related Files
- [experiments.py](experiments.py.explanation.md): one run.
- [selection.py](selection.py.explanation.md): uses the results.
- [train_models.py](../../../scripts/train_models.py.explanation.md): runs the stages.
- [splitting.py](splitting.py.explanation.md): rolling folds.
