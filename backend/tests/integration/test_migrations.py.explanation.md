# test_migrations.py

Source: [backend/tests/integration/test_migrations.py](test_migrations.py)

## A. File Purpose
Tests the migrations and database rules against real PostgreSQL: the tables, the constraints, the application role's limits and the authentication method.

## B. Why This File Exists
PRD 9.2 requires migrations, foreign keys and validated data. Constraints only protect anything if the database really enforces them, and that cannot be shown with a mock or a different database engine.

## C. Dependencies
- **Libraries:** `pytest`, `alembic`, `sqlalchemy`.
- **Internal modules:** `app.core.config`, `app.database.base`, `app.models`, shared fixtures in `tests/conftest.py`.
- **External services / database:** PostgreSQL, through `TEST_DATABASE_URL`.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `_model_version`, `_transaction`, `_prediction`
- **Purpose:** build valid records, which a test then makes invalid in one specific way.
- **Parameters / types:** overrides as keywords, plus a `Transaction` for `_prediction`. **Returns / type:** an unsaved model object.
- **Internal processing:** merges overrides with valid values.
- **Error handling:** none needed. **Calls:** the model classes. **Used by:** the tests.

### `_store_parent`
- **Purpose:** save the model version and transaction a prediction needs.
- **Parameters / types:** `session`. **Returns / type:** `Transaction`.
- **Internal processing:** adds and flushes.
- **Error handling:** none needed. **Calls:** `_model_version`, `_transaction`. **Used by:** the prediction tests.

**Common to every test below:** failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them.

| Function | Proves |
|---|---|
| `test_every_model_table_exists_after_upgrade` | Migrations create all model tables. |
| `test_models_and_migrations_agree` | `alembic check` finds no difference between the models and the migrated schema. |
| `test_downgrade_removes_all_tables_and_upgrade_restores_them` | The migration works in both directions. |
| `test_transaction_table_has_no_balance_or_account_columns` | The leaky PaySim columns cannot be stored. |
| `test_predictions_table_has_model_score_and_no_probability` | The score column has the required name, and the version and threshold are recorded. |
| `test_transaction_constraints_refuse_invalid_rows` | Bad amounts, steps, types and destination combinations are refused by the database itself. |
| `test_prediction_constraints_refuse_contradictions` | A score out of range, a calibration claim, a decision that contradicts the threshold, and a Low level on a flag are all refused. |
| `test_score_exactly_at_the_threshold_must_be_flagged` | At the threshold counts as flagged, matching `>=` in the model code. |
| `test_foreign_keys_are_enforced` | A prediction cannot point at a missing transaction. |
| `test_only_one_model_can_be_active` | The partial unique index works. |
| `test_one_prediction_per_transaction` | A transaction cannot have two predictions. |
| `test_emails_are_unique` | Duplicate accounts are refused. |
| `test_test_database_guard_refuses_other_names` | The safety check blocks a non-test database. |
| `test_truncate_helper_empties_tables` | The clean-up used between tests works. |
| `test_application_role_is_not_a_superuser` | The API's role has no administrative rights. |
| `test_connections_use_scram_authentication` | The connection authenticated with SCRAM, which `trust` would not show. |
| `test_alembic_ini_contains_no_database_address` | No connection address is kept in that file. |
| `test_settings_point_at_the_test_database_during_tests` | Tests can never reach the development database, even though `.env` names it. |

## E. Classes Explained
None.

## F. Execution Flow
`db_engine` migrates the test database, and `db_session` empties it before each test that uses it.

## G. Input and Output
Input: the test database. Output: pass or fail.

## H. Important Technical Concepts
- **`match=` names the constraint,** so a test cannot pass because some other rule happened to fire.
- **`flush` rather than `commit`:** it sends the SQL, which triggers constraints, and the session discards it afterwards.

## I. Example
```powershell
docker compose up -d --wait db
uv run --project backend pytest backend/tests/integration/test_migrations.py
```

## J. Maintenance Notes
A new constraint needs a case here. The downgrade test changes the schema temporarily, so these tests must not run in parallel with others on the same database.

## K. Related Files
- [records.py](../../app/models/records.py.explanation.md): the rules tested.
- [the initial migration](../../migrations/versions/20261107_0001_initial_schema.py.explanation.md): what creates them.
