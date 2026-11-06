# dataset_validation.py

Source: [backend/app/ml/dataset_validation.py](../../../../../backend/app/ml/dataset_validation.py)

## A. File Purpose
Checks a raw PaySim CSV in streaming chunks and returns a JSON-ready report covering columns, types, missing values, duplicates, invalid amounts, the target distribution and the published dataset profile.

## B. Why This File Exists
PRD 4.5 requires verification before processing and forbids silently discarding records or modifying labels. Keeping validation separate from preparation means it only observes: it cannot change data.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `collections`, `dataclasses`, `pathlib`, `typing`.
- **Internal modules:** `app.ml.pipeline_io`, `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `scripts/validate_dataset.py`, `test_dataset_validation.py`.

## D. Every Function Explained

### `_collect_findings`
- **Purpose:** convert a finished tally into findings.
- **Parameters / types:** `tally: _ValidationTally`, `expected: ExpectedProfile | None`.
- **Returns / type:** `tuple[list[str], list[str], int]`: errors, warnings, duplicate count.
- **Internal processing:** structural faults become errors. Zero amounts, negative balances, unsorted steps and duplicates become warnings, because the data can still be processed honestly.
- **Error handling:** reports only; raises nothing.
- **Calls:** `_ValidationTally.duplicate_rows`, `_compare_to_expected`.
- **Used by:** `validate_dataset`.

### `_compare_to_expected`
- **Purpose:** compare the file with the published PaySim profile.
- **Parameters / types:** `tally: _ValidationTally`, `expected: ExpectedProfile`.
- **Returns / type:** `list[str]` of errors.
- **Internal processing:** checks row count range, exact fraud count, type count and distinct step range.
- **Error handling:** reports only.
- **Calls:** none.
- **Used by:** `_collect_findings`.

### `validate_dataset`
- **Purpose:** public entry point.
- **Parameters / types:** `path: Path`, `expected: ExpectedProfile | None = None`, `chunk_size: int`.
- **Returns / type:** `dict[str, Any]` with `passed`, `errors`, `warnings` and statistics.
- **Internal processing:** hashes the file, checks the extension and header, streams chunks into a tally, then assembles the report.
- **Error handling:** a missing file raises `FileNotFoundError`, since nothing can be reported about it. A wrong extension, wrong columns or a non-numeric value returns `passed: False` with an explanation.
- **Calls:** `sha256_file`, `pandas.read_csv`, `_ValidationTally.update`, `_collect_findings`.
- **Used by:** `scripts/validate_dataset.py`.

## E. Classes Explained

### `ExpectedProfile`
- **Responsibility:** the published characteristics a download must match.
- **Constructor / attributes:** `min_rows`, `max_rows`, `fraud_count`, `transaction_type_count`, `min_steps`, `max_steps`.
- **Methods:** none. **Usage:** the `PAYSIM_EXPECTED` constant and tests.

### `_ValidationTally`
- **Responsibility:** running totals, so the full file is never held in memory.
- **Constructor / attributes:** `__init__` zeroes the counters: rows, nulls, steps, type counts, fraud by type, destination prefix by type, amount and balance counts, label counts and row hashes.
- **Methods:**
  - `update(chunk)`: adds one chunk. Called once per chunk by `validate_dataset`; returns `None`.
  - `_update_steps(steps)`: tracks non-integer values, ordering (including across chunk boundaries) and distinct steps; returns `None`.
  - `_update_amounts(chunk)`: counts negative and zero amounts, zero amounts labelled fraud, and the maximum; returns `None`.
  - `duplicate_rows()`: returns `int`, rows whose content hash repeats an earlier row.
- **Dependencies:** pandas and numpy. **Usage:** `validate_dataset`.

## F. Execution Flow
1. Raise if the file is absent; hash it.
2. Stop early with a failed report on a wrong extension or header.
3. Read chunks, calling `update` on each. A parser `ValueError` becomes a failed report.
4. Call `_collect_findings` and assemble the statistics.

## G. Input and Output
Input: a CSV path. Output: a report dictionary, saved by the script to `experiments/results/dataset_validation.json`. The real file passes with one warning about 16 zero-amount rows, all labelled fraud.

## H. Important Technical Concepts
- **Integer columns read as `float64`:** pandas refuses nulls in an integer column, which would stop the counting. `float64` represents these small values exactly.
- **Hash-based duplicate detection:** storing one 64-bit hash per row costs about 51 MB for 6.36M rows, against gigabytes for the rows themselves. A false match is theoretically possible, but it could only over-report a warning, and no data is removed either way.
- **Errors versus warnings:** an error means the file is not trustworthy for this pipeline. A warning means a real property of the data that users must know about.

## I. Example
```python
report = validate_dataset(RAW_CSV_PATH, expected=PAYSIM_EXPECTED)
report["passed"], report["target"]["fraud_rows"]  # (True, 8213)
```

## J. Maintenance Notes
A new check should be counted in `update`, reported in `_collect_findings`, surfaced in the report, and tested by corrupting the fixture in one known way. Results must not depend on chunk size; `test_report_does_not_depend_on_chunk_size` protects this.

## K. Related Files
- [validate_dataset.py](../../../scripts/validate_dataset.py.explanation.md): command-line wrapper.
- [test_dataset_validation.py](../../tests/unit/test_dataset_validation.py.explanation.md): tests.
- [schema.py](schema.py.explanation.md): expected columns.
