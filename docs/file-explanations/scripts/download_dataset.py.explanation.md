# download_dataset.py

Source: [scripts/download_dataset.py](../../../scripts/download_dataset.py)

## A. File Purpose
Places the PaySim CSV at `data/raw/`, either from a file already on disk or through the Kaggle CLI.

## B. Why This File Exists
The dataset is about 494 MB and is deliberately not stored in Git, so every developer needs a repeatable way to obtain it.

## C. Dependencies
- **Libraries:** `argparse`, `shutil`, `subprocess`, `sys`, `pathlib`.
- **Internal modules:** `app.ml.pipeline_io`.
- **External services:** Kaggle, only for the CLI route, using the developer's own API token.
- **Database:** none. **Depended on by:** developers; `test_scripts.py`.

## D. Every Function Explained

### `copy_local_file`
- **Purpose:** copy an already downloaded CSV into place.
- **Parameters / types:** `source: Path`, `destination: Path`.
- **Returns / type:** `None`.
- **Internal processing:** checks both paths, creates the folder, copies the file.
- **Error handling:** raises `FileNotFoundError` for a missing source and `FileExistsError` rather than overwriting.
- **Calls:** `shutil.copyfile`. **Used by:** `main`, tests.

### `download_from_kaggle`
- **Purpose:** download and unzip through the Kaggle CLI.
- **Parameters / types:** `destination: Path`.
- **Returns / type:** `None`.
- **Internal processing:** finds the CLI, then runs `kaggle datasets download -d ealaxi/paysim1 -p <folder> --unzip`.
- **Error handling:** raises `RuntimeError` with manual instructions if the CLI is absent; a failed download raises `CalledProcessError`.
- **Calls:** `shutil.which`, `subprocess.run`. **Used by:** `main`, tests.

### `main`
- **Purpose:** choose a route from the arguments.
- **Parameters / types:** none directly; reads `--from-file` and `--output` as `Path`.
- **Returns / type:** `int`, 0 on success and 1 on failure.
- **Internal processing:** exits early if the file already exists and no source was given; otherwise it copies or downloads.
- **Error handling:** catches `OSError`, `RuntimeError` and `CalledProcessError`, prints them, returns 1.
- **Calls:** `copy_local_file`, `download_from_kaggle`. **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments. With `--from-file`, copy. Without it, report if the file is present, otherwise download from Kaggle. Then point the developer to validation.

## G. Input and Output
Input: optionally a local CSV. Output: `data/raw/PS_20174392719_1491204439457_log.csv`.

## H. Important Technical Concepts
The script never overwrites a dataset. It also does not trust the result: validation is the separate step that verifies the file. The successful Kaggle download path has **not been run**, because no Kaggle token or CLI is present on the development machine. Only its missing-CLI error is tested.

## I. Example
```powershell
uv run --project backend python scripts/download_dataset.py --from-file C:\Users\me\Downloads\PS_20174392719_1491204439457_log.csv
```

## J. Maintenance Notes
If Kaggle changes the dataset slug, update `KAGGLE_DATASET` and `DATASET_DOCUMENTATION.md`. Never add a token to this file.

## K. Related Files
- [validate_dataset.py](validate_dataset.py.explanation.md): the required next step.
- [test_scripts.py](../backend/tests/unit/test_scripts.py.explanation.md): tests.
