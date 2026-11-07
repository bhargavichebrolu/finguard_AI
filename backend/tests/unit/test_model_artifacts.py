"""Saving and independently loading a model, and refusing an altered or incompatible one."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.candidates import CandidateSpec
from app.ml.experiments import fit_candidate, score_rows
from app.ml.features import engineer_features
from app.ml.model_artifacts import (
    ModelArtifactError,
    load_model_artifact,
    save_model_artifact,
)
from app.ml.preprocessing import compact_features
from app.ml.schema import FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION

BACKEND_ROOT = Path(__file__).resolve().parents[2]
THRESHOLD = 0.5


def inputs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "amount": [100.0, 5_000_000.0],
            "transaction_type": ["PAYMENT", "TRANSFER"],
            "step": [10, 400],
            "destination_category": ["merchant", "customer"],
        }
    )


@pytest.fixture
def saved_model(tmp_path, model_partition):
    spec = CandidateSpec(
        "lightgbm", "original", {"n_estimators": 5, "num_leaves": 7, "min_child_samples": 5}, 42
    )
    fitted = fit_candidate(spec, model_partition.features, model_partition.labels.to_numpy(), 1, 3)
    metadata = {
        "model_version": "test_model_v1",
        "status": "frozen",
        "family": "lightgbm",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "threshold": {"value": THRESHOLD},
    }
    metadata_path = tmp_path / "metadata" / "model.json"
    models_dir = tmp_path / "models"
    save_model_artifact(fitted.pipeline, metadata, models_dir, metadata_path)
    return fitted.pipeline, metadata_path, models_dir


def rewrite_metadata(path: Path, **changes) -> None:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata.update(changes)
    path.write_text(json.dumps(metadata), encoding="utf-8")


def test_saved_file_is_versioned_and_hashed(saved_model):
    _, metadata_path, models_dir = saved_model
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["model_file"] == "test_model_v1/model.joblib"
    assert len(metadata["model_sha256"]) == 64
    assert (models_dir / metadata["model_file"]).is_file()


def test_loaded_model_scores_like_the_fitted_one(saved_model, model_partition):
    pipeline, metadata_path, models_dir = saved_model
    loaded = load_model_artifact(metadata_path, models_dir)
    assert np.array_equal(
        score_rows(loaded.pipeline, model_partition.features),
        score_rows(pipeline, model_partition.features),
    )


def test_scores_are_probabilities_in_range(saved_model):
    _, metadata_path, models_dir = saved_model
    scores = load_model_artifact(metadata_path, models_dir).predict_scores(inputs_frame())
    assert scores.shape == (2,)
    assert ((scores >= 0) & (scores <= 1)).all()


def test_classify_uses_the_frozen_threshold(saved_model):
    _, metadata_path, models_dir = saved_model
    model = load_model_artifact(metadata_path, models_dir)
    scores = model.predict_scores(inputs_frame())
    assert model.threshold == THRESHOLD
    assert np.array_equal(model.classify(inputs_frame()), scores >= THRESHOLD)

    # Setting the threshold to a row's score makes that row alert, and only rows at or above it.
    model.threshold = float(scores.max())
    assert model.classify(inputs_frame()).tolist() == (scores >= scores.max()).tolist()


def test_threshold_just_above_a_tied_score_excludes_that_score(saved_model):
    """Frozen thresholds can sit one float64 step above a tied block of float32 model scores.

    Comparing float32 scores with that threshold would round it down onto the block under NumPy 2
    rules and add every tied row as an alert, so scores must be compared as float64.
    """
    _, metadata_path, models_dir = saved_model
    model = load_model_artifact(metadata_path, models_dir)
    highest_model_output = model.pipeline.predict_proba(
        compact_features(engineer_features(inputs_frame()))
    )[:, 1].astype("float32")
    highest = float(highest_model_output.max())
    model.threshold = float(np.nextafter(highest, np.inf))

    assert (highest_model_output >= model.threshold).any(), "float32 comparison would round down"
    assert not model.classify(inputs_frame()).any()


def test_extra_columns_such_as_labels_are_ignored(saved_model):
    _, metadata_path, models_dir = saved_model
    model = load_model_artifact(metadata_path, models_dir)
    tampered = inputs_frame().assign(isFraud=[1, 0], oldbalanceOrg=[9.0, 9.0])
    assert np.array_equal(model.predict_scores(tampered), model.predict_scores(inputs_frame()))


def test_altered_model_file_is_refused(saved_model):
    _, metadata_path, models_dir = saved_model
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with (models_dir / metadata["model_file"]).open("ab") as handle:
        handle.write(b"x")
    with pytest.raises(ModelArtifactError, match="hash"):
        load_model_artifact(metadata_path, models_dir)


def test_schema_version_mismatch_is_refused(saved_model):
    _, metadata_path, models_dir = saved_model
    rewrite_metadata(metadata_path, feature_schema_version="0.0.1")
    with pytest.raises(ModelArtifactError, match="schema"):
        load_model_artifact(metadata_path, models_dir)


def test_feature_column_mismatch_is_refused(saved_model):
    _, metadata_path, models_dir = saved_model
    rewrite_metadata(metadata_path, feature_columns=["amount"])
    with pytest.raises(ModelArtifactError, match="columns"):
        load_model_artifact(metadata_path, models_dir)


def test_missing_files_are_refused(saved_model, tmp_path):
    _, metadata_path, models_dir = saved_model
    with pytest.raises(ModelArtifactError, match="metadata"):
        load_model_artifact(tmp_path / "absent.json", models_dir)
    with pytest.raises(ModelArtifactError, match="not found"):
        load_model_artifact(metadata_path, tmp_path / "empty")


def test_model_loads_in_a_new_process_without_experiment_code(saved_model):
    _, metadata_path, models_dir = saved_model
    program = textwrap.dedent(
        f"""
        import sys
        import pandas as pd
        from pathlib import Path
        from app.ml.model_artifacts import load_model_artifact

        model = load_model_artifact(Path(r"{metadata_path}"), Path(r"{models_dir}"))
        inputs = pd.DataFrame([{{"amount": 100.0, "transaction_type": "PAYMENT", "step": 10,
                                 "destination_category": "merchant"}}])
        score = float(model.predict_scores(inputs)[0])
        assert 0.0 <= score <= 1.0
        for forbidden in ("imblearn", "shap", "app.ml.experiments", "app.ml.imbalance"):
            assert forbidden not in sys.modules, forbidden
        print("loaded")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program], cwd=BACKEND_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "loaded" in result.stdout
