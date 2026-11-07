"""The experiment plan: baselines, imbalance matrix, tuning, sensitivity and stability.

Fitting uses training rows only. Tuning and comparison use validation rows only. The stages
run in order, and the later ones build on results saved by the earlier ones.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterSampler

from app.ml.candidates import IMBALANCE_STRATEGIES, MODEL_FAMILIES, CandidateSpec
from app.ml.dataset_preparation import PartitionData
from app.ml.evaluation import (
    build_slices,
    evaluate_scores,
    ranking_metrics,
    threshold_for_fpr_cap,
    threshold_metrics,
)
from app.ml.experiments import (
    RunStore,
    evaluate_candidate,
    fit_candidate,
    load_development_partition,
    run_candidate,
    score_rows,
)
from app.ml.imbalance import OVERSAMPLING_METHODS
from app.ml.pipeline_io import write_json
from app.ml.regimes import rows_per_step
from app.ml.schema import TRANSACTION_TYPES
from app.ml.splitting import rolling_origin_folds

REQUIRED_CONFIG_KEYS = (
    "version",
    "primary_seed",
    "stability_seeds",
    "threads",
    "oversampling",
    "timing",
    "baseline_hyperparameters",
    "tuning",
    "sensitivity",
    "rolling_origin",
    "threshold",
    "selection",
    "regimes",
    "bootstrap",
    "shap",
)
SEARCH_STAGES = ("matrix", "tuning")
_FEATURE_GROUPS = {
    "hour_features": ("hour_of_day", "hour_sin", "hour_cos"),
    "amount_features": ("amount", "amount_log1p"),
}


def load_experiment_config(path: Path) -> dict[str, Any]:
    """Read the versioned experiment config and reject one that is incomplete or inconsistent."""
    config = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        raise ValueError(f"Experiment config is missing keys: {missing}")
    families = set(config["baseline_hyperparameters"])
    if families != set(MODEL_FAMILIES):
        raise ValueError(f"baseline_hyperparameters must cover exactly {MODEL_FAMILIES}")
    if config["primary_seed"] not in config["stability_seeds"]:
        raise ValueError("primary_seed must be one of stability_seeds")
    if not 0 < config["threshold"]["operational_fpr_cap"] < 1:
        raise ValueError("operational_fpr_cap must lie between 0 and 1")
    return config


@dataclass
class ExperimentData:
    """Training and validation rows, with validation's slices worked out once."""

    train: PartitionData
    validation: PartitionData
    validation_slices: dict[str, np.ndarray]


def load_development_data(processed_dir: Path, config: dict[str, Any]) -> ExperimentData:
    """Load the two partitions experiments may use."""
    train = load_development_partition(processed_dir, "train")
    validation = load_development_partition(processed_dir, "validation")
    slices = build_slices(
        validation.features, validation.steps, config["regimes"]["sparse_step_max_rows"]
    )
    return ExperimentData(train, validation, slices)


def type_rate_scores(
    train_features: pd.DataFrame, train_labels: np.ndarray, target_features: pd.DataFrame
) -> np.ndarray:
    """Score each row with its transaction type's fraud rate in the fit rows.

    This baseline only recognises the type. A model must beat it to show that it learned anything
    from amount or hour.
    """
    fit_types = train_features["transaction_type"].astype(object).to_numpy()
    rates = {
        name: float(np.mean(train_labels[fit_types == name])) if (fit_types == name).any() else 0.0
        for name in TRANSACTION_TYPES
    }
    return target_features["transaction_type"].astype(object).map(rates).to_numpy(dtype="float64")


def run_baselines(
    data: ExperimentData, config: dict[str, Any], output_path: Path
) -> dict[str, Any]:
    """Evaluate non-learning baselines on validation, so model scores have a reference."""
    labels = data.validation.labels.to_numpy()
    fpr_cap = config["threshold"]["operational_fpr_cap"]
    type_scores = type_rate_scores(
        data.train.features, data.train.labels.to_numpy(), data.validation.features
    )
    rule_flags = data.validation.rule_flags.to_numpy()
    baselines = {
        "scope": "validation partition",
        "prevalence_of_random_ranking": ranking_metrics(labels, np.zeros_like(labels, "float64")),
        "transaction_type_rate": evaluate_scores(
            labels, type_scores, data.validation_slices, fpr_cap
        ),
        "existing_rule_is_flagged_fraud": {
            "ranking": ranking_metrics(labels, rule_flags.astype("float64")),
            "at_rule_flag": threshold_metrics(labels, rule_flags.astype("float64"), 1.0),
        },
    }
    write_json(output_path, baselines)
    return baselines


def _matrix_spec(family: str, strategy: str, config: dict[str, Any]) -> CandidateSpec:
    target_ratio = None
    if strategy in OVERSAMPLING_METHODS:
        target_ratio = config["oversampling"]["target_minority_ratio"]
    return CandidateSpec(
        family=family,
        strategy=strategy,
        hyperparameters=config["baseline_hyperparameters"][family],
        seed=config["primary_seed"],
        target_ratio=target_ratio,
    )


def _run_on_validation(
    spec: CandidateSpec, stage: str, data: ExperimentData, config: dict[str, Any], store: RunStore
) -> dict[str, Any]:
    return run_candidate(
        spec,
        stage,
        store,
        lambda: evaluate_candidate(
            spec, stage, data.train, data.validation, data.validation_slices, config
        ),
    )


def run_matrix(data: ExperimentData, config: dict[str, Any], store: RunStore) -> None:
    """Fit every family with every imbalance strategy, at fixed baseline settings."""
    for family in MODEL_FAMILIES:
        for strategy in IMBALANCE_STRATEGIES:
            _run_on_validation(
                _matrix_spec(family, strategy, config), "matrix", data, config, store
            )


def best_run(
    runs: dict[str, dict[str, Any]], family: str, stages: tuple[str, ...] = SEARCH_STAGES
) -> tuple[str, dict[str, Any]] | None:
    """Return a family's highest validation PR-AUC run from the search stages.

    Sensitivity and stability runs are not eligible. They answer other questions, and letting
    them win would add choices the selection rule did not plan for.
    """
    eligible = [
        (run_id, run)
        for run_id, run in sorted(runs.items())
        if run["status"] == "ok" and run["spec"]["family"] == family and run["stage"] in stages
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[1]["evaluation"]["ranking"]["pr_auc"])


def tuning_specs(
    family: str, winner: dict[str, Any], config: dict[str, Any]
) -> list[CandidateSpec]:
    """Sample settings around a family's baseline, keeping its best imbalance strategy."""
    tuning = config["tuning"][family]
    samples = ParameterSampler(
        tuning["grid"], n_iter=tuning["samples"], random_state=config["primary_seed"]
    )
    return [
        CandidateSpec(
            family=family,
            strategy=winner["spec"]["strategy"],
            hyperparameters={**config["baseline_hyperparameters"][family], **sample},
            seed=config["primary_seed"],
            target_ratio=winner["spec"]["target_ratio"],
        )
        for sample in samples
    ]


def run_lightgbm_diagnostic(
    data: ExperimentData, config: dict[str, Any], tuned_hyperparameters: dict[str, Any]
) -> dict[str, Any]:
    """Find out why LightGBM collapsed in the matrix on two imbalance strategies.

    The matrix used one baseline for LightGBM, and tuning kept only its best strategy, so the two
    strategies that collapsed never met any other settings. This refits them with the tuned
    settings, and with LightGBM's starting score turned off, which is what stops the divergence.
    It ran after selection, so none of these fits were eligible and none enter the run store.
    """
    baseline = config["baseline_hyperparameters"]["lightgbm"]
    settings = {
        "baseline": baseline,
        "tuned": tuned_hyperparameters,
        "baseline, boost_from_average off": {**baseline, "boost_from_average": False},
        "tuned, boost_from_average off": {**tuned_hyperparameters, "boost_from_average": False},
    }
    train_labels = data.train.labels.to_numpy()
    labels = data.validation.labels.to_numpy()
    cap = config["threshold"]["operational_fpr_cap"]
    cells = []
    for strategy in ("original", "class_weight"):
        for name, hyperparameters in settings.items():
            cell: dict[str, Any] = {"strategy": strategy, "settings": name}
            spec = CandidateSpec("lightgbm", strategy, hyperparameters, config["primary_seed"])
            try:
                fitted = fit_candidate(
                    spec,
                    data.train.features,
                    train_labels,
                    config["threads"],
                    config["oversampling"]["k_neighbors"],
                )
                scores = score_rows(fitted.pipeline, data.validation.features)
            except Exception as error:  # noqa: BLE001 - a crash is itself the finding to record
                cells.append({**cell, "status": "failed", "error": f"{type(error).__name__}"})
                continue
            ranking = ranking_metrics(labels, scores)
            threshold = threshold_for_fpr_cap(labels, scores, cap)
            booster = fitted.pipeline.named_steps["model"].booster_
            cells.append(
                {
                    **cell,
                    "status": "ok",
                    "trees_built": int(booster.num_trees()),
                    "trees_requested": int(hyperparameters["n_estimators"]),
                    "largest_split_gain": float(booster.trees_to_dataframe()["split_gain"].max()),
                    "distinct_scores": int(np.unique(scores).size),
                    "pr_auc": ranking["pr_auc"],
                    "roc_auc": ranking["roc_auc"],
                    "recall_at_fpr_cap": threshold_metrics(labels, scores, threshold)["recall"],
                }
            )
    return {
        "scope": "Diagnostic on train and validation, after selection. Not eligible for selection.",
        "eligible_for_selection": False,
        "settings": settings,
        "cells": cells,
    }


def run_tuning(data: ExperimentData, config: dict[str, Any], store: RunStore) -> None:
    """Search hyperparameters for each family on its best strategy from the matrix."""
    for family in MODEL_FAMILIES:
        found = best_run(store.runs, family, ("matrix",))
        if found is None:
            print(f"[tuning] {family} skipped: every matrix run failed", flush=True)
            continue
        for spec in tuning_specs(family, found[1], config):
            _run_on_validation(spec, "tuning", data, config, store)


def overall_top_family(runs: dict[str, dict[str, Any]]) -> str:
    """Return the family with the highest validation PR-AUC in the search stages."""
    winners = [found for family in MODEL_FAMILIES if (found := best_run(runs, family))]
    if not winners:
        raise ValueError("No successful search runs exist")
    return max(winners, key=lambda item: item[1]["evaluation"]["ranking"]["pr_auc"])[1]["spec"][
        "family"
    ]


def run_sensitivity(data: ExperimentData, config: dict[str, Any], store: RunStore) -> None:
    """Check two assumptions: the oversampling ratio, and which features carry the signal.

    These runs can inform the report but cannot be selected.
    """
    settings = config["sensitivity"]
    family = settings["oversampling_family"]
    for method in OVERSAMPLING_METHODS:
        for ratio in settings["oversampling_ratios"]:
            spec = CandidateSpec(
                family=family,
                strategy=method,
                hyperparameters=config["baseline_hyperparameters"][family],
                seed=config["primary_seed"],
                target_ratio=ratio,
            )
            _run_on_validation(spec, "sensitivity_ratio", data, config, store)

    found = best_run(store.runs, overall_top_family(store.runs))
    for dropped in _FEATURE_GROUPS.values():
        spec = _spec_from_record(found[1]["spec"], dropped=dropped)
        _run_on_validation(spec, "sensitivity_features", data, config, store)


def _subset(partition: PartitionData, mask: np.ndarray) -> PartitionData:
    return PartitionData(
        features=partition.features.loc[mask],
        labels=partition.labels.loc[mask],
        rule_flags=partition.rule_flags.loc[mask],
        steps=partition.steps.loc[mask],
        source_rows=partition.source_rows.loc[mask],
    )


def _spec_from_record(
    fields: dict[str, Any], seed: int | None = None, dropped: tuple[str, ...] = ()
) -> CandidateSpec:
    """Rebuild a spec from a saved run, optionally with another seed or fewer features."""
    return CandidateSpec(
        family=fields["family"],
        strategy=fields["strategy"],
        hyperparameters=fields["hyperparameters"],
        seed=fields["seed"] if seed is None else seed,
        target_ratio=fields["target_ratio"],
        dropped_features=dropped or tuple(fields["dropped_features"]),
    )


def _run_fold(
    spec: CandidateSpec,
    fold_index: int,
    fit: PartitionData,
    evaluation: PartitionData,
    config: dict[str, Any],
    store: RunStore,
) -> dict[str, Any]:
    """Fit on one fold's earlier rows and evaluate on its later rows. Scores are not kept."""
    slices = build_slices(
        evaluation.features, evaluation.steps, config["regimes"]["sparse_step_max_rows"]
    )
    return run_candidate(
        spec,
        "rolling_fold",
        store,
        lambda: evaluate_candidate(spec, "rolling_fold", fit, evaluation, slices, config),
        run_id=f"{spec.run_id}-fold{fold_index}",
        keep_scores=False,
    )


def run_stability(
    data: ExperimentData, config: dict[str, Any], store: RunStore, folds_path: Path
) -> None:
    """Repeat each family's best run with other seeds and on forward folds inside training.

    Oversampling, when used, is applied inside fit_candidate to each fold's fit rows alone.
    """
    folds = rolling_origin_folds(
        rows_per_step(data.train.steps), tuple(config["rolling_origin"]["row_share_anchors"])
    )
    train_steps = data.train.steps.to_numpy()
    fold_rows: list[tuple[PartitionData, PartitionData]] = []
    fold_reports: list[dict[str, Any]] = []
    for fold in folds:
        fit = _subset(data.train, train_steps <= fold["fit_end_step"])
        evaluation = _subset(
            data.train,
            (train_steps >= fold["evaluation_first_step"])
            & (train_steps <= fold["evaluation_end_step"]),
        )
        type_scores = type_rate_scores(fit.features, fit.labels.to_numpy(), evaluation.features)
        fold_reports.append(
            {
                **fold,
                "fit_rows": len(fit.labels),
                "fit_fraud_rows": int(fit.labels.sum()),
                "transaction_type_rate": ranking_metrics(evaluation.labels.to_numpy(), type_scores),
            }
        )
        fold_rows.append((fit, evaluation))
    write_json(folds_path, {"folds": fold_reports})

    for family in MODEL_FAMILIES:
        found = best_run(store.runs, family)
        if found is None:
            print(f"[stability] {family} skipped: no successful search run", flush=True)
            continue
        fields = found[1]["spec"]
        for seed in config["stability_seeds"]:
            if seed != fields["seed"]:
                spec = _spec_from_record(fields, seed=seed)
                _run_on_validation(spec, "stability_seed", data, config, store)
        for index, (fit, evaluation) in enumerate(fold_rows):
            _run_fold(_spec_from_record(fields), index, fit, evaluation, config, store)
