"""Routes describing the model. All figures come from saved Phase 2 results (PRD 6.8)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.schemas.models import (
    FeatureImportanceView,
    ModelMetricsView,
    ModelReportView,
    ModelVersionView,
)
from app.core.errors import NotFoundError
from app.models.records import ModelVersion, User
from app.security.dependencies import DbSession, ServingModelDep, require_permission
from app.security.permissions import Permission
from app.services.metrics_service import feature_importance, performance_notes

router = APIRouter(prefix="/api/v1/models", tags=["Models"])

Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_MODELS))]
METRICS_SOURCE = "Saved Phase 2 results: artifacts/metadata/model_v1_metrics.json"


@router.get("", response_model=list[ModelVersionView])
def list_models(_user: Viewer, db: DbSession) -> list[ModelVersionView]:
    """List registered model versions."""
    rows = db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    return [ModelVersionView.model_validate(row) for row in rows]


@router.get("/active", response_model=ModelVersionView)
def read_active(_user: Viewer, db: DbSession) -> ModelVersionView:
    """Return the model currently used for predictions."""
    row = db.scalar(select(ModelVersion).where(ModelVersion.is_active))
    if row is None:
        raise NotFoundError("No active model is registered.")
    return ModelVersionView.model_validate(row)


@router.get("/metrics", response_model=ModelMetricsView)
def read_metrics(_user: Viewer, model: ServingModelDep) -> ModelMetricsView:
    """Return the frozen evaluation results, including where the model fell short."""
    return ModelMetricsView(
        **model.metrics,
        source=METRICS_SOURCE,
        performance_notes=performance_notes(model.metrics),
    )


@router.get("/report", response_model=ModelReportView)
def read_report(_user: Viewer, model: ServingModelDep) -> ModelReportView:
    """Return the saved model comparison, curves, thresholds and experiment history.

    Built from saved Phase 2 outputs and checked against a pinned hash at start-up.
    """
    return ModelReportView(**model.report)


@router.get("/feature-importance", response_model=FeatureImportanceView)
def read_feature_importance(_user: Viewer, model: ServingModelDep) -> FeatureImportanceView:
    """Return saved global SHAP importance. This does not show what causes fraud."""
    return FeatureImportanceView(**feature_importance(model.metrics))
