# conftest.py

Source: [backend/tests/conftest.py](../../../../backend/tests/conftest.py)

## A. File Purpose
Provides shared pytest fixtures: a small synthetic PaySim-shaped dataset, a standard split config, and a way to import files from `scripts/`.

## B. Why This File Exists
Tests must run in CI and on any laptop without a 494 MB download. One hand-built fixture also means each test can corrupt known values and predict the exact result.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `pytest`, `importlib`, `sys`, `pathlib`, `types`, `typing`, `collections.abc`.
- **Internal modules:** `app.ml.dataset_preparation`, `app.ml.features`, `app.ml.preprocessing`, `app.ml.schema`, `app.ml.splitting`.
- **External services / database:** none.
- **Depended on by:** all test modules, automatically through pytest.

## D. Every Function Explained

### `configure_test_environment`
- **Purpose:** point the application settings at the test database before anything reads them.
- **Parameters / types:** none. **Returns / type:** `str | None`, the test database address.
- **Internal processing:** reads `TEST_DATABASE_URL` from the environment or `.env`, and sets `DATABASE_URL`, `APP_ENV` and a test signing key. Without a test database it sets an address that nothing listens on, so tests that do not need a database can still import the application.
- **Error handling:** none needed.
- **Calls:** `dotenv_values`. **Used by:** the module body.

### `require_test_database_name`
- **Purpose:** refuse any database not clearly meant for tests, because the fixtures delete rows.
- **Parameters / types:** `url: str`. **Returns / type:** `None`.
- **Internal processing:** the database name must end in `_test`.
- **Error handling:** raises `RuntimeError`.
- **Calls:** `make_url`. **Used by:** `db_engine`, `test_migrations.py`.

### `alembic_config`
- **Purpose:** build an Alembic configuration that works from any folder.
- **Parameters / types:** none. **Returns / type:** `Config`.
- **Internal processing:** uses absolute paths to `alembic.ini` and `migrations/`.
- **Error handling:** none needed.
- **Calls:** `Config`. **Used by:** `db_engine`, `test_migrations.py`.

### `db_engine`
- **Purpose:** session-wide engine for a migrated test database.
- **Parameters / types:** none. **Returns / type:** an iterator yielding `Engine`.
- **Internal processing:** checks the name, runs migrations, and disposes of the engine at the end.
- **Error handling:** skips if no test database is configured.
- **Calls:** `require_test_database_name`, `alembic_config`. **Used by:** database tests.

### `empty_all_tables`
- **Purpose:** remove all rows, so tests do not affect each other.
- **Parameters / types:** `engine: Engine`. **Returns / type:** `None`.
- **Internal processing:** runs `TRUNCATE` on every table in the model metadata.
- **Error handling:** database errors propagate.
- **Calls:** `Base.metadata`. **Used by:** `db_session`, `test_migrations.py`.

### `db_session`
- **Purpose:** provide a session on an empty database.
- **Parameters / types:** `db_engine: Engine`. **Returns / type:** an iterator yielding `Session`.
- **Internal processing:** empties the tables, then opens a session.
- **Error handling:** the session closes when the test ends, discarding uncommitted changes.
- **Calls:** `empty_all_tables`. **Used by:** database tests.

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

### `build_model_partition`
- **Purpose:** build a synthetic partition for Phase 2 tests, in which fraud has larger amounts and occurs in two types.
- **Parameters / types:** `rows`, `first_step`, `last_step`, `seed`: ints; `fraud_rate: float`.
- **Returns / type:** `PartitionData`.
- **Internal processing:** seeded random inputs passed through `engineer_features`.
- **Error handling:** none needed.
- **Calls:** `engineer_features`, `compact_features`.
- **Used by:** `model_partition`, `later_partition`, Phase 2 tests.

### `write_partition`
- **Purpose:** save a partition as the real pipeline would.
- **Parameters / types:** `partition: PartitionData`; `directory: Path`; `name: str`.
- **Returns / type:** `Path`.
- **Internal processing:** adds the tracking columns and writes Parquet.
- **Error handling:** none needed.
- **Calls:** pandas `to_parquet`.
- **Used by:** Phase 2 tests.

### `small_experiment_config`
- **Purpose:** provide a complete experiment config with very small models.
- **Parameters / types:** none.
- **Returns / type:** `dict`.
- **Internal processing:** direct construction.
- **Error handling:** none needed.
- **Calls:** nothing.
- **Used by:** Phase 2 tests.

### `model_partition`, `later_partition`, `experiment_config`
Fixtures returning a synthetic earlier partition, a synthetic later partition, and the small config.

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
