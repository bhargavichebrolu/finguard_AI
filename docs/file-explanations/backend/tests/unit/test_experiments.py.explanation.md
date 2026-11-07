# test_experiments.py

Source: [backend/tests/unit/test_experiments.py](../../../../../backend/tests/unit/test_experiments.py)

## A. File Purpose
Tests the guard on the test partition, oversampling containment, and how runs are stored and resumed.

## B. Why This File Exists
These are the rules the Phase 2 authorisation cares about most. Each one has a test that fails if the rule breaks.

## C. Dependencies
- **Libraries:** `ast`, `pathlib`, `numpy`, `pytest`.
- **Internal modules:** `app.ml.candidates`, `app.ml.evaluation`, `app.ml.experiments`, `app.ml.imbalance`, `tests.conftest`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `spec_for`
- **Purpose:** build a small LightGBM spec.
- **Parameters / types:** `strategy: str`; `target_ratio: float | None`; `seed: int`. **Returns / type:** `CandidateSpec`.
- **Internal processing / errors:** direct construction; invalid fields raise.
- **Calls:** `CandidateSpec`. **Used by:** tests in this file.

### `_partition_names_read_in`
- **Purpose:** find string literals naming the test partition in a source file.
- **Parameters / types:** `path: Path`. **Returns / type:** `set[str]`.
- **Internal processing / errors:** walks the syntax tree, so comments and docstring wording do not count.
- **Calls:** `ast`. **Used by:** `test_selection_code_never_names_the_test_partition`.

### `spy`, `must_not_run`, `failing`
Small helpers nested inside single tests. `spy` records what the oversampler receives. `must_not_run` fails if a finished run repeats. `failing` raises to simulate a failed run.

**Common to every test below:** the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Parameters | Proves |
|---|---|---|
| `test_guard_refuses_anything_but_train_and_validation` | `tmp_path`, `name` | The test partition is refused at run time. |
| `test_guard_allows_train_and_compacts_it` | `tmp_path`, `model_partition` | Permitted partitions load. |
| `test_selection_code_never_names_the_test_partition` | `path` | Selection code contains no reference to the test partition. |
| `test_only_final_evaluation_and_preparation_can_load_a_named_partition` | none | Direct loading is limited to known modules. |
| `test_oversampling_sees_only_training_rows` | `monkeypatch`, `model_partition`, `later_partition` | The sampler receives training rows only, once. |
| `test_fit_report_counts_real_and_synthetic_rows` | `model_partition` | The counts add up. |
| `test_fit_without_oversampling_reports_no_resampling` | `model_partition` | No hidden resampling. |
| `test_fit_without_fraud_is_rejected` | `model_partition` | Invalid data raises. |
| `test_same_seed_reproduces_scores_exactly` | `model_partition`, `later_partition` | PRD 14.1 reproducibility, including oversampling. |
| `test_measure_inference_returns_batch_scores_and_timings` | `model_partition`, `later_partition` | Timing fields are filled. |
| `test_evaluate_candidate_reports_natural_evaluation_rows` | `model_partition`, `later_partition` | Evaluation rows keep their natural count and fraud total. |
| `test_store_saves_and_resumes` | `tmp_path` | Results survive a restart. |
| `test_run_candidate_skips_finished_runs` | `tmp_path` | Reruns don't repeat work. |
| `test_run_candidate_records_failure_rather_than_dropping_it` | `tmp_path` | No selective reporting of failures. |
| `test_scores_digest_detects_any_change` | none | The fingerprint is sensitive. |

## E. Classes Explained
None.

## F. Execution Flow
Fixtures build synthetic partitions, and some tests write them to a temporary folder.

## G. Input and Output
Input: synthetic data and the project's own source files. Output: pass or fail.

## H. Important Technical Concepts
The source-scanning tests complement the run-time guard. The guard stops a bad call. The scan fails the build the moment one is written.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_experiments.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Add any new script that runs before the freeze to the `path` list in `test_selection_code_never_names_the_test_partition`.

## K. Related Files
- [experiments.py](../../app/ml/experiments.py.explanation.md): code under test.
- [test_phase2_pipeline.py](../integration/test_phase2_pipeline.py.explanation.md): proves the same at pipeline level.
