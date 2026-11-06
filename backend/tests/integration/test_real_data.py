"""Checks on the real pipeline outputs. Skipped when the dataset and outputs are not present."""

import json

import pyarrow.parquet as pq
import pytest

from app.ml.dataset_preparation import partition_path
from app.ml.pipeline_io import (
    LEAKAGE_REPORT_PATH,
    PREPROCESSING_METADATA_PATH,
    PROCESSED_DIR,
    RAW_CSV_PATH,
    VALIDATION_REPORT_PATH,
)
from app.ml.schema import FEATURE_COLUMNS, LEAKY_BALANCE_COLUMNS
from app.ml.splitting import PARTITIONS

_PROCESSED_FILES = [partition_path(PROCESSED_DIR, name) for name in PARTITIONS]
pytestmark = [
    pytest.mark.real_data,
    pytest.mark.skipif(
        not (RAW_CSV_PATH.exists() and all(path.exists() for path in _PROCESSED_FILES)),
        reason="Full dataset and processed partitions are not present",
    ),
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_validation_report_matches_published_profile():
    report = read_json(VALIDATION_REPORT_PATH)
    assert report["passed"] is True
    assert report["row_count"] == 6_362_620
    assert report["target"]["fraud_rows"] == 8_213
    assert report["duplicate_rows"] == 0
    assert sum(report["null_counts"].values()) == 0
    assert len(report["transaction_type_counts"]) == 5


def test_partitions_account_for_every_row_and_fraud():
    metadata = read_json(PREPROCESSING_METADATA_PATH)
    partitions = metadata["partitions"]
    assert sum(item["rows"] for item in partitions.values()) == 6_362_620
    assert sum(item["fraud_rows"] for item in partitions.values()) == 8_213
    for name in PARTITIONS:
        rows_on_disk = pq.read_metadata(partition_path(PROCESSED_DIR, name)).num_rows
        assert rows_on_disk == partitions[name]["rows"]


def test_partition_steps_follow_boundaries():
    metadata = read_json(PREPROCESSING_METADATA_PATH)
    boundaries = metadata["split_boundaries"]
    partitions = metadata["partitions"]
    assert partitions["train"]["last_step"] == boundaries["train_end_step"]
    assert partitions["validation"]["first_step"] == boundaries["train_end_step"] + 1
    assert partitions["validation"]["last_step"] == boundaries["validation_end_step"]
    assert partitions["test"]["first_step"] == boundaries["validation_end_step"] + 1


def test_real_partitions_have_only_expected_columns():
    for path in _PROCESSED_FILES:
        columns = set(pq.read_schema(path).names)
        assert set(FEATURE_COLUMNS) <= columns
        assert not columns & {*LEAKY_BALANCE_COLUMNS, "nameOrig", "nameDest", "isFraud"}


def test_metadata_and_validation_describe_the_same_file():
    metadata = read_json(PREPROCESSING_METADATA_PATH)
    report = read_json(VALIDATION_REPORT_PATH)
    assert metadata["source_sha256"] == report["sha256"]


def test_leakage_report_recorded_a_pass():
    report = read_json(LEAKAGE_REPORT_PATH)
    assert report["schema_check"]["passed"] is True
    assert report["processed_file_check"]["passed"] is True
    assert report["training_signal"]["scope"] == "training partition only"
