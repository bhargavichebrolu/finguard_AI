# common.py

Source: [backend/app/api/schemas/common.py](common.py)

## A. File Purpose
Defines the pagination parameters and base classes that the other schemas use.

## B. Why This File Exists
PRD 8.2 requires request and response schemas on all endpoints, and PRD 6.5 requires pagination. A shared definition means every list behaves the same way, with the same size limit.

## C. Dependencies
- **Libraries:** `fastapi`, `pydantic`, `typing`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** every schema and list route.

## D. Every Function Explained
No functions.

## E. Classes Explained

### `ApiModel`
Base for responses. `from_attributes` lets a schema read SQLAlchemy objects. `protected_namespaces=()` allows fields such as `model_score` and `model_version` without a pydantic warning. **Inheritance:** `BaseModel`.

### `Page`
A generic wrapper with `items`, `total`, `limit` and `offset`. **Inheritance:** `ApiModel`, `Generic`.

### `ErrorResponse`
The error format, used for OpenAPI documentation. **Inheritance:** `BaseModel`.

## F. Execution Flow
Imported at start-up. FastAPI uses these to validate and document.

## G. Input and Output
`Limit` and `Offset` validate query parameters. `Page` shapes list responses.

## H. Important Technical Concepts
- **`MAX_PAGE_SIZE`:** without a cap, a single request could ask for millions of rows.

## I. Example
```python
@router.get("", response_model=Page[UserView])
def list_all(limit: Limit = 50, offset: Offset = 0): ...
```

## J. Maintenance Notes
Increasing `MAX_PAGE_SIZE` affects memory use for every list route.

## K. Related Files
- [auth.py](auth.py.explanation.md): one set of schemas built on these.
