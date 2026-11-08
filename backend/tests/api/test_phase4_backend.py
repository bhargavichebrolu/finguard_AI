"""API tests of the Phase 4 backend additions: assignees, the model report, headers and proxies."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.frozen_model import FROZEN_MODEL_VERSION, FROZEN_THRESHOLD
from app.models.enums import UserRole

pytestmark = pytest.mark.database

REPO_ROOT = Path(__file__).resolve().parents[3]
SAVED_REPORT = json.loads(
    (REPO_ROOT / "artifacts" / "metadata" / "model_v1_report.json").read_text(encoding="utf-8")
)
ASSIGNABLE = "/api/v1/users/assignable"


def test_assignable_users_lists_active_investigators_and_admins_only(
    client, make_user, headers_for
):
    make_user(UserRole.INVESTIGATOR, email="b-investigator@example.com")
    make_user(UserRole.ADMIN, email="a-admin@example.com")
    make_user(UserRole.ANALYST, email="analyst@example.com")
    make_user(UserRole.INVESTIGATOR, email="gone@example.com", is_active=False)
    body = client.get(ASSIGNABLE, headers=headers_for(UserRole.INVESTIGATOR)).json()
    emails = [row["email"] for row in body]
    assert "a-admin@example.com" in emails and "b-investigator@example.com" in emails
    assert "analyst@example.com" not in emails and "gone@example.com" not in emails
    assert emails == sorted(emails)
    assert set(body[0]) == {"id", "email", "role"}


@pytest.mark.parametrize("role", [UserRole.ANALYST, UserRole.DEMO])
def test_assignable_users_need_investigation_rights(client, headers_for, role):
    assert client.get(ASSIGNABLE, headers=headers_for(role)).status_code == 403


def test_model_report_is_served_unchanged(client, headers_for):
    response = client.get("/api/v1/models/report", headers=headers_for(UserRole.DEMO))
    assert response.status_code == 200
    body = response.json()
    assert body == SAVED_REPORT
    assert body["model_version"] == FROZEN_MODEL_VERSION
    assert body["threshold"] == FROZEN_THRESHOLD


def test_api_responses_carry_a_strict_content_security_policy(client, headers_for):
    for path in ("/health", "/openapi.json", "/api/v1/auth/me"):
        policy = client.get(path, headers=headers_for(UserRole.ANALYST)).headers[
            "content-security-policy"
        ]
        assert policy == "default-src 'none'; frame-ancestors 'none'"


def test_documentation_pages_get_their_own_policy(client):
    policy = client.get("/docs").headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in policy
    assert "frame-ancestors 'none'" in policy
    assert "default-src 'none'" in policy


def _failed_logins_from(client, forwarded_for: str, count: int) -> list[int]:
    return [
        client.post(
            "/api/v1/auth/login",
            data={"username": "ana@example.com", "password": "wrong password here"},
            headers={"X-Forwarded-For": forwarded_for},
        ).status_code
        for _ in range(count)
    ]


def test_forwarded_addresses_are_ignored_by_default(client, make_user):
    assert get_settings().trusted_proxies == []
    make_user(email="ana@example.com")
    attempts = get_settings().login_rate_limit_attempts
    _failed_logins_from(client, "203.0.113.1", attempts)
    # A spoofed header must not give the attacker a fresh rate-limit allowance.
    assert _failed_logins_from(client, "203.0.113.2", 1) == [429]


def test_forwarded_addresses_are_used_only_from_a_configured_proxy(monkeypatch, make_user, session):
    from app.main import create_app

    monkeypatch.setattr(get_settings(), "trusted_proxy_ips", "testclient")
    proxied = TestClient(create_app())
    make_user(email="ana@example.com")
    attempts = get_settings().login_rate_limit_attempts
    assert _failed_logins_from(proxied, "203.0.113.1", attempts + 1)[-1] == 429
    assert _failed_logins_from(proxied, "203.0.113.2", 1) == [401]


def test_wildcard_proxy_trust_is_refused():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="wildcard"):
        Settings(
            database_url="postgresql+psycopg://u:p@127.0.0.1:1/x_test",
            secret_key="k" * 40,
            trusted_proxy_ips="*",
            _env_file=None,
        )


def test_container_command_disables_uvicorn_proxy_trust():
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert '"--no-proxy-headers"' in dockerfile
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "--no-proxy-headers" in makefile
