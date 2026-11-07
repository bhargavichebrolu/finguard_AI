"""The audit log, for administrators (PRD 2.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas.auth import AuditLogView
from app.api.schemas.common import Limit, Offset, Page
from app.models.records import User
from app.security.dependencies import DbSession, require_permission
from app.security.permissions import Permission
from app.services.audit_service import list_events

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit"])


@router.get("", response_model=Page[AuditLogView])
def list_audit_logs(
    _admin: Annotated[User, Depends(require_permission(Permission.VIEW_AUDIT_LOG))],
    db: DbSession,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[AuditLogView]:
    """List audit entries, newest first."""
    rows, total = list_events(db, limit, offset)
    return Page[AuditLogView](
        items=[AuditLogView.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
