"""Settings an administrator can change. The frozen threshold is deliberately not one of them."""

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidInputError
from app.core.frozen_model import FROZEN_THRESHOLD
from app.models.records import AppSetting
from app.services.audit_service import record_event

HIGH_RISK_BOUNDARY_KEY = "high_risk_boundary"


def get_high_risk_boundary(session: Session) -> float:
    """Return the stored boundary, or the configured default if none has been set."""
    row = session.get(AppSetting, HIGH_RISK_BOUNDARY_KEY)
    return float(row.value) if row else get_settings().default_high_risk_boundary


def set_high_risk_boundary(session: Session, value: float, changed_by: uuid.UUID) -> float:
    """Change the boundary for future predictions. Stored predictions keep the one they used."""
    if not FROZEN_THRESHOLD < value <= 1.0:
        raise InvalidInputError(
            f"The high risk boundary must be above the frozen threshold ({FROZEN_THRESHOLD}) "
            "and at most 1."
        )
    previous = get_high_risk_boundary(session)
    row = session.get(AppSetting, HIGH_RISK_BOUNDARY_KEY)
    if row is None:
        session.add(AppSetting(key=HIGH_RISK_BOUNDARY_KEY, value=value, updated_by=changed_by))
    else:
        row.value = value
        row.updated_by = changed_by
    record_event(
        session,
        changed_by,
        "settings.updated",
        "app_setting",
        HIGH_RISK_BOUNDARY_KEY,
        {"from": previous, "to": value},
    )
    session.commit()
    return value
