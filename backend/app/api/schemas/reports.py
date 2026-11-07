"""Schemas for reports. The three kinds of information from PRD 6.1 are separate sections."""

from pydantic import BaseModel

from app.api.schemas.transactions import TransactionSummary


class ModelFlagsSection(BaseModel):
    """What the model decided. Flags request review and are not findings of fraud."""

    total_analysed: int
    flagged_for_review: int
    not_flagged: int
    flag_rate: float
    total_value: float
    flagged_value: float
    risk_distribution: dict[str, int]
    type_distribution: dict[str, dict[str, int]]
    flags_by_simulation_day: list[dict[str, int]]


class InvestigationWorkflowSection(BaseModel):
    """What people have recorded. These are workflow labels, not verified findings."""

    status_counts: dict[str, int]


class UploadedLabelsSection(BaseModel):
    """Labels supplied with uploads. They were not used to score anything."""

    labelled_rows: int
    labelled_fraud_rows: int
    labelled_fraud_value: float


class SummaryReport(BaseModel):
    """The summary for one scope. Demo figures are never mixed with application figures."""

    scope: str
    is_demo: bool
    note: str
    model_flags: ModelFlagsSection
    investigation_workflow: InvestigationWorkflowSection
    uploaded_labels: UploadedLabelsSection
    model_performance_notes: list[str]
    recent_activity: list[TransactionSummary]
