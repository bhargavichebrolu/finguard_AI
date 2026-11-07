# 20261107_0001_initial_schema.py

Source: [backend/migrations/versions/20261107_0001_initial_schema.py](20261107_0001_initial_schema.py)

## A. File Purpose
Creates all twelve application tables with their constraints and indexes, and removes them on downgrade.

## B. Why This File Exists
PRD 9.2 requires controlled schema changes through Alembic. This is the starting point every later migration builds on.

## C. Dependencies
- **Libraries:** `alembic`, `sqlalchemy`.
- **Internal modules:** none at run time. It was generated from `app/models/records.py`, but is deliberately independent of it, so later model changes cannot alter what this migration does.
- **External services / database:** PostgreSQL.
- **Depended on by:** `alembic upgrade head`, the `migrate` service and the test fixtures.

## D. Every Function Explained

### `upgrade`
- **Purpose:** create the schema.
- **Parameters / types:** none. **Returns / type:** `None`.
- **Internal processing:** creates tables in dependency order, so referenced tables exist first, then adds indexes, including the partial index allowing one active model.
- **Error handling:** runs in one transaction, so a failure leaves nothing behind.
- **Calls:** `op.create_table`, `op.create_index`. **Used by:** Alembic.

### `downgrade`
- **Purpose:** remove the schema.
- **Parameters / types:** none. **Returns / type:** `None`.
- **Internal processing:** drops indexes and tables in reverse order.
- **Error handling:** as above. **This deletes all application data.**
- **Calls:** `op.drop_index`, `op.drop_table`. **Used by:** Alembic.

## E. Classes Explained
None.

## F. Execution Flow
Alembic compares `alembic_version` with this revision (`0001`), and runs `upgrade` if needed.

## G. Input and Output
Input: an empty schema. Output: the tables listed in `DATABASE_SCHEMA.md`.

## H. Important Technical Concepts
- **Generated, then reviewed:** it came from `alembic revision --autogenerate`, and the CHECK constraints and partial index were confirmed present. `test_migrations.py` confirms the result matches the models and that the constraints work.
- **Never edit an applied migration.** Add a new one instead.

## I. Example
```powershell
cd backend
uv run alembic upgrade head
```

## J. Maintenance Notes
This is safe to edit only until the schema has been deployed anywhere that matters. Nothing has been deployed so far.

## K. Related Files
- [records.py](../../app/models/records.py.explanation.md): the models it was generated from.
- [test_migrations.py](../../tests/integration/test_migrations.py.explanation.md): its tests.
