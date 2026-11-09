"""CSV batch processing (PRD 6.4).

The upload is saved to a temporary file, checked, then processed in chunks by a background task.
Each chunk commits on its own, which gives progress reporting and limits lost work. The temporary
file is always deleted afterwards, and only validated rows and results reach the database.
"""

import csv
import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.schemas.transactions import TransactionInput
from app.core.config import Settings, get_settings
from app.core.errors import InvalidInputError, NotFoundError, PayloadTooLargeError
from app.database.session import session_scope
from app.ml.schema import (
    ACCOUNT_IDENTIFIER_COLUMNS,
    LEAKY_BALANCE_COLUMNS,
    PREDICTION_INPUT_COLUMNS,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
)
from app.models.enums import BatchStatus, UserRole
from app.models.records import BatchJob, BatchRowError, GroundTruthLabel, Transaction, User
from app.services.audit_service import record_event
from app.services.model_service import ServingModel
from app.services.prediction_service import (
    ScoredInput,
    add_prediction_records,
    new_external_id,
    score_inputs,
)
from app.services.settings_service import get_high_risk_boundary
from app.utils.csv_safety import clean_filename, csv_lines

logger = logging.getLogger("finguard.batch")

IDENTIFIER_COLUMN = "external_transaction_id"
ALLOWED_COLUMNS = {*PREDICTION_INPUT_COLUMNS, IDENTIFIER_COLUMN}
REFUSED_COLUMNS = {*LEAKY_BALANCE_COLUMNS, *ACCOUNT_IDENTIFIER_COLUMNS}
IGNORED_COLUMNS = {TARGET_COLUMN, RULE_FLAG_COLUMN}
LABEL_SOURCE = "uploaded_csv"
ERROR_REPORT_HEADER = ("row_number", "column", "message")
_READ_BYTES = 1024 * 1024
_FILE_ENCODING = "utf-8-sig"
_ENTIRE_ROW = "row"
_LABEL_VALUES = {"0": False, "1": True}


@dataclass(frozen=True)
class CsvInspection:
    """What the header and row count of an upload showed."""

    rows: int
    ignored_columns: list[str]
    labels_supplied: bool


@dataclass
class _ParsedChunk:
    """One chunk of rows, separated into valid inputs and errors."""

    payloads: list[TransactionInput] = field(default_factory=list)
    labels: list[bool | None] = field(default_factory=list)
    errors: list[tuple[int, str, str]] = field(default_factory=list)
    failed_rows: int = 0


def save_upload(source: BinaryIO, destination: Path, max_bytes: int) -> None:
    """Copy an upload to a temporary file, stopping as soon as it exceeds the limit."""
    written = 0
    with destination.open("wb") as output:
        while chunk := source.read(_READ_BYTES):
            written += len(chunk)
            if written > max_bytes:
                raise PayloadTooLargeError(f"The file exceeds the {max_bytes} byte limit.")
            if b"\x00" in chunk:
                raise InvalidInputError("The file is not a text CSV file.")
            output.write(chunk)
    if written == 0:
        raise InvalidInputError("The file is empty.")


def validate_header(names: list[str]) -> CsvInspection:
    """Check the columns. A leaky column is refused so nobody thinks it influenced a score."""
    columns = [name.strip() for name in names]
    if len(set(columns)) != len(columns):
        raise InvalidInputError("The header contains a repeated column.")
    refused = sorted(set(columns) & REFUSED_COLUMNS)
    if refused:
        raise InvalidInputError(
            f"These columns are not available at prediction time, so they are refused: {refused}"
        )
    missing = sorted(set(PREDICTION_INPUT_COLUMNS) - set(columns))
    if missing:
        raise InvalidInputError(f"Missing required columns: {missing}")
    unknown = sorted(set(columns) - ALLOWED_COLUMNS - IGNORED_COLUMNS)
    if unknown:
        raise InvalidInputError(f"Unsupported columns: {unknown}")
    return CsvInspection(
        rows=0,
        ignored_columns=sorted(set(columns) & IGNORED_COLUMNS),
        labels_supplied=TARGET_COLUMN in columns,
    )


def inspect_csv(path: Path, max_rows: int) -> CsvInspection:
    """Check the header and count the rows, without storing or scoring anything."""
    try:
        with path.open(encoding=_FILE_ENCODING, newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if not header:
                raise InvalidInputError("The file has no header row.")
            inspection = validate_header(header)
            rows = sum(1 for row in reader if row)
    except UnicodeDecodeError as error:
        raise InvalidInputError("The file must be UTF-8 text.") from error
    except csv.Error as error:
        raise InvalidInputError("The file is not a valid CSV file.") from error
    if rows == 0:
        raise InvalidInputError("The file has a header but no rows.")
    if rows > max_rows:
        raise PayloadTooLargeError(f"The file has {rows} rows, and the limit is {max_rows}.")
    return CsvInspection(rows, inspection.ignored_columns, inspection.labels_supplied)


def start_batch(
    session: Session, source: BinaryIO, filename: str | None, user: User, settings: Settings
) -> tuple[BatchJob, Path]:
    """Check an upload and create its job. Returns the temporary file to process."""
    if not (filename or "").lower().endswith(".csv"):
        raise InvalidInputError("Only .csv files are accepted.")
    settings.upload_tmp_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4()
    # The path uses a random identifier, so nothing from the client decides where it is written.
    path = settings.upload_tmp_dir / f"{job_id}.csv"
    try:
        save_upload(source, path, settings.max_upload_bytes)
        inspection = inspect_csv(path, settings.max_batch_rows)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    job = BatchJob(
        id=job_id,
        filename=clean_filename(filename),
        status=BatchStatus.PENDING,
        total_records=inspection.rows,
        ignored_columns=inspection.ignored_columns,
        labels_supplied=inspection.labels_supplied,
        is_demo=user.role == UserRole.DEMO,
        created_by=user.id,
    )
    session.add(job)
    record_event(session, user.id, "batch.uploaded", "batch_job", job_id, {"rows": inspection.rows})
    session.commit()
    return job, path


def _parse_label(value: str | None) -> tuple[bool | None, bool]:
    """Return (label, is_invalid). A blank cell simply means no label."""
    text = (value or "").strip()
    if not text:
        return None, False
    if text in _LABEL_VALUES:
        return _LABEL_VALUES[text], False
    return None, True


def _parse_row(row: dict, row_number: int, seen: set[str], chunk: _ParsedChunk) -> None:
    """Validate one row. The label is read separately and is never part of the scored input."""
    if row.get(None):
        chunk.errors.append((row_number, _ENTIRE_ROW, "The row has too many cells."))
        chunk.failed_rows += 1
        return
    values = {
        name: (row.get(name) or "").strip()
        for name in (*PREDICTION_INPUT_COLUMNS, IDENTIFIER_COLUMN)
    }
    missing = [name for name in PREDICTION_INPUT_COLUMNS if not values[name]]
    if missing:
        chunk.errors.extend((row_number, name, "Missing value.") for name in missing)
        chunk.failed_rows += 1
        return
    try:
        payload = TransactionInput(
            external_transaction_id=values[IDENTIFIER_COLUMN] or None,
            amount=values["amount"],
            transaction_type=values["transaction_type"],
            step=values["step"],
            destination_category=values["destination_category"],
        )
    except ValidationError as error:
        for item in error.errors(include_input=False, include_url=False):
            column = str(item["loc"][0]) if item["loc"] else _ENTIRE_ROW
            chunk.errors.append((row_number, column, item["msg"][:255]))
        chunk.failed_rows += 1
        return
    identifier = payload.external_transaction_id
    if identifier is not None:
        if identifier in seen:
            chunk.errors.append(
                (row_number, IDENTIFIER_COLUMN, "This identifier is repeated in the file.")
            )
            chunk.failed_rows += 1
            return
        seen.add(identifier)
    label, invalid_label = _parse_label(row.get(TARGET_COLUMN))
    if invalid_label:
        # The row is still scored: a label must never decide whether a row gets a prediction.
        chunk.errors.append((row_number, TARGET_COLUMN, "Label ignored: expected 0 or 1."))
    chunk.payloads.append(payload)
    chunk.labels.append(label)


def _read_chunks(path: Path, chunk_rows: int) -> Iterator[list[tuple[int, dict]]]:
    with path.open(encoding=_FILE_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        chunk: list[tuple[int, dict]] = []
        # The header is row 1, matching what a spreadsheet shows.
        for row_number, row in enumerate(reader, start=2):
            chunk.append((row_number, row))
            if len(chunk) == chunk_rows:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def _store_scored_rows(
    session: Session,
    job: BatchJob,
    scored_rows: list[ScoredInput],
    labels: list[bool | None],
    model: ServingModel,
    high_boundary: float,
) -> list[str]:
    """Store valid rows. Returns identifiers that already existed, which were not stored."""
    rows = [
        {
            "id": uuid.uuid4(),
            "external_transaction_id": scored.payload.external_transaction_id or new_external_id(),
            "transaction_type": scored.payload.transaction_type,
            "amount": scored.payload.amount,
            "simulation_step": scored.payload.step,
            "destination_category": scored.payload.destination_category,
            "is_demo": job.is_demo,
            "batch_job_id": job.id,
            "created_by": job.created_by,
        }
        for scored in scored_rows
    ]
    if not rows:
        return []
    statement = (
        insert(Transaction)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["external_transaction_id"])
        .returning(Transaction.id)
    )
    inserted = set(session.scalars(statement).all())
    duplicates: list[str] = []
    for row, scored, label in zip(rows, scored_rows, labels, strict=True):
        if row["id"] not in inserted:
            duplicates.append(row["external_transaction_id"])
            continue
        add_prediction_records(session, row["id"], scored, model, high_boundary, job.is_demo)
        if label is not None:
            session.add(
                GroundTruthLabel(transaction_id=row["id"], is_fraud=label, source=LABEL_SOURCE)
            )
    return duplicates


def _process_chunk(
    session: Session,
    job: BatchJob,
    rows: list[tuple[int, dict]],
    seen: set[str],
    model: ServingModel,
    high_boundary: float,
    settings: Settings,
) -> None:
    """Parse, score and store one chunk, then commit it together with the job's progress."""
    chunk = _ParsedChunk()
    for row_number, row in rows:
        _parse_row(row, row_number, seen, chunk)
    scored = score_inputs(model, chunk.payloads, high_boundary, explain_all=False)
    duplicates = _store_scored_rows(session, job, scored, chunk.labels, model, high_boundary)
    failed = chunk.failed_rows + len(duplicates)
    stored_errors = session.scalar(
        select(func.count()).select_from(BatchRowError).where(BatchRowError.batch_job_id == job.id)
    )
    messages = chunk.errors + [
        (0, IDENTIFIER_COLUMN, f"Identifier {identifier} already exists.")
        for identifier in duplicates
    ]
    for row_number, column, message in messages[
        : max(settings.max_stored_row_errors - (stored_errors or 0), 0)
    ]:
        session.add(
            BatchRowError(
                batch_job_id=job.id, row_number=row_number, column_name=column, message=message
            )
        )
    job.processed_records += len(rows)
    job.failed_records += failed
    session.commit()


def process_batch(job_id: uuid.UUID, path: Path, model: ServingModel) -> None:
    """Background task: process a stored upload. The temporary file is always deleted."""
    settings = get_settings()
    try:
        with session_scope() as session:
            job = session.get(BatchJob, job_id)
            job.status = BatchStatus.PROCESSING
            high_boundary = get_high_risk_boundary(session)
            session.commit()
            seen: set[str] = set()
            for rows in _read_chunks(path, settings.batch_chunk_rows):
                _process_chunk(session, job, rows, seen, model, high_boundary, settings)
            job.status = (
                BatchStatus.COMPLETED_WITH_ERRORS if job.failed_records else BatchStatus.COMPLETED
            )
            job.completed_at = func.now()
            record_event(
                session,
                job.created_by,
                "batch.completed",
                "batch_job",
                job.id,
                {"processed": job.processed_records, "failed": job.failed_records},
            )
            session.commit()
    except Exception:
        logger.exception("Batch %s processing failed", job_id)
        _mark_failed(job_id, "Processing stopped unexpectedly. Rows already stored are kept.")
    finally:
        path.unlink(missing_ok=True)


def _mark_failed(job_id: uuid.UUID, message: str) -> None:
    with session_scope() as session:
        job = session.get(BatchJob, job_id)
        job.status = BatchStatus.FAILED
        job.error_message = message
        job.completed_at = func.now()
        session.commit()


def recover_interrupted_jobs(session: Session, upload_dir: Path) -> int:
    """At start-up, mark unfinished jobs as failed and delete leftover temporary files.

    Assumes one API process, so anything unfinished at start-up cannot still be running.
    """
    result = session.execute(
        update(BatchJob)
        .where(BatchJob.status.in_([BatchStatus.PENDING, BatchStatus.PROCESSING]))
        .values(
            status=BatchStatus.FAILED,
            error_message="The server restarted during processing. Upload the file again.",
            completed_at=func.now(),
        )
    )
    session.commit()
    if upload_dir.is_dir():
        for leftover in upload_dir.glob("*.csv"):
            leftover.unlink(missing_ok=True)
    return result.rowcount


def get_job(session: Session, job_id: uuid.UUID, is_demo: bool) -> BatchJob:
    """Return a job this user may see, or raise NotFoundError."""
    job = session.get(BatchJob, job_id)
    if job is None or job.is_demo != is_demo:
        raise NotFoundError("Batch not found.")
    return job


def list_jobs(
    session: Session, is_demo: bool, limit: int, offset: int
) -> tuple[list[BatchJob], int]:
    """Return one page of jobs, newest first, and the total count."""
    condition = BatchJob.is_demo == is_demo
    total = session.scalar(select(func.count()).select_from(BatchJob).where(condition)) or 0
    rows = session.scalars(
        select(BatchJob)
        .where(condition)
        .order_by(BatchJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


def error_report_lines(job_id: uuid.UUID) -> Iterator[str]:
    """Stream a job's row errors as CSV."""

    def rows() -> Iterator[tuple[int, str, str]]:
        with session_scope() as session:
            query = (
                select(BatchRowError.row_number, BatchRowError.column_name, BatchRowError.message)
                .where(BatchRowError.batch_job_id == job_id)
                .order_by(BatchRowError.row_number)
            )
            for row in session.execute(query.execution_options(yield_per=1000)):
                yield tuple(row)

    return csv_lines(ERROR_REPORT_HEADER, rows())
