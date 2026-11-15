# csv_safety.py

Source: [backend/app/utils/csv_safety.py](csv_safety.py)

## A. File Purpose
Writes CSV output safely, and cleans names of uploaded files.

## B. Why This File Exists
Exported CSV files are often opened in spreadsheets, where a cell starting with `=` can run as a formula. Uploaded file names come from the client, and can contain paths or odd characters.

## C. Dependencies
- **Libraries:** `csv`, `io`, `re`, `pathlib`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `batch_service.py`, `report_service.py`.

## D. Every Function Explained

### `safe_cell`
- **Purpose:** neutralise formula injection.
- **Parameters / types:** `value: Any`. **Returns / type:** the same value, or text prefixed with `'`.
- **Internal processing:** only strings starting with a formula character change. Numbers, including negatives, are left alone.
- **Error handling:** none needed. **Calls:** none. **Used by:** `csv_lines`.

### `csv_lines`
- **Purpose:** stream a CSV file.
- **Parameters / types:** `header`, `rows`, `chunk_chars` (default `CSV_CHUNK_CHARS`, 64 KB). **Returns / type:** an iterator of strings.
- **Internal processing:** writes rows to a buffer and yields it whenever it reaches `chunk_chars`, then the remainder. Until Phase 5 M2 it yielded every line separately; the web server hands each piece over from a worker thread, so a 500,000-row export took 110 seconds. The joined output is byte-identical (`test_csv_streaming.py`), and now takes about 10 seconds.
- **Error handling:** errors from `rows` propagate. **Calls:** `safe_cell`, `flush`. **Used by:** export functions.

### `flush`
Nested. Returns the buffer's content and empties it.

### `clean_filename`
- **Purpose:** make a client-supplied name safe to store and return.
- **Parameters / types:** `name: str | None`. **Returns / type:** `str`.
- **Internal processing:** takes the last path part under both Windows and POSIX rules, and replaces other characters with `_`.
- **Error handling:** an empty result becomes `upload.csv`. **Calls:** `pathlib`, `re`. **Used by:** `batch_service`.

## E. Classes Explained
None.

## F. Execution Flow
Functions are called as needed. `csv_lines` runs while a response is being sent.

## G. Input and Output
`safe_cell("=SUM(A1)")` gives `'=SUM(A1)`. `clean_filename("..\\..\\evil name.csv")` gives `evil_name.csv`.

## H. Important Technical Concepts
- **`CSV_CHUNK_CHARS`** is the piece size: large enough to cut per-piece overhead, small enough to keep memory flat.
- **Formula injection:** a crafted cell can run commands or send data elsewhere when opened in a spreadsheet. A leading apostrophe makes it plain text.
- **The stored name is never used as a path.** Temporary files are named by a random identifier, so `clean_filename` is defence in depth.

## I. Example
```python
"".join(csv_lines(["a"], [["=1+1"]]))  # "a\r\n'=1+1\r\n"
```

## J. Maintenance Notes
Pass all exported text through `csv_lines`.

## K. Related Files
- [batch_service.py](../services/batch_service.py.explanation.md): uploads and exports.
- [report_service.py](../services/report_service.py.explanation.md): report exports.
