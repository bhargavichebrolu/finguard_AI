# test_data_pipeline.py

Source: [backend/tests/integration/test_data_pipeline.py](../../../../../backend/tests/integration/test_data_pipeline.py)

## A. File Purpose
Runs preparation, the leakage audit and EDA together on the synthetic fixture, and checks the files they produce.

## B. Why This File Exists
Unit tests show each part works alone. These tests show the parts work together and that the guarantees hold in real output files, including when those files are tampered with.

## C. Dependencies
- **Libraries:** `pandas`, `pyarrow`, `pytest`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.eda`, `app.ml.features`, `app.ml.leakage_audit`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `prepared`
- **Purpose:** fixture that runs preparation once per test.
- **Parameters / types:** `raw_csv: Path`, `tmp_path: Path`, `split_config: SplitConfig`. **Returns / type:** `tuple` of the output folder, metadata and boundaries.
- **Internal processing:** calls `prepare_dataset` with a small chunk size so chunk logic is exercised.
- **Error handling:** errors fail the test. **Calls:** `prepare_dataset`. **Used by:** most tests here.

**Common to every test below:** parameters are pytest fixtures, the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Proves |
|---|---|
| `test_partitions_hold_every_row_with_labels_unchanged` | No row is lost or duplicated, and each label matches its source row. |
| `test_partitions_are_chronological_with_no_shared_step` | Partitions are contiguous and share no step. |
| `test_processed_files_contain_no_excluded_columns` | Balances, account names and `isFraud` are absent from the files. |
| `test_loaded_features_exclude_label_and_tracking_columns` | `load_partition` features equal `FEATURE_COLUMNS`. |
| `test_stored_features_match_a_direct_serving_call` | Stored features equal a direct `engineer_features` call, so there is no training/serving skew. |
| `test_rerun_gives_identical_metadata` | Two runs give equal metadata, including content hashes. |
| `test_content_hash_does_not_depend_on_chunk_size` | Chunk sizes 13 and 500 give the same content hash. |
| `test_metadata_records_versions_and_source_hash` | Versions and the source hash are recorded. |
| `test_audit_passes_on_clean_output` | Clean output passes the audit. |
| `test_audit_rejects_a_leaky_column_in_a_partition` | A tampered file containing `oldbalanceOrg` raises `LeakageError`. |
| `test_audit_rejects_partitions_that_overlap_in_time` | Wrong boundaries raise `LeakageError`. |
| `test_audit_rejects_a_forbidden_feature` | A patched feature list containing `isFraud` raises `LeakageError`. |
| `test_signal_audit_uses_training_rows_only` | Signal counts equal training rows, not all rows. |
| `test_eda_signal_sections_use_training_rows_only` | EDA behaviour tables total to training rows only. |
| `test_eda_whole_dataset_counts_are_complete` | Whole-dataset counts account for all rows. |
| `test_eda_figures_are_written` | Four non-empty chart files are produced. |

## E. Classes Explained
None.

## F. Execution Flow
The `prepared` fixture creates partitions in a temporary folder, and each test inspects or tampers with them.

## G. Input and Output
Input: the synthetic CSV. Output: pass or fail. No repository file is touched.

## H. Important Technical Concepts
The tamper tests matter most: they prove the audit can fail. An audit that has only been seen passing proves nothing. The two training-only tests protect the untouched test-set rule.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_data_pipeline.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Phase 2 should add its own tests in a separate module rather than extending this one. If processed columns change, update the excluded-column assertions deliberately.

## K. Related Files
- [dataset_preparation.py](../../app/ml/dataset_preparation.py.explanation.md), [leakage_audit.py](../../app/ml/leakage_audit.py.explanation.md), [eda.py](../../app/ml/eda.py.explanation.md): code under test.
- [test_real_data.py](test_real_data.py.explanation.md): the same concerns against real outputs.
