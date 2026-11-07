# explain_model.py

Source: [scripts/explain_model.py](../../../scripts/explain_model.py)

## A. File Purpose
Produces SHAP explanations of the frozen model, on validation rows.

## B. Why This File Exists
PRD 5.7 and the Phase 2 deliverables require SHAP explanations. Using validation rows means this step does not touch the test partition.

## C. Dependencies
- **Libraries:** `argparse`, `pathlib`, `numpy`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.experiments`, `app.ml.explainability`, `app.ml.model_artifacts`, `app.ml.pipeline_io`.
- **External services / database:** none.
- **Depended on by:** the `explain` target in the `Makefile`. `export_metrics.py` reads its outputs.

## D. Every Function Explained

### `main`
- **Purpose:** run the explanation and save it.
- **Parameters / types:** none directly; reads `--config`, `--processed-dir`, `--models-dir`, `--metadata` and `--results-dir`.
- **Returns / type:** `None`.
- **Internal processing:** loads the verified model through `load_model_artifact`, scores validation, explains the sampled rows, and writes a report and a small array file for charts.
- **Error handling:** `ModelArtifactError` if the model fails verification. `ValueError` for a family with no explainer.
- **Calls:** `load_experiment_config`, `load_model_artifact`, `load_development_data`, `score_rows`, `explain_validation_rows`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Load the model and rows, score, explain, save, print a summary.

## G. Input and Output
Input: the frozen model and validation rows. Output: `shap_summary.json` and `shap_sample.npz` in `experiments/results/phase2/`.

## H. Important Technical Concepts
The array file holds SHAP values for all sampled rows, so charts can be redrawn without recalculating them. It contains simulated data only.

## I. Example
```powershell
uv run --project backend python scripts/explain_model.py
```

## J. Maintenance Notes
Check the printed additivity error after any upgrade of SHAP or the model library. It should be close to zero.

## K. Related Files
- [explainability.py](../backend/app/ml/explainability.py.explanation.md): the logic.
- [export_metrics.py](export_metrics.py.explanation.md): charts and tables from the output.
