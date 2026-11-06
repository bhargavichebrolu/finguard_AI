"""Dataset validation tests. Each corrupts the clean fixture in one known way."""

from pathlib import Path

import pandas as pd
import pytest

from app.ml.dataset_validation import ExpectedProfile, validate_dataset


def write_csv(frame: pd.DataFrame, tmp_path: Path, name: str = "data.csv") -> Path:
    path = tmp_path / name
    frame.to_csv(path, index=False)
    return path


def test_clean_file_passes_and_reports_counts(raw_csv, raw_frame):
    report = validate_dataset(raw_csv)
    assert report["passed"] is True
    assert report["errors"] == []
    assert report["row_count"] == len(raw_frame)
    assert report["target"]["fraud_rows"] == int(raw_frame["isFraud"].sum())
    assert report["duplicate_rows"] == 0
    assert report["step"]["distinct"] == 30


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_dataset(tmp_path / "absent.csv")


def test_wrong_extension_fails(tmp_path, raw_frame):
    report = validate_dataset(write_csv(raw_frame, tmp_path, "data.txt"))
    assert report["passed"] is False
    assert "extension" in report["errors"][0]


def test_missing_column_fails(tmp_path, raw_frame):
    report = validate_dataset(write_csv(raw_frame.drop(columns=["amount"]), tmp_path))
    assert report["passed"] is False
    assert "Columns differ" in report["errors"][0]


def test_missing_value_is_counted(tmp_path, raw_frame):
    raw_frame = raw_frame.astype({"amount": "float64"})
    raw_frame.loc[3, "amount"] = None
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert report["passed"] is False
    assert report["null_counts"]["amount"] == 1


def test_non_numeric_amount_fails_cleanly(tmp_path, raw_frame):
    raw_frame = raw_frame.astype({"amount": "object"})
    raw_frame.loc[3, "amount"] = "not-a-number"
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert report["passed"] is False
    assert "type check failed" in report["errors"][0]


def test_negative_amount_fails(tmp_path, raw_frame):
    raw_frame.loc[0, "amount"] = -5.0
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert report["passed"] is False
    assert report["amount"]["negative_rows"] == 1


def test_zero_amount_warns_and_keeps_row(tmp_path, raw_frame):
    raw_frame.loc[4, "amount"] = 0.0  # Row 4 is labelled fraud in the fixture.
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert report["passed"] is True
    assert report["amount"]["zero_rows_labelled_fraud"] == 1
    assert report["row_count"] == len(raw_frame)
    assert any("amount 0" in warning for warning in report["warnings"])


def test_unknown_type_fails(tmp_path, raw_frame):
    raw_frame.loc[0, "type"] = "WIRE"
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert any("Unknown transaction types" in error for error in report["errors"])


def test_non_binary_target_fails(tmp_path, raw_frame):
    raw_frame.loc[0, "isFraud"] = 2
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert any("non-binary isFraud" in error for error in report["errors"])


def test_fractional_step_fails(tmp_path, raw_frame):
    raw_frame = raw_frame.astype({"step": "float64"})
    raw_frame.loc[0, "step"] = 1.5
    report = validate_dataset(write_csv(raw_frame, tmp_path))
    assert any("not whole numbers" in error for error in report["errors"])


def test_duplicates_warn_and_are_not_removed(tmp_path, raw_frame):
    doubled = pd.concat([raw_frame, raw_frame.iloc[[10, 20]]], ignore_index=True)
    report = validate_dataset(write_csv(doubled, tmp_path))
    assert report["duplicate_rows"] == 2
    assert report["row_count"] == len(doubled)


def test_duplicates_across_chunk_boundary_are_found(tmp_path, raw_frame):
    doubled = pd.concat([raw_frame, raw_frame.iloc[[0]]], ignore_index=True)
    report = validate_dataset(write_csv(doubled, tmp_path), chunk_size=50)
    assert report["duplicate_rows"] == 1


def test_unsorted_steps_warn(tmp_path, raw_frame):
    report = validate_dataset(write_csv(raw_frame.iloc[::-1], tmp_path))
    assert report["passed"] is True
    assert report["step"]["order_violations"] > 0


def test_expected_profile_mismatch_fails(raw_csv):
    expected = ExpectedProfile(
        min_rows=1_000_000,
        max_rows=2_000_000,
        fraud_count=8213,
        transaction_type_count=5,
        min_steps=700,
        max_steps=750,
    )
    report = validate_dataset(raw_csv, expected=expected)
    assert report["passed"] is False
    assert len(report["errors"]) == 3


def test_report_does_not_depend_on_chunk_size(raw_csv):
    small = validate_dataset(raw_csv, chunk_size=7)
    large = validate_dataset(raw_csv, chunk_size=10_000)
    assert small == large
