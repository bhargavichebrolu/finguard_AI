# errors.py

Source: [backend/app/core/errors.py](errors.py)

## A. File Purpose
Defines the application's error types, and converts every failure into a JSON response with a safe message.

## B. Why This File Exists
PRD section 10 requires safe error responses. Services can raise a meaningful error without knowing about HTTP, and clients always get the same format.

## C. Dependencies
- **Libraries:** `fastapi`, `starlette`, `logging`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** services, security dependencies, `app/main.py`.

## D. Every Function Explained

### `_request_id`
- **Purpose:** read the request's ID, if the middleware set one.
- **Parameters / types:** `request: Request`. **Returns / type:** `str | None`.
- **Internal processing:** reads `request.state`.
- **Error handling:** returns `None` when absent.
- **Calls:** none. **Used by:** every handler.

### `_safe_validation_errors`
- **Purpose:** remove submitted values from validation errors.
- **Parameters / types:** `error: RequestValidationError`. **Returns / type:** `list[dict]`.
- **Internal processing:** keeps location, message and type. FastAPI's default response echoes the input, which would repeat a rejected password back to the client and into any logs that record responses.
- **Error handling:** none needed.
- **Calls:** none. **Used by:** `handle_validation_error`.

### `register_exception_handlers`
- **Purpose:** attach all the handlers to the application.
- **Parameters / types:** `app: FastAPI`. **Returns / type:** `None`.
- **Internal processing:** registers the four nested handlers below.
- **Error handling:** this is the error handling.
- **Calls:** `app.exception_handler`. **Used by:** `app/main.py`.

### `handle_app_error`
Returns the error's own status, message and headers.

### `handle_validation_error`
Returns 422 with the sanitised list.

### `handle_http_error`
Gives framework errors such as an unknown route the same format.

### `handle_unexpected_error`
Logs the full traceback on the server, and returns only "Internal server error." with the request ID, which links a client's report to the log entry.

### `is_connection_error`
True when a database error means the database could not be reached: SQLAlchemy marked the connection invalidated, or the error happened while connecting (no statement). A statement timeout or deadlock is not an outage (Phase 5 M7).

### `handle_database_error`
Answers a connection error with 503, the message in `DATABASE_UNAVAILABLE_MESSAGE` and `Retry-After: 5`, logging only the driver error's type, since its message can name the host and role. Other database errors go to `_unexpected`.

### `_unexpected`
Logs an error with its trace on the server and answers 500 `Internal server error.` with the request ID.

## E. Classes Explained
### `ScoringError`
The model failed while scoring: 500 with "The model could not score this transaction, so nothing was stored. Give an administrator the reference below." (Phase 5 M7)


### `AppError`
- **Purpose:** base for expected failures. **Attributes:** `status_code`, `message`, `headers`. **Methods:** `__init__`. **Inheritance:** `Exception`.

### `NotFoundError`, `ConflictError`, `PermissionDeniedError`, `InvalidInputError`, `PayloadTooLargeError`
Each sets its own `status_code`: 404, 409, 403, 422 and 413.

### `AuthenticationError`
401, with a default message and the `WWW-Authenticate` header. The same message covers every cause, so a caller cannot tell a bad token from a deleted account.

### `RateLimitedError`
429, with a `Retry-After` header.

## F. Execution Flow
A service raises an error, FastAPI finds the matching handler, and the handler returns JSON.

## G. Input and Output
Input: an exception. Output: `{"detail": ..., "request_id": ...}`, plus `errors` for validation failures.

## H. Important Technical Concepts
- **Database outages (Phase 5 M7):** measured, not assumed: a closed port, a database refusing connections and a connection ended mid-session all raise `OperationalError` with no statement or with `connection_invalidated`; a statement timeout raises one with a statement. Only the first group becomes 503.
- **`AppError` messages are written to be shown.** Anything else becomes a generic 500, so a database error message cannot reach a client.
- **404 rather than 403 for hidden records:** demo users get "not found" for records outside their scope, which does not reveal that those records exist.

## I. Example
```python
raise ConflictError("A transaction with this identifier already exists.")
```

## J. Maintenance Notes
Add a new error type here rather than raising `HTTPException` from a service. Never put a submitted value or internal detail in a message.

## K. Related Files
- [main.py](../main.py.explanation.md): registers these handlers.
- [logging.py](logging.py.explanation.md): writes the server-side record.
