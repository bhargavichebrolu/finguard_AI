# conftest.py

Source: [backend/tests/conftest.py](../../../../backend/tests/conftest.py)

## A. File Purpose
Provides shared pytest fixtures: a small synthetic PaySim-shaped dataset, a standard split config, and a way to import files from `scripts/`.

## B. Why This File Exists
Tests must run in CI and on any laptop without a 494 MB download. One hand-built fixture also means each test can corrupt known values and predict the exact result.

## C. Dependencies
- **Libraries:** `pandas`, `pytest`, `importlib`, `sys`, `pathlib`, `types`, `collections.abc`.
- **Internal modules:** `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** all test modules, automatically through pytest.

## D. Every Function Explained

### `build_raw_frame`
- **Purpose:** create the fixture data.
- **Parameters / types:** none. **Returns / type:** `pd.DataFrame` of 600 rows over 30 steps with all 11 raw columns.
- **Internal processing:** cycles through the five types. The TRANSFER row at position 4 of each step is labelled fraud, and merchant prefixes occur only on PAYMENT, mirroring the real structure.
- **Error handling:** none needed. **Calls:** pandas.
- **Used by:** the `raw_frame` fixture.

### `raw_frame`
- **Purpose:** give a test a fresh, editable copy of the data.
- **Parameters / types:** none. **Returns / type:** `pd.DataFrame`.
- **Internal processing / errors:** calls the builder per test so tests cannot affect each other.
- **Calls:** `build_raw_frame`. **Used by:** most tests.

### `raw_csv`
- **Purpose:** write the fixture to a temporary CSV.
- **Parameters / types:** `tmp_path: Path`, `raw_frame: pd.DataFrame`. **Returns / type:** `Path`.
- **Internal processing / errors:** pandas `to_csv`; no special handling.
- **Calls:** pandas. **Used by:** file-based tests.

### `split_config`
- **Purpose:** a standard 70/15/15 config.
- **Parameters / types:** none. **Returns / type:** `SplitConfig`.
- **Internal processing / errors:** constructs the object.
- **Calls:** `SplitConfig`. **Used by:** `test_data_pipeline.py`.

### `load_script`
- **Purpose:** provide a loader for modules in `scripts/`, which is not an installed package.
- **Parameters / types:** none. **Returns / type:** `Callable[[str], ModuleType]`, the inner `_load` function.
- **Internal processing:** see below.
- **Error handling:** import errors propagate.
- **Calls:** `importlib.util`. **Used by:** `test_scripts.py`.

### `_load`
- **Purpose:** import one script by name.
- **Parameters / types:** `name: str`. **Returns / type:** `ModuleType`.
- **Internal processing:** builds a module spec from the path, registers it in `sys.modules` and executes it. Registration under a unique name avoids clashes with real modules.
- **Error handling:** import errors propagate.
- **Calls:** `importlib.util.spec_from_file_location`. **Used by:** `load_script`.

## E. Classes Explained
None.

## F. Execution Flow
pytest loads this file automatically and injects fixtures by parameter name.

## G. Input and Output
No external input. Output is fixture values for tests.

## H. Important Technical Concepts
The fixture is synthetic and contains no real PaySim rows. It has a uniform 20 rows per step, so all of its steps count as low-volume in EDA, and a test relies on that.

## I. Example
```python
def test_example(raw_csv):
    assert validate_dataset(raw_csv)["passed"]
```

## J. Maintenance Notes
Many tests depend on exact fixture values, such as row 4 being fraud. If a new scenario is needed, modify a copy in the test instead of changing the builder.

## K. Related Files
- [test_dataset_validation.py](unit/test_dataset_validation.py.explanation.md), [test_data_pipeline.py](integration/test_data_pipeline.py.explanation.md), [test_scripts.py](unit/test_scripts.py.explanation.md): main users.
