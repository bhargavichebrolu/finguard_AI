"""API tests of CSV upload, validation, processing, labels, errors and exports."""

import csv
import io
import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.frozen_model import FROZEN_MODEL_VERSION, FROZEN_THRESHOLD
from app.models.enums import BatchStatus, InvestigationStatus, UserRole
from app.models.records import (
    BatchJob,
    GroundTruthLabel,
    Investigation,
    Prediction,
    Transaction,
)
from app.services import batch_service
from app.utils.csv_safety import clean_filename, csv_lines, safe_cell

pytestmark = pytest.mark.database

UPLOAD = "/api/v1/batches/upload"
HEADER = "external_transaction_id,amount,transaction_type,step,destination_category"
FLAGGED_ROW = "B-1,9000000.00,TRANSFER,5,customer"
UNFLAGGED_ROW = "B-2,100.00,PAYMENT,12,merchant"


@pytest.fixture
def analyst(headers_for):
    return headers_for(UserRole.ANALYST)


@pytest.fixture
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_tmp_dir", tmp_path)
    return tmp_path


def send(client, headers, text: str | bytes, name: str = "data.csv"):
    content = text.encode() if isinstance(text, str) else text
    return client.post(UPLOAD, headers=headers, files={"file": (name, content, "text/csv")})


def finished_job(client, headers, text: str):
    response = send(client, headers, text)
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    return client.get(f"/api/v1/batches/{job_id}", headers=headers).json()


def test_valid_file_is_processed_completely(client, analyst, tmp_uploads, session):
    job = finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n{UNFLAGGED_ROW}\n")
    assert job["status"] == "COMPLETED"
    assert job["total_records"] == job["processed_records"] == job["succeeded_records"] == 2
    assert job["failed_records"] == 0
    assert job["progress_percent"] == 100.0
    assert job["completed_at"]
    assert len(session.scalars(select(Prediction)).all()) == 2


def test_temporary_file_is_deleted_after_processing(client, analyst, tmp_uploads):
    finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n")
    assert list(tmp_uploads.iterdir()) == []


def test_batch_results_match_single_predictions(client, analyst, tmp_uploads):
    job = finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n{UNFLAGGED_ROW}\n")
    rows = client.get(f"/api/v1/batches/{job['id']}/results", headers=analyst).json()["items"]
    by_id = {row["external_transaction_id"]: row for row in rows}
    single = client.post(
        "/api/v1/transactions/predict",
        headers=analyst,
        json={
            "amount": 9000000.00,
            "transaction_type": "TRANSFER",
            "step": 5,
            "destination_category": "customer",
        },
    ).json()
    assert by_id["B-1"]["model_score"] == single["model_score"]
    assert by_id["B-1"]["prediction"] == "FLAG_FOR_REVIEW"
    assert by_id["B-2"]["prediction"] == "NOT_FLAGGED"
    assert by_id["B-1"]["model_version"] == FROZEN_MODEL_VERSION
    assert by_id["B-1"]["threshold_used"] == FROZEN_THRESHOLD
    assert by_id["B-1"]["score_is_calibrated"] is False


def test_flagged_rows_open_investigations_and_get_explanations(
    client, analyst, tmp_uploads, session
):
    finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n{UNFLAGGED_ROW}\n")
    investigation = session.scalar(select(Investigation))
    assert investigation.status is InvestigationStatus.NEW
    assert len(session.scalars(select(Investigation)).all()) == 1
    predictions = {p.prediction.value: p for p in session.scalars(select(Prediction))}
    assert predictions["FLAG_FOR_REVIEW"].explanation_json is not None
    assert predictions["NOT_FLAGGED"].explanation_json is None


def test_chunks_commit_progress_across_many_rows(
    client, analyst, tmp_uploads, monkeypatch, session
):
    monkeypatch.setattr(get_settings(), "batch_chunk_rows", 3)
    rows = [f"M-{i},{100 + i}.00,CASH_IN,{i + 1},customer" for i in range(10)]
    job = finished_job(client, analyst, "\n".join([HEADER, *rows]) + "\n")
    assert job["processed_records"] == 10
    assert len(session.scalars(select(Transaction)).all()) == 10


def test_identifier_column_is_optional(client, analyst, tmp_uploads, session):
    text = "amount,transaction_type,step,destination_category\n50.00,CASH_OUT,3,customer\n"
    job = finished_job(client, analyst, text)
    assert job["status"] == "COMPLETED"
    assert session.scalar(select(Transaction)).external_transaction_id.startswith("TXN-")


def test_byte_order_mark_and_spaces_are_handled(client, analyst, tmp_uploads):
    text = (
        "﻿" + " amount , transaction_type,step,destination_category\n 50.00, CASH_OUT,3,customer\n"
    )
    assert finished_job(client, analyst, text)["status"] == "COMPLETED"


@pytest.mark.parametrize("name", ["data.txt", "data.csv.exe", "data", "data.xlsx"])
def test_wrong_extension_is_refused(client, analyst, tmp_uploads, name):
    response = send(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n", name)
    assert response.status_code == 422
    assert ".csv" in response.json()["detail"]
    assert list(tmp_uploads.iterdir()) == []


def test_oversized_file_is_refused_and_removed(client, analyst, tmp_uploads, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 40)
    response = send(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n")
    assert response.status_code == 413
    assert list(tmp_uploads.iterdir()) == []


def test_too_many_rows_are_refused(client, analyst, tmp_uploads, monkeypatch, session):
    monkeypatch.setattr(get_settings(), "max_batch_rows", 1)
    response = send(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n{UNFLAGGED_ROW}\n")
    assert response.status_code == 413
    assert list(tmp_uploads.iterdir()) == []
    assert session.scalar(select(BatchJob)) is None


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (b"amount,step\n1,2\n", "Missing required columns"),
        (f"{HEADER},mystery\n".encode(), "Unsupported columns"),
        (f"{HEADER},{HEADER}\n".encode(), "repeated"),
        (f"{HEADER}\n".encode(), "no rows"),
        (b"\xff\xfe\xfa\x80 not text", "UTF-8"),
        (b"amount\x00,step\n", "not a text CSV"),
    ],
)
def test_bad_files_are_refused(client, analyst, tmp_uploads, session, content, message):
    response = send(client, analyst, content)
    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert list(tmp_uploads.iterdir()) == []
    assert session.scalar(select(BatchJob)) is None


@pytest.mark.parametrize(
    "column", ["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "nameDest"]
)
def test_leaky_columns_are_refused(client, analyst, tmp_uploads, column):
    response = send(client, analyst, f"{HEADER},{column}\n{FLAGGED_ROW},1\n")
    assert response.status_code == 422
    assert column in response.json()["detail"]


@pytest.mark.parametrize(
    ("row", "column"),
    [
        (",,TRANSFER,5,customer", "amount"),
        ("E,abc,TRANSFER,5,customer", "amount"),
        ("E,-5.00,TRANSFER,5,customer", "amount"),
        ("E,1.234,TRANSFER,5,customer", "amount"),
        ("E,nan,TRANSFER,5,customer", "amount"),
        ("E,inf,TRANSFER,5,customer", "amount"),
        ("E,10.00,WIRE,5,customer", "transaction_type"),
        ("E,10.00,TRANSFER,zero,customer", "step"),
        ("E,10.00,TRANSFER,0,customer", "step"),
        ("E,10.00,TRANSFER,5,", "destination_category"),
        ("E,10.00,TRANSFER,5,bank", "destination_category"),
        ("E,10.00,TRANSFER,5,merchant", "row"),
        ("=cmd,10.00,TRANSFER,5,customer", "external_transaction_id"),
        ("E,10.00,TRANSFER,5,customer,extra", "row"),
    ],
)
def test_bad_rows_are_reported_and_good_rows_still_processed(
    client, analyst, tmp_uploads, session, row, column
):
    job = finished_job(client, analyst, f"{HEADER}\n{row}\n{UNFLAGGED_ROW}\n")
    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["processed_records"] == 2
    assert job["failed_records"] == 1
    assert job["succeeded_records"] == 1
    report = client.get(f"/api/v1/batches/{job['id']}/errors", headers=analyst)
    assert report.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(report.text)))
    assert rows[0]["row_number"] == "2"
    assert rows[0]["column"] == column
    assert len(session.scalars(select(Transaction)).all()) == 1


def test_error_report_does_not_repeat_rejected_values(client, analyst, tmp_uploads):
    job = finished_job(client, analyst, f"{HEADER}\nE,SECRETVALUE,TRANSFER,5,customer\n")
    report = client.get(f"/api/v1/batches/{job['id']}/errors", headers=analyst)
    assert "SECRETVALUE" not in report.text


def test_identifier_repeated_in_file_is_reported(client, analyst, tmp_uploads, session):
    row = "SAME,10.00,CASH_IN,5,customer"
    job = finished_job(client, analyst, f"{HEADER}\n{row}\n{row}\n")
    assert job["failed_records"] == 1
    assert job["succeeded_records"] == 1
    assert len(session.scalars(select(Transaction)).all()) == 1


def test_identifier_already_stored_is_reported_without_stopping(
    client, analyst, tmp_uploads, session
):
    finished_job(client, analyst, f"{HEADER}\n{UNFLAGGED_ROW}\n")
    job = finished_job(client, analyst, f"{HEADER}\n{UNFLAGGED_ROW}\n{FLAGGED_ROW}\n")
    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["failed_records"] == 1
    assert job["succeeded_records"] == 1
    assert len(session.scalars(select(Prediction)).all()) == 2


def test_stored_error_count_is_capped_but_failures_are_all_counted(
    client, analyst, tmp_uploads, monkeypatch
):
    monkeypatch.setattr(get_settings(), "max_stored_row_errors", 2)
    rows = [f"E{i},bad,TRANSFER,5,customer" for i in range(5)]
    job = finished_job(client, analyst, "\n".join([HEADER, *rows]) + "\n")
    assert job["failed_records"] == 5
    report = client.get(f"/api/v1/batches/{job['id']}/errors", headers=analyst)
    assert len(list(csv.DictReader(io.StringIO(report.text)))) == 2


def test_labels_are_stored_separately_and_do_not_change_scores(
    client, analyst, tmp_uploads, session
):
    plain = "amount,transaction_type,step,destination_category\n9000000.00,TRANSFER,5,customer\n"
    finished_job(client, analyst, plain)
    labelled = (
        "amount,transaction_type,step,destination_category,isFraud,isFlaggedFraud\n"
        "9000000.00,TRANSFER,5,customer,0,1\n"
    )
    job = finished_job(client, analyst, labelled)
    assert job["ignored_columns"] == ["isFlaggedFraud", "isFraud"]
    assert job["labels_supplied"] is True
    scores = [p.model_score for p in session.scalars(select(Prediction))]
    assert len(scores) == 2
    assert scores[0] == scores[1]
    label = session.scalar(select(GroundTruthLabel))
    assert label.is_fraud is False
    assert label.source == "uploaded_csv"
    assert len(session.scalars(select(GroundTruthLabel)).all()) == 1


@pytest.mark.parametrize(("value", "stored"), [("1", True), ("0", False), ("", None), ("x", None)])
def test_label_values_are_read_strictly_and_never_affect_scoring(
    client, analyst, tmp_uploads, session, value, stored
):
    text = (
        "amount,transaction_type,step,destination_category,isFraud\n"
        f"100.00,PAYMENT,12,merchant,{value}\n"
    )
    job = finished_job(client, analyst, text)
    assert job["failed_records"] == 0
    assert job["succeeded_records"] == 1
    assert session.scalar(select(Prediction)) is not None
    label = session.scalar(select(GroundTruthLabel))
    assert (label.is_fraud if label else None) is stored


def test_export_contains_results_and_scores_are_labelled(client, analyst, tmp_uploads):
    job = finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n{UNFLAGGED_ROW}\n")
    response = client.get(f"/api/v1/batches/{job['id']}/export", headers=analyst)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert {row["external_transaction_id"] for row in rows} == {"B-1", "B-2"}
    assert {row["score_is_calibrated"] for row in rows} == {"False"}
    assert {row["model_version"] for row in rows} == {FROZEN_MODEL_VERSION}
    assert "isFraud" not in response.text
    assert "probability" not in response.text


def test_upload_needs_permission_and_rate_limit_applies(client, analyst, tmp_uploads, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_rate_limit_per_minute", 1)
    assert client.post(UPLOAD, files={"file": ("a.csv", b"x")}).status_code == 401
    assert send(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n").status_code == 202
    assert send(client, analyst, f"{HEADER}\n{UNFLAGGED_ROW}\n").status_code == 429


def test_missing_file_field_is_refused(client, analyst):
    assert client.post(UPLOAD, headers=analyst).status_code == 422


def test_demo_batches_are_labelled_and_kept_apart(client, headers_for, tmp_uploads, session):
    demo = headers_for(UserRole.DEMO)
    analyst = headers_for(UserRole.ANALYST)
    job = finished_job(client, demo, f"{HEADER}\n{FLAGGED_ROW}\n")
    assert job["is_demo"] is True
    assert session.scalar(select(Investigation)) is None
    assert session.scalar(select(Transaction)).is_demo is True
    assert client.get(f"/api/v1/batches/{job['id']}", headers=analyst).status_code == 404
    assert client.get("/api/v1/batches", headers=analyst).json()["total"] == 0
    assert client.get("/api/v1/batches", headers=demo).json()["total"] == 1


def test_unknown_batch_is_not_found(client, analyst):
    missing = uuid.uuid4()
    for suffix in ("", "/results", "/export", "/errors"):
        assert client.get(f"/api/v1/batches/{missing}{suffix}", headers=analyst).status_code == 404


def test_processing_failure_marks_the_job_and_removes_the_file(
    client, analyst, tmp_uploads, monkeypatch, session
):
    def explode(*_args, **_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(batch_service, "score_inputs", explode)
    job = finished_job(client, analyst, f"{HEADER}\n{FLAGGED_ROW}\n")
    assert job["status"] == "FAILED"
    assert "secret internal detail" not in job["error_message"]
    assert list(tmp_uploads.iterdir()) == []


def test_restart_recovery_fails_unfinished_jobs_and_removes_files(session, tmp_path):
    leftover = tmp_path / "old.csv"
    leftover.write_text("x", encoding="utf-8")
    for status in (BatchStatus.PENDING, BatchStatus.PROCESSING, BatchStatus.COMPLETED):
        session.add(BatchJob(filename="a.csv", status=status))
    session.commit()
    assert batch_service.recover_interrupted_jobs(session, tmp_path) == 2
    session.expire_all()
    statuses = sorted(job.status.value for job in session.scalars(select(BatchJob)))
    assert statuses == ["COMPLETED", "FAILED", "FAILED"]
    assert not leftover.exists()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=SUM(A1)", "'=SUM(A1)"),
        ("+1", "'+1"),
        ("-1", "'-1"),
        ("@x", "'@x"),
        ("\tx", "'\tx"),
        ("plain", "plain"),
        (-1.5, -1.5),
        (None, None),
    ],
)
def test_safe_cell(value, expected):
    assert safe_cell(value) == expected


def test_csv_lines_neutralise_formulas_and_stream():
    lines = list(csv_lines(["a", "b"], [["=1+1", 2], ["x", -3]]))
    assert len(lines) == 3
    assert "'=1+1" in lines[1]
    assert lines[2].strip() == "x,-3"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("data.csv", "data.csv"),
        ("../../etc/passwd.csv", "passwd.csv"),
        ("..\\..\\evil name.csv", "evil_name.csv"),
        ("", "upload.csv"),
        (None, "upload.csv"),
    ],
)
def test_clean_filename(name, expected):
    assert clean_filename(name) == expected
