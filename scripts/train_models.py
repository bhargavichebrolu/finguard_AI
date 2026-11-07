"""Run the experiment plan on train and validation. Safe to rerun: finished runs are skipped."""

import argparse
from pathlib import Path

from app.ml.experiment_stages import (
    load_development_data,
    load_experiment_config,
    run_baselines,
    run_matrix,
    run_sensitivity,
    run_stability,
    run_tuning,
)
from app.ml.experiments import RunStore
from app.ml.pipeline_io import EXPERIMENT_CONFIG_PATH, PHASE2_RESULTS_DIR, PROCESSED_DIR, SCORES_DIR

STAGES = ("baselines", "matrix", "tuning", "sensitivity", "stability")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=[*STAGES, "all"], default="all")
    parser.add_argument("--config", type=Path, default=EXPERIMENT_CONFIG_PATH)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    parser.add_argument("--scores-dir", type=Path, default=SCORES_DIR)
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    data = load_development_data(args.processed_dir, config)
    store = RunStore(args.results_dir / "runs.json", args.scores_dir)
    selected = STAGES if args.stage == "all" else (args.stage,)

    if "baselines" in selected:
        run_baselines(data, config, args.results_dir / "baselines.json")
    if "matrix" in selected:
        run_matrix(data, config, store)
    if "tuning" in selected:
        run_tuning(data, config, store)
    if "sensitivity" in selected:
        run_sensitivity(data, config, store)
    if "stability" in selected:
        run_stability(data, config, store, args.results_dir / "rolling_folds.json")

    failed = [run_id for run_id, run in store.runs.items() if run["status"] != "ok"]
    print(f"Runs recorded: {len(store.runs)}. Failed: {len(failed)}.")
    for run_id in failed:
        print(f"  {run_id}: {store.runs[run_id]['error']}")


if __name__ == "__main__":
    main()
