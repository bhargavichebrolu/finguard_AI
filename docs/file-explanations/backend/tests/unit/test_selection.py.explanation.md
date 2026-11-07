# test_selection.py

Source: [backend/tests/unit/test_selection.py](../../../../../backend/tests/unit/test_selection.py)

## A. File Purpose
Tests the selection rule and threshold analysis, using constructed candidates with known answers.

## B. Why This File Exists
The rule was fixed before any result existed. Testing it with constructed inputs shows that it does what the decision record says, independent of the real results.

## C. Dependencies
- **Libraries:** `numpy`, `pytest`.
- **Internal modules:** `app.ml.experiment_stages`, `app.ml.pipeline_io`, `app.ml.selection`, `tests.conftest`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `candidate`
- **Purpose:** build a candidate summary.
- **Parameters / types:** `family`, `pr_auc`, `recall`, `single_row_ms`, `cv`, `folds`. **Returns / type:** `dict`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** nothing. **Used by:** the rule tests.

### `tied`
- **Purpose:** a paired comparison that cannot separate two models.
- **Parameters / types:** ignored. **Returns / type:** `dict`.
- **Internal processing / errors:** constant; no special handling.
- **Calls:** nothing. **Used by:** the rule tests.

### `_run`
- **Purpose:** build a saved run record.
- **Parameters / types:** `family`, `pr_auc`, `stage`, `status`, `hyperparameters`, `seed`. **Returns / type:** `dict`.
- **Internal processing / errors:** direct construction; no special handling.
- **Calls:** nothing. **Used by:** the `best_run` and summary tests.

### `_threshold_data`
- **Purpose:** build labels, scores and steps.
- **Parameters / types:** none. **Returns / type:** `(labels, scores, steps)`.
- **Internal processing / errors:** seeded random data; no special handling.
- **Calls:** numpy. **Used by:** the threshold tests.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_gate_rejects_a_model_no_better_than_the_type_baseline` | none | Minimum skill gate. |
| `test_gate_rejects_high_seed_variation` | none | Stability gate. |
| `test_gate_rejects_a_failed_seed_run` | none | A failed seed is not ignored. |
| `test_gate_rejects_losing_to_the_baseline_in_any_fold` | none | Temporal gate, naming the fold. |
| `test_gate_rejects_a_failed_fold` | none | A failed fold is not ignored. |
| `test_gate_passes_a_good_candidate` | none | The gates can pass. |
| `test_clear_pr_auc_winner_is_chosen_even_if_slower` | none | Speed never overrides a real difference. |
| `test_statistical_tie_goes_to_higher_recall` | none | Step 2. |
| `test_recall_tie_within_the_margin_goes_to_the_faster_model` | none | Step 3. |
| `test_recall_outside_the_margin_is_not_a_tie` | none | The margin's edge. |
| `test_empty_candidate_list_is_rejected` | none | Invalid input raises. |
| `test_best_run_ignores_stability_sensitivity_and_failed_runs` | none | Only planned search stages can win. |
| `test_best_run_is_none_when_nothing_succeeded` | none | Missing results are visible. |
| `test_summary_uses_all_seeds_of_the_same_settings_only` | none | Seed variation is measured correctly. |
| `test_summary_finds_rolling_folds_by_run_id` | none | A missing fold is `None`. |
| `test_threshold_analysis_selects_by_the_fixed_objective` | none | The objective holds, and all sections exist. |
| `test_sweep_shows_recall_falling_as_the_threshold_rises` | none | PRD 14.1 threshold behaviour. |
| `test_reliability_table_covers_every_row` | none | No row is lost in binning. |
| `test_score_semantics_warns_that_inflated_scores_are_not_probabilities` | none | The wording stays honest. |
| `test_real_config_loads_and_records_the_pre_registered_objective` | none | The committed config matches the recorded rule. |

## E. Classes Explained
None.

## F. Execution Flow
All tests run in memory, except the last, which reads the committed config.

## G. Input and Output
Input: constructed dictionaries and arrays. Output: pass or fail.

## H. Important Technical Concepts
The final test ties the committed numbers to the decision record, so changing the rule after results exist means changing a test as well, which is visible in review.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_selection.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Do not adjust these tests to suit a particular outcome. The rule is meant to be independent of results.

## K. Related Files
- [selection.py](../../app/ml/selection.py.explanation.md): code under test.
- [0002-phase-2-decisions.md](../../../../decisions/0002-phase-2-decisions.md): the rule.
