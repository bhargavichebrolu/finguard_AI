"""Schemas for model information. Every metric here is a value saved during Phase 2."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import ApiModel
from app.core.frozen_model import SCORE_IS_CALIBRATED, SCORE_TYPE


class ModelVersionView(ApiModel):
    """A registered model, without its metrics."""

    id: uuid.UUID
    version: str
    algorithm: str
    model_path_or_artifact_reference: str
    model_sha256: str
    threshold: float
    feature_schema_version: str
    is_active: bool
    created_at: datetime
    score_type: str = SCORE_TYPE
    score_is_calibrated: bool = SCORE_IS_CALIBRATED


class ThresholdMetrics(BaseModel):
    """Saved results at the frozen threshold."""

    model_config = ConfigDict(extra="allow")

    accuracy: float
    alert_rate: float
    alerts: int
    balanced_accuracy: float
    f1: float
    false_negative_rate: float
    false_negatives: int
    false_positive_rate: float
    false_positives: int
    precision: float
    recall: float
    threshold: float
    true_negatives: int
    true_positives: int


class RankingMetrics(BaseModel):
    """Saved results that do not depend on a threshold."""

    model_config = ConfigDict(extra="allow")

    brier: float
    fraud_rows: int
    pr_auc: float
    pr_auc_lift: float
    prevalence: float
    roc_auc: float
    rows: int


class RegimeResults(BaseModel):
    """Saved results for one kind of simulation step."""

    at_frozen_threshold: ThresholdMetrics
    ranking: RankingMetrics


class ValidationResults(BaseModel):
    """Saved validation results."""

    at_threshold: ThresholdMetrics
    ranking: RankingMetrics


class TestResults(BaseModel):
    """Saved results from the single test evaluation."""

    __test__ = False

    at_frozen_threshold: ThresholdMetrics
    ranking: RankingMetrics
    regimes: dict[str, RegimeResults]


class ThresholdInfo(BaseModel):
    """How the frozen threshold was chosen."""

    chosen_on: str
    objective: str
    operational_fpr_cap: float
    value: float


class ModelMetricsView(BaseModel):
    """The evaluation of the active model, with plain statements of its limitations."""

    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    family: str
    strategy: str
    feature_schema_version: str
    score_type: str = SCORE_TYPE
    score_is_calibrated: bool = SCORE_IS_CALIBRATED
    score_semantics: str
    source: str
    threshold: ThresholdInfo
    validation: ValidationResults
    test: TestResults
    performance_notes: list[str]


class FeatureImportanceView(BaseModel):
    """Saved global SHAP importance. This describes the model, not what causes fraud."""

    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    output_scale: str
    by_group: dict[str, float]
    by_feature: dict[str, float]
    limitations: list[str]
