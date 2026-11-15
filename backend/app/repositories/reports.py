"""Aggregate queries for the summary report.

Model flags, investigation statuses and uploaded labels are counted by separate functions, because
PRD 6.1 forbids mixing them.
"""

from collections import defaultdict
from dataclasses import dataclass
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


@dataclass(frozen=True)
class FlagBreakdown:
    """Every model-flag figure on the dashboard, from one pass over predictions.

    Phase 5 M2 measured the dashboard at 862 ms with 500,000 predictions; four separate full
    passes over the same join took about 150 ms each. One grouped query now feeds all four.
    """

    total: int
    flagged: int
    total_value: Decimal
    flagged_value: Decimal
    by_risk: dict[str, int]
    by_type: dict[str, dict[str, int]]
    by_day: list[dict[str, int]]


def model_flag_breakdown(session: Session, is_demo: bool) -> FlagBreakdown:
    """Count model decisions by risk level, type and simulated day in a single query."""
    flagged = Prediction.prediction == PredictionDecision.FLAG_FOR_REVIEW
    # Floor division: in SQLAlchemy 2, "/" on integers is true division.
    day = (Transaction.simulation_step // HOURS_PER_DAY).label("day")
    rows = session.execute(
        select(
            Prediction.risk_level,
            Transaction.transaction_type,
            day,
            func.count(),
            func.count(case((flagged, 1))),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.coalesce(func.sum(case((flagged, Transaction.amount))), 0),
        )
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.is_demo == is_demo)
        .group_by(Prediction.risk_level, Transaction.transaction_type, day)
    ).all()
    by_risk: dict[str, int] = defaultdict(int)
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"analysed": 0, "flagged": 0})
    by_day: dict[int, dict[str, int]] = defaultdict(lambda: {"analysed": 0, "flagged": 0})
    total = flags = 0
    total_value = flagged_value = Decimal(0)
    for level, kind, simulated_day, count, flagged_count, value, flagged_amount in rows:
        total += count
        flags += flagged_count
        total_value += Decimal(value)
        flagged_value += Decimal(flagged_amount)
        by_risk[level.value] += count
        by_type[kind]["analysed"] += count
        by_type[kind]["flagged"] += flagged_count
        by_day[int(simulated_day)]["analysed"] += count
        by_day[int(simulated_day)]["flagged"] += flagged_count
    return FlagBreakdown(
        total=total,
        flagged=flags,
        total_value=total_value,
        flagged_value=flagged_value,
        by_risk=dict(sorted(by_risk.items())),
        by_type=dict(sorted(by_type.items())),
        by_day=[{"day": d, **by_day[d]} for d in sorted(by_day)],
    )


def model_flag_totals(session: Session, is_demo: bool) -> dict[str, Any]:
    """Count what the model decided, and the value of the transactions it saw."""
    breakdown = model_flag_breakdown(session, is_demo)
    return {
        "total": breakdown.total,
        "flagged": breakdown.flagged,
        "total_value": breakdown.total_value,
        "flagged_value": breakdown.flagged_value,
    }


def risk_distribution(session: Session, is_demo: bool) -> dict[str, int]:
    """Count predictions by risk level."""
    return model_flag_breakdown(session, is_demo).by_risk


def type_distribution(session: Session, is_demo: bool) -> dict[str, dict[str, int]]:
    """Count analysed and flagged transactions by type."""
    return model_flag_breakdown(session, is_demo).by_type


def flags_by_simulation_day(session: Session, is_demo: bool) -> list[dict[str, int]]:
    """Count analysed and flagged transactions per simulated day."""
    return model_flag_breakdown(session, is_demo).by_day


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
