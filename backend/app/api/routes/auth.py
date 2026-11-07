"""Routes for signing in and for the caller's own account."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas.auth import PasswordChange, TokenResponse, UserView
from app.api.schemas.common import ErrorResponse
from app.security.dependencies import CurrentUser, DbSession
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(
    request: Request, db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenResponse:
    """Exchange an email (sent as `username`) and password for a bearer token."""
    client = request.client.host if request.client else "unknown"
    token = auth_service.authenticate(db, form.username, form.password, client)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserView)
def read_current_user(user: CurrentUser) -> UserView:
    """Return the signed-in account."""
    return UserView.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(user: CurrentUser, db: DbSession, body: PasswordChange) -> None:
    """Change your own password. This signs out all your existing sessions."""
    auth_service.change_password(db, user, body.current_password, body.new_password)
