"""Delete records past their retention period. A dry run by default; --apply deletes.

    python -m app.commands.retention            # report what would be deleted
    python -m app.commands.retention --apply    # delete it, and record that in the audit log

Retention (approved in Phase 5):
- user_sessions: removed once the session ended (expired or was revoked, whichever came first)
  more than 7 days ago. Live sessions are never touched.
- audit_logs: removed when older than 365 days.
- rate_limit_events and rate_limit_windows: removed when older than 1 day, far beyond any limit's
  window, so no current count changes.

A record exactly at its cutoff is kept. Cutoffs are computed from the database clock, or from
the time passed in, and are reported with every count.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.orm import Session

from app.models.records import AuditLog, RateLimitEvent, RateLimitWindow, UserSession
from app.services.audit_service import record_event

SESSION_DAYS = 7
AUDIT_DAYS = 365
RATE_LIMIT_DAYS = 1


@dataclass(frozen=True)
class Category:
    """One kind of record, how long it is kept, and the time it is judged by."""

    name: str
    model: type
    keep: timedelta
    timestamp: ColumnElement


CATEGORIES = (
    # LEAST ignores NULL, so an unrevoked session is judged by its expiry.
    Category(
        "expired_sessions",
        UserSession,
        timedelta(days=SESSION_DAYS),
        func.least(UserSession.expires_at, UserSession.revoked_at),
    ),
    Category("audit_logs", AuditLog, timedelta(days=AUDIT_DAYS), AuditLog.created_at),
    Category(
        "rate_limit_events",
        RateLimitEvent,
        timedelta(days=RATE_LIMIT_DAYS),
        RateLimitEvent.occurred_at,
    ),
    Category(
        "rate_limit_windows",
        RateLimitWindow,
        timedelta(days=RATE_LIMIT_DAYS),
        RateLimitWindow.window_start,
    ),
)


@dataclass(frozen=True)
class Outcome:
    """What one category's run found, or removed."""

    name: str
    cutoff: datetime
    count: int


def run(session: Session, apply: bool, now: datetime | None = None) -> list[Outcome]:
    """Count, and if `apply`, delete, everything past its cutoff. Commits only when applying."""
    now = now or session.scalar(select(func.now()))
    outcomes = []
    for category in CATEGORIES:
        cutoff = now - category.keep
        expired = category.timestamp < cutoff
        if apply:
            count = session.execute(delete(category.model).where(expired)).rowcount
        else:
            count = session.scalar(select(func.count()).select_from(category.model).where(expired))
        outcomes.append(Outcome(category.name, cutoff, count or 0))
    if apply:
        record_event(
            session,
            None,
            "retention.applied",
            "maintenance",
            None,
            {o.name: {"deleted": o.count, "cutoff": o.cutoff.isoformat()} for o in outcomes},
        )
        session.commit()
    else:
        session.rollback()
    return outcomes


def report(outcomes: list[Outcome], applied: bool) -> str:
    verb = "Deleted" if applied else "Would delete"
    lines = [f"{verb} {o.count} {o.name} older than {o.cutoff.isoformat()}" for o in outcomes]
    lines.append("Applied." if applied else "Dry run: nothing was deleted. Use --apply to delete.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="delete; without it, only report")
    arguments = parser.parse_args(argv)
    from app.database.session import session_scope

    with session_scope() as session:
        outcomes = run(session, arguments.apply)
    print(report(outcomes, arguments.apply))
    return 0


if __name__ == "__main__":
    sys.exit(main())
