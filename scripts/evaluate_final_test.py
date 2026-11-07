"""Evaluate the frozen model on the test partition, once.

Refuses to start unless the model metadata and selection results are committed and unchanged,
which leaves a Git record that they were fixed before the test data was opened.
"""

import argparse
import sys
from pathlib import Path

from app.ml.experiment_stages import load_experiment_config
from app.ml.final_evaluation import evaluate_frozen_model
from app.ml.model_artifacts import load_model_artifact
from app.ml.pipeline_io import (
    EXPERIMENT_CONFIG_PATH,
    MODEL_METADATA_PATH,
    MODELS_DIR,
    PHASE2_RESULTS_DIR,
    PROCESSED_DIR,
    current_commit,
    uncommitted_paths,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    parser.add_argument("--metadata", type=Path, default=MODEL_METADATA_PATH)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    args = parser.parse_args()

    freeze_files = [
        args.metadata,
        args.results_dir / "selection.json",
        args.results_dir / "threshold_analysis.json",
        args.config,
    ]
    problems = uncommitted_paths(freeze_files)
    if problems:
        print("Refusing to open the test partition. Commit these freeze files first:")
        for problem in problems:
            print(f"  {problem}")
        return 1

    config = load_experiment_config(args.config)
    model = load_model_artifact(args.metadata, args.models_dir)
    report = evaluate_frozen_model(
        model,
        args.processed_dir,
        args.results_dir / "test_evaluation.json",
        config,
        current_commit(),
    )

    overall = report["overall"]
    ranking = overall["ranking"]
    print(f"Model {report['model_version']} ({report['family']})")
    print(f"Frozen threshold {report['frozen_threshold']}")
    print(f"Test PR-AUC {ranking['pr_auc']:.4f}, ROC-AUC {ranking['roc_auc']:.4f}")
    at_threshold = overall["at_frozen_threshold"]
    print(
        f"Recall {at_threshold['recall']:.4f}, precision {at_threshold['precision']:.4f}, "
        f"false positive rate {at_threshold['false_positive_rate']:.5f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
