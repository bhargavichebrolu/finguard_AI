"""Alembic's entry point. It takes the database address from the application settings."""

from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.database.base import Base
from app.models import records  # noqa: F401  (importing registers the tables on Base.metadata)

_CONNECT_TIMEOUT_SECONDS = 10


def run_migrations_online() -> None:
    """Apply migrations over a real connection, in one transaction."""
    engine = create_engine(
        get_settings().database_url.get_secret_value(),
        connect_args={"connect_timeout": _CONNECT_TIMEOUT_SECONDS},
    )
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not used in this project.")
run_migrations_online()
