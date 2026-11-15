"""Browser sessions held in HttpOnly cookies, with CSRF protection.

The session cookie carries a signed token that names a row in user_sessions, so logging out
revokes that session on the server. Script cannot read the cookie. A second cookie carries a CSRF
token that script can read and must echo in a header on every request that changes something.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import PermissionDeniedError
from app.models.records import User, UserSession
from app.security.tokens import TokenClaims, create_access_token
from app.services.audit_service import record_event

SESSION_COOKIE = "finguard_session"
CSRF_COOKIE = "finguard_csrf"
# Phase 5 M5: when cookies are Secure (production), browsers enforce these name prefixes.
# __Secure- requires Secure; __Host- also requires Path=/ and no Domain, so only the CSRF cookie
# can take it (the session cookie is scoped to /api).
SECURE_PREFIX = "__Secure-"
HOST_PREFIX = "__Host-"
CSRF_HEADER = "x-csrf-token"
SESSION_COOKIE_PATH = "/api"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_BYTES = 32


def session_cookie_name() -> str:
    """The session cookie's name: __Secure- prefixed whenever it is sent with Secure."""
    return (SECURE_PREFIX if get_settings().cookie_secure else "") + SESSION_COOKIE


def csrf_cookie_name() -> str:
    """The CSRF cookie's name: __Host- prefixed whenever it is sent with Secure."""
    return (HOST_PREFIX if get_settings().cookie_secure else "") + CSRF_COOKIE


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def open_session(db: Session, user: User) -> tuple[str, str, UserSession]:
    """Create a session row, and return its signed token, its CSRF token and the row."""
    settings = get_settings()
    csrf_token = secrets.token_urlsafe(_CSRF_BYTES)
    row = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        csrf_token_hash=_digest(csrf_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes),
    )
    db.add(row)
    record_event(db, user.id, "auth.session_started", "user_session", row.id)
    db.commit()
    token = create_access_token(user.id, user.token_version, session_id=row.id)
    return token, csrf_token, row


def set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    """Attach both cookies. SameSite=Strict keeps them off requests started by other sites."""
    settings = get_settings()
    max_age = settings.access_token_minutes * 60
    response.set_cookie(
        session_cookie_name(),
        token,
        max_age=max_age,
        path=SESSION_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.set_cookie(
        csrf_cookie_name(),
        csrf_token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite="strict",
    )


def clear_session_cookies(response: Response) -> None:
    """Tell the browser to delete both cookies."""
    secure = get_settings().cookie_secure
    response.delete_cookie(
        session_cookie_name(),
        path=SESSION_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        csrf_cookie_name(), path="/", secure=secure, httponly=False, samesite="strict"
    )


def find_active_session(db: Session, claims: TokenClaims) -> UserSession | None:
    """Return the session a token names, if it exists, belongs to that user and is still live."""
    if claims.session_id is None:
        return None
    row = db.get(UserSession, claims.session_id)
    if row is None or row.user_id != claims.user_id or row.revoked_at is not None:
        return None
    if row.expires_at <= datetime.now(UTC):
        return None
    return row


def require_allowed_origin(request: Request) -> None:
    """Refuse a cookie request that changes something unless it comes from an allowed origin."""
    origin = request.headers.get("origin")
    if origin is None or origin not in get_settings().cors_origins:
        raise PermissionDeniedError("This request did not come from an allowed origin.")


def require_csrf_token(request: Request, row: UserSession) -> None:
    """Check the header against the session's CSRF token, in constant time."""
    supplied = request.headers.get(CSRF_HEADER)
    if not supplied or not hmac.compare_digest(_digest(supplied), row.csrf_token_hash):
        raise PermissionDeniedError("The CSRF token is missing or does not match.")


def revoke_session(db: Session, row: UserSession) -> None:
    """End one session. Other sessions for the same user are unaffected."""
    row.revoked_at = func.now()
    record_event(db, row.user_id, "auth.session_ended", "user_session", row.id)
    db.commit()
