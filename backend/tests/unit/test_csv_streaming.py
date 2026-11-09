"""CSV exports are streamed in pieces of bounded size, with exactly the bytes a line-by-line
writer produced (Phase 5 M2 made exports send fewer, larger pieces)."""

import csv
import io

import pytest

from app.utils.csv_safety import CSV_CHUNK_CHARS, csv_lines, safe_cell

HEADER = ("id", "note", "amount")


def rows(count: int):
    for index in range(count):
        yield (
            f"ID-{index}",
            "=SUM(A1)" if index % 7 == 0 else f'text, with "quotes" {index}',
            index * 1.5,
        )


def line_by_line(count: int) -> str:
    """The pre-M2 output: one CSV line at a time."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    for row in rows(count):
        writer.writerow([safe_cell(value) for value in row])
    return buffer.getvalue()


@pytest.mark.parametrize("count", [0, 1, 999, 20_000])
def test_chunked_output_is_byte_identical(count):
    assert "".join(csv_lines(HEADER, rows(count))) == line_by_line(count)


def test_pieces_are_bounded_and_few():
    pieces = list(csv_lines(HEADER, rows(20_000), chunk_chars=4096))
    longest_line = max(len(line) for line in line_by_line(20_000).splitlines(keepends=True))
    assert all(len(piece) < 4096 + longest_line for piece in pieces)
    assert len(pieces) < 20_000 / 50  # many lines per piece, not one


def test_formula_cells_are_still_neutralised():
    text = "".join(csv_lines(HEADER, rows(10)))
    assert "'=SUM(A1)" in text
    assert "\n=SUM" not in text and ",=SUM" not in text


def test_default_piece_size_is_set():
    assert CSV_CHUNK_CHARS == 64 * 1024
