"""The batch queue (Phase 5 M4): claiming, leases, resuming, ownership and attempt limits.

Rows without an identifier get a new random one when stored, so if any chunk were stored twice
those rows would be duplicated. Every test therefore includes such rows and counts them.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, text, update

from app.core.config import get_settings
from app.database.session import session_scope
from app.models.enums import BatchStatus, UserRole
from app.models.records import BatchJob, BatchUpload, Transaction
from app.services import batch_service

pytestmark = pytest.mark.database

UPLOAD = "/api/v1/batches/upload"
HEADER = "external_transaction_id,amount,transaction_type,step,destination_category"


class Crash(BaseException):
    """Stands in for the process dying: not an Exception, so nothing in the worker catches it."""


def csv_text(rows: int, prefix: str) -> str:
    lines = [HEADER]
    for index in range(rows):
        identifier = f"{prefix}-{index}" if index % 2 == 0 else ""  # half have no identifier
        lines.append(f"{identifier},{100 + index}.00,TRANSFER,{1 + index % 700},customer")
    return "\n".join(lines) + "\n"


@pytest.fixture
def analyst(headers_for):
    return headers_for(UserRole.ANALYST)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    current = get_settings()
    monkeypatch.setattr(current, "upload_tmp_dir", tmp_path)
    monkeypatch.setattr(current, "batch_chunk_rows", 100)
    return current


def queue(client, headers, rows: int, prefix: str) -> str:
    response = client.post(
        UPLOAD,
        headers=headers,
        files={"file": ("q.csv", csv_text(rows, prefix).encode(), "text/csv")},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def stored_rows(session, job_id) -> int:
    return session.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.batch_job_id == job_id)
    )


def expire_lease(session, job_id) -> None:
    session.execute(
        update(BatchJob)
        .where(BatchJob.id == job_id)
        .values(lease_expires_at=func.clock_timestamp() - text("interval '1 second'"))
    )
    session.commit()


def test_upload_is_stored_in_the_database_and_queued(client, analyst, settings, session):
    job_id = queue(client, analyst, 5, "STORE")
    job = session.get(BatchJob, job_id)
    assert job.status == BatchStatus.PENDING and job.attempts == 0
    assert session.get(BatchUpload, job_id).content.startswith(HEADER.encode())
    assert list(settings.upload_tmp_dir.iterdir()) == []  # nothing left on this machine's disk
    assert batch_service.process_available_jobs(client.app.state.model, "w1", settings) == 1
    session.expire_all()
    assert session.get(BatchJob, job_id).status == BatchStatus.COMPLETED
    assert session.get(BatchUpload, job_id) is None  # bytes removed when the job ends


def test_simultaneous_claims_never_take_the_same_job(client, analyst, settings, session):
    jobs = {queue(client, analyst, 3, f"CLAIM{n}") for n in range(3)}

    def claim(worker: str):
        with session_scope() as own:
            return batch_service.claim_next_job(own, worker, 60, 3)

    with ThreadPoolExecutor(max_workers=6) as pool:
        claimed = list(pool.map(claim, [f"w{n}" for n in range(6)]))
    taken = [str(job) for job in claimed if job is not None]
    assert sorted(taken) == sorted(jobs)  # each job exactly once; the other three got nothing
    owners = session.execute(select(BatchJob.worker_id)).scalars().all()
    assert len(set(owners)) == 3


def test_a_crash_mid_chunk_resumes_after_the_last_commit_without_duplicates(
    client, analyst, settings, session, monkeypatch
):
    job_id = queue(client, analyst, 450, "CRASH")
    real_chunk = batch_service._process_chunk
    calls = {"n": 0}

    def dies_in_third_chunk(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise Crash
        return real_chunk(*args, **kwargs)

    monkeypatch.setattr(batch_service, "_process_chunk", dies_in_third_chunk)
    with pytest.raises(Crash):
        batch_service.process_available_jobs(client.app.state.model, "first", settings)
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert (job.status, job.processed_records, job.worker_id) == (
        BatchStatus.PROCESSING,
        200,
        "first",
    )
    assert stored_rows(session, job_id) == 200  # the third chunk's rows were rolled back

    monkeypatch.setattr(batch_service, "_process_chunk", real_chunk)
    # Not claimable while the dead worker's lease runs; claimable once it expires.
    assert batch_service.process_available_jobs(client.app.state.model, "second", settings) == 0
    expire_lease(session, job_id)
    assert batch_service.process_available_jobs(client.app.state.model, "second", settings) == 1
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert (job.status, job.processed_records, job.attempts) == (BatchStatus.COMPLETED, 450, 2)
    assert stored_rows(session, job_id) == 450
    identifiers = session.scalars(
        select(Transaction.external_transaction_id).where(Transaction.batch_job_id == job_id)
    ).all()
    assert len(set(identifiers)) == 450


def test_a_worker_that_lost_its_lease_stores_nothing(client, analyst, settings, session):
    job_id = queue(client, analyst, 150, "LOST")

    with session_scope() as own:
        assert str(batch_service.claim_next_job(own, "slow", 60, 3)) == job_id
    expire_lease(session, job_id)
    with session_scope() as own:
        assert str(batch_service.claim_next_job(own, "fast", 60, 3)) == job_id
    # The slow worker wakes up and tries to carry on: it no longer owns the job.
    outcome = batch_service.process_job(job_id, "slow", client.app.state.model, settings)
    assert outcome == "lost"
    assert stored_rows(session, job_id) == 0
    assert (
        batch_service.process_job(job_id, "fast", client.app.state.model, settings) == "completed"
    )
    assert stored_rows(session, job_id) == 150


def test_a_job_interrupted_too_often_is_failed_and_its_bytes_removed(
    client, analyst, settings, session
):
    job_id = queue(client, analyst, 5, "TIRED")
    session.execute(
        update(BatchJob)
        .where(BatchJob.id == job_id)
        .values(
            status=BatchStatus.PROCESSING, worker_id="gone", attempts=settings.batch_max_attempts
        )
    )
    session.commit()
    expire_lease(session, job_id)
    assert batch_service.process_available_jobs(client.app.state.model, "w", settings) == 0
    session.expire_all()
    job = session.get(BatchJob, job_id)
    assert job.status == BatchStatus.FAILED
    assert f"interrupted {settings.batch_max_attempts} times" in job.error_message
    assert session.get(BatchUpload, job_id) is None


def test_stopping_gives_the_job_back_for_immediate_resumption(client, analyst, settings, session):
    job_id = queue(client, analyst, 300, "STOP")

    with session_scope() as own:
        batch_service.claim_next_job(own, "stopping", 60, 3)
    stop = threading.Event()
    stop.set()
    assert (
        batch_service.process_job(job_id, "stopping", client.app.state.model, settings, stop)
        == "released"
    )
    session.expire_all()
    assert session.get(BatchJob, job_id).worker_id is None
    # No lease to wait for: another worker resumes at once.
    assert batch_service.process_available_jobs(client.app.state.model, "next", settings) == 1
    assert stored_rows(session, job_id) == 300


def test_several_workers_on_several_jobs_store_every_row_once(client, analyst, settings, session):
    jobs = [queue(client, analyst, 250, f"MANY{n}") for n in range(4)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        claimed = list(
            pool.map(
                lambda name: batch_service.process_available_jobs(
                    client.app.state.model, name, settings
                ),
                ["a", "b", "c"],
            )
        )
    assert sum(claimed) == 4
    session.expire_all()
    for job_id in jobs:
        job = session.get(BatchJob, job_id)
        assert (job.status, job.processed_records, job.attempts) == (BatchStatus.COMPLETED, 250, 1)
        assert stored_rows(session, job_id) == 250
