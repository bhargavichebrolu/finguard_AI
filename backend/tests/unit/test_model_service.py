"""Tests of model verification, scoring, explanations and risk bands, using the frozen model."""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.core.config import Settings
from app.core.frozen_model import FROZEN_MODEL_SHA256, FROZEN_MODEL_VERSION, FROZEN_THRESHOLD
from app.ml.model_artifacts import ModelArtifactError
from app.ml.pipeline_io import sha256_file
from app.models.enums import PredictionDecision, RiskLevel
from app.services.model_service import (
    check_frozen_metadata,
    check_library_versions,
    load_verified_model,
)
from app.services.risk import assess_score

REPO_ROOT = Path(__file__).resolve().parents[3]
METADATA_DIR = REPO_ROOT / "artifacts" / "metadata"
MODEL_FILE = REPO_ROOT / "artifacts" / "models" / "fraud_detector_v1" / "model.joblib"

needs_model = pytest.mark.skipif(not MODEL_FILE.is_file(), reason="frozen model file is absent")


def settings_for(metadata_dir: Path, models_dir: Path) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://u:p@127.0.0.1:1/x_test",
        secret_key="k" * 40,
        model_metadata_path=metadata_dir / "model_v1.json",
        model_metrics_path=metadata_dir / "model_v1_metrics.json",
        preprocessing_metadata_path=metadata_dir / "preprocessing_v1.json",
        model_artifact_dir=models_dir,
        _env_file=None,
    )


@pytest.fixture(scope="module")
def model():
    if not MODEL_FILE.is_file():
        pytest.skip("frozen model file is absent")
    return load_verified_model(settings_for(METADATA_DIR, MODEL_FILE.parents[1]))


@pytest.fixture
def artifact_copy(tmp_path) -> tuple[Path, Path]:
    """Copy the artefacts, so a test can tamper with them and leave the originals alone."""
    if not MODEL_FILE.is_file():
        pytest.skip("frozen model file is absent")
    metadata_dir = tmp_path / "metadata"
    shutil.copytree(METADATA_DIR, metadata_dir)
    models_dir = tmp_path / "models" / "fraud_detector_v1"
    models_dir.mkdir(parents=True)
    shutil.copy(MODEL_FILE, models_dir / "model.joblib")
    return metadata_dir, models_dir.parent


def sample_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "amount": [181.0, 9_000_000.0, 50_000.0, 1_500.0],
            "transaction_type": ["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN"],
            "step": [2, 5, 14, 200],
            "destination_category": ["customer", "customer", "merchant", "customer"],
        }
    )


def edit_metadata(metadata_dir: Path, name: str, change) -> None:
    path = metadata_dir / name
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@needs_model
def test_frozen_files_on_disk_match_the_pins():
    assert sha256_file(MODEL_FILE) == FROZEN_MODEL_SHA256
    metadata = json.loads((METADATA_DIR / "model_v1.json").read_text(encoding="utf-8"))
    check_frozen_metadata(metadata)
    assert metadata["threshold"]["value"] == FROZEN_THRESHOLD


def test_model_loads_and_reports_the_frozen_version(model):
    assert model.version == FROZEN_MODEL_VERSION
    assert model.threshold == FROZEN_THRESHOLD


def test_altered_model_file_is_refused_before_loading(artifact_copy, monkeypatch):
    metadata_dir, models_dir = artifact_copy
    with (models_dir / "fraud_detector_v1" / "model.joblib").open("ab") as handle:
        handle.write(b"tampered")

    def must_not_load(*_args, **_kwargs):
        raise AssertionError("joblib.load ran on a file that failed its hash check")

    monkeypatch.setattr("app.ml.model_artifacts.joblib.load", must_not_load)
    with pytest.raises(ModelArtifactError, match="does not match metadata"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_replacing_model_and_metadata_together_is_refused(artifact_copy):
    metadata_dir, models_dir = artifact_copy
    model_path = models_dir / "fraud_detector_v1" / "model.joblib"
    with model_path.open("ab") as handle:
        handle.write(b"tampered")
    new_hash = sha256_file(model_path)
    edit_metadata(metadata_dir, "model_v1.json", lambda data: data.update(model_sha256=new_hash))
    with pytest.raises(ModelArtifactError, match="frozen hash"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_changed_threshold_is_refused(artifact_copy):
    metadata_dir, models_dir = artifact_copy
    edit_metadata(metadata_dir, "model_v1.json", lambda data: data["threshold"].update(value=0.5))
    with pytest.raises(ModelArtifactError, match="frozen threshold"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_changed_preprocessing_record_is_refused(artifact_copy):
    metadata_dir, models_dir = artifact_copy
    edit_metadata(metadata_dir, "preprocessing_v1.json", lambda data: data.update(extra=1))
    with pytest.raises(ModelArtifactError, match="Preprocessing"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_metrics_for_another_threshold_are_refused(artifact_copy):
    metadata_dir, models_dir = artifact_copy
    edit_metadata(
        metadata_dir, "model_v1_metrics.json", lambda data: data["threshold"].update(value=0.5)
    )
    with pytest.raises(ModelArtifactError, match="different threshold"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_missing_model_file_is_refused(artifact_copy):
    metadata_dir, models_dir = artifact_copy
    (models_dir / "fraud_detector_v1" / "model.joblib").unlink()
    with pytest.raises(ModelArtifactError, match="not found"):
        load_verified_model(settings_for(metadata_dir, models_dir))


def test_different_library_version_is_refused():
    metadata = {"library_versions": {"scikit-learn": "0.0.1", "xgboost": "0.0.1"}}
    with pytest.raises(ModelArtifactError, match="was saved with"):
        check_library_versions(metadata)


@pytest.mark.parametrize(
    "change",
    [
        {"model_version": "other"},
        {"model_sha256": "0" * 64},
        {"threshold": {"value": 0.03}},
        {"status": "draft"},
    ],
)
def test_metadata_disagreeing_with_the_pins_is_refused(change):
    metadata = {
        "model_version": FROZEN_MODEL_VERSION,
        "model_sha256": FROZEN_MODEL_SHA256,
        "threshold": {"value": FROZEN_THRESHOLD},
        "status": "frozen",
    }
    check_frozen_metadata(metadata)
    with pytest.raises(ModelArtifactError):
        check_frozen_metadata({**metadata, **change})


def test_scores_are_between_zero_and_one(model):
    scores = model.score(sample_inputs())
    assert scores.shape == (4,)
    assert ((scores >= 0) & (scores <= 1)).all()


def test_score_matches_the_phase_2_classify_method(model):
    inputs = sample_inputs()
    assert ((model.score(inputs) >= model.threshold) == model.loaded.classify(inputs)).all()


def test_scoring_one_row_gives_the_same_result_as_in_a_batch(model):
    inputs = sample_inputs()
    together = model.score(inputs)
    alone = [model.score(inputs.iloc[[i]])[0] for i in range(len(inputs))]
    np.testing.assert_array_equal(together, alone)


def test_label_and_balance_columns_do_not_change_scores(model):
    inputs = sample_inputs()
    polluted = inputs.assign(isFraud=1, newbalanceOrig=0.0, oldbalanceOrg=123.0)
    np.testing.assert_array_equal(model.score(inputs), model.score(polluted))


def test_concurrent_scoring_is_consistent(model):
    inputs = sample_inputs()
    expected = model.score(inputs)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: model.score(inputs), range(40)))
    for result in results:
        np.testing.assert_array_equal(result, expected)


def test_explanation_adds_up_to_the_score(model):
    inputs = sample_inputs()
    scores = model.score(inputs)
    for explanation, score in zip(model.explain(inputs), scores, strict=True):
        margin = explanation["base_value"] + sum(explanation["by_group"].values())
        np.testing.assert_allclose(1.0 / (1.0 + np.exp(-margin)), score, atol=1e-5)


def test_explanation_matches_the_shap_library(model):
    shap = pytest.importorskip("shap")
    inputs = sample_inputs()
    pipeline = model.loaded.pipeline
    from app.ml.features import engineer_features
    from app.ml.preprocessing import compact_features

    matrix = pipeline.named_steps["preprocess"].transform(
        compact_features(engineer_features(inputs))
    )
    expected = shap.TreeExplainer(pipeline.named_steps["model"]).shap_values(matrix)
    names = [str(n) for n in pipeline.named_steps["preprocess"].get_feature_names_out()]
    for row, explanation in enumerate(model.explain(inputs)):
        found = {item["feature"]: item["contribution"] for item in explanation["by_feature"]}
        np.testing.assert_allclose([found[n] for n in names], expected[row], atol=1e-4)


def test_explanation_groups_cover_every_feature(model):
    explanation = model.explain(sample_inputs())[0]
    assert set(explanation["by_group"]) == {
        "amount",
        "hour",
        "transaction_type_and_destination",
    }
    assert len(explanation["by_feature"]) == 12


@pytest.mark.parametrize(
    ("score", "decision", "level"),
    [
        (0.0, PredictionDecision.NOT_FLAGGED, RiskLevel.LOW),
        (0.0199, PredictionDecision.NOT_FLAGGED, RiskLevel.LOW),
        (0.02, PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.MEDIUM),
        (0.2999, PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.MEDIUM),
        (0.3, PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.HIGH),
        (1.0, PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.HIGH),
    ],
)
def test_risk_bands_at_their_edges(score, decision, level):
    assessment = assess_score(score, threshold=0.02, high_boundary=0.3)
    assert assessment.decision is decision
    assert assessment.risk_level is level
    assert assessment.risk_score == pytest.approx(score * 100)


def test_the_frozen_threshold_itself_is_flagged():
    assessment = assess_score(FROZEN_THRESHOLD, FROZEN_THRESHOLD, 0.3)
    assert assessment.decision is PredictionDecision.FLAG_FOR_REVIEW
    just_below = np.nextafter(FROZEN_THRESHOLD, 0.0)
    assert assess_score(just_below, FROZEN_THRESHOLD, 0.3).decision is (
        PredictionDecision.NOT_FLAGGED
    )


def test_moving_the_high_boundary_never_changes_who_is_flagged():
    scores = np.linspace(0, 1, 501)
    for boundary in (0.05, 0.3, 0.9, 1.0):
        decisions = [assess_score(s, FROZEN_THRESHOLD, boundary).decision for s in scores]
        expected = [
            PredictionDecision.FLAG_FOR_REVIEW
            if s >= FROZEN_THRESHOLD
            else PredictionDecision.NOT_FLAGGED
            for s in scores
        ]
        assert decisions == expected


def test_a_boundary_at_or_below_the_threshold_is_refused():
    with pytest.raises(ValueError, match="above the frozen threshold"):
        assess_score(0.5, 0.3, 0.3)
