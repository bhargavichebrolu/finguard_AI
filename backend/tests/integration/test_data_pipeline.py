"""End-to-end pipeline tests on the synthetic fixture: partitioning, leakage audit and EDA."""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.ml import leakage_audit
from app.ml.dataset_preparation import load_partition, partition_path, prepare_dataset
from app.ml.eda import compute_eda, render_eda_figures
from app.ml.features import engineer_features, raw_to_prediction_inputs
from app.ml.leakage_audit import (
    LeakageError,
    assert_feature_schema_clean,
    assert_processed_files_clean,
    measure_training_signal,
    run_leakage_audit,
)
from app.ml.schema import FEATURE_COLUMNS, LEAKY_BALANCE_COLUMNS
from app.ml.splitting import PARTITIONS, SplitBoundaries


@pytest.fixture
def prepared(raw_csv, tmp_path, split_config):
    out_dir = tmp_path / "processed"
    metadata = prepare_dataset(raw_csv, out_dir, split_config, chunk_size=50)
    return out_dir, metadata, SplitBoundaries(**metadata["split_boundaries"])


def test_partitions_hold_every_row_with_labels_unchanged(prepared, raw_frame):
    out_dir, metadata, _ = prepared
    loaded = [load_partition(partition_path(out_dir, name)) for name in PARTITIONS]
    assert sum(len(part.labels) for part in loaded) == len(raw_frame)
    assert sum(int(part.labels.sum()) for part in loaded) == int(raw_frame["isFraud"].sum())
    source_rows = pd.concat([part.source_rows for part in loaded], ignore_index=True)
    assert source_rows.sort_values().tolist() == list(range(len(raw_frame)))
    for part in loaded:
        original = raw_frame["isFraud"].iloc[part.source_rows.to_numpy()].to_numpy()
        assert (part.labels.to_numpy() == original).all()
    assert sum(item["rows"] for item in metadata["partitions"].values()) == len(raw_frame)


def test_partitions_are_chronological_with_no_shared_step(prepared):
    out_dir, _, boundaries = prepared
    steps = {name: load_partition(partition_path(out_dir, name)).steps for name in PARTITIONS}
    assert steps["train"].max() == boundaries.train_end_step
    assert steps["validation"].min() == boundaries.train_end_step + 1
    assert steps["validation"].max() == boundaries.validation_end_step
    assert steps["test"].min() == boundaries.validation_end_step + 1


def test_processed_files_contain_no_excluded_columns(prepared):
    out_dir, _, _ = prepared
    for name in PARTITIONS:
        columns = set(pq.read_schema(partition_path(out_dir, name)).names)
        assert not columns & {*LEAKY_BALANCE_COLUMNS, "nameOrig", "nameDest", "isFraud"}


def test_loaded_features_exclude_label_and_tracking_columns(prepared):
    out_dir, _, _ = prepared
    part = load_partition(partition_path(out_dir, "train"))
    assert list(part.features.columns) == list(FEATURE_COLUMNS)


def test_stored_features_match_a_direct_serving_call(prepared, raw_frame):
    out_dir, _, _ = prepared
    part = load_partition(partition_path(out_dir, "validation"))
    original = raw_frame.iloc[part.source_rows.to_numpy()]
    direct = engineer_features(raw_to_prediction_inputs(original)).reset_index(drop=True)
    pd.testing.assert_frame_equal(part.features.reset_index(drop=True), direct)


def test_rerun_gives_identical_metadata(raw_csv, tmp_path, split_config):
    first = prepare_dataset(raw_csv, tmp_path / "a", split_config, chunk_size=50)
    second = prepare_dataset(raw_csv, tmp_path / "b", split_config, chunk_size=50)
    assert first == second


def test_content_hash_does_not_depend_on_chunk_size(raw_csv, tmp_path, split_config):
    first = prepare_dataset(raw_csv, tmp_path / "a", split_config, chunk_size=13)
    second = prepare_dataset(raw_csv, tmp_path / "b", split_config, chunk_size=500)
    for name in PARTITIONS:
        first_hash = first["partitions"][name]["content_sha256"]
        assert first_hash == second["partitions"][name]["content_sha256"]


def test_metadata_records_versions_and_source_hash(prepared):
    _, metadata, _ = prepared
    assert metadata["preprocessing_version"] == "test-split"
    assert metadata["feature_schema_version"]
    assert len(metadata["source_sha256"]) == 64
    assert metadata["feature_columns"] == list(FEATURE_COLUMNS)


def test_audit_passes_on_clean_output(prepared, raw_csv):
    out_dir, _, boundaries = prepared
    report = run_leakage_audit(raw_csv, out_dir, boundaries, chunk_size=50)
    assert report["schema_check"]["passed"] is True
    assert report["processed_file_check"]["passed"] is True


def test_audit_rejects_a_leaky_column_in_a_partition(prepared, raw_csv):
    out_dir, _, boundaries = prepared
    path = partition_path(out_dir, "train")
    table = pq.read_table(path)
    leaked = table.append_column("oldbalanceOrg", pa.array([0.0] * table.num_rows))
    pq.write_table(leaked, path)
    with pytest.raises(LeakageError, match="oldbalanceOrg"):
        assert_processed_files_clean(out_dir, boundaries)


def test_audit_rejects_partitions_that_overlap_in_time(prepared):
    out_dir, _, boundaries = prepared
    earlier = SplitBoundaries(
        first_step=boundaries.first_step,
        train_end_step=boundaries.train_end_step - 2,
        validation_end_step=boundaries.validation_end_step,
        last_step=boundaries.last_step,
    )
    with pytest.raises(LeakageError, match="overlap"):
        assert_processed_files_clean(out_dir, earlier)


def test_audit_rejects_a_forbidden_feature(monkeypatch):
    monkeypatch.setattr(leakage_audit, "FEATURE_COLUMNS", ("amount", "isFraud"))
    with pytest.raises(LeakageError, match="isFraud"):
        assert_feature_schema_clean()


def test_signal_audit_uses_training_rows_only(prepared, raw_csv, raw_frame):
    _, _, boundaries = prepared
    signal = measure_training_signal(raw_csv, boundaries, chunk_size=50)
    training = raw_frame[raw_frame["step"] <= boundaries.train_end_step]
    assert signal["training_rows"] == len(training)
    assert signal["training_fraud_rows"] == int(training["isFraud"].sum())
    assert set(signal["selected_features"]) == set(FEATURE_COLUMNS)


def test_eda_signal_sections_use_training_rows_only(prepared, raw_csv, raw_frame):
    _, _, boundaries = prepared
    summary = compute_eda(raw_csv, boundaries, chunk_size=50)
    training = raw_frame[raw_frame["step"] <= boundaries.train_end_step]
    section = summary["training_partition"]
    assert sum(section["rows_by_type"].values()) == len(training)
    assert sum(section["fraud_by_type"].values()) == int(training["isFraud"].sum())
    hours = section["rows_by_hour"]
    assert sum(hours["legitimate"]) + sum(hours["fraud"]) == len(training)


def test_eda_whole_dataset_counts_are_complete(prepared, raw_csv, raw_frame):
    _, _, boundaries = prepared
    whole = compute_eda(raw_csv, boundaries, chunk_size=50)["whole_dataset"]
    assert sum(whole["rows_per_step"]) == len(raw_frame)
    assert sum(item["rows"] for item in whole["partitions"].values()) == len(raw_frame)
    assert all(item["low_volume_steps"] == item["steps"] for item in whole["partitions"].values())


def test_eda_figures_are_written(prepared, raw_csv, tmp_path):
    _, _, boundaries = prepared
    summary = compute_eda(raw_csv, boundaries, chunk_size=50)
    figures = render_eda_figures(summary, tmp_path / "figures")
    assert len(figures) == 4
    assert all(path.stat().st_size > 0 for path in figures)
