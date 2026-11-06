# ADR 0001: Phase 1 decisions

**Status:** accepted for Phase 1. Date: 2026-11-06.

Each entry records a choice the [PRD](../PRD.md) left open or an adaptation of it.

## 1. Explanation documents mirror the source tree
Section 12.1 names the `x.py.explanation.md` convention, and section 13 includes `docs/file-explanations/`. Documents therefore live at `docs/file-explanations/<source path>.explanation.md`. This keeps source folders uncluttered and avoids collisions between same-named files. `scripts/check_explanations.py` enforces the mapping.

## 2. Scope of the per-file rule
Covered: Python, TypeScript and CSS sources, including tests, plus `frontend/index.html`, `frontend/vite.config.ts` and the `Makefile`. Docstring-only `__init__.py` files are exempt, as they have no behaviour.

Documented centrally in [ENVIRONMENT_SETUP.md](../../ENVIRONMENT_SETUP.md) instead: declarative config (`pyproject.toml`, `package.json`, `tsconfig.json`, `.gitignore`, `.env.example`, `split_v1.json`). Section 12.2 explicitly exempts lockfiles and generated files; extending this to declarative config is a project judgement. Say so if you want them covered too.

## 3. One Python project for ML and backend
Feature code must be shared by training and serving, so `app/ml` lives inside the backend package and `scripts/` imports it. Dependency groups keep heavy training libraries out of the API image: `uv sync --no-default-groups` installs runtime dependencies only.

## 4. Python 3.11 with uv
3.11 has wheels for every library in the PRD's stack, confirmed by installing and importing all of them. `numba>=0.61` is pinned because the resolver otherwise backtracks to a version with no 3.11 build.

## 5. Features limited to the four prediction inputs
PRD 6.2 fixes the prediction input as amount, type, step and destination category. Features use only these, so training cannot depend on data serving lacks. Account history features were rejected because they need identifiers and an online store. The full list of rejections is in [DATASET_DOCUMENTATION.md](../../DATASET_DOCUMENTATION.md).

## 6. `destination_category` kept despite adding no information
In PaySim it is fully determined by type (merchant if and only if PAYMENT). The PRD requires it, so it stays. **Consequence for Phase 3:** combinations such as PAYMENT with a customer destination never occur in training, and the API must decide how to handle them. The current proposal is to reject them with a clear validation message.

## 7. Split by row share, snapped to whole steps
A 70/15/15 row split gives train steps 1 to 322, validation 323 to 377 and test 378 to 743. Boundaries use row counts only. The resulting base-rate shift is measured and reported rather than engineered away: see [ML_EXPERIMENTS.md](../../ML_EXPERIMENTS.md). Other row fractions were compared on row and fraud counts only, and all show the same shift.

## 8. EDA boundary, and an honest disclosure
Project EDA computes feature behaviour on training rows only. Later partitions contribute only volume and label counts.

**Disclosure:** before boundaries existed, a one-off throwaway profile of the whole file was run to understand its structure. It included fraud amount quantiles, the balance behaviour rates and the amount-cap counts across all rows, so those aggregates were seen for the test window too. No feature or threshold was tuned from them: the selected features follow directly from the PRD's inputs, and the rejected ones were rejected. The test set has not been used to evaluate any model.

## 9. Zero-amount rows retained
16 rows have amount 0, all labelled fraud. PRD 4.5 forbids silently discarding records, so they stay and are reported as a validation warning. Three are in the training partition. The current proposal for Phase 3 is that the API rejects amounts of 0 or less, since a zero-value request is not meaningful to assess.

## 10. Deferred structure items
These PRD 13 items are intentionally absent after Phase 1 because their phases have not started:

| Item | Phase | Note |
|---|---|---|
| `scripts/train_models.py`, `evaluate_models.py`, `export_metrics.py` | 2 | |
| `backend/app/main.py`, `alembic.ini`, migrations | 3 | |
| `docker-compose.yml`, `backend/Dockerfile` | 3 | Docker is not installed on the development machine. See below. |
| Frontend pages, tests | 4 | |
| `.github/workflows/ci.yml` | 5 | |
| `frontend/Dockerfile` | 6 | Only needed for self-hosting. |

**Docker:** Phase 3's acceptance criteria need PostgreSQL. Installing Docker Desktop or a local PostgreSQL will be required before then.

## 11. Frontend toolchain newer than first pinned
`npm audit` reported advisories against React Router 6 and Vite 5, fixed only in new major versions. No pages existed yet, so upgrading was free: React Router 7 and Vite 8, with `npm audit` now reporting 0 vulnerabilities. React stays on 18.

## 12. Added files beyond PRD 13
`scripts/prepare_dataset.py`, `run_eda.py`, `audit_leakage.py` and `check_explanations.py` give each pipeline stage and the documentation rule a command. Section 13 permits additions.
