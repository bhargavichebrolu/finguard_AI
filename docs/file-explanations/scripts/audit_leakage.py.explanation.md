# audit_leakage.py

Source: [scripts/audit_leakage.py](../../../scripts/audit_leakage.py)

## A. File Purpose
Command-line wrapper that runs the leakage audit, saves the report and prints each column's measured separation.

## B. Why This File Exists
It makes the audit a single repeatable command with a pass or fail exit code, ready to gate later pipeline stages.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `sys`, `pathlib`.
- **Internal modules:** `app.ml.leakage_audit`, `app.ml.pipeline_io`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** the `audit` target in the `Makefile`; `test_real_data.py` reads its report.

## D. Every Function Explained

### `main`
- **Purpose:** run the audit from the command line.
- **Parameters / types:** none directly; reads `--input`, `--processed-dir`, `--metadata`, `--output` as `Path`.
- **Returns / type:** `int`, 0 if hard rules hold and 1 if `LeakageError` was raised.
- **Internal processing:** loads boundaries from metadata, runs the audit, writes the report, prints signal figures ranked by separation.
- **Error handling:** catches `LeakageError`, prints it and exits 1 without writing a passing report. Other errors propagate.
- **Calls:** `run_leakage_audit`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments, load boundaries, audit, write the report, print rankings, exit.

## G. Input and Output
Input: raw CSV, processed partitions and metadata. Output: `experiments/results/leakage_audit.json` and a ranked console listing.

## H. Important Technical Concepts
The script reports evidence, but only the schema and file checks can fail it. A high separation number alone does not fail the audit, because strength and leakage are different questions.

## I. Example
```powershell
uv run --project backend python scripts/audit_leakage.py
```

## J. Maintenance Notes
Add new checks in `leakage_audit.py`. Keep the exit-code contract, because later automation relies on it.

## K. Related Files
- [leakage_audit.py](../backend/app/ml/leakage_audit.py.explanation.md): the logic.
- [prepare_dataset.py](prepare_dataset.py.explanation.md): produces what is audited.
