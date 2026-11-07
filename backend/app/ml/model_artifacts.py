"""Save and independently load the selected model.

Loading needs only this module, the shared feature code and the model's own library. It does
not import the experiment code. A file that fails its hash or schema check is refused rather
than loaded, because joblib files execute code when opened.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from app.ml.features import engineer_features
from app.ml.pipeline_io import sha256_file, write_json
from app.ml.preprocessing import compact_features
from app.ml.schema import FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION

MODEL_FILE_NAME = "model.joblib"
_COMPRESSION_LEVEL = 3


class ModelArtifactError(RuntimeError):
    """Raised when a model file is missing, altered or incompatible with this code."""


def save_model_artifact(
    pipeline: Pipeline, metadata: dict[str, Any], models_dir: Path, metadata_path: Path
) -> dict[str, Any]:
    """Save the pipeline in a version directory, and its metadata with the file's hash."""
    version = metadata["model_version"]
    version_dir = models_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)
    model_path = version_dir / MODEL_FILE_NAME
    joblib.dump(pipeline, model_path, compress=_COMPRESSION_LEVEL)
    complete = {
        **metadata,
        "model_file": f"{version}/{MODEL_FILE_NAME}",
        "model_sha256": sha256_file(model_path),
        "model_size_bytes": model_path.stat().st_size,
    }
    write_json(metadata_path, complete)
    return complete


@dataclass
class LoadedModel:
    """A verified model that accepts the four prediction inputs."""

    pipeline: Pipeline
    threshold: float
    metadata: dict[str, Any]

    def predict_scores(self, inputs: pd.DataFrame) -> np.ndarray:
        """Return one fraud score per row, using the same feature code as training."""
        features = compact_features(engineer_features(inputs))
        return self.pipeline.predict_proba(features)[:, 1].astype("float64")

    def classify(self, inputs: pd.DataFrame) -> np.ndarray:
        """Return True for rows at or above the frozen threshold."""
        return self.predict_scores(inputs) >= self.threshold


def load_model_artifact(metadata_path: Path, models_dir: Path) -> LoadedModel:
    """Load the model described by a metadata file, after verifying it."""
    if not metadata_path.is_file():
        raise ModelArtifactError(f"Model metadata not found: {metadata_path}")
    metadata = _read_metadata(metadata_path)

    if metadata["feature_schema_version"] != FEATURE_SCHEMA_VERSION:
        raise ModelArtifactError(
            f"Model uses feature schema {metadata['feature_schema_version']}, "
            f"but this code uses {FEATURE_SCHEMA_VERSION}"
        )
    if tuple(metadata["feature_columns"]) != FEATURE_COLUMNS:
        raise ModelArtifactError("Model feature columns do not match this code")

    model_path = models_dir / metadata["model_file"]
    if not model_path.is_file():
        raise ModelArtifactError(f"Model file not found: {model_path}")
    actual_hash = sha256_file(model_path)
    if actual_hash != metadata["model_sha256"]:
        raise ModelArtifactError(
            f"Model file hash {actual_hash} does not match metadata {metadata['model_sha256']}"
        )
    return LoadedModel(joblib.load(model_path), float(metadata["threshold"]["value"]), metadata)


def _read_metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
