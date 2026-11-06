# check_explanations.py

Source: [scripts/check_explanations.py](../../../scripts/check_explanations.py)

## A. File Purpose
Verifies PRD section 12: every authored source file has an explanation document with sections A to K, and that document names every function, class and method in the source.

## B. Why This File Exists
Documentation drifts unless something fails when it does. This script turns the most checkable part of the rule into a command, which Phase 5 will add to CI. It cannot judge whether the writing is good; that still needs a reviewer.

## C. Dependencies
- **Libraries:** `ast`, `re`, `sys`, `pathlib` (standard library only).
- **Internal modules:** none, so it can run without installing the backend's dependencies.
- **External services / database:** none.
- **Depended on by:** the `docs-check` target in the `Makefile`; `test_scripts.py`.

## D. Every Function Explained

### `python_definition_names`
- **Purpose:** list definitions in Python source, including nested ones and methods.
- **Parameters / types:** `source: str`. **Returns / type:** `list[str]`.
- **Internal processing:** walks the syntax tree with `ast.walk`.
- **Error handling:** `SyntaxError` propagates; the source must parse.
- **Calls:** `ast.parse`. **Used by:** `check_explanation`.

### `typescript_definition_names`
- **Purpose:** list named functions, arrow-function constants and classes.
- **Parameters / types:** `source: str`. **Returns / type:** `list[str]`.
- **Internal processing:** applies regular expressions, since Python has no TypeScript parser. Patterns outside these forms are not detected.
- **Error handling:** none needed.
- **Calls:** `re`. **Used by:** `check_explanation`.

### `is_package_marker`
- **Purpose:** identify Python files holding only a docstring.
- **Parameters / types:** `path: Path`. **Returns / type:** `bool`.
- **Internal processing:** inspects the top-level syntax nodes.
- **Error handling:** `SyntaxError` propagates.
- **Calls:** `ast.parse`. **Used by:** `is_documented_source`.

### `is_documented_source`
- **Purpose:** decide whether the rule applies to a file.
- **Parameters / types:** `path: Path`. **Returns / type:** `bool`.
- **Internal processing:** excludes dependency and build folders, `.d.ts` files, unsupported suffixes and package markers.
- **Error handling:** none needed.
- **Calls:** `is_package_marker`. **Used by:** `find_source_files`.

### `find_source_files`
- **Purpose:** list every file needing an explanation.
- **Parameters / types:** `root: Path`. **Returns / type:** `list[Path]`, repository-relative and sorted.
- **Internal processing:** searches `SOURCE_DIRECTORIES` and adds `SOURCE_FILES`.
- **Error handling:** missing folders are skipped.
- **Calls:** `is_documented_source`. **Used by:** `run_check`.

### `explanation_path`
- **Purpose:** map a source path to its document.
- **Parameters / types:** `source: Path`, `explanations_dir: Path`. **Returns / type:** `Path`.
- **Internal processing:** mirrors the folder structure and appends `.explanation.md`.
- **Error handling:** none needed.
- **Calls:** none. **Used by:** `run_check`, `find_orphans`.

### `check_explanation`
- **Purpose:** check one document.
- **Parameters / types:** `source_path: Path`, `explanation: Path`, `label: str`. **Returns / type:** `list[str]` of problems.
- **Internal processing:** checks existence, section headings, a minimum word count, and that each definition appears in backticks.
- **Error handling:** problems are returned, not raised.
- **Calls:** `python_definition_names`, `typescript_definition_names`. **Used by:** `run_check`.

### `find_orphans`
- **Purpose:** find documents whose source was deleted or renamed.
- **Parameters / types:** `root: Path`, `explanations_dir: Path`, `sources: list[Path]`. **Returns / type:** `list[str]`.
- **Internal processing:** compares all existing documents with expected ones.
- **Error handling:** a missing folder returns an empty list.
- **Calls:** `explanation_path`. **Used by:** `run_check`.

### `find_broken_links`
- **Purpose:** catch relative links that point at nothing, since PRD 12.1 section K requires usable related-file paths.
- **Parameters / types:** `root: Path`, `explanations_dir: Path`. **Returns / type:** `list[str]`.
- **Internal processing:** reads root-level and `docs/` Markdown, extracts link targets with `_MARKDOWN_LINK`, and skips web links and same-page anchors.
- **Error handling:** problems are returned, not raised.
- **Calls:** `re`, `pathlib`. **Used by:** `run_check`, tests.

### `run_check`
- **Purpose:** check a whole repository.
- **Parameters / types:** `root: Path`, `explanations_dir: Path`. **Returns / type:** `tuple[list[Path], list[str]]`.
- **Internal processing:** combines the functions above. Taking paths as arguments is what makes it testable.
- **Error handling:** none beyond those functions.
- **Calls:** `find_source_files`, `check_explanation`, `explanation_path`, `find_orphans`, `find_broken_links`. **Used by:** `main`, tests.

### `main`
- **Purpose:** command-line entry point.
- **Parameters / types:** none. **Returns / type:** `int`, 0 when clean and 1 otherwise.
- **Internal processing:** prints every problem and a total.
- **Error handling:** none beyond those functions.
- **Calls:** `run_check`. **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Find source files, check each document, look for orphans, print the results, exit with a status code.

## G. Input and Output
Input: the repository tree. Output: one line per problem, a total, and an exit code.

## H. Important Technical Concepts
- **Mirrored paths:** the PRD's tree includes `docs/file-explanations/`, so documents mirror the source tree there rather than sitting beside each source file. This avoids name collisions (such as `__init__.py`) and keeps source folders uncluttered. See `docs/decisions/0001-phase-1-decisions.md`.
- **Scope:** Python, TypeScript and CSS sources, `frontend/index.html`, `frontend/vite.config.ts` and the `Makefile`. Declarative configuration, lockfiles, generated output and data are documented centrally instead, as PRD 12.2 allows for generated files. Treating config as central is a project decision recorded in that same document.
- **A name check is not a quality check:** it proves a function is mentioned, not that the explanation is correct.

## I. Example
```powershell
uv run --project backend python scripts/check_explanations.py
```

## J. Maintenance Notes
When a new source type or top-level file appears, extend `SOURCE_SUFFIXES` or `SOURCE_FILES`. If section titles change, update `REQUIRED_SECTIONS` and the existing documents together.

## K. Related Files
- [test_scripts.py](../backend/tests/unit/test_scripts.py.explanation.md): tests.
- `CONTRIBUTING.md`: the documentation workflow.
