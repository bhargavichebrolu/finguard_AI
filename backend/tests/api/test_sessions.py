"""API tests of browser sessions: HttpOnly cookies, CSRF, origin checks, expiry and logout."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.api.conftest import DEFAULT_PASSWORD

from app.core.config import get_settings
from app.models.enums import UserRole
from app.models.records import AuditLog, UserSession
from app.security.sessions import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE

pytestmark = pytest.mark.database

ORIGIN = "http://localhost:5173"
SESSION = "/api/v1/auth/session"
ME = "/api/v1/auth/me"
FLAGGED = {
    "amount": 9_000_000.0,
    "transaction_type": "TRANSFER",
    "step": 5,
    "destination_category": "customer",
}


@pytest.fixture
def browser(app_client, session):
    """A separate client with its own cookie jar, like one browser."""
    return TestClient(app_client.app, base_url="http://testserver")


def sign_in(client, email, password=DEFAULT_PASSWORD, origin=ORIGIN):
    headers = {"Origin": origin} if origin else {}
    return client.post(SESSION, json={"email": email, "password": password}, headers=headers)


def csrf_headers(client) -> dict[str, str]:
    return {"Origin": ORIGIN, CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


def test_sign_in_sets_httponly_strict_cookies_and_no_token_in_the_body(browser, make_user):
    make_user(UserRole.ANALYST, email="ana@example.com")
    response = sign_in(browser, "ana@example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert "access_token" not in body and "token" not in str(body).lower()
    cookies = {
        header.split("=", 1)[0]: header for header in response.headers.get_list("set-cookie")
    }
    session_cookie = cookies[SESSION_COOKIE]
    assert "HttpOnly" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert "Path=/api" in session_cookie
    assert f"Max-Age={get_settings().access_token_minutes * 60}" in session_cookie
    csrf_cookie = cookies[CSRF_COOKIE]
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=strict" in csrf_cookie


def test_cookies_are_secure_in_production(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "session_cookie_secure", None)
    monkeypatch.setattr(settings, "app_env", "production")
    assert settings.cookie_secure is True
    monkeypatch.setattr(settings, "app_env", "development")
    assert settings.cookie_secure is False


def test_secure_cookies_carry_browser_enforced_prefixes(
    app_client, session, make_user, monkeypatch
):
    # Phase 5 M5: with Secure cookies, __Secure- and __Host- make browsers refuse look-alike
    # cookies set without Secure, or (for __Host-) with a Domain or another path.
    monkeypatch.setattr(get_settings(), "session_cookie_secure", True)
    https = TestClient(app_client.app, base_url="https://testserver")
    make_user(UserRole.ANALYST, email="secure@example.com")
    response = sign_in(https, "secure@example.com")
    assert response.status_code == 200
    cookies = {
        header.split("=", 1)[0]: header for header in response.headers.get_list("set-cookie")
    }
    assert set(cookies) == {"__Secure-finguard_session", "__Host-finguard_csrf"}
    session_cookie, csrf_cookie = (
        cookies["__Secure-finguard_session"],
        cookies["__Host-finguard_csrf"],
    )
    assert (
        "Secure" in session_cookie
        and "HttpOnly" in session_cookie
        and "Path=/api" in session_cookie
    )
    assert "Secure" in csrf_cookie and "Path=/" in csrf_cookie and "Domain" not in csrf_cookie

    assert https.get(ME).status_code == 200
    csrf = {"Origin": ORIGIN, CSRF_HEADER: https.cookies.get("__Host-finguard_csrf")}
    assert https.post("/api/v1/transactions/predict", json=FLAGGED, headers=csrf).status_code == 201

    # The unprefixed name is not read when cookies are Secure.
    token = https.cookies.get("__Secure-finguard_session")
    plain = TestClient(app_client.app, base_url="https://testserver")
    assert plain.get(ME, headers={"Cookie": f"finguard_session={token}"}).status_code == 401
    assert (
        plain.get(ME, headers={"Cookie": f"__Secure-finguard_session={token}"}).status_code == 200
    )


def test_me_reports_permissions_and_expiry(browser, make_user):
    make_user(UserRole.INVESTIGATOR, email="iv@example.com")
    sign_in(browser, "iv@example.com")
    body = browser.get(ME).json()
    assert "update_investigations" in body["permissions"]
    assert "manage_users" not in body["permissions"]
    expires = datetime.fromisoformat(body["session_expires_at"])
    assert timedelta(minutes=29) < expires - datetime.now(UTC) <= timedelta(minutes=30)


def test_wrong_password_sets_no_cookie(browser, make_user):
    make_user(email="ana@example.com")
    response = sign_in(browser, "ana@example.com", "not the right password")
    assert response.status_code == 401
    assert SESSION_COOKIE not in browser.cookies


def test_sign_in_from_another_origin_is_refused(browser, make_user):
    make_user(email="ana@example.com")
    response = sign_in(browser, "ana@example.com", origin="https://evil.example")
    assert response.status_code == 403
    assert SESSION_COOKIE not in browser.cookies


def test_sign_in_accepts_json_only(browser, make_user):
    make_user(email="ana@example.com")
    response = browser.post(
        SESSION,
        data={"email": "ana@example.com", "password": DEFAULT_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 422


def test_reads_work_with_the_cookie_alone(browser, make_user):
    make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    assert browser.get("/api/v1/transactions").status_code == 200


def test_changes_need_the_csrf_header(browser, make_user):
    make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    predict = "/api/v1/transactions/predict"
    assert browser.post(predict, json=FLAGGED, headers={"Origin": ORIGIN}).status_code == 403
    wrong = {"Origin": ORIGIN, CSRF_HEADER: "forged-value"}
    assert browser.post(predict, json=FLAGGED, headers=wrong).status_code == 403
    assert browser.post(predict, json=FLAGGED, headers=csrf_headers(browser)).status_code == 201


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null"])
def test_changes_need_an_allowed_origin(browser, make_user, origin):
    make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    headers = {CSRF_HEADER: browser.cookies.get(CSRF_COOKIE)}
    if origin:
        headers["Origin"] = origin
    response = browser.post("/api/v1/transactions/predict", json=FLAGGED, headers=headers)
    assert response.status_code == 403


def test_csrf_token_of_another_session_is_refused(app_client, browser, make_user):
    make_user(email="ana@example.com")
    make_user(email="ben@example.com")
    other = TestClient(app_client.app)
    sign_in(other, "ben@example.com")
    sign_in(browser, "ana@example.com")
    headers = {"Origin": ORIGIN, CSRF_HEADER: other.cookies.get(CSRF_COOKIE)}
    response = browser.post("/api/v1/transactions/predict", json=FLAGGED, headers=headers)
    assert response.status_code == 403


def test_bearer_tokens_still_work_without_csrf(client, headers_for):
    response = client.post(
        "/api/v1/transactions/predict", json=FLAGGED, headers=headers_for(UserRole.ANALYST)
    )
    assert response.status_code == 201


def test_bearer_token_in_the_session_cookie_is_refused(browser, make_user, headers_for):
    token = headers_for(UserRole.ANALYST)["Authorization"].split()[1]
    browser.cookies.set(SESSION_COOKIE, token, path="/api")
    assert browser.get(ME).status_code == 401


def test_logout_revokes_only_this_session(app_client, browser, make_user, session):
    make_user(email="ana@example.com")
    other = TestClient(app_client.app)
    sign_in(other, "ana@example.com")
    sign_in(browser, "ana@example.com")
    stolen = browser.cookies.get(SESSION_COOKIE)

    response = browser.delete(SESSION, headers=csrf_headers(browser))
    assert response.status_code == 204
    assert SESSION_COOKIE not in browser.cookies
    replay = TestClient(app_client.app)
    replay.cookies.set(SESSION_COOKIE, stolen, path="/api")
    assert replay.get(ME).status_code == 401
    assert other.get(ME).status_code == 200
    revoked = session.scalars(select(UserSession).where(UserSession.revoked_at.is_not(None)))
    assert len(revoked.all()) == 1
    assert session.scalar(select(AuditLog).where(AuditLog.action == "auth.session_ended"))


def test_logout_needs_csrf_for_a_live_session(browser, make_user):
    make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    assert browser.delete(SESSION, headers={"Origin": ORIGIN}).status_code == 403
    assert browser.get(ME).status_code == 200


def test_logout_without_a_session_just_clears_cookies(browser):
    assert browser.delete(SESSION).status_code == 204


def test_expired_session_is_refused(browser, make_user, session):
    make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    row = session.scalar(select(UserSession))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert browser.get(ME).status_code == 401


def test_password_change_ends_cookie_sessions(app_client, browser, make_user):
    make_user(email="ana@example.com")
    other = TestClient(app_client.app)
    sign_in(other, "ana@example.com")
    sign_in(browser, "ana@example.com")
    response = browser.post(
        "/api/v1/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "a brand new passphrase"},
        headers=csrf_headers(browser),
    )
    assert response.status_code == 204
    assert other.get(ME).status_code == 401
    assert browser.get(ME).status_code == 401


def test_deactivation_ends_cookie_sessions(browser, make_user, session):
    user = make_user(email="ana@example.com")
    sign_in(browser, "ana@example.com")
    user.is_active = False
    session.commit()
    assert browser.get(ME).status_code == 401


def test_session_sign_in_is_rate_limited(browser, make_user):
    make_user(email="ana@example.com")
    for _ in range(get_settings().login_rate_limit_attempts):
        assert sign_in(browser, "ana@example.com", "wrong password here").status_code == 401
    assert sign_in(browser, "ana@example.com").status_code == 429


def test_cors_allows_credentials_and_the_csrf_header_for_listed_origins(client):
    response = client.options(
        "/api/v1/transactions/predict",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()
    refused = client.options(
        "/api/v1/transactions/predict",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in refused.headers
