"""Select the model and threshold on validation, then freeze them. Does not read test data."""

import argparse
from pathlib import Path

from app.ml.experiment_stages import load_development_data, load_experiment_config
from app.ml.experiments import RunStore
from app.ml.pipeline_io import (
    EXPERIMENT_CONFIG_PATH,
    MODEL_METADATA_PATH,
    MODELS_DIR,
    PHASE2_RESULTS_DIR,
    PREPROCESSING_METADATA_PATH,
    PROCESSED_DIR,
    SCORES_DIR,
    current_commit,
)
from app.ml.selection import freeze_selected_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    parser.add_argument("--scores-dir", type=Path, default=SCORES_DIR)
    parser.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    parser.add_argument("--metadata", type=Path, default=MODEL_METADATA_PATH)
    parser.add_argument("--preprocessing", type=Path, default=PREPROCESSING_METADATA_PATH)
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    data = load_development_data(args.processed_dir, config)
    store = RunStore(args.results_dir / "runs.json", args.scores_dir)
    report = freeze_selected_model(
        data,
        config,
        store,
        args.results_dir,
        args.models_dir,
        args.metadata,
        args.preprocessing,
        current_commit(),
    )

    decision = report["decision"]
    print(f"Gates passed: {report['gates']['passed']}")
    for rejected in report["gates"]["rejected"]:
        print(f"Rejected {rejected['family']}: {'; '.join(rejected['reasons'])}")
    print(f"Top by PR-AUC: {decision['top_by_pr_auc']}")
    print(f"Indistinguishable: {decision['statistically_indistinguishable']}")
    print(f"Tied on recall: {decision['tied_on_recall']}")
    print(f"Selected: {decision['selected_family']}")
    print(f"Threshold: {report['selected_threshold']}")
    print(f"Refit reproduces the recorded run: {report['refit_matches_recorded_run']}")


if __name__ == "__main__":
    main()
