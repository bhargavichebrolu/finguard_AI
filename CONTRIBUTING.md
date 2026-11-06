# Contributing

## Workflow for any source change

The PRD's documentation synchronisation rule (section 12.2) is mandatory.

1. Create or modify the source file.
2. In the same change, create or update `docs/file-explanations/<source path>.explanation.md`.
3. Confirm the explanation matches the implementation.
4. Run the relevant tests.
5. Update [PROJECT_CONNECTIONS.md](PROJECT_CONNECTIONS.md) if system connections changed.

Before committing:

```powershell
uv run --project backend ruff check backend scripts --config backend/pyproject.toml
uv run --project backend pytest backend/tests --rootdir backend -c backend/pyproject.toml
uv run --project backend python scripts/check_explanations.py
```

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
