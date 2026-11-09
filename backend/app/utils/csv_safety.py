"""Helpers for writing CSV files safely and for cleaning uploaded file names."""

import csv
import io
import re
from collections.abc import Iterable, Iterator
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
_MAX_FILENAME_LENGTH = 255
# Characters per streamed piece of a CSV export: big enough to cut per-piece overhead, small
# enough that memory stays flat.
CSV_CHUNK_CHARS = 64 * 1024


def safe_cell(value: Any) -> Any:
    """Stop spreadsheet programs treating exported text as a formula. Numbers are unchanged."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def csv_lines(
    header: Iterable[str], rows: Iterable[Iterable[Any]], chunk_chars: int = CSV_CHUNK_CHARS
) -> Iterator[str]:
    """Yield a CSV file in pieces of about chunk_chars, so a large export is never held in memory.

    Pieces used to be single lines. The web server sends each piece separately from a worker
    thread, so 500,000 one-line pieces made a 99 MB export take 110 seconds (Phase 5 M2).
    Joining lines into larger pieces gives the same bytes with far fewer hand-offs.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(value) for value in row])
        if buffer.tell() >= chunk_chars:
            yield flush()
    yield flush()


def clean_filename(name: str | None) -> str:
    """Keep only the final part of a supplied name, using safe characters."""
    final_part = PurePosixPath(PureWindowsPath(name or "").name).name
    cleaned = _UNSAFE_FILENAME_CHARACTERS.sub("_", final_part)
    return cleaned[-_MAX_FILENAME_LENGTH:] or "upload.csv"
