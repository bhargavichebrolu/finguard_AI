"""API tests of scoring, storage, wording and the transaction explorer."""

import uuid

import numpy as np
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.frozen_model import FROZEN_MODEL_VERSION, FROZEN_THRESHOLD, SCORE_NOTE
from app.models.enums import InvestigationStatus, UserRole
from app.models.records import AuditLog, Investigation, Prediction, Transaction

pytestmark = pytest.mark.database

PREDICT = "/api/v1/transactions/predict"
LIST = "/api/v1/transactions"
# Chosen from the frozen model's output: the first scores above the threshold, the second below.
HIGH_SCORING = {
    "amount": 9_000_000.0,
    "transaction_type": "TRANSFER",
    "step": 5,
    "destination_category": "customer",
}
LOW_SCORING = {
    "amount": 100.0,
    "transaction_type": "PAYMENT",
    "step": 12,
    "destination_category": "merchant",
}


@pytest.fixture
def analyst(headers_for):
    return headers_for(UserRole.ANALYST)


def test_flagged_prediction_has_every_required_field(client, analyst, session):
    response = client.post(PREDICT, headers=analyst, json=HIGH_SCORING)
    assert response.status_code == 201
    body = response.json()
    assert body["prediction"] == "FLAG_FOR_REVIEW"
    assert body["model_score"] >= FROZEN_THRESHOLD
    assert body["score_is_calibrated"] is False
    assert body["score_type"] == "uncalibrated_model_score"
    assert body["score_note"] == SCORE_NOTE
    assert body["model_version"] == FROZEN_MODEL_VERSION
    assert body["threshold_used"] == FROZEN_THRESHOLD
    assert body["risk_score"] == pytest.approx(body["model_score"] * 100)
    assert body["risk_level"] in {"MEDIUM", "HIGH"}
    assert body["investigation_status"] == "NEW"


def test_unflagged_prediction_is_low_and_has_no_investigation(client, analyst, session):
    body = client.post(PREDICT, headers=analyst, json=LOW_SCORING).json()
    assert body["prediction"] == "NOT_FLAGGED"
    assert body["model_score"] < FROZEN_THRESHOLD
    assert body["risk_level"] == "LOW"
    assert body["investigation_id"] is None
    assert session.scalar(select(Investigation)) is None


def test_api_score_equals_the_model_called_directly(client, analyst):
    body = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    model = client.app.state.model
    import pandas as pd

    direct = model.score(pd.DataFrame([HIGH_SCORING]))[0]
    assert body["model_score"] == float(direct)


def test_prediction_is_stored_with_model_version_and_threshold(client, analyst, session):
    body = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    stored = session.scalar(
        select(Prediction).where(Prediction.transaction_id == uuid.UUID(body["transaction_id"]))
    )
    assert stored.model_version == FROZEN_MODEL_VERSION
    assert stored.threshold_used == FROZEN_THRESHOLD
    assert stored.high_risk_boundary_used == get_settings().default_high_risk_boundary
    assert stored.model_score == body["model_score"]
    assert stored.score_is_calibrated is False


def test_stored_amount_is_exact(client, analyst, session):
    client.post(PREDICT, headers=analyst, json={**LOW_SCORING, "amount": 1234.56})
    stored = session.scalar(select(Transaction))
    assert str(stored.amount) == "1234.56"


def test_prediction_is_audited(client, analyst, session):
    client.post(PREDICT, headers=analyst, json=HIGH_SCORING)
    entry = session.scalar(select(AuditLog).where(AuditLog.action == "transaction.predicted"))
    assert entry.details == {"decision": "FLAG_FOR_REVIEW", "model_version": FROZEN_MODEL_VERSION}


def test_explanation_is_returned_and_adds_up(client, analyst):
    body = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    explanation = body["explanation"]
    assert set(explanation["by_group"]) == {
        "amount",
        "hour",
        "transaction_type_and_destination",
    }
    margin = explanation["base_value"] + sum(explanation["by_group"].values())
    np.testing.assert_allclose(1.0 / (1.0 + np.exp(-margin)), body["model_score"], atol=1e-5)
    assert any("does not establish" in text for text in explanation["limitations"])


def test_no_response_or_schema_uses_probability_wording(client, analyst):
    body = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    schema = client.get("/openapi.json").text
    for text in (str(body["explanation"]["by_group"]), str(list(body))):
        assert "probability" not in text.lower()
    assert "fraud_probability" not in schema
    assert "confirmed" not in schema.lower()


@pytest.mark.parametrize(
    ("change", "location"),
    [
        ({"amount": 0}, "amount"),
        ({"amount": -5}, "amount"),
        ({"amount": 1.234}, "amount"),
        ({"amount": 1e20}, "amount"),
        ({"amount": "abc"}, "amount"),
        ({"transaction_type": "WIRE"}, "transaction_type"),
        ({"step": 0}, "step"),
        ({"step": 1.5}, "step"),
        ({"destination_category": "bank"}, "destination_category"),
    ],
)
def test_invalid_values_are_refused(client, analyst, session, change, location):
    response = client.post(PREDICT, headers=analyst, json={**HIGH_SCORING, **change})
    assert response.status_code == 422
    assert location in str(response.json()["errors"][0]["location"])
    assert session.scalar(select(Transaction)) is None


@pytest.mark.parametrize("field", ["amount", "transaction_type", "step", "destination_category"])
def test_each_input_is_required(client, analyst, field):
    body = {key: value for key, value in HIGH_SCORING.items() if key != field}
    assert client.post(PREDICT, headers=analyst, json=body).status_code == 422


@pytest.mark.parametrize(
    "combination",
    [
        {"transaction_type": "TRANSFER", "destination_category": "merchant"},
        {"transaction_type": "PAYMENT", "destination_category": "customer"},
    ],
)
def test_combinations_absent_from_training_are_refused(client, analyst, combination):
    response = client.post(PREDICT, headers=analyst, json={**HIGH_SCORING, **combination})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field", ["isFraud", "isFlaggedFraud", "newbalanceOrig", "oldbalanceDest", "nameDest"]
)
def test_labels_and_leaky_fields_are_refused(client, analyst, field):
    response = client.post(PREDICT, headers=analyst, json={**HIGH_SCORING, field: 1})
    assert response.status_code == 422


@pytest.mark.parametrize("identifier", ["=SUM(A1)", "-1+1", "@cmd", "+1", "a b", "x" * 65])
def test_unsafe_identifiers_are_refused(client, analyst, identifier):
    body = {**HIGH_SCORING, "external_transaction_id": identifier}
    assert client.post(PREDICT, headers=analyst, json=body).status_code == 422


def test_repeated_identifier_is_a_conflict_and_stores_nothing_new(client, analyst, session):
    body = {**HIGH_SCORING, "external_transaction_id": "ABC-1"}
    assert client.post(PREDICT, headers=analyst, json=body).status_code == 201
    assert client.post(PREDICT, headers=analyst, json=body).status_code == 409
    assert len(session.scalars(select(Prediction)).all()) == 1
    assert len(session.scalars(select(Investigation)).all()) == 1


def test_identifier_is_generated_when_omitted(client, analyst):
    body = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    assert body["external_transaction_id"].startswith("TXN-")


def test_prediction_rate_limit(client, analyst, monkeypatch):
    monkeypatch.setattr(get_settings(), "predict_rate_limit_per_minute", 2)
    assert client.post(PREDICT, headers=analyst, json=HIGH_SCORING).status_code == 201
    assert client.post(PREDICT, headers=analyst, json=HIGH_SCORING).status_code == 201
    assert client.post(PREDICT, headers=analyst, json=HIGH_SCORING).status_code == 429


def _store_samples(client, headers) -> None:
    for identifier, payload in (
        ("HIGH-A", HIGH_SCORING),
        ("HIGH-B", {**HIGH_SCORING, "amount": 8_000_000.0, "step": 6}),
        ("LOW-A", LOW_SCORING),
        ("LOW-B", {**LOW_SCORING, "amount": 200.0, "step": 40}),
    ):
        response = client.post(
            PREDICT, headers=headers, json={**payload, "external_transaction_id": identifier}
        )
        assert response.status_code == 201


def _identifiers(response) -> set[str]:
    return {row["external_transaction_id"] for row in response.json()["items"]}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("external_id=low", {"LOW-A", "LOW-B"}),
        ("external_id=HIGH-A", {"HIGH-A"}),
        ("external_id=%25", set()),
        ("prediction=FLAG_FOR_REVIEW", {"HIGH-A", "HIGH-B"}),
        ("prediction=NOT_FLAGGED", {"LOW-A", "LOW-B"}),
        ("risk_level=LOW", {"LOW-A", "LOW-B"}),
        ("transaction_type=PAYMENT", {"LOW-A", "LOW-B"}),
        ("amount_min=150&amount_max=500", {"LOW-B"}),
        ("step_min=6&step_max=12", {"HIGH-B", "LOW-A"}),
        ("investigation_status=NEW", {"HIGH-A", "HIGH-B"}),
        ("investigation_status=CLOSED", set()),
    ],
)
def test_explorer_filters(client, analyst, query, expected):
    _store_samples(client, analyst)
    response = client.get(f"{LIST}?{query}", headers=analyst)
    assert response.status_code == 200
    assert _identifiers(response) == expected
    assert response.json()["total"] == len(expected)


def test_explorer_rows_never_mix_scores_and_labels(client, analyst):
    _store_samples(client, analyst)
    row = client.get(LIST, headers=analyst).json()["items"][0]
    assert row["score_is_calibrated"] is False
    assert not any(word in key for key in row for word in ("label", "fraud"))


@pytest.mark.parametrize(
    ("sort", "first"),
    [
        ("sort_by=amount&sort_order=desc", "HIGH-A"),
        ("sort_by=amount&sort_order=asc", "LOW-A"),
        ("sort_by=step&sort_order=desc", "LOW-B"),
    ],
)
def test_explorer_sorting(client, analyst, sort, first):
    _store_samples(client, analyst)
    rows = client.get(f"{LIST}?{sort}", headers=analyst).json()["items"]
    assert rows[0]["external_transaction_id"] == first


def test_explorer_sorts_by_score(client, analyst):
    _store_samples(client, analyst)
    rows = client.get(f"{LIST}?sort_by=model_score&sort_order=desc", headers=analyst).json()[
        "items"
    ]
    scores = [row["model_score"] for row in rows]
    assert scores == sorted(scores, reverse=True)


def test_explorer_pagination_is_complete_and_stable(client, analyst):
    _store_samples(client, analyst)
    seen = []
    for offset in range(0, 4, 2):
        page = client.get(f"{LIST}?limit=2&offset={offset}&sort_by=prediction", headers=analyst)
        assert page.status_code == 422
        page = client.get(f"{LIST}?limit=2&offset={offset}&sort_by=amount", headers=analyst).json()
        assert page["total"] == 4
        seen.extend(row["external_transaction_id"] for row in page["items"])
    assert len(seen) == len(set(seen)) == 4


@pytest.mark.parametrize("sort_by", ["created_at", "amount", "model_score", "step"])
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
@pytest.mark.parametrize("query", ["", "&investigation_status=NEW", "&transaction_type=PAYMENT"])
def test_explorer_pages_match_one_full_sort(client, analyst, sort_by, sort_order, query):
    # Phase 6: pages are fetched by a deferred join (identifiers sorted and skipped first, then
    # the rows joined). Walking the pages one row at a time must give exactly the single-page
    # order, including filters on the outer-joined investigation.
    _store_samples(client, analyst)
    base = f"{LIST}?sort_by={sort_by}&sort_order={sort_order}{query}"
    full = client.get(f"{base}&limit=100", headers=analyst).json()
    paged = []
    for offset in range(full["total"] + 1):
        page = client.get(f"{base}&limit=1&offset={offset}", headers=analyst).json()
        assert page["total"] == full["total"]
        paged.extend(page["items"])
    assert paged == full["items"]
    assert len(full["items"]) == full["total"] > 0


def test_detail_view_has_prd_fields(client, analyst):
    created = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()
    body = client.get(f"{LIST}/{created['transaction_id']}", headers=analyst).json()
    assert body["transaction_id"] == created["transaction_id"]
    assert body["amount"] == HIGH_SCORING["amount"]
    assert body["model_score"] == created["model_score"]
    assert body["risk_level"] == created["risk_level"]
    assert body["model_version"] == FROZEN_MODEL_VERSION
    assert body["created_at"]
    assert body["explanation"]["by_feature"]
    assert body["investigation"]["status"] == InvestigationStatus.NEW.value
    assert body["investigation"]["notes"] == []
    assert body["investigation"]["history"][0]["to_status"] == "NEW"


def test_unknown_transaction_is_not_found(client, analyst):
    assert client.get(f"{LIST}/{uuid.uuid4()}", headers=analyst).status_code == 404


def test_demo_records_are_labelled_and_kept_apart(client, headers_for, session):
    demo = headers_for(UserRole.DEMO)
    analyst = headers_for(UserRole.ANALYST)
    demo_row = client.post(PREDICT, headers=demo, json=HIGH_SCORING).json()
    analyst_row = client.post(PREDICT, headers=analyst, json=HIGH_SCORING).json()

    assert demo_row["is_demo"] is True
    assert demo_row["investigation_id"] is None
    assert analyst_row["is_demo"] is False
    assert _identifiers(client.get(LIST, headers=demo)) == {demo_row["external_transaction_id"]}
    assert _identifiers(client.get(LIST, headers=analyst)) == {
        analyst_row["external_transaction_id"]
    }
    other = client.get(f"{LIST}/{analyst_row['transaction_id']}", headers=demo)
    assert other.status_code == 404
