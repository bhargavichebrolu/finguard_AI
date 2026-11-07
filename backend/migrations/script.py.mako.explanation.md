# script.py.mako

Source: [backend/migrations/script.py.mako](script.py.mako)

## A. File Purpose
The template Alembic fills in when creating a new migration file.

## B. Why This File Exists
Alembic needs a template to generate migrations. This one keeps the standard structure: a description, revision identifiers, and `upgrade` and `downgrade` functions.

## C. Dependencies
- **Libraries / tools:** `alembic`, which uses the Mako template language.
- **Internal files:** none.
- **External services / database:** none.
- **Depended on by:** `alembic revision`.

## D. Every Function Explained
These appear in each generated file.

### `upgrade`
Moves the schema forward. Alembic fills it in from the differences it detects.

### `downgrade`
Reverses `upgrade`.

## E. Classes Explained
None.

## F. Execution Flow
`alembic revision` substitutes the `${...}` values and writes a file to `migrations/versions/`.

## G. Input and Output
Input: the revision details. Output: a Python migration file.

## H. Important Technical Concepts
- **Generated migrations must be read.** Autogenerate can miss things, such as some CHECK constraint changes, so each one needs reviewing before use.

## I. Example
```powershell
cd backend
uv run alembic revision --autogenerate -m "add example column"
```

## J. Maintenance Notes
Changing this template affects only future migrations.

## K. Related Files
- [env.py](env.py.explanation.md): runs the migrations.
- [the initial migration](versions/20261107_0001_initial_schema.py.explanation.md): an example of the result.
