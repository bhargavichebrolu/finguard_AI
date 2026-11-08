"""Request and response schemas for sign-in, accounts and the audit log."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.schemas.common import ApiModel
from app.models.enums import UserRole
from app.models.records import User, UserSession
from app.security.permissions import ROLE_PERMISSIONS

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


class TokenResponse(BaseModel):
    """A successful sign-in. The field names follow the OAuth2 convention."""

    access_token: str
    token_type: str = "bearer"


class UserView(ApiModel):
    """An account as shown to clients. The password hash is never included."""

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class CurrentUserView(UserView):
    """The signed-in account and what it may do. The interface mirrors this; the API enforces it."""

    permissions: list[str]
    session_expires_at: datetime | None


class AssigneeView(ApiModel):
    """Someone an investigation can be assigned to."""

    id: uuid.UUID
    email: str
    role: UserRole


class SessionCreate(BaseModel):
    """A browser sign-in. JSON only, so a cross-site form cannot submit it."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


def current_user_view(user: User, session: UserSession | None) -> CurrentUserView:
    """Build the signed-in view, listing permissions from the one role table."""
    return CurrentUserView(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        permissions=sorted(permission.value for permission in ROLE_PERMISSIONS[user.role]),
        session_expires_at=session.expires_at if session else None,
    )


class UserCreate(BaseModel):
    """A new account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    role: UserRole


class UserUpdate(BaseModel):
    """A change to an account. Omitted fields stay as they are."""

    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    """A user changing their own password."""

    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class AuditLogView(ApiModel):
    """One audit entry."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: datetime
