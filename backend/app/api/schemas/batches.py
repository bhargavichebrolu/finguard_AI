"""Schemas for batch uploads and their progress."""

import uuid
from datetime import datetime

from app.api.schemas.common import ApiModel
from app.models.enums import BatchStatus
from app.models.records import BatchJob


class BatchView(ApiModel):
    """A batch job. processed counts rows read, failed counts rows refused."""

    id: uuid.UUID
    filename: str
    status: BatchStatus
    total_records: int
    processed_records: int
    failed_records: int
    succeeded_records: int
    progress_percent: float
    ignored_columns: list[str]
    labels_supplied: bool
    is_demo: bool
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


def batch_view(job: BatchJob) -> BatchView:
    """Build the response, adding the two values worked out from the stored counts."""
    progress = 100.0 * job.processed_records / job.total_records if job.total_records else 0.0
    return BatchView(
        id=job.id,
        filename=job.filename,
        status=job.status,
        total_records=job.total_records,
        processed_records=job.processed_records,
        failed_records=job.failed_records,
        succeeded_records=job.processed_records - job.failed_records,
        progress_percent=round(progress, 2),
        ignored_columns=job.ignored_columns,
        labels_supplied=job.labels_supplied,
        is_demo=job.is_demo,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
