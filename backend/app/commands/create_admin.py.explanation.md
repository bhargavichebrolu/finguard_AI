# create_admin.py

Source: [backend/app/commands/create_admin.py](create_admin.py)

## A. File Purpose
Creates an administrator account. The password comes from `FINGUARD_ADMIN_PASSWORD` or from a prompt that does not echo, and is never printed or stored in plain text.

## B. Why This File Exists
FinGuard has no self-registration, so the first account must be created by a command. Until Phase 6 that command lived only in `scripts/`, which the API image does not contain, so a deployed host had no way to create its first administrator. As part of the `app` package it ships in the image and runs inside the running container.

## C. Dependencies
- **Libraries:** `argparse`, `getpass`, `pydantic` (email validation).
- **Internal modules:** `app.services.auth_service.create_user` (Argon2id hash, audit entry), `app.database.session.session_scope`, the password length limits in `app.api.schemas.auth`.
- **External services / database:** the database named by `DATABASE_URL`.
- **Depended on by:** `scripts/create_admin.py` (development), the deployment instructions in `DEPLOYMENT.md`.

## D. Every Function Explained

### `read_password`
- **Purpose:** get the password without showing it.
- **Parameters / types:** none. **Returns / type:** `str`.
- **Internal processing:** `FINGUARD_ADMIN_PASSWORD` if set, otherwise `getpass.getpass`.
- **Error handling:** none; an empty value fails the length check in `main`.
- **Calls:** `os.environ.get`, `getpass.getpass`. **Used by:** `main`.

### `main`
- **Purpose:** validate the input and create the account.
- **Parameters / types:** `argv: list[str] | None` (tests pass a list). **Returns / type:** exit code `int`.
- **Internal processing:** validates the email, checks the password length, then calls `create_user` with the administrator role inside one transaction.
- **Error handling:** an invalid email, a wrong-length password or an existing account prints a message and returns 1; nothing is stored.
- **Calls:** `read_password`, `create_user`, `session_scope`. **Used by:** `python -m app.commands.create_admin`, `scripts/create_admin.py`.

## E. Classes Explained
None.

## F. Execution Flow
Parse `--email` → validate → read the password → open a session → create the user and its audit entry → commit → print the email only.

## G. Input and Output
Input: `--email`, and the password from the environment or the prompt. Output: one `users` row with an Argon2id hash, one audit entry, and a one-line message.

## H. Important Technical Concepts
- **`PASSWORD_VARIABLE`** lets automation pass the password without a terminal; it is read from the process environment only, never from a file in the repository.
- **Same rules as the API:** the password limits are imported from the API schema, so the command cannot create an account the sign-in form would refuse.

## I. Example
```powershell
docker compose -f docker-compose.prod.yml --env-file .env.production exec api python -m app.commands.create_admin --email admin@example.com
```

## J. Maintenance Notes
Keep it free of anything outside `app/`, so it keeps working inside the image.

## K. Related Files
- [scripts/create_admin.py](../../../scripts/create_admin.py.explanation.md): the development wrapper.
- [test_create_admin.py](../../tests/integration/test_create_admin.py.explanation.md): its tests.
- [auth_service.py](../services/auth_service.py.explanation.md): `create_user`.
