# test_model_service.py

Source: [backend/tests/unit/test_model_service.py](test_model_service.py)

## A. File Purpose
Tests that the frozen model is verified before loading, that altered artefacts are refused, that scores and explanations behave correctly, and that risk bands cannot change who is flagged.

## B. Why This File Exists
The authorisation's model conditions are only meaningful if a violation fails. Most tests here tamper with a copy of the artefacts and require a refusal.

## C. Dependencies
- **Libraries:** `pytest`, `numpy`, `pandas`, optionally `shap`.
- **Internal modules:** `app.services.model_service`, `app.services.risk`, `app.core`, `app.ml`.
- **External services / database:** the frozen model file. Tests needing it skip if it is absent. No database. No test partition data is used; the inputs are hand-written.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `settings_for`
Builds settings pointing at a chosen artefact folder. Parameters: `metadata_dir`, `models_dir`. Returns `Settings`. **Used by:** the fixtures and tamper tests.

### `model`
Module fixture that loads the real frozen model once. Skips if the file is absent.

### `artifact_copy`
Fixture that copies the artefacts to a temporary folder, so tampering never touches the originals. Returns the two folders.

### `sample_inputs`
Returns four hand-written rows, one for each of several transaction types. Takes nothing.

### `edit_metadata`
Changes one JSON file in a copy. Parameters: `metadata_dir`, `name`, `change`. Returns `None`.

### `must_not_load`
Nested stand-in for `joblib.load`, which fails the test if the file is ever opened.

**Common to every test below:** failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them.

| Function | Proves |
|---|---|
| `test_frozen_files_on_disk_match_the_pins` | The real files match the code's pins. |
| `test_model_loads_and_reports_the_frozen_version` | The model loads with the frozen version and threshold. |
| `test_altered_model_file_is_refused_before_loading` | A changed file is refused, and `joblib.load` is never called on it. |
| `test_replacing_model_and_metadata_together_is_refused` | Updating the metadata hash to match a new file does not help. |
| `test_changed_threshold_is_refused` | A threshold edit stops loading. |
| `test_changed_preprocessing_record_is_refused` | The preprocessing hash is enforced. |
| `test_metrics_for_another_threshold_are_refused` | Results for another threshold cannot be served. |
| `test_missing_model_file_is_refused` | A missing file stops loading. |
| `test_different_library_version_is_refused` | Other library versions are refused. |
| `test_metadata_disagreeing_with_the_pins_is_refused` | Each pinned field is enforced on its own. |
| `test_scores_are_between_zero_and_one` | Output range. |
| `test_score_matches_the_phase_2_classify_method` | The serving path agrees with Phase 2's `classify`. |
| `test_scoring_one_row_gives_the_same_result_as_in_a_batch` | Single and batch predictions are identical. |
| `test_label_and_balance_columns_do_not_change_scores` | Leaky columns have no influence. |
| `test_concurrent_scoring_is_consistent` | Parallel requests get the same results. |
| `test_explanation_adds_up_to_the_score` | Base value plus contributions reproduces the score. |
| `test_explanation_matches_the_shap_library` | XGBoost's calculation agrees with the `shap` library used in Phase 2. |
| `test_explanation_groups_cover_every_feature` | All groups and all 12 model inputs are present. |
| `test_risk_bands_at_their_edges` | Each band's boundaries. |
| `test_the_frozen_threshold_itself_is_flagged` | A score exactly at the threshold is flagged, and the next float below is not. |
| `test_moving_the_high_boundary_never_changes_who_is_flagged` | Decisions are unaffected by the boundary. |
| `test_a_boundary_at_or_below_the_threshold_is_refused` | An impossible boundary is refused. |

## E. Classes Explained
None.

## F. Execution Flow
The `model` fixture loads once for the module. Tamper tests each copy the artefacts first.

## G. Input and Output
Input: frozen artefacts, read-only, and literal rows. Output: pass or fail.

## H. Important Technical Concepts
- **Tampering happens on a copy,** so the frozen files cannot be damaged by a test.
- **`np.nextafter`** gives the closest float below a value, the sharpest test of `>=`.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_model_service.py
```

## J. Maintenance Notes
These tests encode the frozen values. They should change only with a deliberate new model release.

## K. Related Files
- [model_service.py](../../app/services/model_service.py.explanation.md): loading and scoring.
- [risk.py](../../app/services/risk.py.explanation.md): bands.
