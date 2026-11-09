# test_scan_secrets.py

Source: [backend/tests/unit/test_scan_secrets.py](test_scan_secrets.py)

## A. File Purpose
Proves the secret scanner still finds real-looking secrets after its false-positive rules, and does not report generated values, references or placeholders.

## B. Why This File Exists
A scanner that reports nothing is only useful if it can find something; this test caught a rule that would have hidden AWS keys.

## C. Dependencies
- **Libraries:** pytest.
- **Internal modules:** `scripts/scan_secrets.py`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `scanner`
Fixture: the loaded script.

## E. Classes Explained
None.

## F. Execution Flow
Feed constructed lines to `scan_lines`.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_real_looking_secrets_are_found` | Each pattern finds its secret, and the preview never shows the value. |
| `test_generated_values_references_and_placeholders_are_not_findings` | Known safe shapes are ignored. |
| `test_secret_files_are_recognised` | The secret-file rule. |

## H. Important Technical Concepts
- **`FAKE`** is assembled at run time, so this file never contains a secret-shaped literal and does not trip the scanner.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_scan_secrets.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Add a case here for any new pattern or exception.

## K. Related Files
- [scan_secrets.py](../../../scripts/scan_secrets.py.explanation.md): the scanner.
