# ci.yml

Source: [.github/workflows/ci.yml](ci.yml)

## A. File Purpose
The GitHub Actions workflow (Phase 5 M8). On every push, pull request or manual run, it checks a clean checkout: backend lint, formatting and tests on a real PostgreSQL database, the skip comparison, the explanation checker, the API schema and model report checks, the secret scan, both dependency audits, and the frontend type check, unit tests and build.

## B. Why This File Exists
PRD sections 3.4 and 15 require GitHub Actions checks, and Phase 5 finding F5 recorded that there were none. The approved decision D6-A runs every test that does not need the model binary or dataset (neither is in Git), and fails when the skipped set differs from a committed list.

**It has not run on GitHub.** The workflow runs only once it is pushed, and pushing needs the owner's permission. Until then, every command in it has been run locally on a fresh clone (TESTING_GUIDE.md, "Continuous integration (Phase 5 M8)"). No GitHub result is claimed.

## C. Dependencies
- **Actions:** `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.3.3 and `actions/setup-node` v7.1.0, each pinned to a full commit hash so a moved tag cannot change what runs.
- **Tools:** uv 0.11.3 with Python 3.11, Node.js 24.22.1, Docker Compose (preinstalled on the runner).
- **Internal files:** `docker-compose.yml` (the same pinned PostgreSQL image and role setup as local development), `scripts/generate_env.py`, `scripts/check_test_run.py`, `.github/expected-tests.json`, and the checks listed in A.
- **Depended on by:** nothing; it is the top of the chain.

## D. Every Function Explained
No functions. Two jobs run in parallel:

### Job `backend`
1. Full-history checkout (`fetch-depth: 0`, for the secret scan), with the token not stored in Git's configuration.
2. Install uv and Python 3.11, caching on `backend/uv.lock`.
3. Fail if `.env`, the model binary or the raw dataset is in the checkout (the same list as `verify_clean_clone.py`).
4. `uv sync --frozen`: install exactly the lockfile.
5. `generate_env.py` writes a `.env` with new random passwords (never printed), then `docker compose up -d --wait db` starts PostgreSQL with SCRAM authentication, the non-superuser application role and `finguard_test`.
6. `ruff check` and `ruff format --check`, with the same scopes as TESTING_GUIDE.md.
7. pytest with JUnit output, deselecting the test-partition check as every run has since Phase 3.
8. `check_test_run.py backend`: compares skips with the list, writes the job summary.
9. Explanation checker, `export_openapi.py --check`, `export_model_report.py --check`, `scan_secrets.py`, `pip-audit`.
10. `docker compose down --volumes`, always.

### Job `frontend`
`npm ci`, `npm run typecheck`, Vitest with a JUnit report, `check_test_run.py frontend` (no skips allowed, at least the recorded number passing), `npm run build`, `npm audit`.

## E. Classes Explained
None.

## F. Execution Flow
Each step after the tests carries `if: ${{ !cancelled() }}`, so one failure still lets the other checks report; the job fails if any step failed. `concurrency` cancels an older run of the same branch.

## G. Input and Output
Input: the pushed commit. Output: pass or fail per job, and a summary on the run page with test totals, skip reasons and the plain statement that real-model inference was not verified.

## H. Important Technical Concepts
- **What CI does not verify:** real-model inference, all API tests (the application checks the frozen model at start-up, so they skip), browser tests and the HTTPS stack. These run locally before each commit. The summary says so on every run.
- **Least privilege:** `permissions: contents: read`, no repository secrets, `persist-credentials: false`. The database password exists only on the runner, for one run.
- **No `trust` authentication:** the database is started the same way as locally, with SCRAM from initialisation.
- **Pinned everything:** actions by hash, uv and Node by exact version, PostgreSQL by image digest, dependencies by lockfile.

## I. Example
After a push, open the run under the repository's Actions tab. The "Compare skipped tests" step's summary lists, for example, "Skipped 289: frozen model file is absent".

## J. Maintenance Notes
- A change that makes tests skip or run differently on a clean checkout needs the expectations updated with `check_test_run.py --update` on a fresh clone, and the diff reviewed.
- When an action is updated, change the hash and the version comment together; `test_ci.py` refuses unpinned actions.
- If the model binary is later published (PLAN option D6-B, Phase 6), a download step with the pinned hash would let the API tests run here.

## K. Related Files
- [expected-tests.json](../expected-tests.json.explanation.md): the expected skips and counts.
- [check_test_run.py](../../scripts/check_test_run.py.explanation.md): the comparison.
- [test_ci.py](../../backend/tests/unit/test_ci.py.explanation.md): checks on this file.
- [TESTING_GUIDE.md](../../TESTING_GUIDE.md): commands and the local rehearsal results.
