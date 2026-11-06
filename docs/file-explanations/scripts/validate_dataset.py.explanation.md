# validate_dataset.py

Source: [scripts/validate_dataset.py](../../../scripts/validate_dataset.py)

## A. File Purpose
Command-line wrapper that validates the raw CSV against the published PaySim profile, saves the report and prints a summary.

## B. Why This File Exists
It keeps command-line concerns (arguments, printing, exit codes) out of the tested library. The non-zero exit code lets a later automation step stop on a bad dataset.

## C. Dependencies
- **Libraries:** `argparse`, `sys`, `pathlib`.
- **Internal modules:** `app.ml.dataset_validation`, `app.ml.pipeline_io`.
- **External services / database:** none.
- **Depended on by:** the `validate` target in the `Makefile`; developers directly.

## D. Every Function Explained

### `main`
- **Purpose:** run validation from the command line.
- **Parameters / types:** none directly; reads `--input` and `--output` as `Path`.
- **Returns / type:** `int`, 0 if validation passed and 1 otherwise.
- **Internal processing:** calls the validator with `PAYSIM_EXPECTED`, saves the report, prints row and fraud counts, errors and warnings.
- **Error handling:** a missing file raises `FileNotFoundError` with a clear message. Data problems are reported, not raised.
- **Calls:** `validate_dataset`, `write_json`.
- **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments, validate, write JSON, print, exit with a status code.

## G. Input and Output
Input: the CSV at `data/raw/`. Output: `experiments/results/dataset_validation.json` and a console summary. The report is written even on failure, so the failure can be inspected.

## H. Important Technical Concepts
The exit code is the script's contract with automation: 0 means later stages may run.

## I. Example
```powershell
uv run --project backend python scripts/validate_dataset.py
```

## J. Maintenance Notes
Put new checks in `dataset_validation.py`, not here. This file should stay limited to arguments and output.

## K. Related Files
- [dataset_validation.py](../backend/app/ml/dataset_validation.py.explanation.md): the logic.
- [Makefile](../Makefile.explanation.md): shortcut.
