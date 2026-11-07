# create_admin.py

Source: [scripts/create_admin.py](create_admin.py)

## A. File Purpose
Creates the first administrator account.

## B. Why This File Exists
Accounts are created by administrators and there is no self-registration, so the first one needs another route. Shipping a default password would be a security hole, so none exists.

## C. Dependencies
- **Libraries:** `argparse`, `getpass`, `os`, `sys`, `pydantic`.
- **Internal modules:** `app.api.schemas.auth`, `app.core.errors`, `app.database.session`, `app.models.enums`, `app.services.auth_service`.
- **External services / database:** PostgreSQL, through `DATABASE_URL`.
- **Depended on by:** developers, and `ENVIRONMENT_SETUP.md`.

## D. Every Function Explained

### `read_password`
- **Purpose:** get the password privately.
- **Parameters / types:** none. **Returns / type:** `str`.
- **Internal processing:** uses `FINGUARD_ADMIN_PASSWORD` if set, otherwise a prompt that does not echo. It is not a command-line argument, because those appear in shell history and process lists.
- **Error handling:** none needed. **Calls:** `getpass.getpass`. **Used by:** `main`.

### `main`
- **Purpose:** command-line entry point.
- **Parameters / types:** `--email`. **Returns / type:** `int`, 0 on success and 1 on refusal.
- **Internal processing:** validates the email and password length with the same rules as the API, then creates the account.
- **Error handling:** an existing email prints a message and returns 1. The password is never printed.
- **Calls:** `read_password`, `create_user`. **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse the email, read the password, validate, create the account.

## G. Input and Output
Input: an email and a password. Output: one `users` row, one audit entry and one line of text.

## H. Important Technical Concepts
- **Runs on the host:** it uses the `.env` database address. Migrations must have run first.

## I. Example
```powershell
uv run --project backend python scripts/create_admin.py --email admin@example.com
```

## J. Maintenance Notes
Further accounts should be created through `POST /api/v1/users`.

## K. Related Files
- [auth_service.py](../backend/app/services/auth_service.py.explanation.md): `create_user`.
