"""Audit logging. Entries join the caller's transaction, so they commit or roll back with it."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.records import AuditLog


def record_event(
    session: Session,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry. Details must never contain passwords, tokens or uploaded values."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            details=details,
        )
    )


def list_events(session: Session, limit: int, offset: int) -> tuple[list[AuditLog], int]:
    """Return one page of entries, newest first, and the total count."""
    total = session.scalar(select(func.count()).select_from(AuditLog)) or 0
    rows = session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows), total
