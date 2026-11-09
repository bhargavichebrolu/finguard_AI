"""API tests that Phase 2 results are served unchanged, and of reports and settings.

No test partition is read here. Figures are compared with the saved Phase 2 files.
"""

import csv
import io
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.frozen_model import FROZEN_MODEL_SHA256, FROZEN_MODEL_VERSION, FROZEN_THRESHOLD
from app.models.enums import UserRole
from app.models.records import AuditLog, ModelVersion, Prediction

pytestmark = pytest.mark.database

REPO_ROOT = Path(__file__).resolve().parents[3]
SAVED_METRICS = json.loads(
    (REPO_ROOT / "artifacts" / "metadata" / "model_v1_metrics.json").read_text(encoding="utf-8")
)
PREDICT = "/api/v1/transactions/predict"
FLAGGED = {
    "amount": 9_000_000.0,
    "transaction_type": "TRANSFER",
    "step": 5,
    "destination_category": "customer",
}
NOT_FLAGGED = {
    "amount": 100.0,
    "transaction_type": "PAYMENT",
    "step": 12,
    "destination_category": "merchant",
}


@pytest.fixture
def analyst(headers_for):
    return headers_for(UserRole.ANALYST)


def test_active_model_is_the_frozen_one(client, analyst):
    body = client.get("/api/v1/models/active", headers=analyst).json()
    assert body["version"] == FROZEN_MODEL_VERSION
    assert body["algorithm"] == "xgboost"
    assert body["model_sha256"] == FROZEN_MODEL_SHA256
    assert body["threshold"] == FROZEN_THRESHOLD
    assert body["score_is_calibrated"] is False
    assert body["is_active"] is True


def test_model_list_has_only_the_frozen_model(client, analyst):
    rows = client.get("/api/v1/models", headers=analyst).json()
    assert [row["version"] for row in rows] == [FROZEN_MODEL_VERSION]
    assert "metrics_json" not in rows[0]


def test_saved_metrics_are_stored_unchanged_in_the_registry(client, session):
    row = session.scalar(select(ModelVersion))
    assert row.metrics_json == SAVED_METRICS


def test_metrics_endpoint_serves_saved_values_exactly(client, analyst):
    body = client.get("/api/v1/models/metrics", headers=analyst).json()
    assert body["test"]["at_frozen_threshold"] == SAVED_METRICS["test"]["at_frozen_threshold"]
    assert body["test"]["ranking"] == SAVED_METRICS["test"]["ranking"]
    assert body["test"]["regimes"] == SAVED_METRICS["test"]["regimes"]
    assert body["validation"]["at_threshold"] == SAVED_METRICS["validation"]["at_threshold"]
    assert body["validation"]["ranking"] == SAVED_METRICS["validation"]["ranking"]
    assert body["threshold"] == SAVED_METRICS["threshold"]
    assert body["score_is_calibrated"] is False


def test_saved_results_are_the_phase_2_figures():
    test = SAVED_METRICS["test"]["at_frozen_threshold"]
    assert round(test["false_positive_rate"] * 100, 3) == 0.282
    assert round(test["recall"] * 100, 1) == 45.9
    assert round(test["precision"] * 100, 1) == 40.7
    assert (test["true_positives"], test["false_positives"]) == (1839, 2684)
    assert (test["false_negatives"], test["true_negatives"]) == (2171, 949050)
    assert SAVED_METRICS["threshold"]["operational_fpr_cap"] == 0.001
    normal = SAVED_METRICS["test"]["regimes"]["normal"]["at_frozen_threshold"]
    assert round(normal["recall"] * 100, 1) == 21.9


def test_performance_notes_state_the_required_shortfalls(client, analyst):
    notes = " ".join(
        client.get("/api/v1/models/metrics", headers=analyst).json()["performance_notes"]
    )
    assert "0.282%" in notes
    assert "2.8 times the 0.1% target" in notes
    assert "not met" in notes
    assert "45.9%" in notes
    assert "21.9%" in notes
    assert "56.1%" in notes
    assert "40.7%" in notes
    assert "0.059% on validation and 0.420% on test" in notes
    assert "not evidence of improvement" in notes
    assert "not calibrated" in notes
    assert "synthetic" in notes


def test_feature_importance_comes_from_saved_results_with_limitations(client, analyst):
    body = client.get("/api/v1/models/feature-importance", headers=analyst).json()
    saved = SAVED_METRICS["global_feature_importance"]
    assert body["by_group"] == saved["by_group"]
    assert body["by_feature"] == saved["by_feature"]
    assert any("does not establish" in text for text in body["limitations"])


def test_summary_counts_stored_records(client, analyst):
    client.post(PREDICT, headers=analyst, json=FLAGGED)
    client.post(PREDICT, headers=analyst, json=NOT_FLAGGED)
    body = client.get("/api/v1/reports/summary", headers=analyst).json()
    flags = body["model_flags"]
    assert flags["total_analysed"] == 2
    assert flags["flagged_for_review"] == 1
    assert flags["not_flagged"] == 1
    assert flags["flag_rate"] == 0.5
    assert flags["total_value"] == 9_000_100.0
    assert flags["flagged_value"] == 9_000_000.0
    assert sum(flags["risk_distribution"].values()) == 2
    assert flags["risk_distribution"]["LOW"] == 1
    assert flags["type_distribution"]["TRANSFER"] == {"analysed": 1, "flagged": 1}
    assert flags["flags_by_simulation_day"] == [{"day": 0, "analysed": 2, "flagged": 1}]
    assert body["investigation_workflow"]["status_counts"] == {"NEW": 1}
    assert body["uploaded_labels"]["labelled_rows"] == 0
    assert len(body["recent_activity"]) == 2
    assert "0.282%" in " ".join(body["model_performance_notes"])


def test_summary_of_an_empty_database(client, analyst):
    body = client.get("/api/v1/reports/summary", headers=analyst).json()
    assert body["model_flags"]["total_analysed"] == 0
    assert body["model_flags"]["flag_rate"] == 0.0
    assert body["recent_activity"] == []


def test_summary_keeps_flags_workflow_and_labels_separate(
    client, analyst, headers_for, tmp_path, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_tmp_dir", tmp_path)
    text = (
        "amount,transaction_type,step,destination_category,isFraud\n"
        "9000000.00,TRANSFER,5,customer,0\n"
        "100.00,PAYMENT,12,merchant,1\n"
    )
    client.post(
        "/api/v1/batches/upload",
        headers=analyst,
        files={"file": ("a.csv", text.encode(), "text/csv")},
    )
    # Uploads are queued since Phase 5 M4; process the queue now, as a worker would.
    from app.services.batch_service import process_available_jobs

    assert process_available_jobs(client.app.state.model, "test-worker") == 1
    investigation = client.get("/api/v1/investigations", headers=analyst).json()["items"][0]
    client.patch(
        f"/api/v1/investigations/{investigation['id']}",
        headers=headers_for(UserRole.INVESTIGATOR),
        json={"status": "FALSE_ALARM"},
    )
    body = client.get("/api/v1/reports/summary", headers=analyst).json()
    # The model flagged the first row. A person marked it a false alarm. Its label says not fraud.
    # The label marks the other row, which the model did not flag. Each count stays independent.
    assert body["model_flags"]["flagged_for_review"] == 1
    assert body["investigation_workflow"]["status_counts"] == {"FALSE_ALARM": 1}
    assert body["uploaded_labels"]["labelled_rows"] == 2
    assert body["uploaded_labels"]["labelled_fraud_rows"] == 1
    assert body["uploaded_labels"]["labelled_fraud_value"] == 100.0
    assert "reported separately" in body["note"]
    labels_keys = set(body["uploaded_labels"])
    assert labels_keys == {"labelled_rows", "labelled_fraud_rows", "labelled_fraud_value"}


def test_demo_summary_is_labelled_and_separate(client, headers_for):
    demo = headers_for(UserRole.DEMO)
    analyst = headers_for(UserRole.ANALYST)
    client.post(PREDICT, headers=demo, json=FLAGGED)
    client.post(PREDICT, headers=analyst, json=NOT_FLAGGED)
    demo_body = client.get("/api/v1/reports/summary", headers=demo).json()
    analyst_body = client.get("/api/v1/reports/summary", headers=analyst).json()
    assert demo_body["is_demo"] is True
    assert demo_body["scope"] == "demo_sample_records"
    assert demo_body["model_flags"]["flagged_for_review"] == 1
    assert analyst_body["is_demo"] is False
    assert analyst_body["model_flags"]["flagged_for_review"] == 0


def _report(client, headers, report_type) -> list[dict[str, str]]:
    response = client.get(f"/api/v1/reports/export?report_type={report_type}", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert f"finguard-{report_type}.csv" in response.headers["content-disposition"]
    return list(csv.DictReader(io.StringIO(response.text)))


def test_prediction_report(client, analyst):
    client.post(PREDICT, headers=analyst, json=FLAGGED)
    rows = _report(client, analyst, "predictions")
    assert len(rows) == 1
    assert rows[0]["prediction"] == "FLAG_FOR_REVIEW"
    assert rows[0]["score_is_calibrated"] == "False"
    assert rows[0]["model_version"] == FROZEN_MODEL_VERSION
    assert float(rows[0]["threshold_used"]) == FROZEN_THRESHOLD


def test_flag_summary_report(client, analyst):
    client.post(PREDICT, headers=analyst, json=FLAGGED)
    client.post(PREDICT, headers=analyst, json=NOT_FLAGGED)
    rows = {row["transaction_type"]: row for row in _report(client, analyst, "flag_summary")}
    assert rows["TRANSFER"]["flagged_for_review"] == "1"
    assert rows["PAYMENT"]["flagged_for_review"] == "0"


def test_investigation_report(client, analyst):
    client.post(PREDICT, headers=analyst, json=FLAGGED)
    rows = _report(client, analyst, "investigations")
    assert rows[0]["workflow_status"] == "NEW"
    assert rows[0]["assigned_user_id"] == ""


def test_model_evaluation_report_matches_saved_values(client, analyst):
    rows = _report(client, analyst, "model_evaluation")
    lookup = {(row["partition"], row["slice"], row["metric"]): row["value"] for row in rows}
    test = SAVED_METRICS["test"]["at_frozen_threshold"]
    assert float(lookup[("test", "all", "false_positive_rate")]) == test["false_positive_rate"]
    assert float(lookup[("test", "all", "recall")]) == test["recall"]
    normal = SAVED_METRICS["test"]["regimes"]["normal"]["at_frozen_threshold"]
    assert float(lookup[("test", "normal_steps", "recall")]) == normal["recall"]
    assert float(lookup[("target", "all", "false_positive_rate_target")]) == 0.001


def test_unknown_report_type_is_refused(client, analyst):
    response = client.get("/api/v1/reports/export?report_type=everything", headers=analyst)
    assert response.status_code == 422


def test_demo_user_cannot_export_reports(client, headers_for):
    response = client.get("/api/v1/reports/export", headers=headers_for(UserRole.DEMO))
    assert response.status_code == 403


def test_settings_show_everything_prd_lists(client, analyst):
    body = client.get("/api/v1/settings", headers=analyst).json()
    assert body["high_risk_boundary"] == 0.30
    assert body["frozen_threshold"] == FROZEN_THRESHOLD
    assert body["frozen_threshold_is_editable"] is False
    assert "not calibrated" in body["risk_bands"]
    assert body["model_version"] == FROZEN_MODEL_VERSION
    assert body["database_available"] is True
    assert body["application_version"]
    assert "PaySim" in body["dataset"]["name"]
    assert body["dataset"]["split_boundaries"]["last_step"] == 743


def test_admin_can_change_the_boundary_and_it_is_audited(client, headers_for, session):
    response = client.patch(
        "/api/v1/settings", headers=headers_for(UserRole.ADMIN), json={"high_risk_boundary": 0.5}
    )
    assert response.status_code == 200
    assert response.json()["high_risk_boundary"] == 0.5
    entry = session.scalar(select(AuditLog).where(AuditLog.action == "settings.updated"))
    assert entry.details == {"from": 0.30, "to": 0.5}


@pytest.mark.parametrize("role", [UserRole.ANALYST, UserRole.INVESTIGATOR, UserRole.DEMO])
def test_only_admins_can_change_settings(client, headers_for, role):
    response = client.patch(
        "/api/v1/settings", headers=headers_for(role), json={"high_risk_boundary": 0.5}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {"high_risk_boundary": 0.02},
        {"high_risk_boundary": FROZEN_THRESHOLD},
        {"high_risk_boundary": 1.5},
        {"high_risk_boundary": 0},
        {"threshold": 0.5},
        {"frozen_threshold": 0.5},
        {"high_risk_boundary": 0.5, "threshold": 0.5},
    ],
)
def test_threshold_cannot_be_changed_through_settings(client, headers_for, body):
    headers = headers_for(UserRole.ADMIN)
    assert client.patch("/api/v1/settings", headers=headers, json=body).status_code == 422
    assert client.get("/api/v1/settings", headers=headers).json()["frozen_threshold"] == (
        FROZEN_THRESHOLD
    )


def test_changing_the_boundary_never_changes_flags_or_stored_rows(
    client, headers_for, analyst, session
):
    before = client.post(PREDICT, headers=analyst, json=FLAGGED).json()
    assert before["risk_level"] == "HIGH" or before["model_score"] < 0.30
    new_boundary = min(before["model_score"] + 0.01, 1.0)
    client.patch(
        "/api/v1/settings",
        headers=headers_for(UserRole.ADMIN),
        json={"high_risk_boundary": new_boundary},
    )
    after = client.post(PREDICT, headers=analyst, json=FLAGGED).json()
    assert after["model_score"] == before["model_score"]
    assert after["prediction"] == before["prediction"] == "FLAG_FOR_REVIEW"
    assert after["threshold_used"] == before["threshold_used"] == FROZEN_THRESHOLD
    assert after["high_risk_boundary_used"] == new_boundary
    session.expire_all()
    rows = {str(row.transaction_id): row for row in session.scalars(select(Prediction))}
    assert rows[before["transaction_id"]].high_risk_boundary_used == 0.30
    assert rows[before["transaction_id"]].risk_level.value == before["risk_level"]
