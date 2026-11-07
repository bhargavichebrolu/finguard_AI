"""Build charts, tables and the metrics bundle from saved results. Fits and scores nothing.

Run it after any stage: sections whose results do not exist yet are skipped and named.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from app.ml.pipeline_io import (
    MODEL_FIGURES_DIR,
    MODEL_METADATA_PATH,
    MODEL_METRICS_PATH,
    PHASE2_RESULTS_DIR,
    REPO_ROOT,
    write_json,
)
from app.ml.reporting import (
    inject_generated_results,
    plot_compute_cost,
    plot_confusion_matrix,
    plot_family_curves,
    plot_imbalance_matrix,
    plot_regime_comparison,
    plot_shap_dependence,
    plot_shap_summary,
    plot_sparse_by_hour,
    plot_temporal_drift,
    plot_test_results,
    plot_threshold_behaviour,
    render_comparison_table,
    render_drift_tables,
    render_lightgbm_diagnostic,
    render_matrix_tables,
    render_results_markdown,
    render_search_tables,
    render_shap_tables,
    render_stability_table,
    render_test_tables,
    render_threshold_tables,
    write_runs_csv,
)


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def build_metrics_bundle(
    metadata: dict[str, Any],
    thresholds: dict[str, Any],
    shap_report: dict[str, Any] | None,
    test: dict[str, Any] | None,
) -> dict[str, Any]:
    """Collect what the Phase 3 API will serve about the model, keeping partitions apart."""
    bundle: dict[str, Any] = {
        "model_version": metadata["model_version"],
        "family": metadata["family"],
        "strategy": metadata["spec"]["strategy"],
        "feature_schema_version": metadata["feature_schema_version"],
        "threshold": metadata["threshold"],
        "score_semantics": metadata["score_semantics"],
        "validation": {
            "ranking": thresholds["ranking"],
            "at_threshold": {
                key: value for key, value in thresholds["selected"].items() if key != "slices"
            },
        },
        "test": None,
        "global_feature_importance": None,
        "explanation_limitations": None,
    }
    if shap_report is not None:
        summary = shap_report["summary"]["all_rows"]
        bundle["global_feature_importance"] = {
            "output_scale": shap_report["output_scale"],
            "by_group": summary["mean_absolute_by_group"],
            "by_feature": summary["mean_absolute_by_feature"],
        }
        bundle["explanation_limitations"] = shap_report["limitations"]
    if test is not None:
        bundle["test"] = {
            "ranking": test["overall"]["ranking"],
            "at_frozen_threshold": test["overall"]["at_frozen_threshold"],
            "regimes": {
                name: {
                    "ranking": item["ranking"],
                    "at_frozen_threshold": item["at_frozen_threshold"],
                }
                for name, item in test["regimes"].items()
            },
        }
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=PHASE2_RESULTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=MODEL_FIGURES_DIR)
    parser.add_argument("--metadata", type=Path, default=MODEL_METADATA_PATH)
    parser.add_argument("--metrics", type=Path, default=MODEL_METRICS_PATH)
    parser.add_argument("--document", type=Path, default=REPO_ROOT / "ML_EXPERIMENTS.md")
    args = parser.parse_args()

    results, figures = args.results_dir, args.figures_dir
    drift = _load(results / "temporal_drift.json")
    baselines = _load(results / "baselines.json")
    runs = _load(results / "runs.json")
    selection = _load(results / "selection.json")
    thresholds = _load(results / "threshold_analysis.json")
    shap_report = _load(results / "shap_summary.json")
    test = _load(results / "test_evaluation.json")
    metadata = _load(args.metadata)
    diagnostic = _load(results / "lightgbm_diagnostic.json") if runs is not None else None

    sections: dict[str, str] = {}
    written: list[Path] = []
    if drift is not None:
        sections["Temporal drift"] = render_drift_tables(drift)
        written += [plot_temporal_drift(drift, figures), plot_sparse_by_hour(drift, figures)]
    if runs is not None:
        written.append(write_runs_csv(runs, results / "all_runs.csv"))
        if baselines is not None:
            sections["Imbalance matrix"] = render_matrix_tables(runs, baselines)
            written.append(plot_imbalance_matrix(runs, figures))
        sections["Search and sensitivity"] = render_search_tables(runs)
    if diagnostic is not None:
        sections["Search and sensitivity"] += "\n\n" + render_lightgbm_diagnostic(diagnostic)
    if selection is not None:
        sections["Model comparison"] = render_comparison_table(selection)
        sections["Stability and selection gates"] = render_stability_table(selection)
        written += [
            plot_family_curves(selection, figures),
            plot_regime_comparison(selection, figures),
            plot_compute_cost(selection, figures),
        ]
    if thresholds is not None:
        sections["Threshold behaviour"] = render_threshold_tables(thresholds)
        written += [
            plot_threshold_behaviour(thresholds, figures),
            plot_confusion_matrix(
                thresholds["selected"],
                "Validation, at the selected threshold",
                figures / "validation_confusion_matrix.png",
            ),
        ]
    if shap_report is not None:
        sections["SHAP"] = render_shap_tables(shap_report)
        written.append(plot_shap_summary(shap_report, figures))
        sample = results / "shap_sample.npz"
        if sample.is_file():
            written.append(plot_shap_dependence(sample, shap_report, figures))
    if test is not None:
        sections["Final test evaluation"] = render_test_tables(test)
        written += plot_test_results(test, figures)

    if sections:
        generated = render_results_markdown(sections)
        (results / "results_tables.md").write_text(generated + "\n", encoding="utf-8", newline="\n")
        inject_generated_results(args.document, generated)
    if metadata is not None and thresholds is not None:
        write_json(args.metrics, build_metrics_bundle(metadata, thresholds, shap_report, test))

    print(f"Sections written: {list(sections)}")
    print(f"Files written: {len(written)}")
    missing = {"test_evaluation.json": test, "shap_summary.json": shap_report}
    for name, value in missing.items():
        if value is None:
            print(f"Not yet available: {name}")


if __name__ == "__main__":
    main()
