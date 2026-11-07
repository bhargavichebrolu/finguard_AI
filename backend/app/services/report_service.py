"""Summaries and report exports (PRD 6.1, 6.9).

Model flags, investigation workflow and uploaded labels are reported in separate sections and are
never combined. Model performance comes from saved Phase 2 results only.
"""

from collections.abc import Iterator
from typing import Any, Literal

from sqlalchemy import select

from app.api.schemas.reports import (
    InvestigationWorkflowSection,
    ModelFlagsSection,
    SummaryReport,
    UploadedLabelsSection,
)
from app.api.schemas.transactions import transaction_summary
from app.database.session import session_scope
from app.models.records import Investigation, Prediction, Transaction
from app.repositories import reports as queries
from app.repositories.transactions import TransactionFilters, list_transactions
from app.services.export_service import prediction_csv_lines
from app.services.metrics_service import evaluation_rows, performance_notes
from app.services.model_service import ServingModel
from app.utils.csv_safety import csv_lines

ReportType = Literal["predictions", "flag_summary", "investigations", "model_evaluation"]
_RECENT_ROWS = 5
SEPARATION_NOTE = (
    "Model flags, investigation statuses and uploaded labels are different kinds of information, "
    "and are reported separately. A flag is not a finding of fraud, and an investigation status "
    "is a workflow label."
)


def build_summary(session: Any, model: ServingModel, is_demo: bool) -> SummaryReport:
    """Build the summary from stored records and saved results."""
    totals = queries.model_flag_totals(session, is_demo)
    rows, _ = list_transactions(
        session, is_demo, TransactionFilters(), "created_at", "desc", _RECENT_ROWS, 0
    )
    return SummaryReport(
        scope="demo_sample_records" if is_demo else "application_records",
        is_demo=is_demo,
        note=SEPARATION_NOTE,
        model_flags=ModelFlagsSection(
            total_analysed=totals["total"],
            flagged_for_review=totals["flagged"],
            not_flagged=totals["total"] - totals["flagged"],
            flag_rate=totals["flagged"] / totals["total"] if totals["total"] else 0.0,
            total_value=float(totals["total_value"]),
            flagged_value=float(totals["flagged_value"]),
            risk_distribution=queries.risk_distribution(session, is_demo),
            type_distribution=queries.type_distribution(session, is_demo),
            flags_by_simulation_day=queries.flags_by_simulation_day(session, is_demo),
        ),
        investigation_workflow=InvestigationWorkflowSection(
            status_counts=queries.investigation_status_counts(session, is_demo)
        ),
        uploaded_labels=UploadedLabelsSection(
            **{
                key: float(value) if key == "labelled_fraud_value" else value
                for key, value in queries.uploaded_label_totals(session, is_demo).items()
            }
        ),
        model_performance_notes=performance_notes(model.metrics),
        recent_activity=[transaction_summary(*row) for row in rows],
    )


def _flag_summary_lines(session_is_demo: bool) -> Iterator[str]:
    with session_scope() as session:
        rows = [
            (name, values["analysed"], values["flagged"])
            for name, values in sorted(queries.type_distribution(session, session_is_demo).items())
        ]
    return csv_lines(("transaction_type", "analysed", "flagged_for_review"), rows)


def _investigation_rows(is_demo: bool) -> Iterator[tuple[Any, ...]]:
    with session_scope() as session:
        query = (
            select(
                Investigation.id,
                Transaction.external_transaction_id,
                Investigation.status,
                Investigation.assigned_user_id,
                Prediction.model_score,
                Prediction.risk_level,
                Investigation.created_at,
                Investigation.updated_at,
            )
            .join(Prediction, Investigation.prediction_id == Prediction.id)
            .join(Transaction, Prediction.transaction_id == Transaction.id)
            .where(Transaction.is_demo == is_demo)
            .order_by(Investigation.created_at)
        )
        for row in session.execute(query).yield_per(1000):
            yield (
                str(row[0]),
                row[1],
                row[2].value,
                str(row[3]) if row[3] else "",
                row[4],
                row[5].value,
                row[6].isoformat(),
                row[7].isoformat(),
            )


def _model_evaluation_lines(model: ServingModel) -> Iterator[str]:
    return csv_lines(("partition", "slice", "metric", "value"), evaluation_rows(model.metrics))


def report_lines(report_type: ReportType, is_demo: bool, model: ServingModel) -> Iterator[str]:
    """Return the requested report as CSV lines."""
    if report_type == "predictions":
        return prediction_csv_lines(is_demo)
    if report_type == "flag_summary":
        return _flag_summary_lines(is_demo)
    if report_type == "investigations":
        header = (
            "investigation_id",
            "external_transaction_id",
            "workflow_status",
            "assigned_user_id",
            "model_score",
            "risk_level",
            "created_at",
            "updated_at",
        )
        return csv_lines(header, _investigation_rows(is_demo))
    return _model_evaluation_lines(model)
