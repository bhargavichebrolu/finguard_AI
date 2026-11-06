# test_real_data.py

Source: [backend/tests/integration/test_real_data.py](../../../../../backend/tests/integration/test_real_data.py)

## A. File Purpose
Checks the saved outputs from the real PaySim dataset. The tests skip themselves if the dataset or partitions are absent, such as in CI.

## B. Why This File Exists
Synthetic fixtures cannot confirm the actual dataset's numbers. This file ties the committed reports to the local files and to the PRD's published figures.

## C. Dependencies
- **Libraries:** `json`, `pyarrow`, `pytest`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.pipeline_io`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `read_json`
- **Purpose:** read a saved report.
- **Parameters / types:** `path: Path`. **Returns / type:** `dict`.
- **Internal processing / errors:** a plain read; a missing report fails the test.
- **Calls:** `json`. **Used by:** tests in this file.

**Common to every test below:** no parameters, returns `None`, failures surface as `AssertionError`, and all carry the `real_data` marker. pytest runs them; no project code does.

| Function | Proves |
|---|---|
| `test_validation_report_matches_published_profile` | 6,362,620 rows, 8,213 frauds, 5 types, no nulls or duplicates. |
| `test_partitions_account_for_every_row_and_fraud` | Partition totals match the dataset, and metadata row counts match the Parquet files. |
| `test_partition_steps_follow_boundaries` | Recorded partition ranges match the boundaries. |
| `test_real_partitions_have_only_expected_columns` | Real files have all features and no excluded columns. |
| `test_metadata_and_validation_describe_the_same_file` | Both reports carry the same source hash. |
| `test_leakage_report_recorded_a_pass` | The audit passed, and its signal scope is training rows only. |

## E. Classes Explained
None.

## F. Execution Flow
`pytestmark` applies the marker and skip condition to the whole module, evaluated at import.

## G. Input and Output
Input: saved reports and processed files. Output: pass, fail or skip.

## H. Important Technical Concepts
These tests read existing outputs rather than recomputing them, so they run in seconds. They check that outputs are consistent, so rerun the pipeline first after changing code. Exact numbers are hardcoded on purpose: they are the verified identity of this dataset.

## I. Example
```powershell
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml -m real_data
```

## J. Maintenance Notes
Update hardcoded values only for a deliberate dataset change, never to make a test pass. Add the Phase 2 result files here when they exist.

## K. Related Files
- [validate_dataset.py](../../../scripts/validate_dataset.py.explanation.md), [prepare_dataset.py](../../../scripts/prepare_dataset.py.explanation.md), [audit_leakage.py](../../../scripts/audit_leakage.py.explanation.md): produce the checked outputs.
