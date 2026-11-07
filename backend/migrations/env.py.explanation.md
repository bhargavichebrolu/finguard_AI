# env.py

Source: [backend/migrations/env.py](env.py)

## A. File Purpose
Connects Alembic to the database and to the application's table definitions.

## B. Why This File Exists
Alembic runs this script for every command. It is the one place where migrations get their connection, and it reuses the application's settings, so credentials stay in the environment.

## C. Dependencies
- **Libraries:** `alembic`, `sqlalchemy`.
- **Internal modules:** `app.core.config`, `app.database.base`, `app.models.records`.
- **External services / database:** PostgreSQL.
- **Depended on by:** every `alembic` command.

## D. Every Function Explained

### `run_migrations_online`
- **Purpose:** run pending migrations.
- **Parameters / types:** none. **Returns / type:** `None`.
- **Internal processing:** opens a connection, gives Alembic the model metadata, and runs everything in one transaction. `compare_type=True` makes change detection notice column type differences.
- **Error handling:** an error rolls the transaction back, so a failed migration leaves the schema unchanged, because PostgreSQL can roll back schema changes.
- **Calls:** `get_settings`, `context.configure`, `context.run_migrations`. **Used by:** the module body.

## E. Classes Explained
None.

## F. Execution Flow
Alembic loads this file, it refuses offline mode, then it runs migrations online.

## G. Input and Output
Input: `DATABASE_URL`. Output: an upgraded schema, recorded in the `alembic_version` table.

## H. Important Technical Concepts
- **The `records` import has no visible use:** importing it is what registers the tables, hence the `noqa` comment.
- **Connection timeout:** without one, a connection attempt to an address that never answers can wait indefinitely. This happened during development with `localhost` on Windows.
- **No offline mode:** generating SQL scripts without a database is not used here, and refusing is clearer than producing an unchecked script.

## I. Example
```powershell
cd backend
uv run alembic check
```

## J. Maintenance Notes
A new model module must be imported here too, or Alembic will think its tables should be dropped.

## K. Related Files
- [alembic.ini](../alembic.ini.explanation.md): Alembic's settings.
- [records.py](../app/models/records.py.explanation.md): the tables.
