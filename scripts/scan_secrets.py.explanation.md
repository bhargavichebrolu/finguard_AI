# scan_secrets.py

Source: [scripts/scan_secrets.py](scan_secrets.py)

## A. File Purpose
Scans every line ever added in the repository's history, or the staged changes, for secrets, and checks that no secret file was ever committed.

## B. Why This File Exists
Phase 5 M5 reviewed secrets across all history, not only the current files. The project forbids committing credentials, and a scan of history is the only way to show none ever were.

## C. Dependencies
- **Libraries:** Python standard library.
- **Internal modules:** none.
- **External services / database:** Git.
- **Depended on by:** Developers and CI (M8): `python scripts/scan_secrets.py`.

## D. Every Function Explained

### `_mask`
Shows only the first three characters of a matched value.

### `scan_lines`
- **Purpose:** check added lines against the patterns.
- **Parameters / types:** list of (location, line). **Returns / type:** list of `Finding`.
- **Internal processing:** each pattern's match is skipped if an `ALLOWED` marker explains it. Assignment and URL matches are also skipped if the value is a call (`token_urlsafe(18)`), an f-string placeholder, or a constant's name; token patterns get no such exception, because real AWS keys are capitals too.
- **Error handling:** none. **Calls:** `_mask`. **Used by:** `main`, tests.

### `added_lines`
Every added line from `git log -p --all` with its commit and file, or from `git diff --cached`.

### `committed_secret_files`
Every `.env`, `.pem` or `.key` file ever added on any branch, except `.env.example` and its explanation.

### `main`
Runs the scan, prints findings with masked values, and fails if any remain.

## E. Classes Explained
### `Finding`
A dataclass: kind, commit and file, and a masked preview.

## F. Execution Flow
Read history, match, filter by documented exceptions, report.

## G. Input and Output
Output, from the Phase 5 run: `Scanned 135,531 added lines (all history). 0 findings, 0 secret files.`

## H. Important Technical Concepts
- **`PATTERNS`**: private keys, AWS keys, GitHub tokens, database URLs with passwords, and secret-named assignments of at least 16 characters.
- **`ALLOWED`**: each deliberate fake value with why it is safe; the first run's 14 candidates were all such fixtures, each checked by reading the line.
- **`SECRET_FILES`, `SAFE_FILES`, `_CONSTANT_NAME`**: the file-name rule, its exceptions, and the constant-name test.
- **A flaw caught by its own test:** an early exception for capitalised values would have hidden real AWS keys; `test_scan_secrets.py` failed and the exception now applies to assignments only.

## I. Example
```powershell
python scripts/scan_secrets.py
python scripts/scan_secrets.py --staged
```

## J. Maintenance Notes
Add to `ALLOWED` only with a reason, and only for values that are certainly fake.

## K. Related Files
- [test_scan_secrets.py](../backend/tests/unit/test_scan_secrets.py.explanation.md): proves it still finds real secrets.
