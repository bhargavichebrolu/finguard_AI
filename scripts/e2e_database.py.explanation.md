# e2e_database.py

Source: [scripts/e2e_database.py](e2e_database.py)

## A. File Purpose
Prepares and adjusts the browser-test database: reseeds it with one account per test role, and expires an account's sessions for the expiry test.

## B. Why This File Exists
Browser tests need known accounts with passwords nobody has written down, and must never touch development records. The script refuses any database whose name does not end in `_test`.

## C. Dependencies
- **Libraries:** SQLAlchemy, python-dotenv.
- **Internal modules:** `app.models.records`, `app.services.auth_service.create_user`.
- **External services / database:** PostgreSQL at `TEST_DATABASE_URL`.
- **Depended on by:** `frontend/tests/e2e/global-setup.ts`, `auth.spec.ts` through `support.ts`.

## D. Every Function Explained

### `test_database_url`
Reads `TEST_DATABASE_URL` from the environment or `.env` and refuses a name not ending in `_test`.

### `configure_settings`
Points the application settings at the test database before any app module reads them.

### `email_for`
The account's address on `e2e.example.com`, a domain the API's email validation accepts.

### `seed`
- **Purpose:** reset the test data.
- **Parameters / types:** `url`, `out: Path`. **Returns / type:** exit code.
- **Internal processing:** checks the browser-test API has registered the frozen model; empties every application table except `model_versions`; creates the accounts with `secrets.token_urlsafe` passwords through the normal service; writes them to `out`.
- **Error handling:** stops with an instruction if the model row is missing, which happens after the backend test suite empties the database. **Calls:** `create_user`. **Used by:** global setup.

### `expire_sessions`
Sets the account's live sessions to have expired a minute ago.

### `main`
Parses the `seed` and `expire-sessions` commands.

## E. Classes Explained
None.

## F. Execution Flow
Command line, then the database.

## G. Input and Output
Input: `TEST_DATABASE_URL`. Output: `frontend/.e2e/accounts.json` (Git-ignored) and one line naming how many accounts were seeded. Passwords are never printed.

## H. Important Technical Concepts
- **`ACCOUNTS`** maps test names to roles. Disruptive tests get their own accounts.

## I. Example
```powershell
python scripts/e2e_database.py seed --out frontend/.e2e/accounts.json
```

## J. Maintenance Notes
Never remove the `_test` check.

## K. Related Files
- [e2e_stack.py](e2e_stack.py.explanation.md): starts the API.
