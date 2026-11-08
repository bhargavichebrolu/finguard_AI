"""Sign-in and user management. Routes stay thin, and all the rules are here."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError, InvalidInputError, NotFoundError
from app.core.rate_limit import limiter
from app.models.enums import UserRole
from app.models.records import User
from app.security.passwords import hash_password, verify_against_dummy, verify_password
from app.security.tokens import create_access_token
from app.services.audit_service import record_event


def normalise_email(email: str) -> str:
    """Compare and store email addresses in one form."""
    return email.strip().lower()


def authenticate(session: Session, email: str, password: str, client_address: str) -> str:
    """Return a bearer token for correct credentials, for API clients."""
    user = verify_login(session, email, password, client_address)
    return create_access_token(user.id, user.token_version)


def verify_login(session: Session, email: str, password: str, client_address: str) -> User:
    """Return the user for correct credentials. Wrong email and wrong password look the same."""
    settings = get_settings()
    address = normalise_email(email)
    key = f"login:{client_address}:{address}"
    limit, window = settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds
    limiter.require_below_limit(key, limit, window)

    user = session.scalar(select(User).where(User.email == address))
    if user is None:
        verify_against_dummy(password)
    if user is None or not verify_password(user.password_hash, password) or not user.is_active:
        limiter.record(key)
        record_event(session, None, "auth.login_failed", "user")
        session.commit()
        raise AuthenticationError("Incorrect email or password.")

    limiter.clear(key)
    record_event(session, user.id, "auth.login_succeeded", "user", user.id)
    session.commit()
    return user


def list_assignable(session: Session) -> list[User]:
    """Return active users who can work investigations, for choosing an assignee."""
    query = (
        select(User)
        .where(User.is_active, User.role.in_([UserRole.INVESTIGATOR, UserRole.ADMIN]))
        .order_by(User.email)
    )
    return list(session.scalars(query))


def create_user(
    session: Session, email: str, password: str, role: UserRole, created_by: uuid.UUID | None
) -> User:
    """Create an account, or refuse if the email is taken."""
    user = User(email=normalise_email(email), password_hash=hash_password(password), role=role)
    session.add(user)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError("An account with this email already exists.") from error
    record_event(session, created_by, "user.created", "user", user.id, {"role": role.value})
    session.commit()
    return user


def list_users(session: Session, limit: int, offset: int) -> tuple[list[User], int]:
    """Return one page of accounts, and the total count."""
    total = session.scalar(select(func.count()).select_from(User)) or 0
    rows = session.scalars(select(User).order_by(User.created_at).limit(limit).offset(offset))
    return list(rows), total


def _require_another_active_admin(session: Session, user: User) -> None:
    """Refuse a change that would leave nobody able to administer the system."""
    # Locking the admin rows stops two simultaneous changes from removing the last two admins.
    admins = session.scalars(
        select(User.id).where(User.role == UserRole.ADMIN, User.is_active).with_for_update()
    ).all()
    if set(admins) == {user.id}:
        raise InvalidInputError("This is the only active administrator.")


def update_user(
    session: Session,
    user_id: uuid.UUID,
    role: UserRole | None,
    is_active: bool | None,
    changed_by: uuid.UUID,
) -> User:
    """Change a role or active state. Takes effect on the user's next request."""
    user = session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.id == changed_by and is_active is False:
        # Enforced here, not only by the disabled button, so no client can lock itself out.
        raise InvalidInputError("You cannot deactivate your own account.")
    loses_admin = (
        user.role == UserRole.ADMIN
        and user.is_active
        and ((role is not None and role != UserRole.ADMIN) or is_active is False)
    )
    if loses_admin:
        _require_another_active_admin(session, user)
    changes: dict[str, str | bool] = {}
    if role is not None and role != user.role:
        user.role = role
        changes["role"] = role.value
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        changes["is_active"] = is_active
    if changes:
        record_event(session, changed_by, "user.updated", "user", user.id, changes)
    session.commit()
    return user


def change_password(session: Session, user: User, current: str, new: str) -> None:
    """Change a user's own password, which invalidates all their existing tokens."""
    if not verify_password(user.password_hash, current):
        raise AuthenticationError("The current password is not correct.")
    user.password_hash = hash_password(new)
    user.token_version += 1
    record_event(session, user.id, "auth.password_changed", "user", user.id)
    session.commit()
