"""FastAPI dependencies for authentication, authorisation and per-user rate limits.

Two ways to sign in reach the same user check. A bearer token in the Authorization header is for
API clients and Swagger, and needs no CSRF token, because browsers never attach that header by
themselves. A session cookie is for the web application, so any request that changes something must
also come from an allowed origin and carry the session's CSRF token.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.models.records import User
from app.security.permissions import Permission, has_permission
from app.security.sessions import (
    SESSION_COOKIE,
    UNSAFE_METHODS,
    find_active_session,
    require_allowed_origin,
    require_csrf_token,
)
from app.security.tokens import TokenClaims, decode_access_token
from app.services.model_service import ServingModel

_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _load_user(db: Session, claims: TokenClaims) -> User:
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active or user.token_version != claims.token_version:
        raise AuthenticationError()
    return user


def get_current_user(
    request: Request, db: DbSession, token: Annotated[str | None, Depends(_bearer)]
) -> User:
    """Return the signed-in user. A missing, invalid or outdated credential gives the same error."""
    request.state.user_session = None
    if token is not None:
        claims = decode_access_token(token)
        # A session token copied into a header must still name a live session.
        if claims.session_id is not None and find_active_session(db, claims) is None:
            raise AuthenticationError()
        return _load_user(db, claims)

    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie is None:
        raise AuthenticationError()
    claims = decode_access_token(cookie)
    row = find_active_session(db, claims)
    if row is None:
        raise AuthenticationError()
    if request.method in UNSAFE_METHODS:
        require_allowed_origin(request)
        require_csrf_token(request, row)
    user = _load_user(db, claims)
    request.state.user_session = row
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Build a dependency that allows only roles holding this permission."""

    def check(user: CurrentUser) -> User:
        if not has_permission(user.role, permission):
            raise PermissionDeniedError("Your role does not allow this action.")
        return user

    return check


def rate_limited(permission: Permission, bucket: str, per_minute: Callable[[], int]):
    """Build a dependency that checks a permission, then counts the call against a limit."""

    def check(user: Annotated[User, Depends(require_permission(permission))]) -> User:
        limiter.hit(f"{bucket}:{user.id}", per_minute(), 60)
        return user

    return check


def get_serving_model(request: Request) -> ServingModel:
    """Return the model verified at start-up."""
    return request.app.state.model


ServingModelDep = Annotated[ServingModel, Depends(get_serving_model)]
