"""Build the read-only model performance report from saved Phase 2 outputs.

Reads only the result files in SOURCES. It opens nothing under data/, imports no partition loader,
trains nothing and changes no existing file. Every value is copied from a source, and the report
records each source's SHA-256 so it can be traced and checked.

    uv run --project backend python scripts/export_model_report.py           # write the report
    uv run --project backend python scripts/export_model_report.py --check   # verify it is current
"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from app.ml.pipeline_io import write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "artifacts" / "metadata" / "model_v1_report.json"
REPORT_VERSION = "model_v1_report.1"
PHASE2 = "experiments/results/phase2"
SOURCES = {
    "selection": f"{PHASE2}/selection.json",
    "runs": f"{PHASE2}/all_runs.csv",
    "thresholds": f"{PHASE2}/threshold_analysis.json",
    "test_evaluation": f"{PHASE2}/test_evaluation.json",
    "lightgbm_diagnostic": f"{PHASE2}/lightgbm_diagnostic.json",
    "metrics": "artifacts/metadata/model_v1_metrics.json",
}
_HISTORY_FIELDS = (
    "run_id",
    "stage",
    "status",
    "family",
    "strategy",
    "seed",
    "target_ratio",
    "dropped_features",
    "pr_auc",
    "roc_auc",
    "fpr_cap_precision",
    "fpr_cap_recall",
    "fpr_cap_false_positive_rate",
    "total_training_seconds",
    "batch_microseconds_per_row",
    "single_row_ms_median",
)
_TEXT_FIELDS = {"run_id", "stage", "status", "family", "strategy", "dropped_features"}


def read_sources(root: Path) -> dict[str, Any]:
    """Load every source file. Fails if one is missing, rather than building a partial report."""
    loaded: dict[str, Any] = {}
    for name, relative in SOURCES.items():
        path = root / relative
        if relative.endswith(".csv"):
            with path.open(encoding="utf-8", newline="") as handle:
                loaded[name] = list(csv.DictReader(handle))
        else:
            loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def content_sha256(path: Path) -> str:
    """SHA-256 of a text file's content with line endings normalised to LF.

    Git stores these files with LF, but a Windows checkout can write CRLF. Hashing raw bytes made
    the recorded hashes depend on how the repository was checked out (found by the Phase 5
    clean-clone check), so the content is hashed instead.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def source_hashes(root: Path) -> dict[str, str]:
    """Return the content hash of each source, keyed by its repository path."""
    return {relative: content_sha256(root / relative) for relative in SOURCES.values()}


def csv_value(field: str, text: str) -> Any:
    """Convert one CSV cell back to the number it was written from, or keep it as text."""
    if field in _TEXT_FIELDS:
        return text
    if text == "":
        return None
    number = float(text)
    return int(number) if field == "seed" else number


def without_slices(values: dict[str, Any]) -> dict[str, Any]:
    """Drop per-slice breakdowns, which the interface does not show, keeping everything else."""
    return {key: value for key, value in values.items() if key != "slices"}


def family_comparison(selection: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per model family: its best run on validation, as selection recorded it."""
    intervals = selection["pr_auc_intervals"]
    paired = selection["paired_difference_from_top"]
    rows = []
    for candidate in selection["candidates"]:
        family = candidate["family"]
        rows.append(
            {
                "family": family,
                "run_id": candidate["run_id"],
                "stage": candidate["stage"],
                "strategy": candidate["spec"]["strategy"],
                "pr_auc": candidate["pr_auc"],
                "pr_auc_mean_over_seeds": candidate["pr_auc_mean"],
                "pr_auc_seed_cv": candidate["pr_auc_seed_cv"],
                "pr_auc_interval": intervals[family],
                "difference_from_top": paired.get(family),
                "roc_auc": candidate["roc_auc"],
                "at_fpr_cap": without_slices(candidate["at_fpr_cap"]),
                "training_seconds": candidate["training_seconds"],
                "batch_microseconds_per_row": candidate["batch_microseconds_per_row"],
                "single_row_ms": candidate["single_row_ms"],
            }
        )
    return rows


def experiment_history(runs: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Every recorded run, in file order, with the fields the history table shows."""
    return [{field: csv_value(field, run[field]) for field in _HISTORY_FIELDS} for run in runs]


def imbalance_matrix(runs: list[dict[str, str]]) -> list[dict[str, Any]]:
    """The family by strategy matrix, from the runs recorded at the matrix stage."""
    return [
        {
            "family": run["family"],
            "strategy": run["strategy"],
            "pr_auc": csv_value("pr_auc", run["pr_auc"]),
            "fpr_cap_recall": csv_value("fpr_cap_recall", run["fpr_cap_recall"]),
        }
        for run in runs
        if run["stage"] == "matrix"
    ]


def threshold_section(thresholds: dict[str, Any]) -> dict[str, Any]:
    """The validation threshold analysis behind the frozen threshold."""
    return {
        "selected_threshold": thresholds["selected_threshold"],
        "objective": thresholds["objective"],
        "selected": without_slices(thresholds["selected"]),
        "sweep": [without_slices(row) for row in thresholds["sweep"]],
        "prd_candidates": {
            key: without_slices(value) for key, value in thresholds["prd_candidates"].items()
        },
        "rule_alternatives": {
            key: without_slices(value) for key, value in thresholds["rule_alternatives"].items()
        },
        "out_of_bag": thresholds["out_of_bag"],
    }


def confusion_section(metrics: dict[str, Any]) -> dict[str, Any]:
    """Confusion matrices at the frozen threshold, overall and for both kinds of step."""

    def counts(values: dict[str, Any]) -> dict[str, int]:
        return {
            key: values[key]
            for key in ("true_positives", "false_positives", "false_negatives", "true_negatives")
        }

    test = metrics["test"]
    return {
        "validation": counts(metrics["validation"]["at_threshold"]),
        "test": counts(test["at_frozen_threshold"]),
        "test_by_step_type": {
            name: counts(values["at_frozen_threshold"]) for name, values in test["regimes"].items()
        },
    }


def notes(selection: dict[str, Any]) -> list[str]:
    """Statements the interface must show, built from recorded decisions, not typed figures."""
    decision = selection["decision"]
    tied = ", ".join(decision["statistically_indistinguishable"])
    return [
        f"{tied} were statistically indistinguishable on validation PR-AUC. "
        f"{decision['top_by_pr_auc']} ranked first, and the pre-registered rule selected "
        f"{decision['selected_family']}. This does not show that {decision['selected_family']} "
        "is better.",
        "Validation results guided every choice. Test results come from a single evaluation, "
        "made after the model and threshold were frozen, and nothing was tuned on them.",
        "Test had a much higher fraud rate than validation, which raises precision and PR-AUC "
        "without the model improving.",
        "LightGBM's results with the original distribution and with class weighting reflect a "
        "numerical divergence during fitting, not those strategies. See the LightGBM diagnostic.",
        "All results come from the synthetic PaySim simulator.",
    ]


def build_report(root: Path) -> dict[str, Any]:
    """Assemble the whole report from the saved sources."""
    sources = read_sources(root)
    selection, metrics, test_evaluation = (
        sources["selection"],
        sources["metrics"],
        sources["test_evaluation"],
    )
    return {
        "report_version": REPORT_VERSION,
        "model_version": metrics["model_version"],
        "threshold": metrics["threshold"]["value"],
        "source_files": source_hashes(root),
        "notes": notes(selection),
        "selection": {
            key: selection[key]
            for key in ("decision", "gates", "rule_source", "type_rate_baseline_pr_auc")
        },
        "families": family_comparison(selection),
        "family_validation_curves": selection["candidate_curves"],
        "selected_model_curves": {
            "validation": test_evaluation["validation_curves"],
            "test": test_evaluation["curves"],
        },
        "confusion_matrices": confusion_section(metrics),
        "thresholds": threshold_section(sources["thresholds"]),
        "imbalance_matrix": imbalance_matrix(sources["runs"]),
        "experiment_history": experiment_history(sources["runs"]),
        "lightgbm_diagnostic": sources["lightgbm_diagnostic"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the saved report is stale")
    arguments = parser.parse_args()

    report = build_report(REPO_ROOT)
    if arguments.check:
        current = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if current != report:
            print(f"{REPORT_PATH.name} differs from its sources. Rebuild it.")
            return 1
        print(f"{REPORT_PATH.name} matches its sources.")
        return 0
    write_json(REPORT_PATH, report)
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)} ({REPORT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
