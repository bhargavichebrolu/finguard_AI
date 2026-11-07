# pipeline_io.py

Source: [backend/app/ml/pipeline_io.py](../../../../../backend/app/ml/pipeline_io.py)

## A. File Purpose
Holds default file locations for the offline data pipeline and two helpers: stable JSON writing and streaming file hashing.

## B. Why This File Exists
Every script needs the same paths, and the reproducibility check depends on JSON being written identically each time. Centralising both avoids scattered path literals and inconsistent formatting.

## C. Dependencies
- **Libraries:** `hashlib`, `json`, `pathlib`, `subprocess`, `typing`.
- **Internal modules:** none.
- **External services / database:** the local `git` command, used only by `current_commit` and `uncommitted_paths`.
- **Depended on by:** all pipeline scripts, `dataset_validation.py`, `dataset_preparation.py`, `leakage_audit.py`, `eda.py`, `experiments.py`, `selection.py`, `model_artifacts.py`, `final_evaluation.py`, `test_real_data.py`.

## D. Every Function Explained

### `current_commit`
- **Purpose:** record which code produced a result.
- **Parameters / types:** `repo_root: Path`.
- **Returns / type:** `str`, the commit hash.
- **Internal processing:** runs `git rev-parse HEAD`.
- **Error handling:** `CalledProcessError` outside a repository.
- **Calls:** `subprocess.run`.
- **Used by:** `scripts/evaluate_models.py`, `scripts/evaluate_final_test.py`.

### `uncommitted_paths`
- **Purpose:** check that files were committed and have not changed since.
- **Parameters / types:** `paths: list[Path]`; `repo_root: Path`.
- **Returns / type:** `list[str]` of files that are untracked, modified or missing.
- **Internal processing:** runs `git status --porcelain` per file. Empty output means committed and unchanged.
- **Error handling:** `CalledProcessError` outside a repository; `ValueError` for a path outside the repository.
- **Calls:** `subprocess.run`.
- **Used by:** `scripts/evaluate_final_test.py`, which uses it to prove the freeze came first.

### `write_json`
- **Purpose:** write a report in a form that diffs cleanly between runs.
- **Parameters / types:** `path: Path`, `payload: dict[str, Any]`.
- **Returns / type:** `None`.
- **Internal processing:** creates parent folders, serialises with sorted keys and two-space indentation, and forces `\n` line endings.
- **Error handling:** lets `OSError` and `TypeError` propagate; a report that cannot be written must fail the run.
- **Calls:** `json.dumps`, `Path.write_text`.
- **Used by:** every script that saves a report.

### `sha256_file`
- **Purpose:** fingerprint a file so outputs can be traced to the exact input.
- **Parameters / types:** `path: Path`.
- **Returns / type:** `str`, 64 hex characters.
- **Internal processing:** feeds 1 MiB blocks to `hashlib.sha256`, so a 494 MB file uses very little memory.
- **Error handling:** lets `OSError` propagate.
- **Calls:** `hashlib.sha256`.
- **Used by:** `validate_dataset`, `prepare_dataset`.

## E. Classes Explained
None.

## F. Execution Flow
`REPO_ROOT` is computed at import time from this file's location, three parents above `backend/app/ml`. All other paths derive from it.

## G. Input and Output
Inputs are a path and a payload (`write_json`) or a path (`sha256_file`). Outputs are a JSON file and a hash string.

## H. Important Technical Concepts
Forcing `newline="\n"` matters on Windows: otherwise the same data hashes differently across operating systems. These paths are for offline use only. The API will read locations from environment configuration, because a deployed container has no repository layout.

## I. Example
```python
write_json(Path("report.json"), {"b": 1, "a": 2})  # keys written as a, then b
```

## J. Maintenance Notes
If a report moves, change it here and update the output tables in `PROJECT_CONNECTIONS.md`. Do not import this module's paths into API code.

## K. Related Files
- [validate_dataset.py](../../../scripts/validate_dataset.py.explanation.md), [prepare_dataset.py](../../../scripts/prepare_dataset.py.explanation.md), [run_eda.py](../../../scripts/run_eda.py.explanation.md), [audit_leakage.py](../../../scripts/audit_leakage.py.explanation.md): use these defaults.
