"""The investigation workflow (PRD 6.7). Nothing here changes a model score or a prediction."""

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import Function

from app.api.schemas.investigations import InvestigationSummary, InvestigationUpdate
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.models.enums import UserRole
from app.models.records import (
    Investigation,
    InvestigationNote,
    InvestigationStatusHistory,
    Prediction,
    Transaction,
    User,
)
from app.repositories.investigations import get_investigation, lock_investigation
from app.services.audit_service import record_event

_ASSIGNABLE_ROLES = {UserRole.INVESTIGATOR, UserRole.ADMIN}


def _after_lock_time() -> Function:
    """The time a statement runs, not when its transaction began.

    now() returns the transaction's start, which is before a request waits for the row lock, so
    two queued changes could be stamped in the wrong order. clock_timestamp() is read after the
    lock is held, so stamps follow the order in which changes were applied.
    """
    return func.clock_timestamp()


def summary_view(
    investigation: Investigation, prediction: Prediction, transaction: Transaction
) -> InvestigationSummary:
    """Build one list row."""
    return InvestigationSummary(
        id=investigation.id,
        status=investigation.status,
        assigned_user_id=investigation.assigned_user_id,
        prediction_id=prediction.id,
        transaction_id=transaction.id,
        external_transaction_id=transaction.external_transaction_id,
        amount=float(transaction.amount),
        transaction_type=transaction.transaction_type,
        step=transaction.simulation_step,
        model_score=prediction.model_score,
        score_is_calibrated=prediction.score_is_calibrated,
        risk_level=prediction.risk_level,
        prediction=prediction.prediction,
        model_version=prediction.model_version,
        threshold_used=prediction.threshold_used,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
    )


def _check_assignee(session: Session, user_id: uuid.UUID) -> None:
    assignee = session.get(User, user_id)
    if assignee is None or not assignee.is_active or assignee.role not in _ASSIGNABLE_ROLES:
        raise InvalidInputError("The assignee must be an active investigator or administrator.")


def update_investigation(
    session: Session, investigation_id: uuid.UUID, change: InvestigationUpdate, user: User
) -> Investigation:
    """Apply a status or assignee change, with its history and audit entries, atomically."""
    investigation = lock_investigation(session, investigation_id)
    if investigation is None:
        raise NotFoundError("Investigation not found.")
    # Checked under the row lock, so a change committed just before this one is seen.
    if change.expected_status is not None and change.expected_status != investigation.status:
        current = investigation.status.value.replace("_", " ").capitalize()
        session.rollback()
        raise ConflictError(
            f"Someone else changed this investigation: its status is now {current}. "
            "Review it and try again."
        )

    if "status" in change.model_fields_set and change.status != investigation.status:
        session.add(
            InvestigationStatusHistory(
                investigation_id=investigation.id,
                from_status=investigation.status,
                to_status=change.status,
                changed_by=user.id,
                created_at=_after_lock_time(),
            )
        )
        record_event(
            session,
            user.id,
            "investigation.status_changed",
            "investigation",
            investigation.id,
            {"from": investigation.status.value, "to": change.status.value},
        )
        investigation.status = change.status
        investigation.updated_at = _after_lock_time()

    if "assigned_user_id" in change.model_fields_set:
        if change.assigned_user_id is not None:
            _check_assignee(session, change.assigned_user_id)
        if change.assigned_user_id != investigation.assigned_user_id:
            investigation.assigned_user_id = change.assigned_user_id
            record_event(
                session,
                user.id,
                "investigation.assigned",
                "investigation",
                investigation.id,
                {"assigned_user_id": str(change.assigned_user_id)},
            )
    session.commit()
    session.expire_all()
    return get_investigation(session, investigation_id)


def add_note(
    session: Session, investigation_id: uuid.UUID, text: str, user: User
) -> InvestigationNote:
    """Add a note and mark the investigation as updated. The text is not copied to the audit log."""
    investigation = lock_investigation(session, investigation_id)
    if investigation is None:
        raise NotFoundError("Investigation not found.")
    note = InvestigationNote(
        investigation_id=investigation.id,
        user_id=user.id,
        note=text,
        created_at=_after_lock_time(),
    )
    session.add(note)
    investigation.updated_at = _after_lock_time()
    record_event(session, user.id, "investigation.note_added", "investigation", investigation.id)
    session.commit()
    session.refresh(note)
    return note
