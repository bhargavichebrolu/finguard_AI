"""Signed login tokens. They prove identity only: roles are read from the database per request."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError

_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ["sub", "ver", "iat", "exp"]


class TokenClaims(NamedTuple):
    """The verified contents of a token. session_id is set only for browser session tokens."""

    user_id: uuid.UUID
    token_version: int
    session_id: uuid.UUID | None = None


def create_access_token(
    user_id: uuid.UUID, token_version: int, session_id: uuid.UUID | None = None
) -> str:
    """Return a signed token that expires after the configured time."""
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    if session_id is not None:
        claims["sid"] = str(session_id)
    return jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> TokenClaims:
    """Verify a token's signature and expiry. Every failure gives the same error."""
    try:
        claims = jwt.decode(
            token,
            get_settings().secret_key.get_secret_value(),
            algorithms=[_ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
        session_id = uuid.UUID(claims["sid"]) if "sid" in claims else None
        return TokenClaims(uuid.UUID(claims["sub"]), int(claims["ver"]), session_id)
    except (jwt.PyJWTError, ValueError, TypeError) as error:
        raise AuthenticationError() from error
