"""Phase 6: the administrator command, which now ships in the API image for deployed hosts."""

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from tests.conftest import empty_all_tables

from app.commands import create_admin
from app.models.enums import UserRole
from app.models.records import AuditLog, User
from app.security.passwords import verify_password

pytestmark = pytest.mark.database
PASSWORD = "a long enough administrator password"


@pytest.fixture
def empty(db_engine: Engine) -> Engine:
    empty_all_tables(db_engine)
    return db_engine


def test_creates_an_administrator_without_printing_the_password(empty, monkeypatch, capsys):
    monkeypatch.setenv(create_admin.PASSWORD_VARIABLE, PASSWORD)
    assert create_admin.main(["--email", "Admin@Example.com"]) == 0
    output = capsys.readouterr().out
    assert PASSWORD not in output
    with Session(empty) as session:
        user = session.scalars(select(User)).one()
        assert user.role is UserRole.ADMIN and user.is_active
        assert user.password_hash != PASSWORD and verify_password(user.password_hash, PASSWORD)
        assert session.scalars(select(AuditLog)).first() is not None  # the creation is audited


def test_refuses_a_second_account_with_the_same_email(empty, monkeypatch, capsys):
    monkeypatch.setenv(create_admin.PASSWORD_VARIABLE, PASSWORD)
    assert create_admin.main(["--email", "admin@example.com"]) == 0
    assert create_admin.main(["--email", "admin@example.com"]) == 1
    with Session(empty) as session:
        assert len(session.scalars(select(User)).all()) == 1


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("not-an-email", PASSWORD, "not valid"),
        ("admin@example.com", "short", "characters"),
    ],
)
def test_refuses_bad_input_and_stores_nothing(empty, monkeypatch, capsys, email, password, message):
    monkeypatch.setenv(create_admin.PASSWORD_VARIABLE, password)
    assert create_admin.main(["--email", email]) == 1
    assert message in capsys.readouterr().out
    with Session(empty) as session:
        assert session.scalars(select(User)).all() == []
