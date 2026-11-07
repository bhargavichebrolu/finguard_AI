# candidates.py

Source: [backend/app/ml/candidates.py](../../../../../backend/app/ml/candidates.py)

## A. File Purpose
Defines the six model families, the four imbalance strategies, and the description of one experiment.

## B. Why This File Exists
PRD 5.1 names the families and PRD 5.2 names the strategies. Keeping their construction in one place means every family receives the same preprocessing and the same meaning of "class weighting".

## C. Dependencies
- **Libraries:** `scikit-learn`, plus `xgboost`, `lightgbm` and `catboost` when those families are built.
- **Internal modules:** `app.ml.imbalance`, `app.ml.preprocessing`.
- **External services / database:** none.
- **Depended on by:** `experiments.py`, `experiment_stages.py`, `selection.py`.

## D. Every Function Explained

### `build_estimator`
- **Purpose:** create one unfitted model.
- **Parameters / types:** `family: str`; `hyperparameters: Mapping`; `class_weighted: bool`; `positive_weight: float`; `seed: int`; `threads: int`.
- **Returns / type:** an unfitted estimator.
- **Internal processing:** imports the family's library and passes the seed, thread count and weighting using that library's own parameter names.
- **Error handling:** `ValueError` for an unknown family. A misspelled hyperparameter raises from the library.
- **Calls:** library constructors.
- **Used by:** `build_pipeline`.

### `build_pipeline`
- **Purpose:** join preprocessing and an estimator.
- **Parameters / types:** `spec: CandidateSpec`; `positive_weight: float`; `threads: int`.
- **Returns / type:** an unfitted `sklearn.pipeline.Pipeline`.
- **Internal processing:** only Logistic Regression gets numeric scaling, as trees do not need it.
- **Error handling:** inherited.
- **Calls:** `build_estimator`, `build_preprocessor`.
- **Used by:** `experiments.fit_candidate`.

### `set_inference_threads`
- **Purpose:** set how many threads a fitted model uses for prediction.
- **Parameters / types:** `pipeline: Pipeline`; `threads: int`.
- **Returns / type:** `None`; changes the pipeline in place.
- **Internal processing:** sets `n_jobs` where the model has it.
- **Error handling:** CatBoost raises an error if a parameter changes after fitting, so it is left alone and keeps the thread count it was fitted with. Its single-row timing is therefore not strictly single-threaded. Models with neither setting, such as Decision Tree, are also left unchanged.
- **Calls:** `set_params`.
- **Used by:** `experiments.measure_inference`.

## E. Classes Explained

### `CandidateSpec`
- **Purpose:** an immutable description of one experiment.
- **Attributes:** `family`, `strategy`, `hyperparameters`, `seed`, `target_ratio`, `dropped_features`.
- **`__post_init__`:** rejects an unknown family or strategy, and a `target_ratio` set when it does not apply or missing when it does.
- **`identity`:** returns the JSON form saved with results.
- **`run_id`:** family, strategy and a hash of all fields. Changing any setting gives a new id, so a stale result can never be mistaken for a new one.

## F. Execution Flow
A stage creates a `CandidateSpec`, `experiments.fit_candidate` calls `build_pipeline` with the fold's weight, and the pipeline is fitted.

## G. Input and Output
Input: settings from `experiments_v1.json`. Output: an unfitted pipeline.

## H. Important Technical Concepts
**Class weighting** makes each fraud row count as much as `legitimate / fraud` legitimate rows, which is about 1,220 in the full training partition. For the libraries that take `scale_pos_weight` this equals sklearn's `class_weight="balanced"` in effect.

**A class-weighted score is not a probability.** Weighting and oversampling push scores upward, which is why thresholds are chosen from data and calibration is reported separately.

**Same encoding for all:** CatBoost receives one-hot columns like the others instead of its own categorical handling, so that its target statistics cannot be a difference between families. With five categories, little is lost.

**Lazy imports:** a saved model needs only its own library, so the API image can stay small.

## I. Example
```python
spec = CandidateSpec("lightgbm", "original", {"n_estimators": 300}, seed=42)
pipeline = build_pipeline(spec, positive_weight=1220.0, threads=8)
```

## J. Maintenance Notes
To add a family: add it to `MODEL_FAMILIES`, add a branch to `build_estimator`, add baseline settings to the config, and check `explainability.py` supports it. See section 29 of [PROJECT_CONNECTIONS.md](../../../../../PROJECT_CONNECTIONS.md).

## K. Related Files
- [experiments.py](experiments.py.explanation.md): fits candidates.
- [preprocessing.py](preprocessing.py.explanation.md): the shared preprocessing.
- [imbalance.py](imbalance.py.explanation.md): the oversampling strategies.
