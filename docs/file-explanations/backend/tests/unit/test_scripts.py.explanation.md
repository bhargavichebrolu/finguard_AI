# test_scripts.py

Source: [backend/tests/unit/test_scripts.py](../../../../../backend/tests/unit/test_scripts.py)

## A. File Purpose
Tests the logic that lives in `scripts/`: the documentation checker, dataset placement and `.env` generation, plus static checks that the environment template and Compose file hold no credentials.

## B. Why This File Exists
A broken documentation checker would pass silently and give false confidence. A faulty download script could overwrite data. Both need proof that they catch or refuse the right things.

## C. Dependencies
- **Libraries:** `pytest`, `pathlib`.
- **Internal modules:** `scripts/check_explanations.py`, `scripts/download_dataset.py` and `scripts/generate_env.py`, loaded through the `load_script` fixture.
- **External services / database:** none; the Kaggle CLI lookup is replaced by a stub.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `make_repo`
- **Purpose:** build a miniature repository in a temporary folder.
- **Parameters / types:** `tmp_path: Path`, `source: str`, `explanation: str | None`. **Returns / type:** `tuple[Path, Path]`, the root and explanations folder.
- **Internal processing:** writes `scripts/tool.py` and, if given, its explanation.
- **Error handling:** none needed. **Calls:** `pathlib`. **Used by:** the checker tests.

**Common to every test below:** parameters are pytest fixtures (`tmp_path`, `load_script`, `monkeypatch`), the return is `None`, and failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them; no project code does.

| Function | Proves |
|---|---|
| `test_checker_accepts_a_complete_explanation` | A correct document produces no problems. |
| `test_checker_reports_a_missing_explanation` | A source without a document is reported. |
| `test_checker_accepts_a_sibling_explanation` | A document beside its source satisfies the rule. |
| `test_checker_checks_the_content_of_a_sibling_explanation` | A sibling gets the same content checks as a mirrored document. |
| `test_checker_reports_a_source_documented_in_both_places` | Two documents for one source are reported, since they could disagree. |
| `test_checker_reports_an_orphan_sibling` | A sibling whose source is gone is reported. |
| `test_checker_covers_configuration_files` | A listed configuration file without a document is reported. |
| `test_generate_env_fills_every_secret_without_placeholders` | A generated `.env` has no placeholder left and uses the chosen ports. |
| `test_generate_env_creates_different_secrets_each_time` | Secrets are random, not fixed. |
| `test_generate_env_refuses_to_overwrite` | An existing `.env` is left untouched. |
| `test_generate_env_refuses_a_file_git_would_track` | Nothing is written if Git would not ignore the file. |
| `test_env_template_contains_only_placeholders` | `.env.example` holds no real secret. |
| `test_no_explanation_document_is_ignored_by_git` | Every explanation document can be committed. The checker reads files on disk, so an ignored document would otherwise pass unnoticed. |
| `test_compose_sets_scram_at_initialisation_and_stores_no_credentials` | The Compose file sets SCRAM at initialisation, never enables `trust`, requires the password from the environment, and binds to this computer only. |
| `test_checker_reports_an_undocumented_function` | A function added later without documentation is reported. |
| `test_checker_reports_a_missing_section` | A missing required section is named. |
| `test_checker_reports_a_thin_explanation` | Headings without content fail the word count. |
| `test_checker_reports_orphan_documents` | A document for a deleted file is reported. |
| `test_checker_reports_broken_links_and_accepts_valid_ones` | A missing link target is reported; valid files, web links and anchors are not. |
| `test_checker_skips_docstring_only_package_markers` | Docstring-only files are exempt; files with code are not. |
| `test_checker_finds_typescript_definitions` | Functions, arrow constants and classes are found; plain constants are not. |
| `test_copy_local_file_copies_content` | A copy succeeds and creates folders. |
| `test_copy_local_file_refuses_to_overwrite` | An existing dataset stays unchanged. |
| `test_copy_local_file_requires_a_source` | A missing source raises `FileNotFoundError`. |
| `test_kaggle_download_explains_a_missing_cli` | A missing CLI gives manual instructions. |

## E. Classes Explained
None.

## F. Execution Flow
Each test loads a script as a module, sets up temporary files if needed, calls one function and asserts on the result. `COMPLETE_SECTIONS` holds a valid document skeleton.

## G. Input and Output
Input: temporary files. Output: pass or fail.

## H. Important Technical Concepts
Testing a checker means feeding it known-bad input. A checker that has only ever seen passing input has not been shown to detect anything. The successful Kaggle download is deliberately not tested, as it needs network access and credentials.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_scripts.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Add a known-bad test whenever the checker gains a rule. Keep `COMPLETE_SECTIONS` in step with `REQUIRED_SECTIONS`.

## K. Related Files
- [check_explanations.py](../../../scripts/check_explanations.py.explanation.md), [download_dataset.py](../../../scripts/download_dataset.py.explanation.md): code under test.
- [conftest.py](../conftest.py.explanation.md): `load_script`.
