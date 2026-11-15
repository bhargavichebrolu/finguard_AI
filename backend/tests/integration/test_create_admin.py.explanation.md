# test_create_admin.py

Source: [backend/tests/integration/test_create_admin.py](test_create_admin.py)

## A. File Purpose
Tests the administrator command against the real test database: it creates an audited administrator with a hashed password, never prints the password, refuses duplicates and refuses bad input without storing anything.

## B. Why This File Exists
Phase 6 moved the command into the API image so a deployed host can create its first account. It had no tests before; this is the only way into an empty production system, so its behaviour is checked directly.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy.
- **Internal modules:** `app.commands.create_admin`, `app.security.passwords.verify_password`, `tests.conftest.empty_all_tables`.
- **External services / database:** `TEST_DATABASE_URL` (skipped without it, like every database test).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `empty`
Fixture: empties every table of the migrated test database and returns its engine.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_creates_an_administrator_without_printing_the_password` | An active administrator is stored with an Argon2id hash that verifies, an audit entry is written, and the output does not contain the password. |
| `test_refuses_a_second_account_with_the_same_email` | A second run with the same email fails and leaves one account. |
| `test_refuses_bad_input_and_stores_nothing` | An invalid email or a short password fails with a message, and no user is stored. |

## E. Classes Explained
None.

## F. Execution Flow
Each test empties the database, sets `FINGUARD_ADMIN_PASSWORD` with `monkeypatch`, calls `main` with arguments, and reads the database back.

## G. Input and Output
Input: email arguments and an environment password. Output: assertions on the exit code, the printed text and stored rows.

## H. Important Technical Concepts
- `DATABASE_URL` is set to the test database by `tests/conftest.py` before anything reads settings, so the command's own `session_scope` writes only there.
- `verify_password` takes the hash first, then the password.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_create_admin.py -q
```

## J. Maintenance Notes
If password rules change in `app.api.schemas.auth`, update the short-password case.

## K. Related Files
- [create_admin.py](../../app/commands/create_admin.py.explanation.md): the command.
