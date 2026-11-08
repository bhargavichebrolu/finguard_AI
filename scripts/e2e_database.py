"""Prepare and adjust the browser-test database. It refuses any database not named *_test.

Commands:
  seed --out FILE         Empty the application tables (keeping the registered model), create
                          one account per test role with a random password, and write the
                          credentials to FILE, which is Git-ignored. Passwords are never printed.
  expire-sessions EMAIL   Mark that account's live sessions as expired, to test expiry.

The address comes from TEST_DATABASE_URL, from the environment or the repository's .env.
"""

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, make_url, select, text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_MODEL_VERSION = "fraud_detector_v1"
KEPT_TABLES = {"model_versions"}

# Each test account has one job, so a test that signs out, changes a password or is
# deactivated cannot disturb another test's session.
ACCOUNTS = {
    "admin": "admin",
    "investigator": "investigator",
    "analyst": "analyst",
    "demo": "demo",
    "colleague": "investigator",
    "logout": "analyst",
    "expiry": "analyst",
    "password": "analyst",
    "deactivate": "analyst",
}
EMAIL_DOMAIN = "e2e.example.com"


def test_database_url() -> str:
    """Return TEST_DATABASE_URL, refusing anything that is not clearly a test database."""
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(REPO_ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        raise SystemExit("TEST_DATABASE_URL is not set.")
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise SystemExit(f"Refusing to use the database named {name!r}: it must end in _test.")
    return url


def configure_settings(url: str) -> None:
    """Point the application settings at the test database before any app module reads them."""
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("SECRET_KEY", "seed-script-unused-signing-key-" + "x" * 32)


def email_for(name: str) -> str:
    return f"{name}@{EMAIL_DOMAIN}"


def seed(url: str, out: Path) -> int:
    configure_settings(url)
    from app.database.base import Base
    from app.models import records  # noqa: F401  (registers the tables)
    from app.models.enums import UserRole
    from app.services.auth_service import create_user

    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with Session(engine) as session:
        registered = session.scalar(
            select(records.ModelVersion).where(
                records.ModelVersion.version == FROZEN_MODEL_VERSION,
                records.ModelVersion.is_active,
            )
        )
        if registered is None:
            print(
                "The test database has no registered model. The backend test suite empties it, "
                "so restart the browser-test API: python scripts/e2e_stack.py up"
            )
            return 1
        names = ", ".join(
            f'"{table.name}"'
            for table in Base.metadata.sorted_tables
            if table.name not in KEPT_TABLES
        )
        session.execute(text(f"TRUNCATE {names} CASCADE"))
        session.commit()

        accounts = {}
        for name, role in ACCOUNTS.items():
            password = secrets.token_urlsafe(18)
            create_user(session, email_for(name), password, UserRole(role), None)
            accounts[name] = {"email": email_for(name), "password": password, "role": role}

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(accounts, indent=2), encoding="utf-8")
    engine.dispose()
    print(f"Seeded {len(accounts)} test accounts on {make_url(url).database}.")
    return 0


def expire_sessions(url: str, email: str) -> int:
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE user_sessions SET expires_at = now() - interval '1 minute' "
                "WHERE revoked_at IS NULL AND user_id = (SELECT id FROM users WHERE email = :email)"
            ),
            {"email": email.lower()},
        )
    engine.dispose()
    print(f"Expired {result.rowcount} session(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    seed_parser = commands.add_parser("seed")
    seed_parser.add_argument("--out", type=Path, required=True)
    expire_parser = commands.add_parser("expire-sessions")
    expire_parser.add_argument("email")
    arguments = parser.parse_args(argv)

    url = test_database_url()
    if arguments.command == "seed":
        return seed(url, arguments.out)
    return expire_sessions(url, arguments.email)


if __name__ == "__main__":
    sys.exit(main())
