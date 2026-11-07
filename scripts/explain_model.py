"""Explain the frozen model with SHAP, on validation rows. Does not read test data."""

import argparse
from pathlib import Path

import numpy as np

from app.ml.experiment_stages import load_development_data, load_experiment_config
from app.ml.experiments import score_rows
from app.ml.explainability import explain_validation_rows
from app.ml.model_artifacts import load_model_artifact
from app.ml.pipeline_io import (
    EXPERIMENT_CONFIG_PATH,
    MODEL_METADATA_PATH,
    MODELS_DIR,
    PHASE2_RESULTS_DIR,
    PROCESSED_DIR,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    parser.add_argument("--metadata", type=Path, default=MODEL_METADATA_PATH)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    model = load_model_artifact(args.metadata, args.models_dir)
    data = load_development_data(args.processed_dir, config)
    features = data.validation.features
    labels = data.validation.labels.to_numpy()
    scores = score_rows(model.pipeline, features)

    result = explain_validation_rows(
        model.pipeline,
        model.metadata["family"],
        features,
        labels,
        scores,
        data.validation_slices,
        model.threshold,
        config["shap"]["legitimate_sample_rows"],
        config["shap"]["seed"],
    )
    write_json(args.results_dir / "shap_summary.json", result["report"])
    np.savez_compressed(
        args.results_dir / "shap_sample.npz",
        values=result["values"].astype("float32"),
        feature_names=np.array(result["feature_names"]),
        amount=result["sample"]["amount"].to_numpy(),
        hour_of_day=result["sample"]["hour_of_day"].to_numpy(),
        labels=result["sample_labels"],
    )

    report = result["report"]
    print(f"Explained {report['rows_explained']} rows; scale {report['output_scale']}.")
    print(f"Largest additivity error: {report['additivity_max_error']:.2e}")
    groups = report["summary"]["all_rows"]["mean_absolute_by_group"]
    for name, value in sorted(groups.items(), key=lambda item: -item[1]):
        print(f"  {name:<36} {value:.4f}")


if __name__ == "__main__":
    main()
