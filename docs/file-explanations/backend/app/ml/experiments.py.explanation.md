# experiments.py

Source: [backend/app/ml/experiments.py](../../../../../backend/app/ml/experiments.py)

## A. File Purpose
Fits, times and evaluates one candidate, keeps the test partition closed, and stores every run so a long experiment can resume.

## B. Why This File Exists
Three rules are easiest to guarantee at one choke point: experiments cannot read the test partition, oversampling only touches training rows, and every run gets recorded, including failures.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `scikit-learn`, standard library `time`, `json`, `hashlib`.
- **Internal modules:** `app.ml.candidates`, `app.ml.dataset_preparation`, `app.ml.evaluation`, `app.ml.imbalance`, `app.ml.pipeline_io`, `app.ml.preprocessing`.
- **External services / database:** none.
- **Depended on by:** `experiment_stages.py`, `selection.py`.

## D. Every Function Explained

### `load_development_partition`
- **Purpose:** the only way experiment code loads data.
- **Parameters / types:** `processed_dir: Path`; `name: str`.
- **Returns / type:** `PartitionData` with float32 numeric features.
- **Internal processing:** checks the name, loads the partition, compacts it.
- **Error handling:** raises `TestPartitionAccessError` for anything except train and validation.
- **Calls:** `load_partition`, `partition_path`, `compact_features`.
- **Used by:** `experiment_stages.load_development_data`.

### `fit_candidate`
- **Purpose:** fit one candidate. The only caller of the oversampler.
- **Parameters / types:** `spec: CandidateSpec`; `features: pd.DataFrame`; `labels: np.ndarray`; `threads: int`; `k_neighbors: int`.
- **Returns / type:** `FittedCandidate`.
- **Internal processing:** oversamples if the strategy requires it, works out the class weight from the rows being fitted, fits the pipeline, and times each stage.
- **Error handling:** `ValueError` if the rows contain no fraud.
- **Calls:** `oversample_training_fold`, `build_pipeline`.
- **Used by:** `evaluate_candidate`, `selection.py`.

### `score_rows`
- **Purpose:** get fraud scores.
- **Parameters / types:** `pipeline: Pipeline`; `features: pd.DataFrame`.
- **Returns / type:** `np.ndarray` of float64.
- **Internal processing:** column 1 of `predict_proba`.
- **Error handling:** inherited.
- **Calls:** `predict_proba`.
- **Used by:** `measure_inference`, `selection.py`.

### `measure_inference`
- **Purpose:** measure prediction speed, both in batch and for single rows.
- **Parameters / types:** `pipeline`, `features`; `threads: int`; `single_rows: int`.
- **Returns / type:** `(scores, timing dict)`.
- **Internal processing:** times one batch, then evenly spaced single rows on one thread, discarding the first five as warm-up.
- **Error handling:** inherited.
- **Calls:** `score_rows`, `set_inference_threads`.
- **Used by:** `evaluate_candidate`.

### `scores_digest`
- **Purpose:** fingerprint a set of scores.
- **Parameters / types:** `scores: np.ndarray`.
- **Returns / type:** hexadecimal `str`.
- **Internal processing:** SHA-256 of the float64 bytes.
- **Error handling:** none needed.
- **Calls:** `hashlib`.
- **Used by:** `evaluate_candidate`, `selection.py`, to confirm that a refit reproduces a run exactly.

### `evaluate_candidate`
- **Purpose:** run one fit-and-evaluate cycle.
- **Parameters / types:** `spec`, `stage: str`, `train`, `evaluation`: `PartitionData`; `slices: dict`; `settings: dict`.
- **Returns / type:** `(record, scores)`.
- **Internal processing:** fits, scores, evaluates, and assembles the record.
- **Error handling:** errors propagate to `run_candidate`.
- **Calls:** `fit_candidate`, `measure_inference`, `evaluate_scores`, `scores_digest`.
- **Used by:** `experiment_stages.py`.

### `run_candidate`
- **Purpose:** run a candidate once and save the outcome.
- **Parameters / types:** `spec`, `stage`, `store: RunStore`, `run: Callable`; optional `run_id`, `keep_scores`.
- **Returns / type:** the run record.
- **Internal processing:** returns the saved record if one exists. Otherwise it calls `run`, saves the result and prints a progress line.
- **Error handling:** any `Exception` becomes a saved record with status `failed`, so failures stay in the results. The broad catch is deliberate, because each library raises its own error types. Interrupting with Ctrl+C still stops the run.
- **Calls:** `RunStore` methods.
- **Used by:** `experiment_stages.py`.

## E. Classes Explained

### `TestPartitionAccessError`
Raised by `load_development_partition`. `__test__ = False` stops pytest collecting it because of its name.

### `FittedCandidate`
A dataclass holding the fitted `pipeline` and a `report` of rows and timing.

### `RunStore`
- **Purpose:** durable results.
- **`__init__`:** loads existing results if the file exists.
- **`has`:** checks whether a run is already recorded.
- **`add`:** saves scores as float32, then rewrites the JSON.
- **`load_scores`:** reads a run's saved scores.
- **`_scores_path`:** the scores location for a run.

## F. Execution Flow
A stage calls `run_candidate`. If the run is new, `evaluate_candidate` calls `fit_candidate` then `measure_inference` then `evaluate_scores`, and the store saves the result.

## G. Input and Output
Input: a spec and partitions. Output: `experiments/results/phase2/runs.json`, committed, and `experiments/scores/<run_id>.npy`, Git-ignored.

## H. Important Technical Concepts
**Why oversampling cannot leak:** the sampler runs in `fit_candidate`, and the returned pipeline does not contain it. Anything passed to the pipeline afterwards is only transformed and scored.

**Timing comparability:** all families use the same thread count, on the same machine, one at a time. Other applications were open during the runs, so treat small differences as noise.

**Precision of saved scores:** saved scores are float32, which is enough for bootstrap ranking comparisons. The final threshold is always calculated from the frozen model's float64 scores, so this rounding cannot move it.

## I. Example
```python
store = RunStore(results_path, scores_dir)
spec = CandidateSpec("lightgbm", "original", {"n_estimators": 300}, seed=42)
record = run_candidate(
    spec, "matrix", store,
    lambda: evaluate_candidate(spec, "matrix", train, validation, slices, settings),
)
```

## J. Maintenance Notes
Deleting a run from `runs.json` makes the next run recalculate it. Never edit values in that file by hand. Any new oversampling call must go through `fit_candidate`.

## K. Related Files
- [experiment_stages.py](experiment_stages.py.explanation.md): decides which candidates to run.
- [candidates.py](candidates.py.explanation.md): builds models.
- [imbalance.py](imbalance.py.explanation.md): oversampling.
- [evaluation.py](evaluation.py.explanation.md): metrics.
