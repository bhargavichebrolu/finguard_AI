"""Routes for CSV batch uploads, progress, results and exports (PRD 6.4)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.schemas.batches import BatchView, batch_view
from app.api.schemas.common import ErrorResponse, Limit, Offset, Page
from app.api.schemas.transactions import TransactionSummary, transaction_summary
from app.core.config import get_settings
from app.models.enums import UserRole
from app.models.records import User
from app.repositories.transactions import (
    SortField,
    SortOrder,
    TransactionFilters,
    list_transactions,
)
from app.security.dependencies import DbSession, ServingModelDep, rate_limited, require_permission
from app.security.permissions import Permission
from app.services import batch_service
from app.services.export_service import prediction_csv_lines

router = APIRouter(prefix="/api/v1/batches", tags=["Batch Analysis"])

UploadUser = Annotated[
    User,
    Depends(
        rate_limited(
            Permission.UPLOAD_BATCH, "upload", lambda: get_settings().upload_rate_limit_per_minute
        )
    ),
]
ViewUser = Annotated[User, Depends(require_permission(Permission.VIEW_TRANSACTIONS))]


def _is_demo(user: User) -> bool:
    return user.role == UserRole.DEMO


def _csv_response(lines, filename: str) -> StreamingResponse:
    return StreamingResponse(
        lines,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/upload",
    response_model=BatchView,
    status_code=status.HTTP_202_ACCEPTED,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def upload(
    user: UploadUser,
    db: DbSession,
    model: ServingModelDep,
    background: BackgroundTasks,
    file: UploadFile,
) -> BatchView:
    """Accept a CSV file, and process it in the background. Poll the batch for progress."""
    job, path = batch_service.start_batch(db, file.file, file.filename, user, get_settings())
    background.add_task(batch_service.process_batch, job.id, path, model)
    return batch_view(job)


@router.get("", response_model=Page[BatchView])
def list_batches(
    user: ViewUser, db: DbSession, limit: Limit = 50, offset: Offset = 0
) -> Page[BatchView]:
    """List batch jobs, newest first."""
    jobs, total = batch_service.list_jobs(db, _is_demo(user), limit, offset)
    return Page[BatchView](
        items=[batch_view(job) for job in jobs], total=total, limit=limit, offset=offset
    )


@router.get("/{batch_id}", response_model=BatchView, responses={404: {"model": ErrorResponse}})
def read_batch(user: ViewUser, db: DbSession, batch_id: uuid.UUID) -> BatchView:
    """Return a job's status and progress."""
    return batch_view(batch_service.get_job(db, batch_id, _is_demo(user)))


@router.get(
    "/{batch_id}/results",
    response_model=Page[TransactionSummary],
    responses={404: {"model": ErrorResponse}},
)
def read_results(
    user: ViewUser,
    db: DbSession,
    batch_id: uuid.UUID,
    sort_by: SortField = "created_at",
    sort_order: SortOrder = "desc",
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[TransactionSummary]:
    """Return a job's stored results, one page at a time."""
    batch_service.get_job(db, batch_id, _is_demo(user))
    rows, total = list_transactions(
        db,
        _is_demo(user),
        TransactionFilters(batch_job_id=batch_id),
        sort_by,
        sort_order,
        limit,
        offset,
    )
    return Page[TransactionSummary](
        items=[transaction_summary(*row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{batch_id}/export", responses={200: {"content": {"text/csv": {}}}})
def export_results(user: ViewUser, db: DbSession, batch_id: uuid.UUID) -> StreamingResponse:
    """Download a job's results as CSV."""
    job = batch_service.get_job(db, batch_id, _is_demo(user))
    return _csv_response(prediction_csv_lines(job.is_demo, job.id), f"batch-{job.id}-results.csv")


@router.get("/{batch_id}/errors", responses={200: {"content": {"text/csv": {}}}})
def export_errors(user: ViewUser, db: DbSession, batch_id: uuid.UUID) -> StreamingResponse:
    """Download a report of the rows that were refused, and why."""
    job = batch_service.get_job(db, batch_id, _is_demo(user))
    return _csv_response(batch_service.error_report_lines(job.id), f"batch-{job.id}-errors.csv")
