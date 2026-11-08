# models.py (routes)

Source: [backend/app/api/routes/models.py](models.py)

## A. File Purpose
Exposes the registered models, the active model, its saved evaluation and its saved feature importance.

## B. Why This File Exists
These are the PRD 8.2 model endpoints. PRD 6.8 requires every displayed metric to come from saved experiment outputs.

## C. Dependencies
- **Libraries:** `fastapi`, `sqlalchemy`.
- **Internal modules:** `app.api.schemas.models`, `app.core.errors`, `app.models.records`, `app.security`, `app.services.metrics_service`.
- **External services / database:** `model_versions`, and the metrics loaded at start-up.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `list_models`
`GET /api/v1/models`. Returns all registered versions.

### `read_active`
`GET /api/v1/models/active`. Returns the active version, or 404.

### `read_metrics`
`GET /api/v1/models/metrics`. Returns validation and test results, the threshold, and `performance_notes`.

### `read_report`
`GET /api/v1/models/report`. Returns the report verified at start-up, unchanged.

### `read_feature_importance`
`GET /api/v1/models/feature-importance`. Returns saved SHAP importance with limitations.

All four need `VIEW_MODELS`.

## E. Classes Explained
None.

## F. Execution Flow
Permission check, then read saved values.

## G. Input and Output
`read_metrics` returns, for example, `test.at_frozen_threshold.false_positive_rate: 0.00282`, and a note stating the target was not met.

## H. Important Technical Concepts
- **No computation.** Nothing is recalculated, so no route can alter or re-derive a Phase 2 result.
- **PRD 6.8 data:** the comparison table, curves and experiment history are served by `read_report`, from a file built only from saved Phase 2 outputs.

## I. Example
```powershell
curl.exe -H "Authorization: Bearer <token>" http://127.0.0.1:8010/api/v1/models/metrics
```

## J. Maintenance Notes
Keep these read-only.

## K. Related Files
- [metrics_service.py](../../services/metrics_service.py.explanation.md): the notes.
- [model_service.py](../../services/model_service.py.explanation.md): loads the saved metrics.
- [test_models_and_reports.py](../../../tests/api/test_models_and_reports.py.explanation.md): tests.
