"""Validate the raw PaySim CSV and save the report. Exits 1 if validation fails."""

import argparse
import sys
from pathlib import Path

from app.ml.dataset_validation import PAYSIM_EXPECTED, validate_dataset
from app.ml.pipeline_io import RAW_CSV_PATH, VALIDATION_REPORT_PATH, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_CSV_PATH)
    parser.add_argument("--output", type=Path, default=VALIDATION_REPORT_PATH)
    args = parser.parse_args()

    report = validate_dataset(args.input, expected=PAYSIM_EXPECTED)
    write_json(args.output, report)

    print(f"Passed: {report['passed']}")
    if "row_count" in report:
        target = report["target"]
        print(f"Rows: {report['row_count']:,}")
        print(f"Fraud rows: {target['fraud_rows']:,} ({target['fraud_rate']:.4%})")
    for message in report["errors"]:
        print(f"ERROR: {message}")
    for message in report["warnings"]:
        print(f"WARNING: {message}")
    print(f"Report: {args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
