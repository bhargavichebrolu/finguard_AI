"""CSV batch processing (PRD 6.4), as a queue any API process can work (Phase 5 M4).

An upload is checked through a temporary file, then its bytes are stored in batch_uploads and the
job waits as PENDING. Each API process runs one BatchWorker thread. A worker claims the oldest
claimable job with SELECT ... FOR UPDATE SKIP LOCKED and holds it with a lease. Each chunk is
stored in one transaction that also locks the job row, checks this worker still owns it, advances
processed_records and renews the lease, so a crash loses at most the chunk in progress, which is
redone, and never stores a row twice. A job whose lease expires is resumed by any worker after the
last committed chunk; after batch_max_attempts interrupted claims it is marked failed. The bytes
are deleted when the job ends.
"""

import csv
import io
import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

from pydantic import ValidationError
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.schemas.transactions import TransactionInput
from app.core.config import Settings, get_settings
from app.core.errors import (
    InvalidInputError,
    NotFoundError,
    PayloadTooLargeError,
    is_connection_error,
)
from app.database.session import session_scope
from app.ml.schema import (
    ACCOUNT_IDENTIFIER_COLUMNS,
    LEAKY_BALANCE_COLUMNS,
    PREDICTION_INPUT_COLUMNS,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
)
from app.models.enums import BatchStatus, UserRole
from app.models.records import (
    BatchJob,
    BatchRowError,
    BatchUpload,
    GroundTruthLabel,
    Transaction,
    User,
)
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
FAILED_MESSAGE = "Processing stopped unexpectedly. Rows already stored are kept."
# Temporary files older than this can only belong to a request that crashed mid-upload.
_STALE_UPLOAD_SECONDS = 3600


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
) -> BatchJob:
    """Check an upload, store its bytes and queue its job. Any API process may then process it."""
    if not (filename or "").lower().endswith(".csv"):
        raise InvalidInputError("Only .csv files are accepted.")
    settings.upload_tmp_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4()
    # The path uses a random identifier, so nothing from the client decides where it is written.
    path = settings.upload_tmp_dir / f"{job_id}.csv"
    try:
        save_upload(source, path, settings.max_upload_bytes)
        inspection = inspect_csv(path, settings.max_batch_rows)
        content = path.read_bytes()
    finally:
        path.unlink(missing_ok=True)
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
    session.flush()
    session.add(BatchUpload(job_id=job_id, content=content))
    record_event(session, user.id, "batch.uploaded", "batch_job", job_id, {"rows": inspection.rows})
    session.commit()
    return job


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


def _read_chunks(
    content: bytes, chunk_rows: int, skip_rows: int, seen: set[str]
) -> Iterator[list[tuple[int, dict]]]:
    """Yield chunks of (row number, row), after skipping rows a previous attempt committed.

    Identifiers in skipped rows are added to `seen`, so a repeat later in the file is still
    reported as repeated in the file.
    """
    handle = io.TextIOWrapper(io.BytesIO(content), encoding=_FILE_ENCODING, newline="")
    reader = csv.DictReader(handle, skipinitialspace=True)
    reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
    chunk: list[tuple[int, dict]] = []
    # The header is row 1, matching what a spreadsheet shows.
    for index, row in enumerate(reader):
        if index < skip_rows:
            identifier = (row.get(IDENTIFIER_COLUMN) or "").strip()
            if identifier:
                seen.add(identifier)
            continue
        chunk.append((index + 2, row))
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


def new_worker_id() -> str:
    """A name for one worker: host, process and a random part, so restarts never reuse it."""
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def fail_exhausted_jobs(session: Session, max_attempts: int) -> int:
    """Fail jobs whose lease ran out after their last allowed attempt, and drop their bytes."""
    ids = session.scalars(
        update(BatchJob)
        .where(
            BatchJob.status == BatchStatus.PROCESSING,
            BatchJob.lease_expires_at < func.clock_timestamp(),
            BatchJob.attempts >= max_attempts,
        )
        .values(
            status=BatchStatus.FAILED,
            error_message=(
                f"Processing was interrupted {max_attempts} times, so it stopped. "
                "Rows already stored are kept."
            ),
            completed_at=func.now(),
            worker_id=None,
            lease_expires_at=None,
        )
        .returning(BatchJob.id)
    ).all()
    if ids:
        session.execute(delete(BatchUpload).where(BatchUpload.job_id.in_(ids)))
    session.commit()
    return len(ids)


def claim_next_job(
    session: Session, worker_id: str, lease_seconds: int, max_attempts: int
) -> uuid.UUID | None:
    """Claim the oldest waiting job, or one whose lease expired, for this worker.

    SKIP LOCKED makes simultaneous claims by other workers pass over a row being claimed, so two
    workers never claim the same job.
    """
    claimable = (
        select(BatchJob.id)
        .where(
            or_(
                BatchJob.status == BatchStatus.PENDING,
                and_(
                    BatchJob.status == BatchStatus.PROCESSING,
                    BatchJob.lease_expires_at < func.clock_timestamp(),
                ),
            ),
            BatchJob.attempts < max_attempts,
        )
        .order_by(BatchJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    job_id = session.scalar(
        update(BatchJob)
        .where(BatchJob.id == claimable)
        .values(
            status=BatchStatus.PROCESSING,
            worker_id=worker_id,
            attempts=BatchJob.attempts + 1,
            lease_expires_at=func.clock_timestamp() + timedelta(seconds=lease_seconds),
        )
        .returning(BatchJob.id)
    )
    session.commit()
    return job_id


def _owned_job(session: Session, job_id: uuid.UUID, worker_id: str) -> BatchJob | None:
    """Lock the job row if this worker still owns it. None means another worker took it over."""
    return session.scalar(
        select(BatchJob)
        .where(BatchJob.id == job_id, BatchJob.worker_id == worker_id)
        .with_for_update()
    )


def process_job(
    job_id: uuid.UUID,
    worker_id: str,
    model: ServingModel,
    settings: Settings,
    stop: threading.Event | None = None,
) -> str:
    """Work a claimed job to the end.

    Returns "completed", "failed", "released", "lost" or "interrupted". A lost database connection
    interrupts the job rather than failing it: chunks are idempotent, so it is resumed from the
    last stored chunk, within the attempt limit (Phase 5 M7).
    """
    lease = timedelta(seconds=settings.batch_lease_seconds)
    try:
        with session_scope() as session:
            upload = session.get(BatchUpload, job_id)
            job = _owned_job(session, job_id, worker_id)
            if job is None:
                session.rollback()
                return "lost"
            if upload is None:
                raise RuntimeError("the job's upload is missing")
            content = upload.content
            skip = job.processed_records
            high_boundary = get_high_risk_boundary(session)
            session.commit()
            seen: set[str] = set()
            for rows in _read_chunks(content, settings.batch_chunk_rows, skip, seen):
                if stop is not None and stop.is_set():
                    release_job(session, job_id, worker_id)
                    return "released"
                job = _owned_job(session, job_id, worker_id)
                if job is None:
                    session.rollback()
                    return "lost"
                # The heartbeat: renewed in the same commit as this chunk's rows and progress.
                job.lease_expires_at = func.clock_timestamp() + lease
                _process_chunk(session, job, rows, seen, model, high_boundary, settings)
            job = _owned_job(session, job_id, worker_id)
            if job is None:
                session.rollback()
                return "lost"
            job.status = (
                BatchStatus.COMPLETED_WITH_ERRORS if job.failed_records else BatchStatus.COMPLETED
            )
            job.completed_at = func.now()
            job.worker_id = None
            job.lease_expires_at = None
            session.execute(delete(BatchUpload).where(BatchUpload.job_id == job_id))
            record_event(
                session,
                job.created_by,
                "batch.completed",
                "batch_job",
                job.id,
                {"processed": job.processed_records, "failed": job.failed_records},
            )
            session.commit()
            return "completed"
    except Exception as error:
        if is_connection_error(error):
            logger.warning("Batch %s interrupted: the database connection was lost", job_id)
            _release_after_interruption(job_id, worker_id)
            return "interrupted"
        logger.exception("Batch %s processing failed", job_id)
        _mark_failed(job_id, worker_id, FAILED_MESSAGE)
        return "failed"


def _release_after_interruption(job_id: uuid.UUID, worker_id: str) -> None:
    """Give an interrupted job back. If the database is still down, its lease expiring does."""
    try:
        with session_scope() as session:
            release_job(session, job_id, worker_id)
    except Exception as error:
        if not is_connection_error(error):
            raise
        logger.warning("Batch %s will be resumed when its lease expires", job_id)


def release_job(session: Session, job_id: uuid.UUID, worker_id: str) -> None:
    """Give a job back at once, as when the process stops, so another worker resumes it now."""
    session.rollback()
    session.execute(
        update(BatchJob)
        .where(BatchJob.id == job_id, BatchJob.worker_id == worker_id)
        .values(worker_id=None, lease_expires_at=func.clock_timestamp())
    )
    session.commit()


def _mark_failed(job_id: uuid.UUID, worker_id: str, message: str) -> None:
    with session_scope() as session:
        job = _owned_job(session, job_id, worker_id)
        if job is None:
            return
        job.status = BatchStatus.FAILED
        job.error_message = message
        job.completed_at = func.now()
        job.worker_id = None
        job.lease_expires_at = None
        session.execute(delete(BatchUpload).where(BatchUpload.job_id == job_id))
        session.commit()


def process_available_jobs(
    model: ServingModel,
    worker_id: str,
    settings: Settings | None = None,
    stop: threading.Event | None = None,
) -> int:
    """Claim and process jobs until none is waiting. Returns how many were claimed."""
    settings = settings or get_settings()
    claimed = 0
    while stop is None or not stop.is_set():
        with session_scope() as session:
            fail_exhausted_jobs(session, settings.batch_max_attempts)
            job_id = claim_next_job(
                session, worker_id, settings.batch_lease_seconds, settings.batch_max_attempts
            )
        if job_id is None:
            break
        claimed += 1
        if process_job(job_id, worker_id, model, settings, stop) == "interrupted":
            # Wait for the next poll rather than reclaiming at once against a failing database.
            break
    return claimed


def remove_stale_uploads(upload_dir: Path, max_age_seconds: int = _STALE_UPLOAD_SECONDS) -> int:
    """Delete temporary upload files left by requests that crashed mid-upload.

    Only old files are removed, so a request still checking its upload in another process is
    never disturbed. Job data itself lives in the database.
    """
    if not upload_dir.is_dir():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for leftover in upload_dir.glob("*.csv"):
        if leftover.stat().st_mtime < cutoff:
            leftover.unlink(missing_ok=True)
            removed += 1
    return removed


class BatchWorker:
    """One background thread per API process that works the batch queue."""

    def __init__(self, model: ServingModel, settings: Settings) -> None:
        self.model = model
        self.settings = settings
        self.worker_id = new_worker_id()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run, name="batch-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wake(self) -> None:
        """Look for work now, rather than at the next poll; called after an upload."""
        self._wake.set()

    def stop(self, timeout: float = 30) -> None:
        """Finish the current chunk, give the job back, and stop."""
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                process_available_jobs(self.model, self.worker_id, self.settings, self._stop)
            except Exception:
                logger.exception("The batch worker could not reach the queue")
            self._wake.wait(self.settings.batch_poll_seconds)
            self._wake.clear()


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
