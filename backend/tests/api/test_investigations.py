"""API tests of the investigation workflow: statuses, history, notes, assignment and access."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.models.enums import InvestigationStatus, UserRole
from app.models.records import AuditLog, InvestigationStatusHistory, Prediction
from app.security.tokens import create_access_token

pytestmark = pytest.mark.database

BASE = "/api/v1/investigations"
FLAGGED = {
    "amount": 9_000_000.0,
    "transaction_type": "TRANSFER",
    "step": 5,
    "destination_category": "customer",
}


@pytest.fixture
def investigator(headers_for):
    return headers_for(UserRole.INVESTIGATOR)


@pytest.fixture
def case(client, headers_for) -> dict:
    """Create a flagged prediction, which opens an investigation."""
    body = client.post(
        "/api/v1/transactions/predict", headers=headers_for(UserRole.ANALYST), json=FLAGGED
    ).json()
    assert body["prediction"] == "FLAG_FOR_REVIEW"
    return body


def test_flag_opens_a_new_investigation_listed_with_its_score(client, investigator, case):
    body = client.get(BASE, headers=investigator).json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["id"] == case["investigation_id"]
    assert row["status"] == "NEW"
    assert "not verified criminal findings" in row["status_note"]
    assert row["model_score"] == case["model_score"]
    assert row["score_is_calibrated"] is False
    assert row["prediction"] == "FLAG_FOR_REVIEW"


@pytest.mark.parametrize("status", list(InvestigationStatus))
def test_every_prd_status_can_be_set(client, investigator, case, status):
    response = client.patch(
        f"{BASE}/{case['investigation_id']}", headers=investigator, json={"status": status.value}
    )
    assert response.status_code == 200
    assert response.json()["status"] == status.value


def test_prd_statuses_are_exactly_these():
    assert {status.value for status in InvestigationStatus} == {
        "NEW",
        "UNDER_REVIEW",
        "ESCALATED",
        "CLOSED",
        "FALSE_ALARM",
    }


def test_invalid_status_is_refused(client, investigator, case):
    for status in ("CONFIRMED_FRAUD", None):
        response = client.patch(
            f"{BASE}/{case['investigation_id']}", headers=investigator, json={"status": status}
        )
        assert response.status_code == 422


def test_empty_update_is_refused(client, investigator, case):
    response = client.patch(f"{BASE}/{case['investigation_id']}", headers=investigator, json={})
    assert response.status_code == 422


def test_status_history_records_each_change_in_order(client, make_user, case, session):
    user = make_user(UserRole.INVESTIGATOR)
    headers = {"Authorization": f"Bearer {create_access_token(user.id, 0)}"}
    url = f"{BASE}/{case['investigation_id']}"
    for status in ("UNDER_REVIEW", "ESCALATED", "CLOSED", "UNDER_REVIEW"):
        client.patch(url, headers=headers, json={"status": status})
    history = client.get(url, headers=headers).json()["history"]
    assert [(item["from_status"], item["to_status"]) for item in history] == [
        (None, "NEW"),
        ("NEW", "UNDER_REVIEW"),
        ("UNDER_REVIEW", "ESCALATED"),
        ("ESCALATED", "CLOSED"),
        ("CLOSED", "UNDER_REVIEW"),
    ]
    assert history[0]["changed_by"] is None
    assert history[1]["changed_by"] == str(user.id)


def test_setting_the_same_status_adds_no_history(client, investigator, case, session):
    url = f"{BASE}/{case['investigation_id']}"
    client.patch(url, headers=investigator, json={"status": "NEW"})
    assert len(session.scalars(select(InvestigationStatusHistory)).all()) == 1


def test_status_change_is_audited(client, investigator, case, session):
    client.patch(
        f"{BASE}/{case['investigation_id']}", headers=investigator, json={"status": "ESCALATED"}
    )
    entry = session.scalar(
        select(AuditLog).where(AuditLog.action == "investigation.status_changed")
    )
    assert entry.details == {"from": "NEW", "to": "ESCALATED"}
    assert entry.entity_id == case["investigation_id"]


def test_workflow_status_never_changes_the_prediction(client, investigator, case, session):
    client.patch(
        f"{BASE}/{case['investigation_id']}", headers=investigator, json={"status": "FALSE_ALARM"}
    )
    stored = session.scalar(select(Prediction))
    assert stored.model_score == case["model_score"]
    assert stored.prediction.value == "FLAG_FOR_REVIEW"
    assert stored.risk_level.value == case["risk_level"]


def test_notes_are_saved_with_author_and_shown_on_the_transaction(client, make_user, case):
    user = make_user(UserRole.INVESTIGATOR)
    headers = {"Authorization": f"Bearer {create_access_token(user.id, 0)}"}
    response = client.post(
        f"{BASE}/{case['investigation_id']}/notes",
        headers=headers,
        json={"note": "  Checked the amount.  "},
    )
    assert response.status_code == 201
    assert response.json()["note"] == "Checked the amount."
    assert response.json()["user_id"] == str(user.id)
    detail = client.get(f"/api/v1/transactions/{case['transaction_id']}", headers=headers).json()
    assert [note["note"] for note in detail["investigation"]["notes"]] == ["Checked the amount."]


def test_note_text_is_not_copied_to_the_audit_log(client, investigator, case, session):
    client.post(
        f"{BASE}/{case['investigation_id']}/notes",
        headers=investigator,
        json={"note": "private remark"},
    )
    entry = session.scalar(select(AuditLog).where(AuditLog.action == "investigation.note_added"))
    assert entry is not None
    assert "private remark" not in str(entry.details)


@pytest.mark.parametrize("note", ["", "    ", "x" * 5001])
def test_invalid_notes_are_refused(client, investigator, case, note):
    response = client.post(
        f"{BASE}/{case['investigation_id']}/notes", headers=investigator, json={"note": note}
    )
    assert response.status_code == 422


def test_note_changes_updated_at(client, investigator, case):
    url = f"{BASE}/{case['investigation_id']}"
    before = client.get(url, headers=investigator).json()["updated_at"]
    client.post(f"{url}/notes", headers=investigator, json={"note": "Later note."})
    assert client.get(url, headers=investigator).json()["updated_at"] > before


def test_assignment_and_unassignment(client, investigator, make_user, case):
    assignee = make_user(UserRole.INVESTIGATOR)
    url = f"{BASE}/{case['investigation_id']}"
    body = client.patch(url, headers=investigator, json={"assigned_user_id": str(assignee.id)})
    assert body.json()["assigned_user_id"] == str(assignee.id)
    assert body.json()["status"] == "NEW"
    listing = client.get(f"{BASE}?assigned_user_id={assignee.id}", headers=investigator).json()
    assert listing["total"] == 1
    body = client.patch(url, headers=investigator, json={"assigned_user_id": None})
    assert body.json()["assigned_user_id"] is None


@pytest.mark.parametrize(
    "values",
    [
        {"role": UserRole.ANALYST},
        {"role": UserRole.DEMO},
        {"role": UserRole.INVESTIGATOR, "is_active": False},
    ],
)
def test_assignee_must_be_an_active_investigator(client, investigator, make_user, case, values):
    assignee = make_user(**values)
    response = client.patch(
        f"{BASE}/{case['investigation_id']}",
        headers=investigator,
        json={"assigned_user_id": str(assignee.id)},
    )
    assert response.status_code == 422


def test_unknown_assignee_is_refused_and_nothing_changes(client, investigator, case, session):
    url = f"{BASE}/{case['investigation_id']}"
    response = client.patch(
        url,
        headers=investigator,
        json={"status": "CLOSED", "assigned_user_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422
    assert client.get(url, headers=investigator).json()["status"] == "NEW"
    assert len(session.scalars(select(InvestigationStatusHistory)).all()) == 1


def test_list_filters_by_status(client, investigator, case):
    url = f"{BASE}/{case['investigation_id']}"
    client.patch(url, headers=investigator, json={"status": "ESCALATED"})
    assert client.get(f"{BASE}?investigation_status=NEW", headers=investigator).json()["total"] == 0
    assert (
        client.get(f"{BASE}?investigation_status=ESCALATED", headers=investigator).json()["total"]
        == 1
    )


def test_analyst_can_view_but_not_change(client, headers_for, case):
    analyst = headers_for(UserRole.ANALYST)
    url = f"{BASE}/{case['investigation_id']}"
    assert client.get(url, headers=analyst).status_code == 200
    assert client.patch(url, headers=analyst, json={"status": "CLOSED"}).status_code == 403
    assert client.post(f"{url}/notes", headers=analyst, json={"note": "x"}).status_code == 403


def test_demo_user_has_no_access(client, headers_for, case):
    demo = headers_for(UserRole.DEMO)
    url = f"{BASE}/{case['investigation_id']}"
    assert client.get(BASE, headers=demo).status_code == 403
    assert client.get(url, headers=demo).status_code == 403
    assert client.patch(url, headers=demo, json={"status": "CLOSED"}).status_code == 403


def test_admin_can_update(client, headers_for, case):
    response = client.patch(
        f"{BASE}/{case['investigation_id']}",
        headers=headers_for(UserRole.ADMIN),
        json={"status": "UNDER_REVIEW"},
    )
    assert response.status_code == 200


def test_unknown_investigation_is_not_found(client, investigator):
    missing = f"{BASE}/{uuid.uuid4()}"
    assert client.get(missing, headers=investigator).status_code == 404
    assert client.patch(missing, headers=investigator, json={"status": "CLOSED"}).status_code == 404
    assert client.post(
        f"{missing}/notes", headers=investigator, json={"note": "x"}
    ).status_code == (404)


def test_simultaneous_changes_keep_the_history_consistent(client, investigator, case):
    url = f"{BASE}/{case['investigation_id']}"
    statuses = ["UNDER_REVIEW", "ESCALATED", "CLOSED", "FALSE_ALARM"] * 3
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(
            pool.map(
                lambda status: client.patch(url, headers=investigator, json={"status": status}),
                statuses,
            )
        )
    assert {result.status_code for result in results} == {200}
    body = client.get(url, headers=investigator).json()
    history = body["history"]
    assert history[-1]["to_status"] == body["status"]
    # Row locking means each change starts from the status the previous one left.
    for earlier, later in zip(history, history[1:], strict=False):
        assert later["from_status"] == earlier["to_status"]
