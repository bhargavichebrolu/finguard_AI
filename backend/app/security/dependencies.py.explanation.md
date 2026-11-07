# dependencies.py

Source: [backend/app/security/dependencies.py](dependencies.py)

## A. File Purpose
Provides the FastAPI dependencies routes use to identify the caller, check permissions, apply rate limits and reach the model.

## B. Why This File Exists
Each protected route should state what it requires in one line, and the checks should be written once.

## C. Dependencies
- **Libraries:** `fastapi`, `sqlalchemy`.
- **Internal modules:** `app.core.errors`, `app.core.rate_limit`, `app.database.session`, `app.models.records`, `app.security.permissions`, `app.security.tokens`, `app.services.model_service`.
- **External services / database:** reads `users`.
- **Depended on by:** all protected routes.

## D. Every Function Explained

### `get_current_user`
- **Purpose:** identify the caller.
- **Parameters / types:** `db`, `token: str | None`. **Returns / type:** `User`.
- **Internal processing:** verifies the token, loads the user, and checks they are active and that the token version is current.
- **Error handling:** every failure raises the same `AuthenticationError`.
- **Calls:** `decode_access_token`. **Used by:** `check`, routes through `CurrentUser`.

### `require_permission`
- **Purpose:** build a permission check.
- **Parameters / types:** `permission: Permission`. **Returns / type:** a dependency.
- **Internal processing:** the inner `check` calls `has_permission`.
- **Error handling:** raises `PermissionDeniedError`.
- **Calls:** `has_permission`. **Used by:** routes.

### `check`
The inner function of `require_permission` and of `rate_limited`, which FastAPI calls for each request.

### `rate_limited`
- **Purpose:** combine a permission check with a per-user limit.
- **Parameters / types:** `permission`, `bucket: str`, `per_minute: Callable[[], int]`. **Returns / type:** a dependency.
- **Internal processing:** checks the permission first, so unauthorised calls do not use up the limit. `per_minute` is a function, so the setting is read when a request arrives.
- **Error handling:** `RateLimitedError` from `limiter.hit`.
- **Calls:** `require_permission`, `limiter.hit`. **Used by:** predict and upload routes.

### `get_serving_model`
Returns `request.app.state.model`, set during start-up.

## E. Classes Explained
None. `DbSession`, `CurrentUser` and `ServingModelDep` are annotated type aliases that shorten route signatures.

## F. Execution Flow
Token, user, permission, rate limit, then the route.

## G. Input and Output
Input: the `Authorization` header. Output: a `User`, or a 401, 403 or 429 response.

## H. Important Technical Concepts
- **`auto_error=False`:** FastAPI's default would produce its own error format, and this keeps the project's format.
- **401 versus 403:** 401 means the caller's identity is not established, and 403 means it is but the role does not allow the action.
- **Swagger:** `tokenUrl` powers the Authorize button in `/docs`.

## I. Example
```python
@router.patch("/settings")
def update(user: Annotated[User, Depends(require_permission(Permission.UPDATE_SETTINGS))]): ...
```

## J. Maintenance Notes
Every new route except `/health` and login must use one of these. `test_every_api_route_requires_authentication` enforces this automatically.

## K. Related Files
- [permissions.py](permissions.py.explanation.md): the role table.
- [tokens.py](tokens.py.explanation.md): token checks.
