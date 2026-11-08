"""Routes for administrators to manage accounts (PRD 2.3)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.schemas.auth import AssigneeView, UserCreate, UserUpdate, UserView
from app.api.schemas.common import Limit, Offset, Page
from app.models.records import User
from app.security.dependencies import DbSession, require_permission
from app.security.permissions import Permission
from app.services import auth_service

router = APIRouter(prefix="/api/v1/users", tags=["Users"])
AdminUser = Annotated[User, Depends(require_permission(Permission.MANAGE_USERS))]


@router.get("", response_model=Page[UserView])
def list_users(
    _admin: AdminUser, db: DbSession, limit: Limit = 50, offset: Offset = 0
) -> Page[UserView]:
    """List accounts."""
    users, total = auth_service.list_users(db, limit, offset)
    return Page[UserView](
        items=[UserView.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/assignable", response_model=list[AssigneeView])
def list_assignable(
    _user: Annotated[User, Depends(require_permission(Permission.UPDATE_INVESTIGATIONS))],
    db: DbSession,
) -> list[AssigneeView]:
    """List active investigators and administrators, for assigning an investigation.

    Returns only identifiers, emails and roles, so it reveals far less than the admin user list.
    """
    return [AssigneeView.model_validate(user) for user in auth_service.list_assignable(db)]


@router.post("", response_model=UserView, status_code=status.HTTP_201_CREATED)
def create_user(admin: AdminUser, db: DbSession, body: UserCreate) -> UserView:
    """Create an account. There is no self-registration."""
    user = auth_service.create_user(db, body.email, body.password, body.role, admin.id)
    return UserView.model_validate(user)


@router.patch("/{user_id}", response_model=UserView)
def update_user(admin: AdminUser, db: DbSession, user_id: uuid.UUID, body: UserUpdate) -> UserView:
    """Change a role or deactivate an account. The change applies from the next request."""
    user = auth_service.update_user(db, user_id, body.role, body.is_active, admin.id)
    return UserView.model_validate(user)
