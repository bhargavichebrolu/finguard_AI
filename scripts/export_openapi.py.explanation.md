# export_openapi.py

Source: [scripts/export_openapi.py](export_openapi.py)

## A. File Purpose
Writes the API's OpenAPI schema to `frontend/openapi.json`, which the frontend's TypeScript types are generated from.

## B. Why This File Exists
The frontend must agree with the API about every field. Generating types from the API's own schema, and failing a test when the saved schema falls behind, means a backend change cannot silently break the interface.

## C. Dependencies
- **Libraries:** `argparse`, `json`, `sys`, `pathlib`.
- **Internal modules:** `app.main`, imported inside `current_schema`.
- **External services / database:** none. Building the schema does not start the application or connect to the database.
- **Depended on by:** the frontend's `gen:api` script, and `test_scripts.py`.

## D. Every Function Explained

### `current_schema`
Builds the application and returns `app.openapi()`.

### `render`
Formats the schema as indented JSON with sorted keys and a final newline, so regenerating changes the file only when the API changes.

### `main`
Writes the file, or with `--check` returns 1 if the saved file differs from the current API.

### `use_placeholder_settings`
When there is no `.env` (a clean clone or CI), sets a throwaway `DATABASE_URL` and a random `SECRET_KEY` for this process only, so the app's settings load. Building the schema connects to nothing. Existing values are never replaced. Added in Phase 5 M1, when the clean-clone check found `--check` could not run without `.env`.

## E. Classes Explained
None.

## F. Execution Flow
Import the application, generate the schema, then write or compare.

## G. Input and Output
Input: the backend code. Output: `frontend/openapi.json`.

## H. Important Technical Concepts
- **Two-step contract:** `export_openapi.py` keeps the schema in step with the API, and `npm run gen:api` keeps `src/types/api.generated.ts` in step with the schema. Each step has a check test.

## I. Example
```powershell
uv run --project backend python scripts/export_openapi.py
cd frontend; npm run gen:api
```

## J. Maintenance Notes
After any route or schema change, run both commands and commit the results with the change.

## K. Related Files
- [test_scripts.py](../docs/file-explanations/backend/tests/unit/test_scripts.py.explanation.md): the check test.
- `frontend/src/types/api.generated.ts`: generated from the schema.
