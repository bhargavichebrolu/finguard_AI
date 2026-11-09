"""Stream stored predictions as CSV, for batch exports and reports (PRD 6.4, 6.9)."""

import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy import select

from app.database.session import session_scope
from app.models.records import Investigation, Prediction, Transaction
from app.utils.csv_safety import csv_lines

PREDICTION_HEADER = (
    "external_transaction_id",
    "transaction_type",
    "amount",
    "step",
    "destination_category",
    "model_score",
    "score_is_calibrated",
    "risk_score",
    "risk_level",
    "prediction",
    "model_version",
    "threshold_used",
    "high_risk_boundary_used",
    "investigation_status",
    "created_at",
)
_STREAM_ROWS = 1000


def _prediction_rows(is_demo: bool, batch_job_id: uuid.UUID | None) -> Iterator[tuple[Any, ...]]:
    # This runs while the response is being sent, after the request's own session has closed.
    with session_scope() as session:
        query = (
            select(
                Transaction.external_transaction_id,
                Transaction.transaction_type,
                Transaction.amount,
                Transaction.simulation_step,
                Transaction.destination_category,
                Prediction.model_score,
                Prediction.score_is_calibrated,
                Prediction.risk_score,
                Prediction.risk_level,
                Prediction.prediction,
                Prediction.model_version,
                Prediction.threshold_used,
                Prediction.high_risk_boundary_used,
                Investigation.status,
                Prediction.created_at,
            )
            .join(Prediction, Prediction.transaction_id == Transaction.id)
            .outerjoin(Investigation, Investigation.prediction_id == Prediction.id)
            .where(Transaction.is_demo == is_demo)
            .order_by(Prediction.created_at, Transaction.id)
        )
        if batch_job_id is not None:
            query = query.where(Transaction.batch_job_id == batch_job_id)
        # yield_per as an execution option streams rows from a server-side cursor; called on the
        # result instead, the driver had already fetched every row into memory (Phase 5 M2).
        for row in session.execute(query.execution_options(yield_per=_STREAM_ROWS)):
            yield tuple(_plain(value) for value in row)


def _plain(value: Any) -> Any:
    """Write enums as their text values and timestamps in ISO format."""
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def prediction_csv_lines(is_demo: bool, batch_job_id: uuid.UUID | None = None) -> Iterator[str]:
    """Return a stored-predictions CSV, for one batch or for everything in scope."""
    return csv_lines(PREDICTION_HEADER, _prediction_rows(is_demo, batch_job_id))
