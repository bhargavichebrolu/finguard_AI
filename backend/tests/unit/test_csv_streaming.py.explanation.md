# test_csv_streaming.py

Source: [backend/tests/unit/test_csv_streaming.py](test_csv_streaming.py)

## A. File Purpose
Proves chunked CSV streaming produces the same bytes as line-by-line writing, in bounded pieces.

## B. Why This File Exists
Phase 5 M2 changed `csv_lines` to yield larger pieces for a tenfold faster export; exports must be byte-identical and memory must stay bounded.

## C. Dependencies
- **Libraries:** pytest, Python `csv`.
- **Internal modules:** `app.utils.csv_safety`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `rows`
Generates rows with quotes, commas, numbers and formula-shaped text.

### `line_by_line`
The pre-M2 output, written one line at a time, as the reference.

## E. Classes Explained
None.

## F. Execution Flow
Compare outputs and piece sizes.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_chunked_output_is_byte_identical` | Same bytes for 0, 1, 999 and 20,000 rows. |
| `test_pieces_are_bounded_and_few` | Pieces stay near the limit and hold many lines. |
| `test_formula_cells_are_still_neutralised` | Spreadsheet safety is unchanged. |
| `test_default_piece_size_is_set` | The default is 64 KB. |

## H. Important Technical Concepts
- **`HEADER`** is the test file's column names.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_csv_streaming.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If the piece size changes, update `test_default_piece_size_is_set` deliberately.

## K. Related Files
- [csv_safety.py](../../app/utils/csv_safety.py.explanation.md): the writer.
