"""Load the frozen model for inference, after checking it has not changed.

Nothing here trains. Checks run before the model file is opened, because joblib files can execute
code when loaded: the metadata must match the pins in code, and the file must match its hash.
"""

import json
import threading
from dataclasses import dataclass, field
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.frozen_model import (
    FROZEN_MODEL_SHA256,
    FROZEN_MODEL_VERSION,
    FROZEN_THRESHOLD,
    VERIFIED_LIBRARIES,
)
from app.ml.explainability import LIMITATIONS, feature_group
from app.ml.features import engineer_features
from app.ml.model_artifacts import LoadedModel, ModelArtifactError, load_model_artifact
from app.ml.pipeline_io import sha256_file
from app.ml.preprocessing import compact_features
from app.models.records import ModelVersion

EXPLANATION_METHOD = "xgboost_tree_shap"
EXPLANATION_SCALE = "log_odds"


@dataclass
class ServingModel:
    """The verified model, plus the saved Phase 2 results that describe it."""

    loaded: LoadedModel
    metrics: dict[str, Any]
    preprocessing: dict[str, Any]
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def version(self) -> str:
        return self.loaded.metadata["model_version"]

    @property
    def threshold(self) -> float:
        return self.loaded.threshold

    @property
    def metadata(self) -> dict[str, Any]:
        return self.loaded.metadata

    def score(self, inputs: pd.DataFrame) -> np.ndarray:
        """Return one uncalibrated score per row. Rows are scored independently of each other."""
        with self._lock:
            return self.loaded.predict_scores(inputs)

    def explain(self, inputs: pd.DataFrame) -> list[dict[str, Any]]:
        """Return each row's TreeSHAP contributions, by feature and by feature group."""
        pipeline = self.loaded.pipeline
        preprocess = pipeline.named_steps["preprocess"]
        features = compact_features(engineer_features(inputs))
        names = [str(name) for name in preprocess.get_feature_names_out()]
        matrix = xgb.DMatrix(preprocess.transform(features))
        with self._lock:
            contributions = (
                pipeline.named_steps["model"]
                .get_booster()
                .predict(matrix, pred_contribs=True, validate_features=False)
            )
        return [_describe_contributions(row, names) for row in np.asarray(contributions)]


def _describe_contributions(row: np.ndarray, names: list[str]) -> dict[str, Any]:
    values = [float(value) for value in row[:-1]]
    by_group: dict[str, float] = {}
    for name, value in zip(names, values, strict=True):
        group = feature_group(name)
        by_group[group] = by_group.get(group, 0.0) + value
    by_feature = sorted(zip(names, values, strict=True), key=lambda item: -abs(item[1]))
    return {
        "method": EXPLANATION_METHOD,
        "output_scale": EXPLANATION_SCALE,
        "base_value": float(row[-1]),
        "by_group": by_group,
        "by_feature": [{"feature": name, "contribution": value} for name, value in by_feature],
    }


def explanation_limitations() -> list[str]:
    """Return the limits of SHAP explanations recorded in Phase 2."""
    return list(LIMITATIONS)


def check_frozen_metadata(metadata: dict[str, Any]) -> None:
    """Refuse metadata that disagrees with the model approved in code."""
    if metadata.get("model_version") != FROZEN_MODEL_VERSION:
        raise ModelArtifactError(f"Model version is not {FROZEN_MODEL_VERSION}")
    if metadata.get("model_sha256") != FROZEN_MODEL_SHA256:
        raise ModelArtifactError("Model hash in metadata differs from the frozen hash")
    if metadata.get("threshold", {}).get("value") != FROZEN_THRESHOLD:
        raise ModelArtifactError("Threshold in metadata differs from the frozen threshold")
    if metadata.get("status") != "frozen":
        raise ModelArtifactError("Model metadata is not marked as frozen")


def check_library_versions(metadata: dict[str, Any]) -> None:
    """Refuse to load the model under library versions it was not saved with."""
    recorded = metadata.get("library_versions", {})
    for library in VERIFIED_LIBRARIES:
        installed = package_metadata.version(library)
        if recorded.get(library) != installed:
            raise ModelArtifactError(
                f"{library} {installed} is installed, but the model was saved with "
                f"{recorded.get(library)}"
            )


def check_preprocessing_metadata(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    """Verify the preprocessing record by hash, and return its contents."""
    if not path.is_file():
        raise ModelArtifactError(f"Preprocessing metadata not found: {path}")
    if sha256_file(path) != metadata.get("preprocessing_metadata_sha256"):
        raise ModelArtifactError("Preprocessing metadata hash does not match the model metadata")
    return json.loads(path.read_text(encoding="utf-8"))


def read_metrics(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    """Read the saved evaluation results, and confirm they describe this model and threshold."""
    if not path.is_file():
        raise ModelArtifactError(f"Model metrics not found: {path}")
    metrics = json.loads(path.read_text(encoding="utf-8"))
    if metrics.get("model_version") != metadata["model_version"]:
        raise ModelArtifactError("Model metrics describe a different model version")
    if metrics.get("threshold", {}).get("value") != metadata["threshold"]["value"]:
        raise ModelArtifactError("Model metrics describe a different threshold")
    return metrics


def load_verified_model(settings: Settings) -> ServingModel:
    """Run every check, then load the model. Any failure stops the application from starting."""
    if not settings.model_metadata_path.is_file():
        raise ModelArtifactError(f"Model metadata not found: {settings.model_metadata_path}")
    metadata = json.loads(settings.model_metadata_path.read_text(encoding="utf-8"))
    check_frozen_metadata(metadata)
    check_library_versions(metadata)
    preprocessing = check_preprocessing_metadata(metadata, settings.preprocessing_metadata_path)
    metrics = read_metrics(metadata, settings.model_metrics_path)
    loaded = load_model_artifact(settings.model_metadata_path, settings.model_artifact_dir)
    return ServingModel(loaded=loaded, metrics=metrics, preprocessing=preprocessing)


def register_active_model(session: Session, model: ServingModel) -> None:
    """Record the served model in model_versions, as the only active row. Safe to repeat."""
    session.execute(
        update(ModelVersion).where(ModelVersion.version != model.version).values(is_active=False)
    )
    row = session.scalar(select(ModelVersion).where(ModelVersion.version == model.version))
    if row is None:
        row = ModelVersion(version=model.version)
        session.add(row)
    row.algorithm = model.metadata["family"]
    row.model_path_or_artifact_reference = model.metadata["model_file"]
    row.model_sha256 = model.metadata["model_sha256"]
    row.threshold = model.threshold
    row.feature_schema_version = model.metadata["feature_schema_version"]
    row.metrics_json = model.metrics
    row.is_active = True
    session.commit()
