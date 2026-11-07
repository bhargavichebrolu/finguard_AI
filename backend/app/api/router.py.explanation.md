# router.py

Source: [backend/app/api/router.py](router.py)

## A. File Purpose
Combines all route modules into a single router that the application includes.

## B. Why This File Exists
PRD 8.1 separates API routing from everything else. A single list makes it easy to see what the API exposes.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** every module in `app/api/routes/`.
- **External services / database:** none.
- **Depended on by:** `app/main.py`.

## D. Every Function Explained
No functions. `api_router` is built when the module is imported.

## E. Classes Explained
None.

## F. Execution Flow
Importing this module imports each route module and includes its router.

## G. Input and Output
None at run time.

## H. Important Technical Concepts
- **Each route module sets its own prefix,** so reading one module shows its full paths.

## I. Example
```python
app.include_router(api_router)
```

## J. Maintenance Notes
A new route module must be added to this list. `test_every_api_route_requires_authentication` then covers it automatically.

## K. Related Files
- [main.py](../main.py.explanation.md): includes this router.
