"""Routes for the investigation workflow (PRD 6.7)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.schemas.common import ErrorResponse, Limit, Offset, Page
from app.api.schemas.investigations import InvestigationSummary, InvestigationUpdate, NoteCreate
from app.api.schemas.transactions import InvestigationDetail, NoteView
from app.core.errors import NotFoundError
from app.models.enums import InvestigationStatus
from app.models.records import User
from app.repositories.investigations import get_investigation, list_investigations
from app.security.dependencies import DbSession, require_permission
from app.security.permissions import Permission
from app.services import investigation_service

router = APIRouter(prefix="/api/v1/investigations", tags=["Investigations"])

Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_INVESTIGATIONS))]
Investigator = Annotated[User, Depends(require_permission(Permission.UPDATE_INVESTIGATIONS))]


@router.get("", response_model=Page[InvestigationSummary])
def list_all(
    _user: Viewer,
    db: DbSession,
    investigation_status: InvestigationStatus | None = None,
    assigned_user_id: uuid.UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[InvestigationSummary]:
    """List investigations, newest first. Statuses are workflow labels, not findings."""
    rows, total = list_investigations(db, investigation_status, assigned_user_id, limit, offset)
    return Page[InvestigationSummary](
        items=[investigation_service.summary_view(*row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationDetail,
    responses={404: {"model": ErrorResponse}},
)
def read_one(_user: Viewer, db: DbSession, investigation_id: uuid.UUID) -> InvestigationDetail:
    """Return one investigation with its notes and status history."""
    investigation = get_investigation(db, investigation_id)
    if investigation is None:
        raise NotFoundError("Investigation not found.")
    return InvestigationDetail.model_validate(investigation)


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationDetail,
    responses={404: {"model": ErrorResponse}},
)
def update(
    user: Investigator, db: DbSession, investigation_id: uuid.UUID, body: InvestigationUpdate
) -> InvestigationDetail:
    """Change the status or assignee. Status changes are added to the history."""
    investigation = investigation_service.update_investigation(db, investigation_id, body, user)
    return InvestigationDetail.model_validate(investigation)


@router.post(
    "/{investigation_id}/notes",
    response_model=NoteView,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
def add_note(
    user: Investigator, db: DbSession, investigation_id: uuid.UUID, body: NoteCreate
) -> NoteView:
    """Add a note to an investigation."""
    note = investigation_service.add_note(db, investigation_id, body.note, user)
    return NoteView.model_validate(note)
