"""Database engine and sessions. The connection address comes only from settings."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_CONNECT_TIMEOUT_SECONDS = 5


@lru_cache
def get_engine() -> Engine:
    """Return the one connection pool for this process."""
    return create_engine(
        get_settings().database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": _CONNECT_TIMEOUT_SECONDS},
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Provide a session for one request. Anything not committed is rolled back at the end."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a session outside a request, such as a background task or a start-up step."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()


def database_is_available(session: Session) -> bool:
    """Return True if the database answers a simple query."""
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        session.rollback()
        return False
    return True
