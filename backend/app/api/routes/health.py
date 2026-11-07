"""Health routes. /health is public and says only that the process is up."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.schemas.common import ApiModel
from app.core.config import APP_VERSION, get_settings
from app.database.session import database_is_available
from app.models.records import User
from app.security.dependencies import DbSession, ServingModelDep, require_permission
from app.security.permissions import Permission

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """The process is running."""

    status: str


class SystemStatus(ApiModel):
    """The state of the application and what it depends on."""

    status: str
    application_version: str
    environment: str
    database_available: bool
    model_loaded: bool
    model_version: str
    model_sha256: str
    threshold: float


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the process is running. This deliberately needs no database or token."""
    return HealthResponse(status="ok")


@router.get("/api/v1/system/status", response_model=SystemStatus)
def system_status(
    _user: Annotated[User, Depends(require_permission(Permission.VIEW_SYSTEM_STATUS))],
    db: DbSession,
    model: ServingModelDep,
) -> SystemStatus:
    """Report whether the database and model are working."""
    available = database_is_available(db)
    return SystemStatus(
        status="ok" if available else "degraded",
        application_version=APP_VERSION,
        environment=get_settings().app_env,
        database_available=available,
        model_loaded=True,
        model_version=model.version,
        model_sha256=model.metadata["model_sha256"],
        threshold=model.threshold,
    )
