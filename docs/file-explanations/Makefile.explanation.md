# Makefile

Source: [Makefile](../../Makefile)

## A. File Purpose
Gives short names to the project's setup, pipeline, test, lint and build commands.

## B. Why This File Exists
The PRD's repository structure requires it, and it gives every developer the same entry points. Each recipe is one plain command, so developers without `make` can copy it directly.

## C. Dependencies
- **Tools:** `make`, `uv`, `npm`, `docker compose`.
- **Internal files:** `scripts/*.py`, `backend/pyproject.toml`, `frontend/package.json`.
- **External services / database:** none.
- **Depended on by:** developers; CI may use it from Phase 5.

## D. Every Function Explained
A Makefile has targets rather than functions. Each takes no parameters and returns the exit code of its command; a failure stops the run.

| Target | Runs |
|---|---|
| `setup` | Installs Python and frontend dependencies. |
| `data` | `validate`, `prepare`, `eda`, `audit`, in that required order. |
| `validate` | `scripts/validate_dataset.py` |
| `prepare` | `scripts/prepare_dataset.py` |
| `eda` | `scripts/run_eda.py` |
| `audit` | `scripts/audit_leakage.py` |
| `drift`, `train`, `select`, `explain`, `diagnose`, `final-test`, `export` | The Phase 2 scripts of the same names. `final-test` must not be run again: the test partition has been used. |
| `env` | `scripts/generate_env.py`, with the API on port 8010. |
| `db-up` | Starts PostgreSQL and waits until it is healthy. |
| `stack` | Builds and starts the database, migrations and API. |
| `migrate` | `alembic upgrade head` on the host. |
| `serve` | Runs the API on the host, port 8010, with Uvicorn's own proxy trust turned off. |
| `admin` | Creates the first administrator: `make admin EMAIL=you@example.com`. |
| `test` | The whole backend test suite. |
| `test-phase3` | The suite without the one test that rereads the test partition. |
| `test-fast` | All tests except those needing real data or a database. |
| `lint` | `ruff check` on `backend` and `scripts`. |
| `docs-check` | `scripts/check_explanations.py` |
| `frontend-build` | Type-checks and builds the frontend. |

## E. Classes Explained
None.

## F. Execution Flow
`make data` runs each stage in order and stops at the first failure, so an invalid dataset never reaches later stages.

## G. Input and Output
Input: a target name. Output: whatever the underlying command produces.

## H. Important Technical Concepts
`.PHONY` marks targets as commands rather than files. **`make` is not installed on the development machine, so this file itself has not been executed.** The commands inside it have each been run directly.

## I. Example
```bash
make data
make test-fast
```

## J. Maintenance Notes
Keep recipes as single commands that can be pasted. Recipes with `cd backend &&` need a POSIX shell, which `make` provides.

## K. Related Files
- `ENVIRONMENT_SETUP.md` and `TESTING_GUIDE.md`: the same commands, written out.
- [validate_dataset.py](scripts/validate_dataset.py.explanation.md), [prepare_dataset.py](scripts/prepare_dataset.py.explanation.md), [run_eda.py](scripts/run_eda.py.explanation.md), [audit_leakage.py](scripts/audit_leakage.py.explanation.md): pipeline stages.
