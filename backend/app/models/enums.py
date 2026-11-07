"""The fixed vocabularies stored in the database and used in API schemas."""

import enum


class UserRole(enum.StrEnum):
    """What a person may do. The permissions for each role are in app/security/permissions.py."""

    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    ANALYST = "analyst"
    DEMO = "demo"


class PredictionDecision(enum.StrEnum):
    """The model's output. A flag requests human review and is not a finding of fraud."""

    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"
    NOT_FLAGGED = "NOT_FLAGGED"


class RiskLevel(enum.StrEnum):
    """A display band over the uncalibrated score. Low means not flagged."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class InvestigationStatus(enum.StrEnum):
    """Workflow labels from PRD 6.7. These are not verified criminal findings."""

    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    FALSE_ALARM = "FALSE_ALARM"


class BatchStatus(enum.StrEnum):
    """Where a CSV upload is in its processing."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
