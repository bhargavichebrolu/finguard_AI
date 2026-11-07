"""Measure temporal drift before any model is fitted. Reads published counts, train and validation.

Feature values from the later partition are not opened here: they are compared in the final
evaluation, after the freeze.
"""

import argparse
import json
from pathlib import Path

from app.ml.drift import build_prevalence_report, feature_drift
from app.ml.experiment_stages import load_development_data, load_experiment_config
from app.ml.pipeline_io import (
    EDA_SUMMARY_PATH,
    EXPERIMENT_CONFIG_PATH,
    PHASE2_RESULTS_DIR,
    PREPROCESSING_METADATA_PATH,
    PROCESSED_DIR,
    write_json,
)
from app.ml.splitting import SplitBoundaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--eda-summary", type=Path, default=EDA_SUMMARY_PATH)
    parser.add_argument("--metadata", type=Path, default=PREPROCESSING_METADATA_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--output", type=Path, default=PHASE2_RESULTS_DIR / "temporal_drift.json")
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    eda_summary = json.loads(args.eda_summary.read_text(encoding="utf-8"))
    regimes = config["regimes"]
    report = build_prevalence_report(
        eda_summary,
        SplitBoundaries(**metadata["split_boundaries"]),
        regimes["sparse_step_max_rows"],
        regimes["sensitivity_cutoffs"],
    )

    data = load_development_data(args.processed_dir, config)
    report["feature_drift_train_to_validation"] = feature_drift(
        data.train.features,
        data.train.labels.to_numpy(),
        data.validation.features,
        data.validation.labels.to_numpy(),
    )
    write_json(args.output, report)

    for name, summary in report["partitions"].items():
        print(
            f"{name:<11} prevalence {summary['prevalence']:.4%}  "
            f"fraud/step {summary['fraud_per_step']:.1f}  "
            f"legitimate/step {summary['legitimate_per_step']:.0f}"
        )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
