"""Fixtures for API tests: the real application, a real database and the frozen model."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from tests.conftest import empty_all_tables

from app.core.rate_limit import limiter
from app.models.enums import UserRole
from app.models.records import User
from app.security.passwords import hash_password
from app.security.tokens import create_access_token
from app.services.model_service import register_active_model

MODEL_FILE = (
    Path(__file__).resolve().parents[3]
    / "artifacts"
    / "models"
    / "fraud_detector_v1"
    / "model.joblib"
)
DEFAULT_PASSWORD = "correct horse battery staple"
# Hashing is deliberately slow, so test users share one precomputed hash where possible.
_DEFAULT_HASH = hash_password(DEFAULT_PASSWORD)


@pytest.fixture(scope="session")
def app_client(db_engine: Engine) -> Iterator[TestClient]:
    """Start the real application once, which loads and verifies the frozen model."""
    if not MODEL_FILE.is_file():
        pytest.skip("frozen model file is absent")
    from app.main import create_app

    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def session(db_engine: Engine, app_client: TestClient) -> Iterator[Session]:
    """Return a session on an empty database in which the model is registered."""
    empty_all_tables(db_engine)
    limiter.reset()
    with Session(db_engine, expire_on_commit=False) as db:
        register_active_model(db, app_client.app.state.model)
        yield db


@pytest.fixture
def client(app_client: TestClient, session: Session) -> TestClient:
    """Return a test client, after the database has been prepared."""
    return app_client


@pytest.fixture
def make_user(session: Session) -> Callable[..., User]:
    """Return a function that stores a user."""

    def _make(role: UserRole = UserRole.ANALYST, email: str | None = None, **values) -> User:
        user = User(
            email=email or f"{role.value}-{session.query(User).count()}@example.com",
            password_hash=_DEFAULT_HASH,
            role=role,
            **values,
        )
        session.add(user)
        session.commit()
        return user

    return _make


@pytest.fixture
def headers_for(make_user: Callable[..., User]) -> Callable[[UserRole], dict[str, str]]:
    """Return a function giving request headers for a new user with a role."""

    def _headers(role: UserRole) -> dict[str, str]:
        user = make_user(role)
        return {"Authorization": f"Bearer {create_access_token(user.id, user.token_version)}"}

    return _headers
