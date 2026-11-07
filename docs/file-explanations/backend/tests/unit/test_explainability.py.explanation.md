# test_explainability.py

Source: [backend/tests/unit/test_explainability.py](../../../../../backend/tests/unit/test_explainability.py)

## A. File Purpose
Tests that SHAP values add up to the model's output for every family, and that summaries are calculated correctly.

## B. Why This File Exists
SHAP support differs across libraries and versions. Additivity is a check that fails if an explanation is wrong, so it can be tested without judging the explanation by eye.

## C. Dependencies
- **Libraries:** `numpy`, `pytest`, `shap` through the code under test.
- **Internal modules:** `app.ml.candidates`, `app.ml.experiments`, `app.ml.explainability`, `tests.conftest`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `fit_family`
- **Purpose:** fit a small model of a family.
- **Parameters / types:** `family: str`; `partition: PartitionData`. **Returns / type:** `Pipeline`.
- **Internal processing / errors:** direct call; no special handling.
- **Calls:** `fit_candidate`. **Used by:** tests.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_explanations_add_up_to_the_score` | `family`, `model_partition`, `later_partition` | All six families are supported and additive. |
| `test_unsupported_family_is_refused` | `model_partition` | No silent approximation. |
| `test_feature_groups` | `name`, `group` | Grouping of columns. |
| `test_sampling_keeps_all_fraud_and_restores_natural_weights` | none | Weights add back to the true row count. |
| `test_sampling_is_capped_at_the_available_rows` | none | A small input works. |
| `test_group_importance_adds_values_within_the_group` | none | Values are summed before taking the absolute. |
| `test_weights_are_applied_in_importance` | none | The weighted mean, by hand. |
| `test_empty_slice_is_reported_as_empty` | none | No crash on an empty slice. |
| `test_local_explanation_separates_and_orders_contributions` | none | PRD 5.7 positive and negative contributions. |
| `test_report_has_examples_limitations_and_a_causality_warning` | `model_partition`, `later_partition` | PRD 5.7 stated limitations. |

## E. Classes Explained
None.

## F. Execution Flow
Small models fit on the synthetic partition, then each test explains a few rows.

## G. Input and Output
Input: synthetic rows and small constructed arrays. Output: pass or fail.

## H. Important Technical Concepts
**Additivity** means base value plus all SHAP values equals the model's output. Summing within a group before taking absolute values matters, because `amount` and `amount_log1p` can push in opposite directions, and only their sum reflects the amount's effect.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_explainability.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
A failure after upgrading SHAP or a booster library usually means a change in output shape. Fix it in `explain_rows`.

## K. Related Files
- [explainability.py](../../app/ml/explainability.py.explanation.md): code under test.
