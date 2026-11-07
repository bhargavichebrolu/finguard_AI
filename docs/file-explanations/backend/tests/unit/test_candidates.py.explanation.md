# test_candidates.py

Source: [backend/tests/unit/test_candidates.py](../../../../../backend/tests/unit/test_candidates.py)

## A. File Purpose
Tests the six model families and the experiment description.

## B. Why This File Exists
Each library has its own parameter names, so a mistake could silently leave class weighting off. A spec's identity also decides whether old results get reused.

## C. Dependencies
- **Libraries:** `numpy`, `pytest`, and all six model libraries through the code under test.
- **Internal modules:** `app.ml.candidates`, `tests.conftest`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `spec_for`
- **Purpose:** build a spec with small settings.
- **Parameters / types:** `family: str`; `strategy: str`; keyword overrides. **Returns / type:** `CandidateSpec`.
- **Internal processing / errors:** merges defaults with overrides; invalid fields raise.
- **Calls:** `CandidateSpec`. **Used by:** tests in this file.

### `has_scaler`
- **Purpose:** check whether a family's pipeline scales numeric columns.
- **Parameters / types:** `family: str`. **Returns / type:** `bool`.
- **Internal processing / errors:** nested in one test; reads the column transformer.
- **Calls:** `build_pipeline`. **Used by:** `test_only_logistic_regression_scales_numeric_features`.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_every_family_fits_and_gives_probabilities` | `family`, `model_partition` | PRD 14.1 output and range checks for all six. |
| `test_pipeline_contains_no_sampler` | `family` | A sampler cannot run at prediction. |
| `test_inference_threads_can_be_set_after_fitting` | `family`, `model_partition` | Single-row timing works for every library, including CatBoost. |
| `test_only_logistic_regression_scales_numeric_features` | `model_partition` | Scaling is applied where it matters. |
| `test_booster_weight_applies_only_when_class_weighted` | `family`, `parameter`, `expected` | The class weight reaches XGBoost and LightGBM. |
| `test_sklearn_weight_applies_only_when_class_weighted` | none | The class weight reaches sklearn models. |
| `test_run_id_changes_with_every_field` | none | Stale results can't be reused. |
| `test_run_id_ignores_key_order` | none | Equal settings give the same id. |
| `test_spec_rejects_unknown_family_and_strategy` | none | Typos fail immediately. |
| `test_oversampling_spec_requires_target_ratio` | `strategy` | Oversampling must state its ratio. |
| `test_non_oversampling_spec_rejects_target_ratio` | none | Other strategies must not. |
| `test_strategies_cover_the_four_in_the_prd` | none | PRD 5.2 coverage. |
| `test_build_estimator_rejects_unknown_family` | none | Invalid family raises. |

## E. Classes Explained
None.

## F. Execution Flow
Small models fit on the synthetic partition. These tests take a few seconds.

## G. Input and Output
Input: the synthetic partition. Output: pass or fail.

## H. Important Technical Concepts
Testing each library through one interface confirms that upgrades of any library still satisfy the project's assumptions.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_candidates.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
A new family needs an entry in `small_experiment_config` in `conftest.py`.

## K. Related Files
- [candidates.py](../../app/ml/candidates.py.explanation.md): code under test.
