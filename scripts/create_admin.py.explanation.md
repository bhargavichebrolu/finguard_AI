# create_admin.py

Source: [scripts/create_admin.py](create_admin.py)

## A. File Purpose
Creates the first administrator on a development computer. It runs `main` from `app/commands/create_admin.py`, which holds all the logic.

## B. Why This File Exists
Accounts are created by administrators and there is no self-registration, so the first one needs another route; shipping a default password would be a security hole, so none exists. Until Phase 6 the logic lived here. It moved into the `app` package so that the API image, which does not contain `scripts/`, can create the first account on a deployed host. This file keeps the documented development command working.

## C. Dependencies
- **Libraries:** `sys`.
- **Internal modules:** `app.commands.create_admin`.
- **External services / database:** PostgreSQL, through `DATABASE_URL`.
- **Depended on by:** developers, `README.md` and `ENVIRONMENT_SETUP.md`.

## D. Every Function Explained

No functions of its own: it calls `main` from `app.commands.create_admin` and exits with its code.

## E. Classes Explained
None.

## F. Execution Flow
Import the command → run `main` → exit with 0 on success or 1 on refusal.

## G. Input and Output
Input: `--email`, and the password from `FINGUARD_ADMIN_PASSWORD` or a prompt that does not echo. Output: one administrator account.

## H. Important Technical Concepts
The password is never a command-line argument, because those appear in shell history and process lists.

## I. Example
```powershell
uv run --project backend python scripts/create_admin.py --email admin@example.com
```

## J. Maintenance Notes
Change behaviour in `app/commands/create_admin.py`, not here.

## K. Related Files
- [app/commands/create_admin.py](../backend/app/commands/create_admin.py.explanation.md): the command itself.
- [auth_service.py](../backend/app/services/auth_service.py.explanation.md): `create_user`.
