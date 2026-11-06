"""Run the leakage audit and save the report. Exits 1 if a hard leakage rule is broken."""

import argparse
import json
import sys
from pathlib import Path

from app.ml.leakage_audit import LeakageError, run_leakage_audit
from app.ml.pipeline_io import (
    LEAKAGE_REPORT_PATH,
    PREPROCESSING_METADATA_PATH,
    PROCESSED_DIR,
    RAW_CSV_PATH,
    write_json,
)
from app.ml.splitting import SplitBoundaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_CSV_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--metadata", type=Path, default=PREPROCESSING_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=LEAKAGE_REPORT_PATH)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    boundaries = SplitBoundaries(**metadata["split_boundaries"])
    try:
        report = run_leakage_audit(args.input, args.processed_dir, boundaries)
    except LeakageError as exc:
        print(f"LEAKAGE AUDIT FAILED: {exc}")
        return 1

    write_json(args.output, report)
    print("Leakage audit passed: schema and processed-file checks hold.")
    signal = report["training_signal"]
    for group in ("excluded_balance_columns", "selected_features"):
        print(group)
        ranked = sorted(signal[group].items(), key=lambda item: -item[1]["separation"])
        for name, values in ranked:
            print(f"  {name:<36} separation {values['separation']:.3f}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
