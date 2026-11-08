# middleware.py

Source: [backend/app/core/middleware.py](middleware.py)

## A. File Purpose
Adds a request ID, one access log line, security headers and an early size limit to every HTTP request.

## B. Why This File Exists
These apply to all routes, so they should not be repeated in each. The size check also has to run before the framework parses a body, because parsing an upload happens before any route code runs.

## C. Dependencies
- **Libraries:** `starlette`, `json`, `logging`, `time`, `uuid`.
- **Internal modules:** `app.core.config`.
- **External services / database:** none.
- **Depended on by:** `app/main.py`.

## D. Every Function Explained

### `content_security_policy`
Returns the policy for a path. `/docs` and `/redoc` get `DOCS_CONTENT_SECURITY_POLICY`, which allows the CDN and inline start-up script they need. Everything else gets `API_CONTENT_SECURITY_POLICY`, which allows nothing to load.

### `_declared_size`
- **Purpose:** read the `Content-Length` header.
- **Parameters / types:** `scope: Scope`. **Returns / type:** `int | None`.
- **Internal processing:** searches the raw headers.
- **Error handling:** a malformed value returns `None`.
- **Calls:** none. **Used by:** `__call__`.

### `__init__`
Stores the wrapped application.

### `__call__`
- **Purpose:** handle one request.
- **Parameters / types:** the ASGI `scope`, `receive`, `send`. **Returns / type:** `None`.
- **Internal processing:** creates the ID and stores it where `request.state` reads it. It refuses requests over the limit, otherwise passes them on. It logs method, path, status and duration in `finally`, so failures are logged too.
- **Error handling:** exceptions continue to the error handlers.
- **Calls:** `_declared_size`, `_send_too_large`, `send_with_headers`. **Used by:** the ASGI server.

### `send_with_headers`
Nested. Adds headers when the response starts, and records the status for the log.

### `_send_too_large`
- **Purpose:** respond 413 without reading the body.
- **Parameters / types:** `send: Send`, `request_id: str`. **Returns / type:** `None`.
- **Internal processing:** sends a small JSON response.
- **Error handling:** none needed. **Calls:** `json.dumps`. **Used by:** `__call__`.

## E. Classes Explained

### `RequestContextMiddleware`
- **Purpose:** the middleware itself. **Attributes:** `app`. **Methods:** `__init__`, `__call__`. **Inheritance:** none; it follows the ASGI interface.

## F. Execution Flow
Request arrives, ID assigned, size checked, passed to the application, headers added to the response, one log line written.

## G. Input and Output
Input: ASGI messages. Output: the same messages plus headers, and one JSON log line.

## H. Important Technical Concepts
- **Plain ASGI, not `BaseHTTPMiddleware`:** the latter wraps responses in a way that has historically interfered with background tasks, which batch processing depends on.
- **`Cache-Control: no-store` on `/api/`:** responses can hold sensitive records, so they should not be cached.
- **Content Security Policy:** added in Phase 4. JSON responses get the strictest policy. The documentation pages need a CDN and inline script, so they get a narrower allowance. The frontend's own policy is served by the frontend.
- **Limitation:** the size check relies on `Content-Length`. A chunked upload without one is limited later, by the streaming check in the batch service, after the framework has spooled it to temporary storage.

## I. Example
Every response carries `x-request-id`, and errors repeat it as `request_id`.

## J. Maintenance Notes
Never read or log the body here. The allowance above `max_upload_bytes` covers multipart overhead.

## K. Related Files
- [main.py](../main.py.explanation.md): installs this.
- [logging.py](logging.py.explanation.md): formats the log line.
- [errors.py](errors.py.explanation.md): reads the request ID.
