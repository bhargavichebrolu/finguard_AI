"""Tests of the migrations and database constraints on real PostgreSQL."""

import uuid
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from tests.conftest import alembic_config, empty_all_tables, require_test_database_name

from app.core.config import get_settings
from app.database.base import Base
from app.models.enums import PredictionDecision, RiskLevel, UserRole
from app.models.records import ModelVersion, Prediction, Transaction, User

pytestmark = pytest.mark.database


def _model_version() -> ModelVersion:
    return ModelVersion(
        version="constraint_test_model",
        algorithm="xgboost",
        model_path_or_artifact_reference="x/model.joblib",
        model_sha256="0" * 64,
        threshold=0.5,
        feature_schema_version="1.0.0",
        metrics_json={},
        is_active=True,
    )


def _transaction(**overrides) -> Transaction:
    values = {
        "external_transaction_id": f"T-{uuid.uuid4()}",
        "transaction_type": "TRANSFER",
        "amount": Decimal("100.00"),
        "simulation_step": 1,
        "destination_category": "customer",
    }
    return Transaction(**{**values, **overrides})


def _prediction(transaction: Transaction, **overrides) -> Prediction:
    values = {
        "transaction_id": transaction.id,
        "model_version": "constraint_test_model",
        "model_score": 0.9,
        "risk_score": 90.0,
        "risk_level": RiskLevel.HIGH,
        "prediction": PredictionDecision.FLAG_FOR_REVIEW,
        "threshold_used": 0.5,
        "high_risk_boundary_used": 0.8,
    }
    return Prediction(**{**values, **overrides})


def _store_parent(session) -> Transaction:
    session.add(_model_version())
    transaction = _transaction()
    session.add(transaction)
    session.flush()
    return transaction


def test_every_model_table_exists_after_upgrade(db_engine):
    tables = set(inspect(db_engine).get_table_names())
    assert {table.name for table in Base.metadata.sorted_tables} <= tables
    assert "alembic_version" in tables


def test_models_and_migrations_agree(db_engine):
    command.check(alembic_config())


def test_downgrade_removes_all_tables_and_upgrade_restores_them(db_engine):
    command.downgrade(alembic_config(), "base")
    assert set(inspect(db_engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(alembic_config(), "head")
    assert {table.name for table in Base.metadata.sorted_tables} <= set(
        inspect(db_engine).get_table_names()
    )


def test_transaction_table_has_no_balance_or_account_columns(db_engine):
    columns = {column["name"].lower() for column in inspect(db_engine).get_columns("transactions")}
    assert not any(
        "balance" in name or "namedest" in name or "nameorig" in name for name in columns
    )


def test_predictions_table_has_model_score_and_no_probability(db_engine):
    columns = {column["name"] for column in inspect(db_engine).get_columns("predictions")}
    assert {"model_score", "model_version", "threshold_used", "score_is_calibrated"} <= columns
    assert "fraud_probability" not in columns


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"amount": Decimal("0.00")}, "amount_positive"),
        ({"simulation_step": 0}, "step_positive"),
        ({"transaction_type": "UNKNOWN"}, "known_type"),
        ({"destination_category": "merchant"}, "merchant_only_for_payment"),
    ],
)
def test_transaction_constraints_refuse_invalid_rows(db_session, overrides, constraint):
    db_session.add(_transaction(**overrides))
    with pytest.raises(IntegrityError, match=constraint):
        db_session.flush()


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"model_score": 1.5}, "score_in_range"),
        ({"score_is_calibrated": True}, "score_not_calibrated"),
        ({"model_score": 0.4, "risk_score": 40.0}, "decision_matches_threshold"),
        ({"risk_level": RiskLevel.LOW}, "low_risk_means_not_flagged"),
    ],
)
def test_prediction_constraints_refuse_contradictions(db_session, overrides, constraint):
    transaction = _store_parent(db_session)
    db_session.add(_prediction(transaction, **overrides))
    with pytest.raises(IntegrityError, match=constraint):
        db_session.flush()


def test_score_exactly_at_the_threshold_must_be_flagged(db_session):
    transaction = _store_parent(db_session)
    db_session.add(_prediction(transaction, model_score=0.5, risk_score=50.0))
    db_session.flush()


def test_foreign_keys_are_enforced(db_session):
    db_session.add(_prediction(_transaction()))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_only_one_model_can_be_active(db_session):
    db_session.add(_model_version())
    db_session.flush()
    second = _model_version()
    second.version = "another"
    db_session.add(second)
    with pytest.raises(IntegrityError, match="uq_model_versions_single_active"):
        db_session.flush()


def test_one_prediction_per_transaction(db_session):
    transaction = _store_parent(db_session)
    db_session.add(_prediction(transaction))
    db_session.flush()
    db_session.add(_prediction(transaction))
    with pytest.raises(IntegrityError, match="transaction_id"):
        db_session.flush()


def test_emails_are_unique(db_session):
    for _ in range(2):
        db_session.add(User(email="same@example.com", password_hash="x", role=UserRole.ANALYST))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_test_database_guard_refuses_other_names():
    with pytest.raises(RuntimeError, match="Refusing"):
        require_test_database_name("postgresql+psycopg://u:p@127.0.0.1:5432/finguard")


def test_truncate_helper_empties_tables(db_engine, db_session):
    db_session.add(_transaction())
    db_session.commit()
    empty_all_tables(db_engine)
    assert db_session.execute(text("select count(*) from transactions")).scalar() == 0


def test_application_role_is_not_a_superuser(db_engine):
    with db_engine.connect() as connection:
        is_super = connection.execute(
            text(
                "select rolsuper or rolcreaterole or rolcreatedb from pg_roles "
                "where rolname = current_user"
            )
        ).scalar()
    assert is_super is False


def test_connections_use_scram_authentication(db_engine):
    with db_engine.connect() as connection:
        identity = connection.execute(text("select system_user")).scalar()
    assert identity.startswith("scram-sha-256:")


def test_alembic_ini_contains_no_database_address():
    assert alembic_config().get_main_option("sqlalchemy.url") is None


def test_settings_point_at_the_test_database_during_tests():
    # The real .env holds the development database, and tests delete rows.
    url = get_settings().database_url.get_secret_value()
    require_test_database_name(url)
