# metrics_service.py

Source: [backend/app/services/metrics_service.py](metrics_service.py)

## A. File Purpose
Turns the saved Phase 2 metrics into plain statements, importance figures and report rows.

## B. Why This File Exists
The authorisation requires preserving the actual metrics, and documenting the test FPR of 0.282% against the 0.1% target, recall of 45.9%, and normal-step recall of 21.9%. PRD 6.8 requires all displayed metrics to come from saved outputs. Building the statements from those saved values means they cannot disagree with them.

## C. Dependencies
- **Libraries:** none beyond typing.
- **Internal modules:** none.
- **External services / database:** none. It receives the contents of `artifacts/metadata/model_v1_metrics.json`.
- **Depended on by:** the models route and `report_service.py`.

## D. Every Function Explained

### `performance_notes`
- **Purpose:** state what the saved results show, including where they fall short.
- **Parameters / types:** `metrics: dict`. **Returns / type:** `list[str]`.
- **Internal processing:** formats saved values into sentences.
- **Error handling:** a missing key raises `KeyError`, since a malformed file should not be served quietly.
- **Calls:** none. **Used by:** the models route, reports.

### `feature_importance`
- **Purpose:** return saved SHAP importance with its limitations.
- **Parameters / types:** `metrics: dict`. **Returns / type:** `dict`.
- **Internal processing:** selects saved fields.
- **Error handling:** as above. **Calls:** none. **Used by:** the models route.

### `evaluation_rows`
- **Purpose:** flatten results for a CSV report.
- **Parameters / types:** `metrics: dict`. **Returns / type:** `list[tuple]`.
- **Internal processing:** walks validation, test and the two step types, then adds the target as its own row.
- **Error handling:** as above. **Calls:** none. **Used by:** `report_service`.

## E. Classes Explained
None.

## F. Execution Flow
A route passes `model.metrics`, loaded and checked at start-up.

## G. Input and Output
Output example: "The false positive rate on the test partition was 0.282%, which is 2.8 times the 0.1% target set on validation. The target was not met on test."

## H. Important Technical Concepts
- **The test set is not touched.** The file holds results recorded during the single Phase 2 evaluation. This module reads only that file.
- **Test performance is not improvement.** Test's higher precision and PR-AUC partly reflect a higher fraud rate. See `ML_EXPERIMENTS.md`.

## I. Example
```python
performance_notes(model.metrics)[0]
```

## J. Maintenance Notes
Do not type figures into the sentences. `test_models_and_reports.py` compares the output with the saved file and with the required values.

## K. Related Files
- [models.py route](../api/routes/models.py.explanation.md): serves these.
- [ML_EXPERIMENTS.md](../../../ML_EXPERIMENTS.md): the full results.
