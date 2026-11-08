# verify_clean_clone.py

Source: [scripts/verify_clean_clone.py](verify_clean_clone.py)

## A. File Purpose
Clones the committed repository into a temporary folder and checks that, without the dataset, model binary or `.env`, it installs from the lockfiles and passes every check that does not need them, recording exactly which tests skip and why.

## B. Why This File Exists
Phase 5 M1 asks for reproducibility evidence. A developer's working copy hides problems: files that exist but are not committed, dependencies installed by hand. A fresh clone is what CI and a new contributor see.

## C. Dependencies
- **Libraries:** Python standard library, python-dotenv, SQLAlchemy (`make_url`).
- **Internal modules:** `test_report.py`.
- **External services / database:** Git, uv, npm, and PostgreSQL through `TEST_DATABASE_URL` (must end in `_test`).
- **Depended on by:** Developers before a phase gate; the results are recorded in TESTING_GUIDE.md.

## D. Every Function Explained

### `run`
Prints and runs one command, returning its exit code.

### `test_database_url`
Reads `TEST_DATABASE_URL` and refuses a database not ending in `_test`.

### `remove_tree`
Deletes the temporary folder, clearing Git's read-only flags on Windows.

### `make_writable`
Nested in `remove_tree`: makes a file writable, then retries the deletion.

### `main`
- **Purpose:** the whole check.
- **Parameters / types:** `--ref` (default HEAD), `--skip-frontend`, `--keep`, `--report FILE`. **Returns / type:** exit code, 0 only if every step passed.
- **Internal processing:** clone with `--no-local`; check out the ref; confirm `.env`, the model binary and the raw dataset are absent; `uv sync --frozen`; pytest with JUnit output (the test-partition check deselected, as everywhere since Phase 3); the explanation checker, `export_openapi.py --check` and `export_model_report.py --check`; `npm ci`, type check, unit tests and build.
- **Error handling:** the temporary folder is always removed unless `--keep`. **Calls:** `read_junit`. **Used by:** command line.

## E. Classes Explained
None.

## F. Execution Flow
Clone, confirm absences, install from lockfiles, test, report, clean up.

## G. Input and Output
Output: step exit codes, pytest totals and every skipped test with its reason, printed and optionally written as JSON.

## H. Important Technical Concepts
- **`MUST_BE_ABSENT`** lists the ignored inputs; a test confirms Git ignores each.
- **`TEST_PARTITION_CHECK`** is the deselected test that rereads the frozen test partition.
- **Testing uncommitted work:** commit the working tree to a temporary branch (`git commit-tree`) and pass it as `--ref`, so the clone sees exactly the files that would be committed.
- **Environment:** `DATABASE_URL`, `SECRET_KEY` and `VIRTUAL_ENV` are removed, so nothing from this machine's configuration leaks into the clone.

## I. Example
```powershell
python scripts/verify_clean_clone.py --report clean-clone.json
```

## J. Maintenance Notes
Add any new ignored input the code expects to `MUST_BE_ABSENT`.

## K. Related Files
- [test_report.py](test_report.py.explanation.md): report reading.
