# models.py (schemas)

Source: [backend/app/api/schemas/models.py](models.py)

## A. File Purpose
Defines the responses for model versions, metrics and feature importance.

## B. Why This File Exists
PRD 8.2 requires schemas, and PRD 5.4 forbids presenting accuracy alone. Typed fields here guarantee every required metric is present in the response.

## C. Dependencies
- **Libraries:** `pydantic`.
- **Internal modules:** `app.api.schemas.common`, `app.core.frozen_model`.
- **External services / database:** none.
- **Depended on by:** the models route.

## D. Every Function Explained
No functions.

## E. Classes Explained

### `ModelVersionView`
A registered model and its hash, without metrics. **Inheritance:** `ApiModel`.

### `ThresholdMetrics`
Precision, recall, F1, balanced accuracy, false positive and negative rates, and the confusion matrix. `extra="allow"` keeps saved fields such as `alerts_per_step`. **Inheritance:** `BaseModel`.

### `RankingMetrics`
PR-AUC, ROC-AUC, Brier score, lift, prevalence and row counts. **Inheritance:** `BaseModel`.

### `RegimeResults`, `ValidationResults`, `TestResults`
Group these two for each part of the data. `__test__ = False` tells pytest that `TestResults` is not a test class. **Inheritance:** `BaseModel`.

### `ThresholdInfo`
The threshold, its objective, where it was chosen and the target. **Inheritance:** `BaseModel`.

### `ModelMetricsView`
The whole response, including `performance_notes` and the score's uncalibrated labelling. **Inheritance:** `BaseModel`.

### `ModelReportView`
The saved report for the Model Performance page: model version, threshold, source hashes, notes, selection, family comparison, curves, confusion matrices, thresholds, imbalance matrix, experiment history and the LightGBM diagnostic. `extra="allow"` keeps every saved field. **Inheritance:** `BaseModel`.

### `FeatureImportanceView`
Saved SHAP importance and its limitations. **Inheritance:** `BaseModel`.

## F. Execution Flow
The route builds these from the saved metrics, and pydantic checks them.

## G. Input and Output
See `API_DOCUMENTATION.md`.

## H. Important Technical Concepts
- **`extra="allow"` means no saved field is dropped,** which fits the requirement to preserve results.

## I. Example
```python
ModelMetricsView(**model.metrics, source="...", performance_notes=[...])
```

## J. Maintenance Notes
If `export_metrics.py` changes the bundle, update these together.

## K. Related Files
- [metrics_service.py](../../services/metrics_service.py.explanation.md): the notes.
- [models.py route](../routes/models.py.explanation.md): the routes.
