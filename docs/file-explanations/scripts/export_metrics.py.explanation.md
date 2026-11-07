# export_metrics.py

Source: [scripts/export_metrics.py](../../../scripts/export_metrics.py)

## A. File Purpose
Builds charts, tables and a metrics bundle from saved results. It fits and scores nothing.

## B. Why This File Exists
PRD 13 names this script. Generating tables from saved files keeps `ML_EXPERIMENTS.md` traceable to executed runs, instead of depending on figures copied by hand.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `pathlib`, `typing`.
- **Internal modules:** `app.ml.pipeline_io`, `app.ml.reporting`.
- **External services / database:** none.
- **Depended on by:** the `export` target in the `Makefile`, and the Phase 3 API, which will read the bundle.

## D. Every Function Explained

### `_load`
- **Purpose:** read a results file if it exists.
- **Parameters / types:** `path: Path`.
- **Returns / type:** `dict | None`.
- **Internal processing:** `json.loads`.
- **Error handling:** an absent file gives `None`, so earlier stages can be exported alone.
- **Calls:** `json`.
- **Used by:** `main`.

### `build_metrics_bundle`
- **Purpose:** collect what the Phase 3 API will serve about the model.
- **Parameters / types:** `metadata`, `thresholds`: dicts; `shap_report`, `test`: dicts or `None`.
- **Returns / type:** `dict`.
- **Internal processing:** copies validation results, importance and limitations, and adds test results in their own section once they exist.
- **Error handling:** `KeyError` if a report has the wrong shape.
- **Calls:** nothing.
- **Used by:** `main`.

### `main`
- **Purpose:** regenerate all reporting outputs.
- **Parameters / types:** none directly; reads `--results-dir`, `--figures-dir`, `--metadata`, `--metrics` and `--document`.
- **Returns / type:** `None`.
- **Internal processing:** loads whatever exists, draws charts, renders tables, injects them into the document's generated block, writes the bundle, and names what is not yet available.
- **Error handling:** a document without the generated block raises `ValueError`.
- **Calls:** the functions in `reporting.py`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Load, draw, render, inject, bundle, print.

## G. Input and Output
Input: `experiments/results/phase2/*`, `artifacts/metadata/model_v1.json`. Output: `experiments/figures/models/*.png`, `all_runs.csv`, `results_tables.md`, the generated block in `ML_EXPERIMENTS.md`, and `artifacts/metadata/model_v1_metrics.json`.

## H. Important Technical Concepts
Validation and test results stay in separate sections of the bundle, so a later consumer cannot mistake one for the other. Running this after the test evaluation cannot affect the model: it only reads results.

## I. Example
```powershell
uv run --project backend python scripts/export_metrics.py
```

## J. Maintenance Notes
Do not edit text inside the generated block of `ML_EXPERIMENTS.md`, as it gets overwritten. Written interpretation goes outside the block.

## K. Related Files
- [reporting.py](../backend/app/ml/reporting.py.explanation.md): charts and tables.
- [test_reporting.py](../backend/tests/unit/test_reporting.py.explanation.md): tests.
