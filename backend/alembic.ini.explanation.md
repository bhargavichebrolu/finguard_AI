# alembic.ini

Source: [backend/alembic.ini](alembic.ini)

## A. File Purpose
Tells Alembic where the migrations are, how to name them and how to log.

## B. Why This File Exists
PRD 9.2 requires Alembic migrations, and Alembic needs this file to find its scripts. The usual `sqlalchemy.url` line is missing on purpose, so no credential can end up here.

## C. Dependencies
- **Libraries / tools:** `alembic`.
- **Internal files:** `migrations/`.
- **External services / database:** none directly.
- **Depended on by:** every `alembic` command, the `migrate` service and the test fixtures.

## D. Every Function Explained
No functions. The settings:

### `script_location`
The migrations folder, relative to where the command runs, which must be `backend/`.

### `file_template`
Names files by date, revision and description, so they sort in order.

### `prepend_sys_path`
Puts `backend/` on the import path, so `migrations/env.py` can import `app`.

### `path_separator`
How multiple paths in this file are separated. Setting it avoids a deprecation warning.

### Logging sections
Keep SQL output quiet and show Alembic's progress.

## E. Classes Explained
None.

## F. Execution Flow
Alembic reads this file, then runs `migrations/env.py`.

## G. Input and Output
Not applicable.

## H. Important Technical Concepts
- **`%%` in the template:** this file format treats `%` as special, so a literal one is doubled.

## I. Example
```powershell
cd backend
uv run alembic upgrade head
```

## J. Maintenance Notes
Never add `sqlalchemy.url`. Set `DATABASE_URL` in the environment or `.env`.

## K. Related Files
- [env.py](migrations/env.py.explanation.md): supplies the database address.
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md): the resulting schema.
