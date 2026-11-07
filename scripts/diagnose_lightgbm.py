"""Test whether LightGBM's collapse in the matrix comes from its settings. Validation only.

This is a diagnostic run after selection, so it cannot change which model was chosen.
"""

import argparse
import json
from pathlib import Path

from app.ml.experiment_stages import (
    load_development_data,
    load_experiment_config,
    run_lightgbm_diagnostic,
)
from app.ml.pipeline_io import (
    EXPERIMENT_CONFIG_PATH,
    PHASE2_RESULTS_DIR,
    PROCESSED_DIR,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    selection = json.loads((args.results_dir / "selection.json").read_text(encoding="utf-8"))
    tuned = next(item for item in selection["candidates"] if item["family"] == "lightgbm")
    report = run_lightgbm_diagnostic(
        load_development_data(args.processed_dir, config), config, tuned["spec"]["hyperparameters"]
    )
    write_json(args.results_dir / "lightgbm_diagnostic.json", report)
    for cell in report["cells"]:
        print(cell)


if __name__ == "__main__":
    main()
