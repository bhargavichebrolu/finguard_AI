# generate_production_env.py

Source: [scripts/generate_production_env.py](generate_production_env.py)

## A. File Purpose
Creates `.env.production` for `docker-compose.prod.yml`: new random database passwords and signing key, plus the site's domain, certificate mode, ports, bind address and model folder. It never overwrites an existing file and never prints a secret.

## B. Why This File Exists
Production secrets must come from the environment, not from committed files (PRD 10). Generating them avoids weak hand-typed values, and checking the inputs now gives a clear message instead of a failed start later.

## C. Dependencies
- **Libraries:** `argparse`, `secrets`, `re`, `subprocess` (for `git check-ignore`).
- **Internal modules:** none; it runs with any Python 3.11, without the backend environment.
- **External services / database:** Git, when the output is inside the repository.
- **Depended on by:** `DEPLOYMENT.md`, the CI `images` job, `test_deployment.py`.

## D. Every Function Explained

### `public_origin`
Returns `https://domain`, adding `:port` only when the HTTPS port is not 443. This becomes `CORS_ALLOWED_ORIGINS`, which the CSRF check compares with each request's `Origin`.

### `check_inputs`
- **Purpose:** refuse values that would fail later.
- **Parameters / types:** `domain: str`, `tls: str`. **Returns / type:** `None`.
- **Internal processing:** the domain must be a lower-case host name or IPv4 address, without a scheme, and not `localhost` (production refuses it). `--tls` must be `internal` or an email address.
- **Error handling:** raises `ValueError` with the reason.
- **Calls:** `re`. **Used by:** `main`.

### `render`
- **Purpose:** produce the file's text.
- **Parameters / types:** domain, TLS mode, ports, bind address, model folder. **Returns / type:** `str`.
- **Internal processing:** 24-byte hex passwords (safe in URLs) for the database administrator and the API's role, and a 48-byte URL-safe signing key, all from `secrets`.
- **Error handling:** none needed.
- **Calls:** `public_origin`. **Used by:** `main`, tests.

### `is_git_ignored`
Returns whether Git ignores a path, using `git check-ignore`.

### `main`
- **Purpose:** the command line.
- **Parameters / types:** `argv`. **Returns / type:** exit code `int`.
- **Internal processing:** checks inputs, refuses to overwrite, refuses a path inside the repository that Git would track, writes with LF endings.
- **Error handling:** returns 2 for bad input, 1 for an existing or tracked file.
- **Calls:** the functions above. **Used by:** people, CI.

## E. Classes Explained
None.

## F. Execution Flow
Parse arguments → check inputs → check the output path → render → write → print the origin only.

## G. Input and Output
Input: `--domain`, `--tls` and optional ports and paths. Output: `.env.production` (or `--output`).

## H. Important Technical Concepts
- **`internal` TLS** is for rehearsals on one computer; browsers do not trust it.
- **Passwords are fixed at first start:** the database volume keeps the passwords it was created with.

## I. Example
```powershell
python scripts/generate_production_env.py --domain finguard.example.com --tls ops@example.com
```

## J. Maintenance Notes
If `docker-compose.prod.yml` requires a new variable, add it to `render`; `test_deployment.py` fails until it is supplied.

## K. Related Files
- [docker-compose.prod.yml](../docker-compose.prod.yml.explanation.md)
- [generate_env.py](generate_env.py.explanation.md): the development equivalent.
