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


def safe_cell(value: Any) -> Any:
    """Stop spreadsheet programs treating exported text as a formula. Numbers are unchanged."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def csv_lines(header: Iterable[str], rows: Iterable[Iterable[Any]]) -> Iterator[str]:
    """Yield a CSV file line by line, so a large export is never held in memory."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    writer.writerow(header)
    yield flush()
    for row in rows:
        writer.writerow([safe_cell(value) for value in row])
        yield flush()


def clean_filename(name: str | None) -> str:
    """Keep only the final part of a supplied name, using safe characters."""
    final_part = PurePosixPath(PureWindowsPath(name or "").name).name
    cleaned = _UNSAFE_FILENAME_CHARACTERS.sub("_", final_part)
    return cleaned[-_MAX_FILENAME_LENGTH:] or "upload.csv"
