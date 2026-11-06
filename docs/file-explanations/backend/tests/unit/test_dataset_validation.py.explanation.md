# test_dataset_validation.py

Source: [backend/tests/unit/test_dataset_validation.py](../../../../../backend/tests/unit/test_dataset_validation.py)

## A. File Purpose
Tests that the validator catches each class of data problem and that it never discards rows.

## B. Why This File Exists
The real dataset is clean apart from zero amounts, so most checks would never fire on it. Only deliberate corruption can show those checks work.

## C. Dependencies
- **Libraries:** `pandas`, `pytest`, `pathlib`.
- **Internal modules:** `app.ml.dataset_validation`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `write_csv`
- **Purpose:** save a frame to a temporary CSV.
- **Parameters / types:** `frame: pd.DataFrame`, `tmp_path: Path`, `name: str`. **Returns / type:** `Path`.
- **Internal processing / errors:** `to_csv`; no special handling.
- **Calls:** pandas. **Used by:** tests in this file.

**Common to every test below:** parameters are pytest fixtures, the return is `None`, failures surface as `AssertionError`, and each calls `validate_dataset`. pytest runs them; no project code does.

| Function | Corruption or scenario | Expected result |
|---|---|---|
| `test_clean_file_passes_and_reports_counts` | None | Passes, with correct counts. |
| `test_missing_file_raises` | No file | `FileNotFoundError`. |
| `test_wrong_extension_fails` | `.txt` file | Fails, naming the extension. |
| `test_missing_column_fails` | `amount` removed | Fails on columns. |
| `test_missing_value_is_counted` | One null amount | Fails, null count is 1. |
| `test_non_numeric_amount_fails_cleanly` | Text in `amount` | Fails with a report, not a crash. |
| `test_negative_amount_fails` | Negative amount | Fails, count is 1. |
| `test_zero_amount_warns_and_keeps_row` | Zero amount on a fraud row | Passes with a warning; no row lost. |
| `test_unknown_type_fails` | Type `WIRE` | Fails. |
| `test_non_binary_target_fails` | `isFraud` of 2 | Fails. |
| `test_fractional_step_fails` | Step of 1.5 | Fails. |
| `test_duplicates_warn_and_are_not_removed` | Two repeated rows | Count is 2; row count retained. |
| `test_duplicates_across_chunk_boundary_are_found` | Repeat in a later chunk | Count is 1. |
| `test_unsorted_steps_warn` | Reversed file | Passes, with order violations reported. |
| `test_expected_profile_mismatch_fails` | Impossible profile | Fails with three errors. |
| `test_report_does_not_depend_on_chunk_size` | Chunk sizes 7 and 10,000 | Identical reports. |

## E. Classes Explained
None.

## F. Execution Flow
Each test edits a fixture copy, writes a CSV, validates it and asserts on the report.

## G. Input and Output
Input: corrupted temporary CSVs. Output: pass or fail.

## H. Important Technical Concepts
Each test changes one thing, so a failure points to one check. The chunk-size test guards against the most common streaming bug: results that change with batch boundaries.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_dataset_validation.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Every new validator check needs a corruption test here.

## K. Related Files
- [dataset_validation.py](../../app/ml/dataset_validation.py.explanation.md): code under test.
- [conftest.py](../conftest.py.explanation.md): fixtures.
