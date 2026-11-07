"""Request and response schemas for sign-in, accounts and the audit log."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.schemas.common import ApiModel
from app.models.enums import UserRole

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
