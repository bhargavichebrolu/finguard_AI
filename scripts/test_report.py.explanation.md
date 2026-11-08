# test_report.py

Source: [scripts/test_report.py](test_report.py)

## A. File Purpose
Reads a pytest JUnit XML report into totals and a list of skipped tests with their reasons.

## B. Why This File Exists
Phase 5 needs an exact record of which tests a clean checkout skips (M1), and CI must fail when that set changes (M8). Both read the same report format, so the reading lives here once.

## C. Dependencies
- **Libraries:** Python standard library (`xml.etree`, `dataclasses`).
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `verify_clean_clone.py`; the CI skip check (M8).

## D. Every Function Explained

### `passed`
A property of `TestReport`: tests minus failures, errors and skips.

### `node_id`
- **Purpose:** rebuild a pytest node id from JUnit's dotted class name.
- **Parameters / types:** `classname`, `name`, `root: Path`. **Returns / type:** `str` such as `tests/unit/test_x.py::TestGroup::test_y`.
- **Internal processing:** the module is the longest dotted prefix that exists as a `.py` file under `root`; the rest are test class names.
- **Error handling:** falls back to the dotted name. **Calls:** none. **Used by:** `read_junit`.

### `read_junit`
Parses the report, counting tests, failures and errors, and recording each skipped test's node id and message.

## E. Classes Explained
### `TestReport`
A dataclass with `tests`, `failures`, `errors` and `skipped` (node id to reason). `__test__ = False` stops pytest treating it as a test class.

## F. Execution Flow
Called after a pytest run with `--junitxml`.

## G. Input and Output
Input: a JUnit XML file. Output: a `TestReport`.

## H. Important Technical Concepts
- **Why node ids:** CI compares skips by node id, which is stable across runs, unlike output text.

## I. Example
```python
report = read_junit(Path("pytest.xml"), Path("backend"))
print(report.passed, sorted(report.skipped))
```

## J. Maintenance Notes
If pytest changes its JUnit layout, `test_reproducibility.py` fails first.

## K. Related Files
- [verify_clean_clone.py](verify_clean_clone.py.explanation.md): the first user.
