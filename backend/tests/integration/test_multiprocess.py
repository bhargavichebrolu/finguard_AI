"""Several API processes share rate limits, the model registry and the batch queue (Phase 5 M3, M4).

Each test starts real Uvicorn processes against the test database, as separate containers or
workers would run, and talks to them over HTTP.
"""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.conftest import TEST_DATABASE_URL, empty_all_tables

from app.models.enums import UserRole
from app.models.records import ModelVersion, Transaction
from app.services.auth_service import create_user

pytestmark = pytest.mark.database

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_FILE = BACKEND_DIR.parent / "artifacts" / "models" / "fraud_detector_v1" / "model.joblib"
EMAIL = "multiprocess@example.com"
PASSWORD = "a long and correct test password"
LOGIN_LIMIT = 5


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_healthy(process: subprocess.Popen, base: str) -> None:
    deadline = time.monotonic() + 90
    while True:
        if process.poll() is not None:
            raise RuntimeError(f"API process exited with code {process.returncode}")
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                return
        except httpx.TransportError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError("API process did not become healthy")
        time.sleep(0.3)


class ApiProcess(str):
    """A running API process's base address, which also carries the process itself."""

    process: subprocess.Popen


@contextmanager
def api_processes(
    count: int, store: str = "database", settings: list[dict[str, str]] | None = None
) -> Iterator[list[ApiProcess]]:
    """Start `count` API processes at the same moment and wait for all. Yields their addresses.

    All are launched before any is waited for, so their start-ups overlap, as when several
    containers or workers start together. `settings` gives extra environment per process.
    """
    base_env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "multiprocess-test-signing-key-" + "x" * 32,
        "RATE_LIMIT_STORE": store,
        "BATCH_WORKER_ENABLED": "true",
    }
    running: list[ApiProcess] = []
    try:
        for index in range(count):
            port = free_port()
            env = {**base_env, **((settings or [{}] * count)[index])}
            command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1"]
            command += ["--port", str(port), "--no-proxy-headers"]
            handle = ApiProcess(f"http://127.0.0.1:{port}")
            handle.process = subprocess.Popen(
                command,
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            running.append(handle)
        for handle in running:
            _wait_until_healthy(handle.process, handle)
        yield running
    finally:
        for handle in running:
            if handle.process.poll() is None:
                handle.process.terminate()
        for handle in running:
            try:
                handle.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                handle.process.kill()


def sign_in(base: str, password: str) -> int:
    response = httpx.post(
        f"{base}/api/v1/auth/login", data={"username": EMAIL, "password": password}, timeout=30
    )
    return response.status_code


@pytest.fixture
def account(db_engine):
    if not MODEL_FILE.is_file():
        pytest.skip("frozen model file is absent")
    empty_all_tables(db_engine)
    with Session(db_engine) as session:
        create_user(session, EMAIL, PASSWORD, UserRole.ANALYST, None)
    yield
    empty_all_tables(db_engine)


def test_failed_sign_ins_are_counted_across_processes_and_restarts(account):
    with api_processes(2) as (first, second):
        for attempt in range(LOGIN_LIMIT):
            assert sign_in(first if attempt % 2 == 0 else second, "wrong password") == 401
        # Five failures in total, split between two processes, reach the limit in both.
        assert sign_in(first, "wrong password") == 429
        assert sign_in(second, PASSWORD) == 429
    # A newly started process still refuses: the counts outlived the processes.
    with api_processes(1) as (restarted,):
        assert sign_in(restarted, PASSWORD) == 429


def test_the_memory_store_lets_each_process_allow_the_full_limit(account):
    # Records why M3 moved the counts to the database: per-process counts doubled the limit.
    with api_processes(2, "memory") as (first, second):
        for attempt in range(2 * LOGIN_LIMIT):
            assert sign_in(first if attempt % 2 == 0 else second, "wrong password") == 401
        assert sign_in(first, "wrong password") == 429
    with api_processes(1, "memory") as (restarted,):
        assert sign_in(restarted, PASSWORD) == 200  # a restart forgot every failure


def test_processes_starting_together_register_the_model_once(db_engine, account):
    with Session(db_engine) as session:
        session.execute(ModelVersion.__table__.delete())
        session.commit()
    # Four processes start together against an empty model registry.
    with api_processes(4) as bases:
        assert all(httpx.get(f"{base}/health").status_code == 200 for base in bases)
    with Session(db_engine) as session:
        rows = session.scalar(select(func.count()).select_from(ModelVersion))
        active = session.scalar(
            select(func.count()).select_from(ModelVersion).where(ModelVersion.is_active)
        )
    assert (rows, active) == (1, 1)


# ---------------------------------------------------------------- batch queue (Phase 5 M4)

BATCH_HEADER = "external_transaction_id,amount,transaction_type,step,destination_category"


def batch_csv(rows: int, prefix: str) -> bytes:
    """Half the rows have no identifier: stored twice, they would show up as extra rows."""
    lines = [BATCH_HEADER]
    for index in range(rows):
        identifier = f"{prefix}-{index}" if index % 2 == 0 else ""
        lines.append(f"{identifier},{100 + index}.00,CASH_OUT,{1 + index % 700},customer")
    return ("\n".join(lines) + "\n").encode()


def bearer(base: str) -> dict[str, str]:
    response = httpx.post(
        f"{base}/api/v1/auth/login", data={"username": EMAIL, "password": PASSWORD}, timeout=30
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(base: str, headers: dict[str, str], content: bytes) -> str:
    response = httpx.post(
        f"{base}/api/v1/batches/upload",
        headers=headers,
        files={"file": ("rows.csv", content, "text/csv")},
        timeout=60,
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def wait_for(base: str, headers: dict[str, str], job_id: str, done, timeout: float = 180) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = httpx.get(f"{base}/api/v1/batches/{job_id}", headers=headers, timeout=10).json()
        if done(job):
            return job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} did not reach the expected state: {job}")


def stored(db_engine, job_id: str) -> tuple[int, int]:
    with Session(db_engine) as session:
        total = session.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.batch_job_id == job_id)
        )
        distinct = session.scalar(
            select(func.count(func.distinct(Transaction.external_transaction_id))).where(
                Transaction.batch_job_id == job_id
            )
        )
    return total, distinct


QUEUE_SETTINGS = {
    "BATCH_CHUNK_ROWS": "200",
    "BATCH_LEASE_SECONDS": "3",
    "BATCH_POLL_SECONDS": "0.5",
}


def test_a_killed_process_s_batch_is_finished_by_another_process(account, db_engine, tmp_path):
    rows = 6000
    first_dir, second_dir = tmp_path / "first", tmp_path / "second"
    with api_processes(1, settings=[{**QUEUE_SETTINGS, "UPLOAD_TMP_DIR": str(first_dir)}]) as (
        first,
    ):
        headers = bearer(first)
        job_id = upload(first, headers, batch_csv(rows, "KILL"))
        part = wait_for(first, headers, job_id, lambda j: 400 <= j["processed_records"] < rows)
        first.process.kill()  # no shutdown: the lease is never released
        first.process.wait(timeout=20)
    stopped_at = part["processed_records"]

    # A second process with its own, empty upload folder: the job's bytes are in the database.
    with api_processes(1, settings=[{**QUEUE_SETTINGS, "UPLOAD_TMP_DIR": str(second_dir)}]) as (
        second,
    ):
        headers = bearer(second)
        job = wait_for(second, headers, job_id, lambda j: j["status"] == "COMPLETED")
    assert job["processed_records"] == job["succeeded_records"] == rows
    assert job["attempts"] == 2
    assert stopped_at < rows
    assert stored(db_engine, job_id) == (rows, rows)  # every row once, none twice


def test_two_processes_share_the_queue_and_store_every_row_once(account, db_engine):
    rows = 1500
    with api_processes(2, settings=[QUEUE_SETTINGS, QUEUE_SETTINGS]) as (first, second):
        headers = bearer(first)
        jobs = [upload(first, headers, batch_csv(rows, f"SHARE{n}")) for n in range(4)]
        for job_id in jobs:
            job = wait_for(second, headers, job_id, lambda j: j["status"] == "COMPLETED")
            assert (job["processed_records"], job["attempts"]) == (rows, 1)
    for job_id in jobs:
        assert stored(db_engine, job_id) == (rows, rows)
