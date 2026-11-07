# generate_env.py

Source: [scripts/generate_env.py](generate_env.py)

## A. File Purpose
Creates a local `.env` with newly generated secrets, from the `.env.example` template.

## B. Why This File Exists
Secrets typed by hand tend to be weak and tend to get reused. This gives every developer unique, strong values in one command, and none are displayed or committed.

## C. Dependencies
- **Libraries:** `argparse`, `secrets`, `subprocess`, `sys`, `pathlib` (standard library).
- **Internal modules:** none. Reads `.env.example`.
- **External services / database:** the `git` command.
- **Depended on by:** developers, `ENVIRONMENT_SETUP.md`, and `test_scripts.py`.

## D. Every Function Explained

### `is_git_ignored`
- **Purpose:** confirm Git will not track the file before secrets are written to it.
- **Parameters / types:** `path: Path`, `root: Path`. **Returns / type:** `bool`.
- **Internal processing:** runs `git check-ignore -q` and reads the exit code.
- **Error handling:** any non-zero exit counts as not ignored, which fails safely.
- **Calls:** `subprocess.run`. **Used by:** `main`.

### `render_env`
- **Purpose:** fill the template with new values.
- **Parameters / types:** `template: str`, `host_port: int`, `api_port: int`. **Returns / type:** `str`.
- **Internal processing:** generates hexadecimal passwords, which are safe in URLs, and a URL-safe signing key. It replaces only named variables and leaves comments alone. Both connection URLs share the same application password.
- **Error handling:** none needed.
- **Calls:** `secrets`. **Used by:** `main`, tests.

### `main`
- **Purpose:** command-line entry point.
- **Parameters / types:** `--db-port`, `--api-port`. **Returns / type:** `int`, 0 on success and 1 on refusal.
- **Internal processing:** refuses to overwrite an existing `.env`, refuses if Git would track it, then writes with LF endings.
- **Error handling:** refusals print a reason without any secret.
- **Calls:** `is_git_ignored`, `render_env`. **Used by:** the `__main__` block.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments, run the two refusal checks, read the template, write `.env`, and print a message without any value.

## G. Input and Output
Input: `.env.example` and optional port numbers. Output: `.env`, plus one line of text.

## H. Important Technical Concepts
- **`secrets` rather than `random`:** `secrets` draws from the operating system's secure source, and `random` is predictable.
- **Refusing to overwrite:** replacing the database password in `.env` does not change it inside an existing volume, so overwriting would lock the application out.

## I. Example
```powershell
uv run --project backend python scripts/generate_env.py --api-port 8010
```

## J. Maintenance Notes
A new secret needs a placeholder in `.env.example` and an entry in `render_env`. To rotate database passwords, use `ALTER ROLE` first, then edit `.env`.

## K. Related Files
- [.env.example](../.env.example.explanation.md): the template.
- [docker-compose.yml](../docker-compose.yml.explanation.md): reads the result.
- [test_scripts.py](../docs/file-explanations/backend/tests/unit/test_scripts.py.explanation.md): tests.
