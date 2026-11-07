# model_artifacts.py

Source: [backend/app/ml/model_artifacts.py](../../../../../backend/app/ml/model_artifacts.py)

## A. File Purpose
Saves the selected model with its metadata, and loads it again after verifying it.

## B. Why This File Exists
PRD 5.8 requires a versioned model, preprocessing pipeline, feature schema, metadata and threshold. The Phase 2 acceptance criteria require that artefacts can be loaded independently. This module imports no experiment code, so the Phase 3 API can use it directly.

## C. Dependencies
- **Libraries:** `joblib`, `numpy`, `pandas`, `scikit-learn`, plus the library of the saved model.
- **Internal modules:** `app.ml.features`, `app.ml.pipeline_io`, `app.ml.preprocessing`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `selection.py`, `final_evaluation.py`, `scripts/explain_model.py`, `scripts/evaluate_final_test.py`, and the API from Phase 3.

## D. Every Function Explained

### `save_model_artifact`
- **Purpose:** write the model and metadata.
- **Parameters / types:** `pipeline: Pipeline`; `metadata: dict`; `models_dir: Path`; `metadata_path: Path`.
- **Returns / type:** `dict`, the complete metadata.
- **Internal processing:** saves `<models_dir>/<version>/model.joblib`, hashes it, and adds the path, hash and size to the metadata.
- **Error handling:** `KeyError` if `model_version` is missing. Write errors propagate.
- **Calls:** `joblib.dump`, `sha256_file`, `write_json`.
- **Used by:** `selection.freeze_selected_model`.

### `load_model_artifact`
- **Purpose:** load a verified model.
- **Parameters / types:** `metadata_path: Path`; `models_dir: Path`.
- **Returns / type:** `LoadedModel`.
- **Internal processing:** checks the schema version, feature columns and file hash before opening the file.
- **Error handling:** raises `ModelArtifactError` for each failed check, without opening the file.
- **Calls:** `_read_metadata`, `sha256_file`, `joblib.load`.
- **Used by:** `final_evaluation`, `scripts/explain_model.py`, tests, and the API from Phase 3.

### `_read_metadata`
- **Purpose:** read the metadata JSON.
- **Parameters / types:** `path: Path`.
- **Returns / type:** `dict`.
- **Internal processing:** `json.loads`.
- **Error handling:** a JSON error propagates.
- **Calls:** `json`.
- **Used by:** `load_model_artifact`.

## E. Classes Explained

### `ModelArtifactError`
Raised when a model is missing, altered or incompatible.

### `LoadedModel`
- **Purpose:** the object the API will hold.
- **Attributes:** `pipeline`, `threshold`, `metadata`.
- **`predict_scores`:** takes the four prediction inputs, applies `engineer_features` and `compact_features`, and returns scores.
- **`classify`:** compares scores with the frozen threshold, where a score equal to the threshold counts as an alert.

## F. Execution Flow
Save: dump, hash, write metadata. Load: read metadata, check schema, check hash, open the file.

## G. Input and Output
Files: `artifacts/models/<version>/model.joblib`, Git-ignored, and `artifacts/metadata/model_v1.json`, committed.

## H. Important Technical Concepts
**Why verify before loading:** joblib files are pickles, which can execute code when opened. The hash check ensures that the file is the one recorded in the committed metadata. Only load model files from a trusted source.

**Everything in one pipeline:** the saved `Pipeline` includes preprocessing, so the encoding and any scaling cannot be separated from the model.

**Score is not automatically a probability:** a class-weighted or oversampled model gives inflated scores. `metadata["score_semantics"]` records this, so the API and interface can describe it correctly.

## I. Example
```python
model = load_model_artifact(MODEL_METADATA_PATH, MODELS_DIR)
inputs = pd.DataFrame([{"amount": 950000.0, "transaction_type": "TRANSFER",
                        "step": 400, "destination_category": "customer"}])
print(model.predict_scores(inputs), model.classify(inputs))
```

## J. Maintenance Notes
Do not import `experiments.py`, `imbalance.py` or `candidates.py` here: the API image will not have the training libraries. A new model version goes in a new directory, with new metadata.

## K. Related Files
- [selection.py](selection.py.explanation.md): saves the model.
- [preprocessing.py](preprocessing.py.explanation.md): must stay importable for loading.
- [test_model_artifacts.py](../../tests/unit/test_model_artifacts.py.explanation.md): tests loading and refusal.
