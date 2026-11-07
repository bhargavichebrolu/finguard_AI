"""All application tables (PRD 9.1, with additions recorded in DATABASE_SCHEMA.md)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, created_at_column, enum_type, uuid_primary_key
from app.ml.schema import TRANSACTION_TYPES
from app.models.enums import (
    BatchStatus,
    InvestigationStatus,
    PredictionDecision,
    RiskLevel,
    UserRole,
)

_TYPES_SQL = ", ".join(f"'{name}'" for name in TRANSACTION_TYPES)


class User(Base):
    """A person who can sign in. Only a password hash is stored."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole, "user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = created_at_column()


class ModelVersion(Base):
    """A registered model, copied from the frozen metadata at start-up."""

    __tablename__ = "model_versions"
    __table_args__ = (
        Index(
            "uq_model_versions_single_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_primary_key()
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    model_path_or_artifact_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    model_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold: Mapped[float] = mapped_column(Float(53), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = created_at_column()


class BatchJob(Base):
    """One uploaded CSV file and its progress. The file itself is not stored here."""

    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        enum_type(BatchStatus, "batch_status"), nullable=False, index=True
    )
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ignored_columns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    labels_supplied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BatchRowError(Base):
    """Why one row of an upload was refused. The rejected value is not stored."""

    __tablename__ = "batch_row_errors"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    batch_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)


class Transaction(Base):
    """The four prediction inputs, and where the record came from. No balances or account IDs."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("simulation_step >= 1", name="step_positive"),
        CheckConstraint(f"transaction_type IN ({_TYPES_SQL})", name="known_type"),
        CheckConstraint(
            "(destination_category = 'merchant') = (transaction_type = 'PAYMENT')",
            name="merchant_only_for_payment",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_primary_key()
    external_transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, index=True)
    simulation_step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    destination_category: Mapped[str] = mapped_column(String(16), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    batch_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("batch_jobs.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    prediction: Mapped["Prediction | None"] = relationship(back_populates="transaction")


class GroundTruthLabel(Base):
    """A label supplied in an upload. The scoring path never reads this table (PRD 6.1, 6.4)."""

    __tablename__ = "ground_truth_labels"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True
    )
    is_fraud: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class Prediction(Base):
    """One scored transaction, with the model version and threshold that produced the decision."""

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("model_score >= 0 AND model_score <= 1", name="score_in_range"),
        CheckConstraint("NOT score_is_calibrated", name="score_not_calibrated"),
        CheckConstraint(
            "(prediction = 'FLAG_FOR_REVIEW') = (model_score >= threshold_used)",
            name="decision_matches_threshold",
        ),
        CheckConstraint(
            "(risk_level = 'LOW') = (prediction = 'NOT_FLAGGED')",
            name="low_risk_means_not_flagged",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_primary_key()
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    model_version: Mapped[str] = mapped_column(
        ForeignKey("model_versions.version"), nullable=False, index=True
    )
    model_score: Mapped[float] = mapped_column(Float(53), nullable=False, index=True)
    score_is_calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_score: Mapped[float] = mapped_column(Float(53), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_type(RiskLevel, "risk_level"), nullable=False, index=True
    )
    prediction: Mapped[PredictionDecision] = mapped_column(
        enum_type(PredictionDecision, "prediction_decision"), nullable=False, index=True
    )
    threshold_used: Mapped[float] = mapped_column(Float(53), nullable=False)
    high_risk_boundary_used: Mapped[float] = mapped_column(Float(53), nullable=False)
    explanation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    transaction: Mapped[Transaction] = relationship(back_populates="prediction")
    investigation: Mapped["Investigation | None"] = relationship(back_populates="prediction")


class Investigation(Base):
    """The review of one flagged prediction. Its status is a workflow label, not a finding."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        enum_type(InvestigationStatus, "investigation_status"), nullable=False, index=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    prediction: Mapped[Prediction] = relationship(back_populates="investigation")
    notes: Mapped[list["InvestigationNote"]] = relationship(
        order_by="InvestigationNote.created_at", cascade="all, delete-orphan"
    )
    history: Mapped[list["InvestigationStatusHistory"]] = relationship(
        order_by="InvestigationStatusHistory.created_at", cascade="all, delete-orphan"
    )


class InvestigationNote(Base):
    """A note written by an investigator."""

    __tablename__ = "investigation_notes"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class InvestigationStatusHistory(Base):
    """One status change. Rows are only ever added (PRD 6.7)."""

    __tablename__ = "investigation_status_history"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[InvestigationStatus | None] = mapped_column(
        enum_type(InvestigationStatus, "history_from_status")
    )
    to_status: Mapped[InvestigationStatus] = mapped_column(
        enum_type(InvestigationStatus, "history_to_status"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()


class AuditLog(Base):
    """A record of a significant action. Details must never include secrets."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AppSetting(Base):
    """A value an administrator can change, currently only the high risk boundary."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
