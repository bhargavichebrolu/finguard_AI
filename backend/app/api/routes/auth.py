"""Routes for signing in, browser sessions and the caller's own account."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas.auth import (
    CurrentUserView,
    PasswordChange,
    SessionCreate,
    TokenResponse,
    current_user_view,
)
from app.api.schemas.common import ErrorResponse
from app.core.errors import AuthenticationError
from app.security import sessions
from app.security.dependencies import CurrentUser, DbSession
from app.security.tokens import decode_access_token
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(
    request: Request, db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenResponse:
    """For API clients and Swagger: exchange an email (as `username`) and password for a token."""
    token = auth_service.authenticate(db, form.username, form.password, _client(request))
    return TokenResponse(access_token=token)


@router.post(
    "/session",
    response_model=CurrentUserView,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def start_session(
    request: Request, response: Response, db: DbSession, body: SessionCreate
) -> CurrentUserView:
    """For the web application: sign in, receiving HttpOnly session and CSRF cookies.

    No token appears in the response body, so page script never handles it.
    """
    if "origin" in request.headers:
        sessions.require_allowed_origin(request)
    user = auth_service.verify_login(db, body.email, body.password, _client(request))
    token, csrf_token, row = sessions.open_session(db, user)
    sessions.set_session_cookies(response, token, csrf_token)
    return current_user_view(user, row)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def end_session(request: Request, response: Response, db: DbSession) -> None:
    """Sign out: revoke this browser session on the server and delete its cookies."""
    cookie = request.cookies.get(sessions.session_cookie_name())
    if cookie is not None:
        try:
            row = sessions.find_active_session(db, decode_access_token(cookie))
        except AuthenticationError:
            row = None
        if row is not None:
            sessions.require_allowed_origin(request)
            sessions.require_csrf_token(request, row)
            sessions.revoke_session(db, row)
    sessions.clear_session_cookies(response)


@router.get("/me", response_model=CurrentUserView)
def read_current_user(request: Request, user: CurrentUser) -> CurrentUserView:
    """Return the signed-in account, what it may do, and when a browser session expires."""
    return current_user_view(user, request.state.user_session)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(user: CurrentUser, db: DbSession, body: PasswordChange) -> None:
    """Change your own password. This signs out all your existing sessions and tokens."""
    auth_service.change_password(db, user, body.current_password, body.new_password)
