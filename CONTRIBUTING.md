# Contributing

## Workflow for any source change

The PRD's documentation synchronisation rule (section 12.2) is mandatory.

1. Create or modify the source or configuration file.
2. In the same change, create or update its explanation document. See the next section for where it lives.
3. Confirm the explanation matches the implementation.
4. Run the relevant tests.
5. Update [PROJECT_CONNECTIONS.md](PROJECT_CONNECTIONS.md) if system connections changed.

Before committing:

```powershell
uv run --project backend ruff check backend scripts --config backend/pyproject.toml
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml --deselect tests/integration/test_real_models.py::test_test_results_can_be_recalculated_from_the_saved_model
uv run --project backend python scripts/check_explanations.py
```

For frontend changes, also run `npm run typecheck`, `npm test` and `npm run build` in `frontend/`, and the browser tests (`npm run test:e2e`, see [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md#browser-tests)) when a change affects pages, layout, sessions or permissions. Fix accessibility violations in the code; never disable an axe rule to pass.

CI (`.github/workflows/ci.yml`, Phase 5) repeats the clean-checkout checks after a push, but it cannot run the API, browser or real-model tests, because the model binary is not in Git. Run those locally before committing. If a change makes tests skip or run differently on a clean checkout, update `.github/expected-tests.json` with `scripts/check_test_run.py --update` from a fresh clone and explain the change; never edit it to make CI pass ([TESTING_GUIDE.md](TESTING_GUIDE.md#continuous-integration-phase-5-m8)).

## Where explanation documents live

The project has two locations, by decision ([ADR 0001](docs/decisions/0001-phase-1-decisions.md), [ADR 0003](docs/decisions/0003-phase-3-decisions.md)):

| Files | Document location | Example |
|---|---|---|
| Created in Phase 1 or 2 | Mirrored under `docs/file-explanations/` | `docs/file-explanations/backend/app/ml/features.py.explanation.md` |
| Created from Phase 3 onward | Beside the file | `backend/app/main.py.explanation.md` |

- **Editing an existing file:** update its document wherever it already is. Do not move a document.
- **Creating a file:** put its document beside it.
- **The checker accepts either location, but not both.** It reports a file documented twice, a document whose file is gone, and a document Git would ignore. It covers Python, TypeScript, CSS, SQL and migration templates, plus the configuration files listed in `SOURCE_FILES` in `scripts/check_explanations.py`.
- **Moving the 61 Phase 1 and 2 documents was considered and declined** on 2026-11-08, because it adds no information and churns history.

The checker verifies documents exist, contain sections A to K, and name every function, and that relative links resolve. It cannot judge whether an explanation is correct: reviewers do that.

## Explanation document sections

A. File Purpose, B. Why This File Exists, C. Dependencies, D. Every Function Explained, E. Classes Explained, F. Execution Flow, G. Input and Output, H. Important Technical Concepts, I. Example, J. Maintenance Notes, K. Related Files. See PRD 12.1 for what each must contain.

## Rules that protect results

- Never fabricate or hand-edit a metric. Numbers in documents and in the UI come from saved outputs.
- Never add a target-derived or post-transaction feature. Add new features through `schema.py` and bump `FEATURE_SCHEMA_VERSION`.
- Never tune anything on the test partition.
- Never hardcode production statistics in the frontend.
- A dataset row is never dropped or relabelled silently. Report it.

## Commits

- Commit each completed milestone separately, with a meaningful message.
- Do not claim something is complete before verifying it, or push untested changes.
- The AI coding agent does not push to GitHub without explicit authorisation.

## Style

- Python: type annotations on public functions; `ruff` for lint.
- TypeScript: strict mode stays on.
- Comments explain why, not what.
- Add a dependency in the same change as the code that first uses it.
