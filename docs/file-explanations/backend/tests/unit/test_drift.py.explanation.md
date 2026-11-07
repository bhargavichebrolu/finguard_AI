# test_drift.py

Source: [backend/tests/unit/test_drift.py](../../../../../backend/tests/unit/test_drift.py)

## A. File Purpose
Tests the temporal drift calculations against hand calculations.

## B. Why This File Exists
The drift report drives how test results are interpreted. An error here could turn a model failure into an apparent base-rate effect, or the reverse.

## C. Dependencies
- **Libraries:** `numpy`, `pytest`.
- **Internal modules:** `app.ml.drift`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `eda_summary`
- **Purpose:** build a four-step EDA report.
- **Parameters / types:** none. **Returns / type:** `dict`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** nothing. **Used by:** `table`, tests.

### `table`
- **Purpose:** build the step table from that report.
- **Parameters / types:** none. **Returns / type:** `pd.DataFrame`.
- **Internal processing / errors:** calls the code under test; no special handling.
- **Calls:** `step_table_from_eda`. **Used by:** tests.

### `window`
A helper nested in one test. It builds a window with fixed regime rates and a chosen sparse share.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError`. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_step_table_assigns_partitions_from_boundaries` | none | Partition labels follow boundaries. |
| `test_partition_summary_by_hand` | none | Counts, rates and shares are correct. |
| `test_decomposition_effects_add_up_exactly` | none | The two effects sum to the total. |
| `test_decomposition_attributes_a_pure_mix_change_to_mix` | none | A pure mix change gives no rate effect. |
| `test_prevalence_at_reference_volume_by_hand` | none | The counterfactual formula. |
| `test_psi_of_identical_data_is_zero` | none | No drift gives zero. |
| `test_psi_detects_a_shift` | none | Small for the same distribution, large for a moved one. |
| `test_categorical_psi_by_hand` | none | The formula. |
| `test_absent_category_does_not_give_infinity` | none | The floor works. |
| `test_regime_by_hour_reports_sparse_share` | none | Share per hour, with `None` for an absent hour. |
| `test_feature_drift_reports_all_rows_and_each_class` | `model_partition`, `later_partition` | All sections exist. |
| `test_report_states_the_definition_uses_no_labels` | none | The report documents its definition. |

## E. Classes Explained
None.

## F. Execution Flow
All tests run in memory on small constructed tables.

## G. Input and Output
Input: a four-step report and synthetic partitions. Output: pass or fail.

## H. Important Technical Concepts
The pure mix case is the key check: when within-regime rates do not change, the whole prevalence change must be attributed to regime mix.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_drift.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Re-derive any expected value by hand before changing it.

## K. Related Files
- [drift.py](../../app/ml/drift.py.explanation.md): code under test.
