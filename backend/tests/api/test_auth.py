"""API tests of health, sign-in, tokens, permissions, accounts and safe errors."""

import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select
from tests.api.conftest import DEFAULT_PASSWORD

from app.core.config import get_settings
from app.core.frozen_model import FROZEN_MODEL_SHA256, FROZEN_MODEL_VERSION, FROZEN_THRESHOLD
from app.models.enums import UserRole
from app.models.records import AuditLog, User
from app.security.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.security.tokens import create_access_token

pytestmark = pytest.mark.database

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
# Signing in and out must work without a session. Everything else needs one.
PUBLIC_PATHS = {"/health", LOGIN, "/api/v1/auth/session"}
FILE_DOWNLOAD_SUFFIXES = ("/export", "/errors")


def login(client, email, password=DEFAULT_PASSWORD):
    return client.post(LOGIN, data={"username": email, "password": password})


def bearer(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.token_version)}"}


def test_health_is_public_and_reveals_nothing(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_the_api(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "FinGuard AI API"
    assert "bearer" in str(schema["components"]["securitySchemes"]).lower()


def test_system_status_reports_the_frozen_model(client, headers_for):
    body = client.get("/api/v1/system/status", headers=headers_for(UserRole.ANALYST)).json()
    assert body["status"] == "ok"
    assert body["database_available"] is True
    assert body["model_version"] == FROZEN_MODEL_VERSION
    assert body["model_sha256"] == FROZEN_MODEL_SHA256
    assert body["threshold"] == FROZEN_THRESHOLD


def test_login_returns_a_working_token(client, make_user):
    user = make_user(UserRole.INVESTIGATOR, email="ana@example.com")
    response = login(client, "ana@example.com")
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert me.json()["id"] == str(user.id)
    assert me.json()["role"] == "investigator"
    assert "password_hash" not in me.json()


def test_login_email_is_not_case_sensitive(client, make_user):
    make_user(email="ana@example.com")
    assert login(client, "  ANA@Example.com ").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client, make_user):
    make_user(email="ana@example.com")
    wrong = login(client, "ana@example.com", "not the right password")
    unknown = login(client, "nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_inactive_account_cannot_log_in(client, make_user):
    make_user(email="ana@example.com", is_active=False)
    assert login(client, "ana@example.com").status_code == 401


def test_repeated_failures_are_rate_limited_even_with_the_right_password(client, make_user):
    make_user(email="ana@example.com")
    attempts = get_settings().login_rate_limit_attempts
    for _ in range(attempts):
        assert login(client, "ana@example.com", "wrong password here").status_code == 401
    limited = login(client, "ana@example.com")
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_success_clears_the_failure_count(client, make_user):
    make_user(email="ana@example.com")
    for _ in range(get_settings().login_rate_limit_attempts - 1):
        login(client, "ana@example.com", "wrong password here")
    assert login(client, "ana@example.com").status_code == 200
    assert login(client, "ana@example.com", "wrong password here").status_code == 401
    assert login(client, "ana@example.com").status_code == 200


def test_failed_login_is_audited_without_the_email_or_password(client, session, make_user):
    make_user(email="ana@example.com")
    login(client, "ana@example.com", "my secret guess")
    entry = session.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
    assert entry is not None
    assert "ana@example.com" not in str(entry.details)
    assert "my secret guess" not in str(entry.details)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Basic abc"},
    ],
)
def test_requests_without_a_valid_token_are_refused(client, headers):
    response = client.get(ME, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_refused(client, make_user):
    user = make_user()
    claims = {
        "sub": str(user.id),
        "ver": 0,
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    token = jwt.encode(claims, get_settings().secret_key.get_secret_value(), algorithm="HS256")
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_another_key_is_refused(client, make_user):
    user = make_user()
    claims = {
        "sub": str(user.id),
        "ver": 0,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(claims, "another-key-" + "x" * 40, algorithm="HS256")
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_unsigned_token_is_refused(client, make_user):
    user = make_user()
    claims = {"sub": str(user.id), "ver": 0, "iat": 1, "exp": 9999999999}
    token = jwt.encode(claims, key="", algorithm="none")
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_a_deleted_user_is_refused(client):
    token = create_access_token(uuid.uuid4(), 0)
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_deactivation_applies_immediately(client, session, make_user):
    user = make_user()
    headers = bearer(user)
    assert client.get(ME, headers=headers).status_code == 200
    user.is_active = False
    session.commit()
    assert client.get(ME, headers=headers).status_code == 401


def test_role_change_applies_immediately(client, session, make_user):
    user = make_user(UserRole.ADMIN)
    make_user(UserRole.ADMIN)
    headers = bearer(user)
    assert client.get("/api/v1/users", headers=headers).status_code == 200
    user.role = UserRole.ANALYST
    session.commit()
    assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_changing_password_invalidates_old_tokens(client, make_user):
    make_user(email="ana@example.com")
    old = {"Authorization": f"Bearer {login(client, 'ana@example.com').json()['access_token']}"}
    new_password = "a completely new passphrase"
    response = client.post(
        "/api/v1/auth/change-password",
        headers=old,
        json={"current_password": DEFAULT_PASSWORD, "new_password": new_password},
    )
    assert response.status_code == 204
    assert client.get(ME, headers=old).status_code == 401
    assert login(client, "ana@example.com").status_code == 401
    assert login(client, "ana@example.com", new_password).status_code == 200


def test_changing_password_needs_the_current_one(client, headers_for):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers_for(UserRole.ANALYST),
        json={"current_password": "not the current one", "new_password": "x" * 20},
    )
    assert response.status_code == 401


def test_permissions_matrix():
    everyone = {
        Permission.PREDICT,
        Permission.UPLOAD_BATCH,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_MODELS,
        Permission.VIEW_SUMMARY,
        Permission.VIEW_SETTINGS,
        Permission.VIEW_SYSTEM_STATUS,
    }
    analyst = everyone | {Permission.VIEW_INVESTIGATIONS, Permission.EXPORT_REPORTS}
    investigator = analyst | {Permission.UPDATE_INVESTIGATIONS}
    assert ROLE_PERMISSIONS[UserRole.DEMO] == everyone
    assert ROLE_PERMISSIONS[UserRole.ANALYST] == analyst
    assert ROLE_PERMISSIONS[UserRole.INVESTIGATOR] == investigator
    assert ROLE_PERMISSIONS[UserRole.ADMIN] == set(Permission)
    assert not has_permission(UserRole.INVESTIGATOR, Permission.UPDATE_SETTINGS)


def documented_operations(client) -> list[tuple[str, str, dict]]:
    """Return every (method, path, operation) in the OpenAPI schema, which lists all routes."""
    paths = client.get("/openapi.json").json()["paths"]
    return [
        (method.upper(), path, operation)
        for path, methods in paths.items()
        for method, operation in methods.items()
    ]


def test_every_api_route_requires_authentication(client):
    operations = documented_operations(client)
    protected = [item for item in operations if item[1] not in PUBLIC_PATHS]
    assert len(protected) >= 5
    for method, path, _operation in protected:
        concrete = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        response = client.request(method, concrete)
        assert response.status_code == 401, f"{method} {path}"


def test_every_route_declares_a_response_schema(client):
    operations = documented_operations(client)
    assert operations
    for method, path, operation in operations:
        successes = {code: body for code, body in operation["responses"].items() if code[0] == "2"}
        assert successes, f"{method} {path}"
        for code, body in successes.items():
            if code == "204" or path.endswith(FILE_DOWNLOAD_SUFFIXES):
                continue
            schema = body["content"]["application/json"]["schema"]
            assert schema, f"{method} {path}"


def test_routes_that_accept_a_json_body_declare_a_schema(client):
    for method, path, operation in documented_operations(client):
        content = operation.get("requestBody", {}).get("content", {})
        if "application/json" in content:
            assert content["application/json"]["schema"], f"{method} {path}"


@pytest.mark.parametrize("role", [UserRole.ANALYST, UserRole.INVESTIGATOR, UserRole.DEMO])
def test_non_admins_cannot_manage_users_or_read_the_audit_log(client, headers_for, role):
    headers = headers_for(role)
    assert client.get("/api/v1/users", headers=headers).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=headers).status_code == 403
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={"email": "x@example.com", "password": "y" * 20, "role": "admin"},
    )
    assert response.status_code == 403


def test_admin_can_create_a_user_who_can_then_log_in(client, session, headers_for):
    response = client.post(
        "/api/v1/users",
        headers=headers_for(UserRole.ADMIN),
        json={"email": "New@Example.com", "password": "a long passphrase", "role": "analyst"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "password" not in str(response.json())
    stored = session.scalar(select(User).where(User.email == "new@example.com"))
    assert stored.password_hash.startswith("$argon2id$")
    assert "a long passphrase" not in stored.password_hash
    assert login(client, "new@example.com", "a long passphrase").status_code == 200


def test_duplicate_email_is_a_conflict(client, headers_for, make_user):
    make_user(email="ana@example.com")
    response = client.post(
        "/api/v1/users",
        headers=headers_for(UserRole.ADMIN),
        json={"email": "ANA@example.com", "password": "a long passphrase", "role": "analyst"},
    )
    assert response.status_code == 409


def test_rejected_password_is_not_echoed(client, headers_for):
    response = client.post(
        "/api/v1/users",
        headers=headers_for(UserRole.ADMIN),
        json={"email": "a@example.com", "password": "shortsecret", "role": "analyst"},
    )
    assert response.status_code == 422
    assert "shortsecret" not in response.text
    assert "request_id" in response.json()


def test_unknown_fields_are_refused(client, headers_for):
    response = client.post(
        "/api/v1/users",
        headers=headers_for(UserRole.ADMIN),
        json={"email": "a@example.com", "password": "x" * 20, "role": "admin", "is_active": True},
    )
    assert response.status_code == 422


def test_last_admin_cannot_be_removed(client, make_user):
    admin = make_user(UserRole.ADMIN)
    for change in ({"is_active": False}, {"role": "analyst"}):
        response = client.patch(f"/api/v1/users/{admin.id}", headers=bearer(admin), json=change)
        assert response.status_code == 422
        assert "only active administrator" in response.json()["detail"]


def test_admin_can_be_removed_when_another_exists(client, make_user):
    admin = make_user(UserRole.ADMIN)
    other = make_user(UserRole.ADMIN)
    response = client.patch(
        f"/api/v1/users/{other.id}", headers=bearer(admin), json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_user_changes_are_audited(client, session, make_user):
    admin = make_user(UserRole.ADMIN)
    target = make_user(UserRole.ANALYST)
    client.patch(f"/api/v1/users/{target.id}", headers=bearer(admin), json={"role": "investigator"})
    body = client.get("/api/v1/audit-logs", headers=bearer(admin)).json()
    entry = next(item for item in body["items"] if item["action"] == "user.updated")
    assert entry["entity_id"] == str(target.id)
    assert entry["user_id"] == str(admin.id)
    assert entry["details"] == {"role": "investigator"}


def test_unknown_user_is_not_found(client, headers_for):
    response = client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers=headers_for(UserRole.ADMIN),
        json={"is_active": False},
    )
    assert response.status_code == 404


def test_page_size_is_capped(client, headers_for):
    headers = headers_for(UserRole.ADMIN)
    assert client.get("/api/v1/users?limit=1000", headers=headers).status_code == 422
    assert client.get("/api/v1/users?offset=-1", headers=headers).status_code == 422


def test_responses_carry_security_headers(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert len(response.headers["x-request-id"]) == 32


def test_api_responses_are_not_cached(client, headers_for):
    response = client.get(ME, headers=headers_for(UserRole.ANALYST))
    assert response.headers["cache-control"] == "no-store"


def test_unknown_route_uses_the_error_format(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert set(response.json()) == {"detail", "request_id"}


def test_unexpected_errors_reveal_nothing(client, headers_for, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.routes import audit as audit_route

    def explode(*_args, **_kwargs):
        raise RuntimeError("secret internal detail: postgres://user:pass@host")

    monkeypatch.setattr(audit_route, "list_events", explode)
    headers = headers_for(UserRole.ADMIN)
    quiet = TestClient(client.app, raise_server_exceptions=False)
    response = quiet.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert "secret internal detail" not in response.text


def test_oversized_request_is_refused_before_reading(client, headers_for):
    limit = get_settings().max_upload_bytes + 1024 * 1024
    response = client.post(
        "/api/v1/users",
        headers={**headers_for(UserRole.ADMIN), "content-length": str(limit + 1)},
        content=b"{}",
    )
    assert response.status_code == 413


def test_cors_allows_only_the_configured_origin(client):
    allowed = "http://localhost:5173"
    good = client.options(ME, headers={"Origin": allowed, "Access-Control-Request-Method": "GET"})
    assert good.headers["access-control-allow-origin"] == allowed
    bad = client.options(
        ME, headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in bad.headers
