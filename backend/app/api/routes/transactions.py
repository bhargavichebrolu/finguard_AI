"""Routes for scoring a transaction and exploring stored ones (PRD 6.2, 6.5, 6.6)."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.schemas.common import ErrorResponse, Limit, Offset, Page
from app.api.schemas.transactions import (
    MAX_STEP,
    PredictionView,
    TransactionDetail,
    TransactionInput,
    TransactionSummary,
    TransactionTypeName,
    transaction_detail,
    transaction_summary,
)
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.enums import InvestigationStatus, PredictionDecision, RiskLevel, UserRole
from app.models.records import User
from app.repositories.transactions import (
    SortField,
    SortOrder,
    TransactionFilters,
    get_transaction,
    list_transactions,
)
from app.security.dependencies import (
    DbSession,
    ServingModelDep,
    rate_limited,
    require_permission,
)
from app.security.permissions import Permission
from app.services.prediction_service import create_prediction

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])

PredictUser = Annotated[
    User,
    Depends(
        rate_limited(
            Permission.PREDICT, "predict", lambda: get_settings().predict_rate_limit_per_minute
        )
    ),
]
ViewUser = Annotated[User, Depends(require_permission(Permission.VIEW_TRANSACTIONS))]


@router.post(
    "/predict",
    response_model=PredictionView,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def predict(
    user: PredictUser, db: DbSession, model: ServingModelDep, body: TransactionInput
) -> PredictionView:
    """Score one transaction and store the result.

    `model_score` is uncalibrated and is not a probability of fraud. `FLAG_FOR_REVIEW` asks for
    human review and is not a finding of fraud.
    """
    return create_prediction(db, model, body, user)


@router.get("", response_model=Page[TransactionSummary])
def explore(
    user: ViewUser,
    db: DbSession,
    external_id: Annotated[str | None, Query(max_length=64)] = None,
    risk_level: RiskLevel | None = None,
    prediction: PredictionDecision | None = None,
    transaction_type: TransactionTypeName | None = None,
    amount_min: Annotated[Decimal | None, Query(ge=0)] = None,
    amount_max: Annotated[Decimal | None, Query(ge=0)] = None,
    step_min: Annotated[int | None, Query(ge=1, le=MAX_STEP)] = None,
    step_max: Annotated[int | None, Query(ge=1, le=MAX_STEP)] = None,
    investigation_status: InvestigationStatus | None = None,
    batch_job_id: uuid.UUID | None = None,
    sort_by: SortField = "created_at",
    sort_order: SortOrder = "desc",
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[TransactionSummary]:
    """Search stored transactions, with filters, sorting and pagination."""
    filters = TransactionFilters(
        external_id=external_id,
        risk_level=risk_level,
        prediction=prediction,
        transaction_type=transaction_type,
        amount_min=amount_min,
        amount_max=amount_max,
        step_min=step_min,
        step_max=step_max,
        investigation_status=investigation_status,
        batch_job_id=batch_job_id,
    )
    rows, total = list_transactions(
        db, user.role == UserRole.DEMO, filters, sort_by, sort_order, limit, offset
    )
    return Page[TransactionSummary](
        items=[transaction_summary(*row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetail,
    responses={404: {"model": ErrorResponse}},
)
def read_transaction(user: ViewUser, db: DbSession, transaction_id: uuid.UUID) -> TransactionDetail:
    """Return one transaction with its score, explanation and investigation."""
    row = get_transaction(db, transaction_id, user.role == UserRole.DEMO)
    if row is None:
        raise NotFoundError("Transaction not found.")
    return transaction_detail(*row)
