"""Routes for application settings (PRD 6.10). The frozen threshold can be read but not changed."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import APP_VERSION, get_settings
from app.core.frozen_model import FROZEN_THRESHOLD
from app.database.session import database_is_available
from app.models.records import User
from app.security.dependencies import DbSession, ServingModelDep, require_permission
from app.security.permissions import Permission
from app.services.settings_service import get_high_risk_boundary, set_high_risk_boundary

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

RISK_BANDS = (
    "LOW: model_score below the frozen threshold (NOT_FLAGGED). "
    "MEDIUM: at or above the threshold and below the high risk boundary (FLAG_FOR_REVIEW). "
    "HIGH: at or above the high risk boundary (FLAG_FOR_REVIEW). "
    "The bands are not calibrated measures of risk."
)
DATASET_NAME = "PaySim (synthetic mobile money simulator)"


class DatasetInfo(BaseModel):
    """What the model was built from."""

    name: str
    source_file: str
    preprocessing_version: str
    feature_schema_version: str
    split_boundaries: dict[str, Any]


class SettingsView(BaseModel):
    """Everything PRD 6.10 lists."""

    model_config = ConfigDict(protected_namespaces=())

    high_risk_boundary: float
    frozen_threshold: float
    frozen_threshold_is_editable: bool = False
    risk_bands: str
    application_version: str
    model_version: str
    database_available: bool
    max_upload_bytes: int
    max_batch_rows: int
    dataset: DatasetInfo


class SettingsUpdate(BaseModel):
    """The only setting that can change. Sending a threshold is refused as an unknown field."""

    model_config = ConfigDict(extra="forbid")

    high_risk_boundary: float = Field(gt=0, le=1, allow_inf_nan=False)


def _view(db: DbSession, model: ServingModelDep) -> SettingsView:
    settings = get_settings()
    preprocessing = model.preprocessing
    return SettingsView(
        high_risk_boundary=get_high_risk_boundary(db),
        frozen_threshold=FROZEN_THRESHOLD,
        risk_bands=RISK_BANDS,
        application_version=APP_VERSION,
        model_version=model.version,
        database_available=database_is_available(db),
        max_upload_bytes=settings.max_upload_bytes,
        max_batch_rows=settings.max_batch_rows,
        dataset=DatasetInfo(
            name=DATASET_NAME,
            source_file=preprocessing["source_file"],
            preprocessing_version=preprocessing["preprocessing_version"],
            feature_schema_version=preprocessing["feature_schema_version"],
            split_boundaries=preprocessing["split_boundaries"],
        ),
    )


@router.get("", response_model=SettingsView)
def read_settings(
    _user: Annotated[User, Depends(require_permission(Permission.VIEW_SETTINGS))],
    db: DbSession,
    model: ServingModelDep,
) -> SettingsView:
    """Return current settings, versions and health."""
    return _view(db, model)


@router.patch("", response_model=SettingsView)
def update_settings(
    admin: Annotated[User, Depends(require_permission(Permission.UPDATE_SETTINGS))],
    db: DbSession,
    model: ServingModelDep,
    body: SettingsUpdate,
) -> SettingsView:
    """Change the high risk boundary for future predictions. This never changes who is flagged."""
    set_high_risk_boundary(db, body.high_risk_boundary, admin.id)
    return _view(db, model)
