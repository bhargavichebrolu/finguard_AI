"""Several API processes share one set of rate limits and register the model safely (Phase 5 M3).

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
from app.models.records import ModelVersion
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


@contextmanager
def api_processes(count: int, store: str = "database") -> Iterator[list[str]]:
    """Start `count` API processes at the same moment and wait for all. Yields their addresses.

    All are launched before any is waited for, so their start-ups overlap, as when several
    containers or workers start together.
    """
    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "multiprocess-test-signing-key-" + "x" * 32,
        "RATE_LIMIT_STORE": store,
    }
    running: list[tuple[subprocess.Popen, str]] = []
    try:
        for _ in range(count):
            port = free_port()
            command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1"]
            command += ["--port", str(port), "--no-proxy-headers"]
            process = subprocess.Popen(
                command,
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            running.append((process, f"http://127.0.0.1:{port}"))
        for process, base in running:
            _wait_until_healthy(process, base)
        yield [base for _, base in running]
    finally:
        for process, _ in running:
            process.terminate()
        for process, _ in running:
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()


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
