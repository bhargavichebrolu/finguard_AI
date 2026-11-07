"""Database queries for investigations. Demo records never have one, so no demo filter is needed."""

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import InvestigationStatus
from app.models.records import Investigation, Prediction, Transaction

Row = tuple[Investigation, Prediction, Transaction]


def _rows_query() -> Select:
    return (
        select(Investigation, Prediction, Transaction)
        .join(Prediction, Investigation.prediction_id == Prediction.id)
        .join(Transaction, Prediction.transaction_id == Transaction.id)
    )


def list_investigations(
    session: Session,
    status: InvestigationStatus | None,
    assigned_user_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Row], int]:
    """Return one page, newest first, and the total matching count."""
    conditions = []
    if status is not None:
        conditions.append(Investigation.status == status)
    if assigned_user_id is not None:
        conditions.append(Investigation.assigned_user_id == assigned_user_id)
    total = session.scalar(select(func.count()).select_from(Investigation).where(*conditions)) or 0
    rows = session.execute(
        _rows_query()
        .where(*conditions)
        .order_by(Investigation.created_at.desc(), Investigation.id)
        .limit(limit)
        .offset(offset)
    )
    return [tuple(row) for row in rows.all()], total


def get_investigation(session: Session, investigation_id: uuid.UUID) -> Investigation | None:
    """Return one investigation with its notes and history."""
    return session.scalar(
        select(Investigation)
        .where(Investigation.id == investigation_id)
        .options(selectinload(Investigation.notes), selectinload(Investigation.history))
    )


def lock_investigation(session: Session, investigation_id: uuid.UUID) -> Investigation | None:
    """Return an investigation, locked until the transaction ends."""
    return session.scalar(
        select(Investigation).where(Investigation.id == investigation_id).with_for_update()
    )
