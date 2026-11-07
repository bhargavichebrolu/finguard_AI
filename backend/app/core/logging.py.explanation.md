# logging.py

Source: [backend/app/core/logging.py](logging.py)

## A. File Purpose
Configures the application's logs as one JSON object per line.

## B. Why This File Exists
PRD 11.3 requires structured logs on the deployed backend. JSON lets a hosting provider's log tools filter by request ID or status.

## C. Dependencies
- **Libraries:** `json`, `logging`, `sys`, `datetime`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `app/main.py`, and anything using a `finguard.*` logger.

## D. Every Function Explained

### `format`
- **Purpose:** convert one log record to JSON.
- **Parameters / types:** `record: logging.LogRecord`. **Returns / type:** `str`.
- **Internal processing:** writes the timestamp, level, logger and message, then any fields in `_EXTRA_FIELDS` and the traceback if there is one.
- **Error handling:** `default=str` stops an unusual value breaking the log line.
- **Calls:** `json.dumps`. **Used by:** the logging system.

### `configure_logging`
- **Purpose:** install the formatter on the `finguard` logger.
- **Parameters / types:** `level: int`. **Returns / type:** `None`.
- **Internal processing:** replaces handlers, so repeated calls do not double every line, and turns off propagation.
- **Error handling:** none needed.
- **Calls:** `logging`. **Used by:** `create_app` in `app/main.py`.

## E. Classes Explained

### `JsonFormatter`
- **Purpose:** the JSON output format. **Attributes:** none. **Methods:** `format`. **Inheritance:** `logging.Formatter`.

## F. Execution Flow
`create_app` calls `configure_logging`. After that, each `finguard.*` log call passes through `JsonFormatter` to standard output.

## G. Input and Output
Input: log records. Output: JSON lines on standard output, for example `{"timestamp": "...", "level": "INFO", "logger": "finguard.request", "message": "request", "status_code": 200}`.

## H. Important Technical Concepts
- **Allow-list of extra fields:** only names in `_EXTRA_FIELDS` are written, so passing extra data to a log call cannot leak it into the output unless it is deliberately listed.
- **Standard output:** containers and hosting platforms collect it, and free hosting may have no persistent disk (PRD 11.7).

## I. Example
```python
logging.getLogger("finguard.request").info("request", extra={"status_code": 200})
```

## J. Maintenance Notes
Do not add request bodies, passwords, tokens or transaction amounts to `_EXTRA_FIELDS`.

## K. Related Files
- [main.py](../main.py.explanation.md): calls `configure_logging` and writes request logs.
- [errors.py](errors.py.explanation.md): logs unexpected errors.
