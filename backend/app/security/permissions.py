"""What each role may do. This table is the single source of truth for authorisation."""

import enum

from app.models.enums import UserRole


class Permission(enum.StrEnum):
    """One action that needs authorisation."""

    PREDICT = "predict"
    UPLOAD_BATCH = "upload_batch"
    VIEW_TRANSACTIONS = "view_transactions"
    VIEW_MODELS = "view_models"
    VIEW_SUMMARY = "view_summary"
    VIEW_SETTINGS = "view_settings"
    VIEW_SYSTEM_STATUS = "view_system_status"
    VIEW_INVESTIGATIONS = "view_investigations"
    UPDATE_INVESTIGATIONS = "update_investigations"
    EXPORT_REPORTS = "export_reports"
    UPDATE_SETTINGS = "update_settings"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOG = "view_audit_log"


_EVERYONE = {
    Permission.PREDICT,
    Permission.UPLOAD_BATCH,
    Permission.VIEW_TRANSACTIONS,
    Permission.VIEW_MODELS,
    Permission.VIEW_SUMMARY,
    Permission.VIEW_SETTINGS,
    Permission.VIEW_SYSTEM_STATUS,
}
_ANALYST = _EVERYONE | {Permission.VIEW_INVESTIGATIONS, Permission.EXPORT_REPORTS}
_INVESTIGATOR = _ANALYST | {Permission.UPDATE_INVESTIGATIONS}

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.DEMO: frozenset(_EVERYONE),
    UserRole.ANALYST: frozenset(_ANALYST),
    UserRole.INVESTIGATOR: frozenset(_INVESTIGATOR),
    UserRole.ADMIN: frozenset(Permission),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Return True if this role may perform this action."""
    return permission in ROLE_PERMISSIONS[role]
