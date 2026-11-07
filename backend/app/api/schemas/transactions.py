"""Schemas for prediction requests, prediction results and the transaction explorer.

TransactionInput is also used for each CSV row, so a row and an API request obey the same rules.
Scores are called model_score everywhere, and are never described as probabilities.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.api.schemas.common import ApiModel
from app.core.frozen_model import SCORE_IS_CALIBRATED, SCORE_NOTE, SCORE_TYPE
from app.ml.schema import DESTINATION_CATEGORIES, TRANSACTION_TYPES
from app.models.enums import InvestigationStatus, PredictionDecision, RiskLevel
from app.models.records import Investigation, Prediction, Transaction
from app.services.model_service import explanation_limitations

MAX_STEP = 1_000_000
ExternalId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")]
TransactionTypeName = Literal[TRANSACTION_TYPES]  # type: ignore[valid-type]
DestinationCategoryName = Literal[DESTINATION_CATEGORIES]  # type: ignore[valid-type]


class TransactionInput(BaseModel):
    """The four inputs of PRD 6.2, and an optional identifier. Anything else is refused."""

    model_config = ConfigDict(extra="forbid")

    external_transaction_id: ExternalId | None = None
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2, allow_inf_nan=False)
    transaction_type: TransactionTypeName
    step: int = Field(ge=1, le=MAX_STEP)
    destination_category: DestinationCategoryName

    @model_validator(mode="after")
    def _destination_must_fit_type(self) -> "TransactionInput":
        """In PaySim a merchant receives only PAYMENT, so the model knows no other combination."""
        if (self.destination_category == "merchant") != (self.transaction_type == "PAYMENT"):
            raise ValueError("merchant is valid only with PAYMENT, and PAYMENT only with merchant")
        return self


class ExplanationView(ApiModel):
    """How each input moved this score. This describes the model, not what causes fraud."""

    method: str
    output_scale: str
    base_value: float
    by_group: dict[str, float]
    by_feature: list[dict[str, Any]]
    limitations: list[str]


class PredictionView(ApiModel):
    """A scored transaction. model_score is uncalibrated, and a flag is not a finding of fraud."""

    transaction_id: uuid.UUID
    external_transaction_id: str
    prediction_id: uuid.UUID
    amount: float
    transaction_type: str
    step: int
    destination_category: str
    model_score: float
    score_type: str = SCORE_TYPE
    score_is_calibrated: bool = SCORE_IS_CALIBRATED
    score_note: str = SCORE_NOTE
    risk_score: float
    risk_level: RiskLevel
    prediction: PredictionDecision
    model_version: str
    threshold_used: float
    high_risk_boundary_used: float
    is_demo: bool
    investigation_id: uuid.UUID | None
    investigation_status: InvestigationStatus | None
    explanation: ExplanationView | None
    created_at: datetime


class TransactionSummary(ApiModel):
    """One row of the transaction explorer."""

    transaction_id: uuid.UUID
    external_transaction_id: str
    amount: float
    transaction_type: str
    step: int
    destination_category: str
    model_score: float
    score_is_calibrated: bool = SCORE_IS_CALIBRATED
    risk_score: float
    risk_level: RiskLevel
    prediction: PredictionDecision
    model_version: str
    threshold_used: float
    is_demo: bool
    batch_job_id: uuid.UUID | None
    investigation_id: uuid.UUID | None
    investigation_status: InvestigationStatus | None
    created_at: datetime


class NoteView(ApiModel):
    """A note on an investigation."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    note: str
    created_at: datetime


class StatusChangeView(ApiModel):
    """One entry in an investigation's status history."""

    from_status: InvestigationStatus | None
    to_status: InvestigationStatus
    changed_by: uuid.UUID | None
    created_at: datetime


class InvestigationDetail(ApiModel):
    """A review of one flagged prediction. Its status is a workflow label, not a finding."""

    id: uuid.UUID
    prediction_id: uuid.UUID
    status: InvestigationStatus
    assigned_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    notes: list[NoteView]
    history: list[StatusChangeView]


class TransactionDetail(PredictionView):
    """Everything PRD 6.6 lists for one transaction."""

    batch_job_id: uuid.UUID | None
    investigation: InvestigationDetail | None


def explanation_view(explanation: dict[str, Any] | None) -> ExplanationView | None:
    """Add the standing limitations to a stored explanation."""
    if explanation is None:
        return None
    return ExplanationView(**explanation, limitations=explanation_limitations())


def _shared_fields(
    transaction: Transaction, prediction: Prediction, investigation: Investigation | None
) -> dict[str, Any]:
    return {
        "transaction_id": transaction.id,
        "external_transaction_id": transaction.external_transaction_id,
        "amount": float(transaction.amount),
        "transaction_type": transaction.transaction_type,
        "step": transaction.simulation_step,
        "destination_category": transaction.destination_category,
        "model_score": prediction.model_score,
        "risk_score": prediction.risk_score,
        "risk_level": prediction.risk_level,
        "prediction": prediction.prediction,
        "model_version": prediction.model_version,
        "threshold_used": prediction.threshold_used,
        "is_demo": transaction.is_demo,
        "investigation_id": investigation.id if investigation else None,
        "investigation_status": investigation.status if investigation else None,
        "created_at": prediction.created_at,
    }


def prediction_view(
    transaction: Transaction, prediction: Prediction, investigation: Investigation | None
) -> PredictionView:
    """Build the response for a new prediction."""
    return PredictionView(
        **_shared_fields(transaction, prediction, investigation),
        prediction_id=prediction.id,
        high_risk_boundary_used=prediction.high_risk_boundary_used,
        explanation=explanation_view(prediction.explanation_json),
    )


def transaction_summary(
    transaction: Transaction, prediction: Prediction, investigation: Investigation | None
) -> TransactionSummary:
    """Build one explorer row."""
    return TransactionSummary(
        **_shared_fields(transaction, prediction, investigation),
        batch_job_id=transaction.batch_job_id,
    )


def transaction_detail(
    transaction: Transaction, prediction: Prediction, investigation: Investigation | None
) -> TransactionDetail:
    """Build the full detail view."""
    return TransactionDetail(
        **_shared_fields(transaction, prediction, investigation),
        prediction_id=prediction.id,
        high_risk_boundary_used=prediction.high_risk_boundary_used,
        explanation=explanation_view(prediction.explanation_json),
        batch_job_id=transaction.batch_job_id,
        investigation=(
            InvestigationDetail.model_validate(investigation) if investigation else None
        ),
    )
