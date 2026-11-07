# test_model_artifacts.py

Source: [backend/tests/unit/test_model_artifacts.py](../../../../../backend/tests/unit/test_model_artifacts.py)

## A. File Purpose
Tests saving and independently loading a model, and refusing one that is altered or incompatible.

## B. Why This File Exists
A Phase 2 acceptance criterion is that artefacts can be loaded independently. PRD 14.1 requires tests of model loading, prediction output, probability range and threshold behaviour.

## C. Dependencies
- **Libraries:** `json`, `subprocess`, `sys`, `textwrap`, `pathlib`, `numpy`, `pandas`, `pytest`.
- **Internal modules:** `app.ml.candidates`, `app.ml.experiments`, `app.ml.model_artifacts`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `inputs_frame`
- **Purpose:** build two rows of the four prediction inputs.
- **Parameters / types:** none. **Returns / type:** `pd.DataFrame`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** pandas. **Used by:** tests.

### `saved_model`
- **Purpose:** a fixture that fits and saves a small model.
- **Parameters / types:** `tmp_path`, `model_partition`. **Returns / type:** `(pipeline, metadata_path, models_dir)`.
- **Internal processing / errors:** calls the save function; no special handling.
- **Calls:** `fit_candidate`, `save_model_artifact`. **Used by:** every test.

### `rewrite_metadata`
- **Purpose:** alter the saved metadata, to simulate an incompatible model.
- **Parameters / types:** `path: Path`; keyword changes. **Returns / type:** `None`.
- **Internal processing / errors:** reads, updates and writes JSON; no special handling.
- **Calls:** `json`. **Used by:** mismatch tests.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_saved_file_is_versioned_and_hashed` | `saved_model` | PRD 5.8 versioned storage. |
| `test_loaded_model_scores_like_the_fitted_one` | `saved_model`, `model_partition` | Saving changes nothing. |
| `test_scores_are_probabilities_in_range` | `saved_model` | PRD 14.1 output and range. |
| `test_classify_uses_the_frozen_threshold` | `saved_model` | PRD 14.1 threshold behaviour. |
| `test_extra_columns_such_as_labels_are_ignored` | `saved_model` | A label or balance column cannot affect a prediction. |
| `test_altered_model_file_is_refused` | `saved_model` | A one-byte change is detected. |
| `test_schema_version_mismatch_is_refused` | `saved_model` | Incompatible schema is refused. |
| `test_feature_column_mismatch_is_refused` | `saved_model` | Incompatible columns are refused. |
| `test_missing_files_are_refused` | `saved_model`, `tmp_path` | Missing files give a clear error. |
| `test_model_loads_in_a_new_process_without_experiment_code` | `saved_model` | Independent loading, without the training-only modules. |

## E. Classes Explained
None.

## F. Execution Flow
Each test uses a freshly saved model in a temporary folder. The last test starts a new Python process.

## G. Input and Output
Input: synthetic rows. Output: pass or fail.

## H. Important Technical Concepts
The new-process test proves independence directly: it imports only `model_artifacts`, and checks that `imblearn`, `shap` and the experiment modules were never imported.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_model_artifacts.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If the last test starts failing because of a new import, fix the import in `model_artifacts.py`. Don't relax the test: the API image will not contain training libraries.

## K. Related Files
- [model_artifacts.py](../../app/ml/model_artifacts.py.explanation.md): code under test.
