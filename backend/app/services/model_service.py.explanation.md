# model_service.py

Source: [backend/app/services/model_service.py](model_service.py)

## A. File Purpose
Verifies and loads the frozen Phase 2 model for inference, scores transactions, computes per-transaction explanations, and records the active model in the database.

## B. Why This File Exists
The authorisation requires loading the existing model, verifying hashes before loading, never retraining at start-up, and never changing the model or threshold. All of that is enforced here, so routes and other services only see a `ServingModel` that has passed every check.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `xgboost`, `sqlalchemy`, `importlib.metadata`, `threading`.
- **Internal modules:** `app.ml.model_artifacts`, `app.ml.features`, `app.ml.preprocessing`, `app.ml.explainability`, `app.ml.pipeline_io`, `app.core.frozen_model`.
- **External services / database:** reads `artifacts/`, and writes `model_versions`.
- **Depended on by:** `app/main.py`, the prediction and batch services, model routes and reports.

## D. Every Function Explained

### `version`, `threshold`, `metadata`
Read-only properties of `ServingModel`, giving access to the loaded model's values.

### `score`
- **Purpose:** return one uncalibrated score per row.
- **Parameters / types:** `inputs: pd.DataFrame` with the four prediction inputs. **Returns / type:** `np.ndarray` of `float64`.
- **Internal processing:** calls Phase 2's `predict_scores` under a lock, using the same feature code as training.
- **Error handling:** invalid inputs raise `ValueError` from `engineer_features`. Inputs are validated before reaching here.
- **Calls:** `LoadedModel.predict_scores`. **Used by:** `prediction_service`.

### `explain`
- **Purpose:** explain each row's score.
- **Parameters / types:** `inputs: pd.DataFrame`. **Returns / type:** `list[dict]`.
- **Internal processing:** transforms features as for scoring, then asks XGBoost for `pred_contribs`. That is XGBoost's own TreeSHAP calculation, so the `shap` library, a training-only dependency, is not needed in the API image.
- **Error handling:** as `score`.
- **Calls:** `_describe_contributions`. **Used by:** `prediction_service`.

### `_describe_contributions`
- **Purpose:** turn one row of raw contributions into a readable record.
- **Parameters / types:** `row: np.ndarray`, `names: list[str]`. **Returns / type:** `dict`.
- **Internal processing:** the last value is the base value. The rest are summed by `feature_group`, and sorted by size per feature.
- **Error handling:** `strict=True` catches a mismatch in lengths.
- **Calls:** `feature_group`. **Used by:** `explain`.

### `explanation_limitations`
- **Purpose:** provide Phase 2's list of what an explanation does not show.
- **Parameters / types:** none. **Returns / type:** `list[str]`.
- **Internal processing:** copies `LIMITATIONS`.
- **Error handling:** none needed.
- **Calls:** none. **Used by:** response building.

### `check_frozen_metadata`
- **Purpose:** compare the metadata with the pins in `frozen_model.py`.
- **Parameters / types:** `metadata: dict`. **Returns / type:** `None`.
- **Internal processing:** checks version, hash, threshold and frozen status, with exact equality on the threshold.
- **Error handling:** raises `ModelArtifactError`.
- **Calls:** none. **Used by:** `load_verified_model`.

### `check_library_versions`
- **Purpose:** ensure `scikit-learn` and `xgboost` match what saved the model.
- **Parameters / types:** `metadata: dict`. **Returns / type:** `None`.
- **Internal processing:** compares installed versions with those recorded.
- **Error handling:** raises `ModelArtifactError`.
- **Calls:** `importlib.metadata.version`. **Used by:** `load_verified_model`.

### `check_preprocessing_metadata`
- **Purpose:** verify the preprocessing record by hash.
- **Parameters / types:** `metadata: dict`, `path: Path`. **Returns / type:** `dict`.
- **Internal processing:** compares the SHA-256 with the value in the model metadata.
- **Error handling:** raises `ModelArtifactError` if missing or different.
- **Calls:** `sha256_file`. **Used by:** `load_verified_model`.

### `read_metrics`
- **Purpose:** load the saved evaluation results.
- **Parameters / types:** `metadata: dict`, `path: Path`. **Returns / type:** `dict`.
- **Internal processing:** confirms they describe this model and threshold, so wrong figures cannot be served for this model.
- **Error handling:** raises `ModelArtifactError`.
- **Calls:** none. **Used by:** `load_verified_model`.

### `read_report`
- **Purpose:** load the performance report.
- **Parameters / types:** `metadata: dict`, `path: Path`. **Returns / type:** `dict`.
- **Internal processing:** checks the hash against `MODEL_REPORT_SHA256`, then that the report names this model and threshold.
- **Error handling:** raises `ModelArtifactError`.
- **Calls:** `sha256_file`. **Used by:** `load_verified_model`.

### `load_verified_model`
- **Purpose:** the single entry point for getting a model.
- **Parameters / types:** `settings: Settings`. **Returns / type:** `ServingModel`.
- **Internal processing:** runs the checks above, then `load_model_artifact`, which verifies the file hash and only then opens the file.
- **Error handling:** any `ModelArtifactError` stops start-up.
- **Calls:** the checks above. **Used by:** `app/main.py`.

### `register_active_model`
- **Purpose:** keep `model_versions` in step with what is being served.
- **Parameters / types:** `session: Session`, `model: ServingModel`. **Returns / type:** `None`.
- **Internal processing:** deactivates other rows, inserts or updates this one, and commits.
- **Error handling:** database errors propagate and stop start-up.
- **Calls:** `session`. **Used by:** `app/main.py`.

## E. Classes Explained

### `ServingModel`
- **Purpose:** the verified model plus its saved results.
- **Attributes:** `loaded`, `metrics`, `preprocessing`, `report`, `_lock`.
- **Methods:** `score`, `explain` and the properties above.
- **Inheritance:** none; a dataclass.

## F. Execution Flow
At start-up: metadata pins, library versions, preprocessing hash, metrics, model file hash, then load. During requests: `score` and `explain`.

## G. Input and Output
Input: files under `artifacts/`, and DataFrames of the four inputs. Output: scores and explanations.

## H. Important Technical Concepts
- **Order matters:** `joblib.load` can run code, so nothing is opened until the hash has passed.
- **Two hash layers:** the file must match the metadata, and the metadata must match the pin in code. Replacing both the model and its metadata is still refused.
- **Lock:** predictions are short, about 2 ms a row, so serialising them costs little and removes any doubt about concurrent use of the booster.
- **Log-odds scale:** contributions add up to the score only on the log-odds scale. `test_model_service.py` checks this.
- **Explanations are not causes:** PRD 5.7. The limitations are returned with every explanation.
- **Hour dependence:** Phase 2 found the model relies heavily on hour, largely as a proxy for sparse steps, and that sparse-step recall fell from 95.6% on validation to 56.1% on test.

## I. Example
```python
model = load_verified_model(get_settings())
model.score(inputs)[0] >= model.threshold
```

## J. Maintenance Notes
A new model needs a new version, new pins and a new evaluation. If a family other than XGBoost is ever selected, `explain` must change, because `pred_contribs` is XGBoost-specific.

## K. Related Files
- [frozen_model.py](../core/frozen_model.py.explanation.md): the pins.
- [model_artifacts.py](../../../docs/file-explanations/backend/app/ml/model_artifacts.py.explanation.md): the file hash check and load.
- [risk.py](risk.py.explanation.md): turns scores into decisions.
- [test_model_service.py](../../tests/unit/test_model_service.py.explanation.md): tests.
