"""Streaming validation of a raw PaySim CSV.

The validator only observes and reports. It never removes rows or edits labels, which is
what PRD section 4.5 requires: any finding is a visible error or warning in the report.
"""

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.ml.pipeline_io import DEFAULT_CHUNK_SIZE, sha256_file
from app.ml.schema import (
    LEAKY_BALANCE_COLUMNS,
    RAW_COLUMNS,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
    TRANSACTION_TYPES,
)

# Integer columns are read as float64 so a missing value can be counted rather than making
# the parser fail. float64 represents every value in these columns exactly.
_VALIDATION_DTYPES: dict[str, str] = {
    "step": "float64",
    "type": "object",
    "amount": "float64",
    "nameOrig": "object",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "object",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    TARGET_COLUMN: "float64",
    RULE_FLAG_COLUMN: "float64",
}


@dataclass(frozen=True)
class ExpectedProfile:
    """Published dataset characteristics that a download must match."""

    min_rows: int
    max_rows: int
    fraud_count: int
    transaction_type_count: int
    min_steps: int
    max_steps: int


# From PRD section 4.1: about 6.36M rows, 8,213 frauds, 5 types, about 30 days of hourly steps.
PAYSIM_EXPECTED = ExpectedProfile(
    min_rows=6_300_000,
    max_rows=6_400_000,
    fraud_count=8_213,
    transaction_type_count=5,
    min_steps=700,
    max_steps=750,
)


class _ValidationTally:
    """Running totals built one chunk at a time so the full file is never held in memory."""

    def __init__(self) -> None:
        self.rows = 0
        self.null_counts: Counter[str] = Counter()
        self.non_integer_steps = 0
        self.step_order_violations = 0
        self.last_step = -np.inf
        self.seen_steps: set[int] = set()
        self.type_counts: Counter[str] = Counter()
        self.fraud_by_type: Counter[str] = Counter()
        self.destination_prefix_by_type: Counter[str] = Counter()
        self.origin_prefix_counts: Counter[str] = Counter()
        self.negative_amounts = 0
        self.zero_amounts = 0
        self.zero_amount_frauds = 0
        self.max_amount = -np.inf
        self.negative_balances: Counter[str] = Counter()
        self.non_binary_target = 0
        self.non_binary_flag = 0
        self.fraud_count = 0
        self.flagged_count = 0
        self.flagged_and_fraud = 0
        self.row_hashes: list[np.ndarray] = []

    def update(self, chunk: pd.DataFrame) -> None:
        """Add one chunk to the running totals."""
        self.rows += len(chunk)
        self.null_counts.update(chunk.isna().sum().to_dict())
        self._update_steps(chunk["step"])
        self._update_amounts(chunk)

        for column in LEAKY_BALANCE_COLUMNS:
            self.negative_balances[column] += int((chunk[column] < 0).sum())

        is_fraud = chunk[TARGET_COLUMN] == 1
        is_flagged = chunk[RULE_FLAG_COLUMN] == 1
        self.non_binary_target += int((~chunk[TARGET_COLUMN].isin([0, 1])).sum())
        self.non_binary_flag += int((~chunk[RULE_FLAG_COLUMN].isin([0, 1])).sum())
        self.fraud_count += int(is_fraud.sum())
        self.flagged_count += int(is_flagged.sum())
        self.flagged_and_fraud += int((is_fraud & is_flagged).sum())

        self.type_counts.update(chunk["type"].value_counts().to_dict())
        self.fraud_by_type.update(chunk.loc[is_fraud, "type"].value_counts().to_dict())
        prefixes = chunk["nameDest"].astype("string").str[0]
        pairs = chunk["type"].astype("string") + "/" + prefixes
        self.destination_prefix_by_type.update(pairs.value_counts().to_dict())
        self.origin_prefix_counts.update(
            chunk["nameOrig"].astype("string").str[0].value_counts().to_dict()
        )
        self.row_hashes.append(pd.util.hash_pandas_object(chunk, index=False).to_numpy())

    def _update_steps(self, steps: pd.Series) -> None:
        present = steps.dropna()
        if present.empty:
            return
        self.non_integer_steps += int((present != present.round()).sum())
        self.step_order_violations += int((present.diff() < 0).sum())
        if present.iloc[0] < self.last_step:
            self.step_order_violations += 1
        self.last_step = float(present.iloc[-1])
        self.seen_steps.update(int(step) for step in present.unique())

    def _update_amounts(self, chunk: pd.DataFrame) -> None:
        amount = chunk["amount"]
        is_zero = amount == 0
        self.negative_amounts += int((amount < 0).sum())
        self.zero_amounts += int(is_zero.sum())
        self.zero_amount_frauds += int((is_zero & (chunk[TARGET_COLUMN] == 1)).sum())
        if amount.notna().any():
            self.max_amount = max(self.max_amount, float(amount.max()))

    def duplicate_rows(self) -> int:
        """Count rows whose 64-bit content hash repeats an earlier row."""
        if not self.row_hashes:
            return 0
        hashes = np.concatenate(self.row_hashes)
        return int(hashes.size - np.unique(hashes).size)


def _collect_findings(
    tally: _ValidationTally, expected: ExpectedProfile | None
) -> tuple[list[str], list[str], int]:
    """Turn the tally into (errors, warnings, duplicate count)."""
    errors: list[str] = []
    warnings: list[str] = []

    nulls = {column: count for column, count in tally.null_counts.items() if count}
    if nulls:
        errors.append(f"Missing values found: {dict(sorted(nulls.items()))}")
    if tally.non_integer_steps:
        errors.append(f"{tally.non_integer_steps} step values are not whole numbers")
    unknown_types = sorted(set(tally.type_counts) - set(TRANSACTION_TYPES))
    if unknown_types:
        errors.append(f"Unknown transaction types: {unknown_types}")
    if tally.negative_amounts:
        errors.append(f"{tally.negative_amounts} rows have a negative amount")
    if tally.non_binary_target:
        errors.append(f"{tally.non_binary_target} rows have a non-binary {TARGET_COLUMN}")
    if tally.non_binary_flag:
        errors.append(f"{tally.non_binary_flag} rows have a non-binary {RULE_FLAG_COLUMN}")

    negative_balances = sum(tally.negative_balances.values())
    if negative_balances:
        warnings.append(f"{negative_balances} negative balance values (excluded from features)")
    if tally.zero_amounts:
        warnings.append(
            f"{tally.zero_amounts} rows have amount 0, of which {tally.zero_amount_frauds} are "
            "labelled fraud. They are retained, not discarded."
        )
    if tally.step_order_violations:
        warnings.append(
            f"File is not sorted by step ({tally.step_order_violations} order violations). "
            "Splitting uses the step value, so partitions are unaffected."
        )
    duplicates = tally.duplicate_rows()
    if duplicates:
        warnings.append(f"{duplicates} duplicate rows detected. They are retained, not discarded.")

    if expected is not None:
        errors.extend(_compare_to_expected(tally, expected))
    return errors, warnings, duplicates


def _compare_to_expected(tally: _ValidationTally, expected: ExpectedProfile) -> list[str]:
    errors: list[str] = []
    if not expected.min_rows <= tally.rows <= expected.max_rows:
        errors.append(f"Row count {tally.rows} is outside {expected.min_rows}-{expected.max_rows}")
    if tally.fraud_count != expected.fraud_count:
        errors.append(f"Fraud count {tally.fraud_count} differs from {expected.fraud_count}")
    if len(tally.type_counts) != expected.transaction_type_count:
        errors.append(
            f"Found {len(tally.type_counts)} transaction types, "
            f"expected {expected.transaction_type_count}"
        )
    if not expected.min_steps <= len(tally.seen_steps) <= expected.max_steps:
        errors.append(
            f"Distinct step count {len(tally.seen_steps)} is outside "
            f"{expected.min_steps}-{expected.max_steps}"
        )
    return errors


def validate_dataset(
    path: Path,
    expected: ExpectedProfile | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    """Validate a raw CSV and return a JSON-ready report.

    Data problems are reported in the "errors" list with "passed" set to False. Only a
    missing file raises, because no report can describe a file that is not there.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    report: dict[str, Any] = {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "expected_profile": asdict(expected) if expected else None,
    }

    if path.suffix.lower() != ".csv":
        return {**report, "passed": False, "errors": ["File extension is not .csv"], "warnings": []}

    header = pd.read_csv(path, nrows=0).columns.tolist()
    report["columns"] = header
    if header != list(RAW_COLUMNS):
        message = f"Columns differ from the PaySim schema. Expected {list(RAW_COLUMNS)}"
        return {**report, "passed": False, "errors": [message], "warnings": []}

    tally = _ValidationTally()
    try:
        for chunk in pd.read_csv(path, dtype=_VALIDATION_DTYPES, chunksize=chunk_size):
            tally.update(chunk)
    except ValueError as exc:
        message = f"Column type check failed after {tally.rows} rows: {exc}"
        return {**report, "passed": False, "errors": [message], "warnings": []}

    errors, warnings, duplicates = _collect_findings(tally, expected)
    report.update(
        {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings,
            "row_count": tally.rows,
            "null_counts": {column: tally.null_counts[column] for column in RAW_COLUMNS},
            "duplicate_rows": duplicates,
            "step": {
                "min": min(tally.seen_steps, default=None),
                "max": max(tally.seen_steps, default=None),
                "distinct": len(tally.seen_steps),
                "order_violations": tally.step_order_violations,
            },
            "transaction_type_counts": dict(sorted(tally.type_counts.items())),
            "fraud_by_transaction_type": {
                name: tally.fraud_by_type[name] for name in sorted(tally.type_counts)
            },
            "destination_prefix_by_type": dict(sorted(tally.destination_prefix_by_type.items())),
            "origin_prefix_counts": dict(sorted(tally.origin_prefix_counts.items())),
            "amount": {
                "negative_rows": tally.negative_amounts,
                "zero_rows": tally.zero_amounts,
                "zero_rows_labelled_fraud": tally.zero_amount_frauds,
                "max": tally.max_amount if tally.rows else None,
            },
            "negative_balance_values": dict(sorted(tally.negative_balances.items())),
            "target": {
                "fraud_rows": tally.fraud_count,
                "legitimate_rows": tally.rows - tally.fraud_count,
                "fraud_rate": tally.fraud_count / tally.rows if tally.rows else None,
            },
            "rule_flag": {
                "flagged_rows": tally.flagged_count,
                "flagged_and_fraud": tally.flagged_and_fraud,
            },
        }
    )
    return report
