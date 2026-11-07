"""Schemas for investigations. Statuses are workflow labels, not verified criminal findings."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.api.schemas.common import ApiModel
from app.models.enums import InvestigationStatus, PredictionDecision, RiskLevel

STATUS_NOTE = (
    "Investigation statuses are workflow labels. They are not verified criminal findings, and they "
    "do not feed back into the model or its evaluation."
)
MAX_NOTE_LENGTH = 5000


class InvestigationSummary(ApiModel):
    """One row of the investigation list."""

    id: uuid.UUID
    status: InvestigationStatus
    status_note: str = STATUS_NOTE
    assigned_user_id: uuid.UUID | None
    prediction_id: uuid.UUID
    transaction_id: uuid.UUID
    external_transaction_id: str
    amount: float
    transaction_type: str
    step: int
    model_score: float
    score_is_calibrated: bool
    risk_level: RiskLevel
    prediction: PredictionDecision
    model_version: str
    threshold_used: float
    created_at: datetime
    updated_at: datetime


class InvestigationUpdate(BaseModel):
    """A change to status or assignee. Send assigned_user_id as null to unassign."""

    model_config = ConfigDict(extra="forbid")

    status: InvestigationStatus | None = None
    assigned_user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _must_change_something(self) -> "InvestigationUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide status or assigned_user_id")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null")
        return self


class NoteCreate(BaseModel):
    """A new note."""

    model_config = ConfigDict(extra="forbid")

    note: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NOTE_LENGTH)
    ]
