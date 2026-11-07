"""Aggregate queries for the summary report.

Model flags, investigation statuses and uploaded labels are counted by separate functions, because
PRD 6.1 forbids mixing them.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.enums import PredictionDecision
from app.models.records import GroundTruthLabel, Investigation, Prediction, Transaction

HOURS_PER_DAY = 24


def _scoped_predictions(is_demo: bool):
    return (
        select(Prediction)
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
    )


def model_flag_totals(session: Session, is_demo: bool) -> dict[str, Any]:
    """Count what the model decided, and the value of the transactions it saw."""
    flagged = Prediction.prediction == PredictionDecision.FLAG_FOR_REVIEW
    row = session.execute(
        select(
            func.count(Prediction.id),
            func.count(case((flagged, 1))),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.coalesce(func.sum(case((flagged, Transaction.amount))), 0),
        )
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
    ).one()
    return {
        "total": row[0],
        "flagged": row[1],
        "total_value": Decimal(row[2]),
        "flagged_value": Decimal(row[3]),
    }


def risk_distribution(session: Session, is_demo: bool) -> dict[str, int]:
    """Count predictions by risk level."""
    rows = session.execute(
        select(Prediction.risk_level, func.count())
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Prediction.risk_level)
    )
    return {level.value: count for level, count in rows}


def type_distribution(session: Session, is_demo: bool) -> dict[str, dict[str, int]]:
    """Count analysed and flagged transactions by type."""
    flagged = Prediction.prediction == PredictionDecision.FLAG_FOR_REVIEW
    rows = session.execute(
        select(Transaction.transaction_type, func.count(), func.count(case((flagged, 1))))
        .join(Prediction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Transaction.transaction_type)
    )
    return {name: {"analysed": total, "flagged": flags} for name, total, flags in rows}


def flags_by_simulation_day(session: Session, is_demo: bool) -> list[dict[str, int]]:
    """Count analysed and flagged transactions per simulated day."""
    flagged = Prediction.prediction == PredictionDecision.FLAG_FOR_REVIEW
    # Floor division: in SQLAlchemy 2, "/" on integers is true division.
    day = (Transaction.simulation_step // HOURS_PER_DAY).label("day")
    rows = session.execute(
        select(day, func.count(), func.count(case((flagged, 1))))
        .join(Prediction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(day)
        .order_by(day)
    )
    return [{"day": int(d), "analysed": total, "flagged": flags} for d, total, flags in rows]


def investigation_status_counts(session: Session, is_demo: bool) -> dict[str, int]:
    """Count investigations by workflow status."""
    rows = session.execute(
        select(Investigation.status, func.count())
        .join(Prediction, Investigation.prediction_id == Prediction.id)
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Investigation.status)
    )
    return {status.value: count for status, count in rows}


def uploaded_label_totals(session: Session, is_demo: bool) -> dict[str, Any]:
    """Count labels supplied in uploads. No performance metric is computed from them."""
    row = session.execute(
        select(
            func.count(GroundTruthLabel.transaction_id),
            func.count(case((GroundTruthLabel.is_fraud, 1))),
            func.coalesce(func.sum(case((GroundTruthLabel.is_fraud, Transaction.amount))), 0),
        )
        .join(Transaction, GroundTruthLabel.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
    ).one()
    return {
        "labelled_rows": row[0],
        "labelled_fraud_rows": row[1],
        "labelled_fraud_value": Decimal(row[2]),
    }
