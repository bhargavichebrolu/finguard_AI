"""Integration failures (Phase 5 M7): the database going away and coming back, the model failing,
batch jobs interrupted by lost connections, and stale investigation changes.

Every error response is also checked for what it must never contain.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from tests.api.test_batch_queue import expire_lease, queue, stored_rows

from app.api.routes import health
from app.core.config import get_settings
from app.database.session import get_db
from app.models.enums import BatchStatus, InvestigationStatus, UserRole
from app.models.records import (
    AuditLog,
    BatchJob,
    InvestigationStatusHistory,
    Prediction,
    Transaction,
)
from app.services import batch_service, prediction_service

pytestmark = pytest.mark.database

PREDICT = "/api/v1/transactions/predict"
FLAGGED = {
    "amount": 9_000_000.0,
    "transaction_type": "TRANSFER",
    "step": 5,
    "destination_category": "customer",
}
# Words that would show a response leaking internals: SQL, driver or server details, traces.
FORBIDDEN = (
    "traceback",
    "select ",
    "insert ",
    "psycopg",
    "sqlalchemy",
    "postgres",
    "password",
    "127.0.0.1",
    "secret",
    'file "',
)


def assert_safe(response) -> dict:
    """The body is the documented error shape and names nothing internal."""
    body = response.json()
    assert set(body) <= {"detail", "request_id", "errors"}
    assert body["request_id"]
    text_ = response.text.lower()
    for word in FORBIDDEN:
        assert word not in text_, word
    return body


def connection_lost(statement: str | None = "INSERT INTO transactions") -> OperationalError:
    """An error as SQLAlchemy raises it when a connection dies mid-use."""
    return OperationalError(
        statement,
        {},
        Exception("server closed the connection, secret"),
        connection_invalidated=True,
    )


@pytest.fixture
def analyst(headers_for):
    return headers_for(UserRole.ANALYST)


@pytest.fixture
def admin(headers_for):
    return headers_for(UserRole.ADMIN)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    current = get_settings()
    monkeypatch.setattr(current, "upload_tmp_dir", tmp_path)
    monkeypatch.setattr(current, "batch_chunk_rows", 100)
    return current


@pytest.fixture
def unreachable_database(client):
    """Requests get sessions on a database address where nothing listens: a real driver error."""
    url = make_url(get_settings().database_url.get_secret_value()).set(port=1)
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 2})

    def broken_db():
        with Session(engine) as session:
            yield session

    client.app.dependency_overrides[get_db] = broken_db
    yield
    client.app.dependency_overrides.pop(get_db, None)
    engine.dispose()


# The database going away and coming back.


def test_an_unreachable_database_gives_a_safe_503_with_retry_after(
    client, analyst, unreachable_database
):
    response = client.get("/api/v1/transactions", headers=analyst)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    body = assert_safe(response)
    assert body["detail"].startswith("The database could not be reached. Try again in a moment")


def test_signing_in_while_the_database_is_unreachable_says_so(client, unreachable_database):
    response = client.post(
        "/api/v1/auth/session", json={"email": "someone@example.com", "password": "x" * 12}
    )
    assert response.status_code == 503
    assert_safe(response)


def test_the_api_recovers_from_lost_connections_without_a_restart(
    client, analyst, session, db_engine
):
    assert client.get("/api/v1/transactions", headers=analyst).status_code == 200
    # End every connection to this database except this test's own, as a database restart does.
    ended = session.scalar(
        text(
            "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )
    )
    session.commit()
    try:
        assert ended >= 1  # the application's pooled connection was among them
        # The pool checks each connection before use, so the next request reconnects.
        response = client.get("/api/v1/transactions", headers=analyst)
        assert response.status_code == 200, response.text
    finally:
        db_engine.dispose()  # the test engine's own pooled connections were ended too


def test_a_database_error_that_is_not_an_outage_stays_a_plain_500(client, admin, monkeypatch):
    def timed_out(_session):
        raise OperationalError(
            "SELECT secret FROM users", {}, Exception("canceling statement due to timeout")
        )

    monkeypatch.setattr(health, "database_is_available", timed_out)
    response = client.get("/api/v1/system/status", headers=admin)
    assert response.status_code == 500
    assert assert_safe(response)["detail"] == "Internal server error."


def test_a_connection_lost_mid_request_is_an_outage(client, admin, monkeypatch):
    def lost(_session):
        raise connection_lost("SELECT 1")

    monkeypatch.setattr(health, "database_is_available", lost)
    response = client.get("/api/v1/system/status", headers=admin)
    assert response.status_code == 503
    assert_safe(response)


# The model failing.


def test_a_scoring_failure_stores_nothing_and_says_what_to_do(
    client, analyst, session, monkeypatch
):
    def broken(*_args, **_kwargs):
        raise RuntimeError("secret model internals")

    monkeypatch.setattr(prediction_service, "score_inputs", broken)
    response = client.post(
        PREDICT, headers=analyst, json={**FLAGGED, "external_transaction_id": "BROKEN-1"}
    )
    assert response.status_code == 500
    body = assert_safe(response)
    assert body["detail"] == (
        "The model could not score this transaction, so nothing was stored. "
        "Give an administrator the reference below."
    )
    assert session.scalar(select(func.count()).select_from(Transaction)) == 0
    assert session.scalar(select(func.count()).select_from(Prediction)) == 0
    assert (
        session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "transaction.predicted")
        )
        == 0
    )
    # The same request succeeds once the model works again: nothing half-stored blocks it.
    monkeypatch.undo()
    retried = client.post(
        PREDICT, headers=analyst, json={**FLAGGED, "external_transaction_id": "BROKEN-1"}
    )
    assert retried.status_code == 201, retried.text


# Batch jobs interrupted by lost connections.


def test_a_lost_connection_interrupts_a_batch_which_resumes_storing_every_row_once(
    client, analyst, settings, session, monkeypatch
):
    job_id = queue(client, analyst, 450, "LOSTCONN")
    real_chunk = batch_service._process_chunk
    calls = {"n": 0}

    def connection_drops_in_third_chunk(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise connection_lost()
        return real_chunk(*args, **kwargs)

    monkeypatch.setattr(batch_service, "_process_chunk", connection_drops_in_third_chunk)
    model = client.app.state.model
    assert batch_service.process_available_jobs(model, "first", settings) == 1
    session.expire_all()
    job = session.get(BatchJob, job_id)
    # Not failed: given back with its progress, for any worker to resume at once.
    assert (job.status, job.processed_records, job.worker_id, job.attempts) == (
        BatchStatus.PROCESSING,
        200,
        None,
        1,
    )
    assert job.error_message is None

    monkeypatch.setattr(batch_service, "_process_chunk", real_chunk)
    assert batch_service.process_available_jobs(model, "second", settings) == 1
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert (job.status, job.processed_records, job.attempts) == (BatchStatus.COMPLETED, 450, 2)
    assert stored_rows(session, job_id) == 450
    predictions = session.scalar(
        select(func.count())
        .select_from(Prediction)
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.batch_job_id == job_id)
    )
    assert predictions == 450  # one prediction per row, none repeated by the retry


def test_while_the_database_stays_down_the_lease_brings_the_job_back(
    client, analyst, settings, session, monkeypatch
):
    job_id = queue(client, analyst, 250, "STILLDOWN")
    real_chunk = batch_service._process_chunk
    calls = {"n": 0}

    def drops(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise connection_lost()
        return real_chunk(*args, **kwargs)

    def cannot_release(*_args, **_kwargs):
        raise connection_lost(statement=None)  # reconnecting fails too

    monkeypatch.setattr(batch_service, "_process_chunk", drops)
    monkeypatch.setattr(batch_service, "release_job", cannot_release)
    model = client.app.state.model
    batch_service.process_available_jobs(model, "first", settings)
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert (job.status, job.worker_id, job.processed_records) == (
        BatchStatus.PROCESSING,
        "first",
        100,
    )

    monkeypatch.undo()
    monkeypatch.setattr(get_settings(), "upload_tmp_dir", settings.upload_tmp_dir)
    monkeypatch.setattr(get_settings(), "batch_chunk_rows", 100)
    assert batch_service.process_available_jobs(model, "second", settings) == 0  # lease still held
    expire_lease(session, job_id)
    assert batch_service.process_available_jobs(model, "second", settings) == 1
    session.expire_all()
    assert session.get(BatchJob, job_id).status == BatchStatus.COMPLETED
    assert stored_rows(session, job_id) == 250


def test_a_database_error_that_is_not_an_outage_fails_the_job(
    client, analyst, settings, session, monkeypatch
):
    job_id = queue(client, analyst, 50, "TIMEOUT")

    def timed_out(*_args, **_kwargs):
        raise OperationalError("INSERT secret", {}, Exception("canceling statement due to timeout"))

    monkeypatch.setattr(batch_service, "_process_chunk", timed_out)
    batch_service.process_available_jobs(client.app.state.model, "w", settings)
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert job.status == BatchStatus.FAILED
    assert job.error_message == batch_service.FAILED_MESSAGE
    assert "secret" not in job.error_message


# Stale investigation changes.


@pytest.fixture
def investigator(headers_for):
    return headers_for(UserRole.INVESTIGATOR)


@pytest.fixture
def case(client, analyst) -> str:
    body = client.post(PREDICT, headers=analyst, json=FLAGGED).json()
    assert body["prediction"] == "FLAG_FOR_REVIEW"
    return f"/api/v1/investigations/{body['investigation_id']}"


def history_of(session, url: str) -> list[tuple]:
    investigation_id = uuid.UUID(url.rsplit("/", 1)[1])
    session.expire_all()
    return session.execute(
        select(InvestigationStatusHistory.from_status, InvestigationStatusHistory.to_status)
        .where(InvestigationStatusHistory.investigation_id == investigation_id)
        .order_by(InvestigationStatusHistory.created_at)
    ).all()


def test_a_change_based_on_a_stale_status_is_refused_and_changes_nothing(
    client, investigator, case, session
):
    assert client.patch(case, headers=investigator, json={"status": "ESCALATED"}).status_code == 200
    stale = client.patch(
        case, headers=investigator, json={"status": "CLOSED", "expected_status": "NEW"}
    )
    assert stale.status_code == 409
    assert assert_safe(stale)["detail"] == (
        "Someone else changed this investigation: its status is now Escalated. "
        "Review it and try again."
    )
    assert client.get(case, headers=investigator).json()["status"] == "ESCALATED"
    assert history_of(session, case) == [
        (None, InvestigationStatus.NEW),
        (InvestigationStatus.NEW, InvestigationStatus.ESCALATED),
    ]
    current = client.patch(
        case, headers=investigator, json={"status": "CLOSED", "expected_status": "ESCALATED"}
    )
    assert current.status_code == 200 and current.json()["status"] == "CLOSED"


def test_expected_status_alone_changes_nothing_and_is_refused(client, investigator, case):
    response = client.patch(case, headers=investigator, json={"expected_status": "NEW"})
    assert response.status_code == 422


def test_of_two_simultaneous_changes_from_the_same_status_exactly_one_applies(
    client, investigator, case, session
):
    changes = [
        {"status": "CLOSED", "expected_status": "NEW"},
        {"status": "ESCALATED", "expected_status": "NEW"},
    ] * 4
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda body: client.patch(case, headers=investigator, json=body), changes)
        )
    codes = sorted(result.status_code for result in results)
    assert codes == [200] + [409] * 7
    winner = next(result.json()["status"] for result in results if result.status_code == 200)
    assert history_of(session, case) == [
        (None, InvestigationStatus.NEW),
        (InvestigationStatus.NEW, InvestigationStatus(winner)),
    ]
