"""The retention command (Phase 5 M5): cutoffs, boundaries, dry runs and exact deletion."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.conftest import empty_all_tables

from app.commands import retention
from app.models.enums import UserRole
from app.models.records import AuditLog, RateLimitEvent, RateLimitWindow, User, UserSession

pytestmark = pytest.mark.database

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
SECOND = timedelta(seconds=1)
SESSION_CUTOFF = NOW - timedelta(days=7)
AUDIT_CUTOFF = NOW - timedelta(days=365)
RATE_CUTOFF = NOW - timedelta(days=1)


@pytest.fixture
def db(db_engine):
    empty_all_tables(db_engine)
    with Session(db_engine, expire_on_commit=False) as session:
        yield session
    empty_all_tables(db_engine)


def add_session(db, user, *, expires_at, revoked_at=None, label=""):
    row = UserSession(
        user_id=user.id,
        csrf_token_hash=f"{label:0<64}"[:64],
        created_at=expires_at - timedelta(minutes=30),
        expires_at=expires_at,
        revoked_at=revoked_at,
    )
    db.add(row)
    return row


@pytest.fixture
def records(db):
    user = User(email="keep@example.com", password_hash="x", role=UserRole.ANALYST)
    db.add(user)
    db.flush()
    sessions = {
        "ended_long_ago": add_session(db, user, expires_at=SESSION_CUTOFF - SECOND, label="a"),
        "ended_at_cutoff": add_session(db, user, expires_at=SESSION_CUTOFF, label="b"),
        "ended_just_after_cutoff": add_session(
            db, user, expires_at=SESSION_CUTOFF + SECOND, label="c"
        ),
        "live": add_session(db, user, expires_at=NOW + timedelta(minutes=10), label="d"),
        # Revoked eight days ago, though its expiry would have been later: judged by revocation.
        "revoked_long_ago": add_session(
            db, user, expires_at=NOW, revoked_at=SESSION_CUTOFF - timedelta(days=1), label="e"
        ),
        "revoked_recently": add_session(
            db, user, expires_at=NOW, revoked_at=NOW - timedelta(days=1), label="f"
        ),
    }
    for name, created in (
        ("old", AUDIT_CUTOFF - SECOND),
        ("at_cutoff", AUDIT_CUTOFF),
        ("recent", AUDIT_CUTOFF + SECOND),
    ):
        db.add(AuditLog(action=f"test.{name}", entity_type="test", created_at=created))
    db.add(RateLimitEvent(key="old", occurred_at=RATE_CUTOFF - SECOND))
    db.add(RateLimitEvent(key="recent", occurred_at=RATE_CUTOFF + SECOND))
    db.add(RateLimitWindow(key="old", window_start=RATE_CUTOFF - SECOND, count=3))
    db.add(RateLimitWindow(key="recent", window_start=NOW, count=1))
    db.commit()
    return sessions


def counts(db) -> dict[str, int]:
    return {
        "sessions": db.scalar(select(func.count()).select_from(UserSession)),
        "audit": db.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action.like("test.%"))
        ),
        "events": db.scalar(select(func.count()).select_from(RateLimitEvent)),
        "windows": db.scalar(select(func.count()).select_from(RateLimitWindow)),
    }


EXPECTED = {"expired_sessions": 2, "audit_logs": 1, "rate_limit_events": 1, "rate_limit_windows": 1}


def test_dry_run_reports_counts_and_cutoffs_and_deletes_nothing(db, records):
    before = counts(db)
    outcomes = retention.run(db, apply=False, now=NOW)
    assert {o.name: o.count for o in outcomes} == EXPECTED
    cutoffs = {o.name: o.cutoff for o in outcomes}
    assert cutoffs == {
        "expired_sessions": SESSION_CUTOFF,
        "audit_logs": AUDIT_CUTOFF,
        "rate_limit_events": RATE_CUTOFF,
        "rate_limit_windows": RATE_CUTOFF,
    }
    assert counts(db) == before


def test_apply_deletes_exactly_what_the_dry_run_reported(db, records):
    assert {o.name: o.count for o in retention.run(db, apply=True, now=NOW)} == EXPECTED
    remaining = {row.csrf_token_hash[0] for row in db.scalars(select(UserSession))}
    # Kept: at the cutoff, just after it, live, and recently revoked.
    assert remaining == {"b", "c", "d", "f"}
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.action.like("test.%"))))
    assert actions == {"test.at_cutoff", "test.recent"}
    assert set(db.scalars(select(RateLimitEvent.key))) == {"recent"}
    assert set(db.scalars(select(RateLimitWindow.key))) == {"recent"}


def test_applying_is_recorded_and_running_again_deletes_nothing(db, records):
    retention.run(db, apply=True, now=NOW)
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "retention.applied"))
    assert entry.details["expired_sessions"]["deleted"] == 2
    assert entry.details["audit_logs"]["cutoff"] == AUDIT_CUTOFF.isoformat()
    assert all(o.count == 0 for o in retention.run(db, apply=True, now=NOW))


def test_the_command_is_a_dry_run_unless_told_to_apply(db, records, capsys):
    before = counts(db)
    assert retention.main([]) == 0
    output = capsys.readouterr().out
    assert "Would delete" in output and "Dry run: nothing was deleted" in output
    assert counts(db) == before
    assert retention.main(["--apply"]) == 0
    assert "Deleted" in capsys.readouterr().out
