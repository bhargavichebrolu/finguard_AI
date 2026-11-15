"""Score validated inputs and store the results (PRD 6.2).

Inputs reach the model through inputs_frame only, which uses the four allowed fields. Labels are
never passed in, so they cannot influence a score.
"""

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.transactions import PredictionView, TransactionInput, prediction_view
from app.core.errors import ConflictError, ScoringError
from app.core.frozen_model import SCORE_IS_CALIBRATED
from app.models.enums import InvestigationStatus, PredictionDecision, UserRole
from app.models.records import (
    Investigation,
    InvestigationStatusHistory,
    Prediction,
    Transaction,
    User,
)
from app.services.audit_service import record_event
from app.services.model_service import ServingModel
from app.services.risk import RiskAssessment, assess_score
from app.services.settings_service import get_high_risk_boundary

logger = logging.getLogger("finguard.predictions")


@dataclass(frozen=True)
class ScoredInput:
    """One input with its score, classification and optional explanation."""

    payload: TransactionInput
    score: float
    assessment: RiskAssessment
    explanation: dict[str, Any] | None


def inputs_frame(payloads: Sequence[TransactionInput]) -> pd.DataFrame:
    """Build the model's input table. It holds exactly the four prediction inputs."""
    return pd.DataFrame(
        {
            "amount": [float(payload.amount) for payload in payloads],
            "transaction_type": [payload.transaction_type for payload in payloads],
            "step": [payload.step for payload in payloads],
            "destination_category": [payload.destination_category for payload in payloads],
        }
    )


def score_inputs(
    model: ServingModel,
    payloads: Sequence[TransactionInput],
    high_boundary: float,
    explain_all: bool,
) -> list[ScoredInput]:
    """Score rows. Explanations are computed for every row, or only for flagged ones."""
    if not payloads:
        return []
    frame = inputs_frame(payloads)
    scores = [float(score) for score in model.score(frame)]
    assessments = [assess_score(score, model.threshold, high_boundary) for score in scores]
    explained = [
        position
        for position, assessment in enumerate(assessments)
        if explain_all or assessment.decision is PredictionDecision.FLAG_FOR_REVIEW
    ]
    explanations: dict[int, dict[str, Any]] = {}
    if explained:
        rows = model.explain(frame.iloc[explained])
        explanations = dict(zip(explained, rows, strict=True))
    return [
        ScoredInput(payloads[i], scores[i], assessments[i], explanations.get(i))
        for i in range(len(payloads))
    ]


def new_external_id() -> str:
    """Return an identifier for a transaction submitted without one."""
    return f"TXN-{uuid.uuid4().hex}"


def add_prediction_records(
    session: Session,
    transaction_id: uuid.UUID,
    scored: ScoredInput,
    model: ServingModel,
    high_boundary: float,
    is_demo: bool,
) -> tuple[Prediction, Investigation | None]:
    """Add a prediction and, for a flagged non-demo row, a new investigation. Does not commit."""
    prediction = Prediction(
        id=uuid.uuid4(),
        transaction_id=transaction_id,
        model_version=model.version,
        model_score=scored.score,
        score_is_calibrated=SCORE_IS_CALIBRATED,
        risk_score=scored.assessment.risk_score,
        risk_level=scored.assessment.risk_level,
        prediction=scored.assessment.decision,
        threshold_used=model.threshold,
        high_risk_boundary_used=high_boundary,
        explanation_json=scored.explanation,
    )
    session.add(prediction)
    if is_demo or scored.assessment.decision is not PredictionDecision.FLAG_FOR_REVIEW:
        return prediction, None
    investigation = Investigation(
        id=uuid.uuid4(), prediction_id=prediction.id, status=InvestigationStatus.NEW
    )
    session.add(investigation)
    session.add(
        InvestigationStatusHistory(
            investigation_id=investigation.id,
            from_status=None,
            to_status=InvestigationStatus.NEW,
            changed_by=None,
        )
    )
    return prediction, investigation


def create_prediction(
    session: Session, model: ServingModel, payload: TransactionInput, user: User
) -> PredictionView:
    """Score one transaction and store everything in one database transaction."""
    is_demo = user.role == UserRole.DEMO
    high_boundary = get_high_risk_boundary(session)
    try:
        scored = score_inputs(model, [payload], high_boundary, explain_all=True)[0]
    except Exception as error:
        # Scoring runs before anything is written, so a failure here stores nothing (Phase 5 M7).
        logger.exception("The model failed to score a transaction")
        raise ScoringError() from error
    transaction = Transaction(
        id=uuid.uuid4(),
        external_transaction_id=payload.external_transaction_id or new_external_id(),
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        simulation_step=payload.step,
        destination_category=payload.destination_category,
        is_demo=is_demo,
        created_by=user.id,
    )
    session.add(transaction)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError("A transaction with this identifier already exists.") from error
    prediction, investigation = add_prediction_records(
        session, transaction.id, scored, model, high_boundary, is_demo
    )
    record_event(
        session,
        user.id,
        "transaction.predicted",
        "transaction",
        transaction.id,
        {"decision": scored.assessment.decision.value, "model_version": model.version},
    )
    session.commit()
    session.refresh(prediction)
    return prediction_view(transaction, prediction, investigation)
