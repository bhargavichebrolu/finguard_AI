"""Fit, time and evaluate one candidate, and store the result so long runs can resume.

fit_candidate is the only place oversampling happens. It receives training rows and returns a
plain pipeline, so nothing passed to the pipeline later can be resampled. Every run is saved,
including failed ones, which keeps the record complete.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from app.ml.candidates import CandidateSpec, build_pipeline, set_inference_threads
from app.ml.dataset_preparation import PartitionData, load_partition, partition_path
from app.ml.evaluation import evaluate_scores
from app.ml.imbalance import OVERSAMPLING_METHODS, oversample_training_fold
from app.ml.pipeline_io import write_json
from app.ml.preprocessing import compact_features

DEVELOPMENT_PARTITIONS: tuple[str, ...] = ("train", "validation")
_SINGLE_ROW_WARMUP = 5
_MICROSECONDS_PER_SECOND = 1e6
_MILLISECONDS_PER_SECOND = 1e3


class TestPartitionAccessError(RuntimeError):
    """Raised when experiment code asks for a partition other than train or validation."""

    __test__ = False  # Tells pytest this is not a test class, despite the name.


def load_development_partition(processed_dir: Path, name: str) -> PartitionData:
    """Load train or validation, compacted for training. The test partition is refused."""
    if name not in DEVELOPMENT_PARTITIONS:
        raise TestPartitionAccessError(
            f"Experiments may read {DEVELOPMENT_PARTITIONS} only, not {name!r}. "
            "The test partition opens only through final_evaluation.py, after the freeze."
        )
    partition = load_partition(partition_path(processed_dir, name))
    partition.features = compact_features(partition.features)
    return partition


@dataclass
class FittedCandidate:
    """A fitted pipeline with a report of how it was fitted."""

    pipeline: Pipeline
    report: dict[str, Any]


def fit_candidate(
    spec: CandidateSpec,
    features: pd.DataFrame,
    labels: np.ndarray,
    threads: int,
    k_neighbors: int,
) -> FittedCandidate:
    """Fit one candidate on training rows, with any oversampling applied to those rows only."""
    labels = np.asarray(labels)
    fit_features, fit_labels = features, labels
    resample_report: dict[str, Any] | None = None
    resample_seconds = 0.0
    if spec.strategy in OVERSAMPLING_METHODS:
        start = time.perf_counter()
        result = oversample_training_fold(
            features, labels, spec.strategy, spec.target_ratio, k_neighbors, spec.seed
        )
        resample_seconds = time.perf_counter() - start
        fit_features, fit_labels, resample_report = result.features, result.labels, result.report

    fraud_rows = int(np.count_nonzero(fit_labels == 1))
    if fraud_rows == 0:
        raise ValueError("Training rows contain no fraud")
    positive_weight = (fit_labels.size - fraud_rows) / fraud_rows
    pipeline = build_pipeline(spec, positive_weight, threads)
    start = time.perf_counter()
    pipeline.fit(fit_features, fit_labels)
    fit_seconds = time.perf_counter() - start
    return FittedCandidate(
        pipeline,
        {
            "source_rows": int(labels.size),
            "source_fraud_rows": int(np.count_nonzero(labels == 1)),
            "rows_fitted": int(fit_labels.size),
            "fraud_rows_fitted": fraud_rows,
            "resampling": resample_report,
            "resample_seconds": resample_seconds,
            "fit_seconds": fit_seconds,
            "total_seconds": resample_seconds + fit_seconds,
        },
    )


def score_rows(pipeline: Pipeline, features: pd.DataFrame) -> np.ndarray:
    """Return the fraud score for each row as float64."""
    return pipeline.predict_proba(features)[:, 1].astype("float64")


def measure_inference(
    pipeline: Pipeline, features: pd.DataFrame, threads: int, single_rows: int
) -> tuple[np.ndarray, dict[str, Any]]:
    """Score all rows in one batch, then time single rows on one thread as the API would.

    The pipeline's thread setting is restored afterwards.
    """
    start = time.perf_counter()
    scores = score_rows(pipeline, features)
    batch_seconds = time.perf_counter() - start

    set_inference_threads(pipeline, 1)
    positions = np.linspace(0, len(features) - 1, single_rows + _SINGLE_ROW_WARMUP, dtype="int64")
    timings = np.empty(positions.size)
    for index, position in enumerate(positions):
        row = features.iloc[[int(position)]]
        start = time.perf_counter()
        score_rows(pipeline, row)
        timings[index] = time.perf_counter() - start
    set_inference_threads(pipeline, threads)

    settled = timings[_SINGLE_ROW_WARMUP:]
    return scores, {
        "batch_rows": int(len(features)),
        "batch_threads": threads,
        "batch_seconds": batch_seconds,
        "batch_microseconds_per_row": batch_seconds / len(features) * _MICROSECONDS_PER_SECOND,
        "single_row_samples": int(settled.size),
        "single_row_ms_median": float(np.median(settled)) * _MILLISECONDS_PER_SECOND,
        "single_row_ms_p95": float(np.percentile(settled, 95)) * _MILLISECONDS_PER_SECOND,
    }


def scores_digest(scores: np.ndarray) -> str:
    """Hash scores, so a later refit can be compared with this run exactly."""
    return hashlib.sha256(np.asarray(scores, dtype="float64").tobytes()).hexdigest()


class RunStore:
    """Saves run records to one JSON file, and scores to one file per run.

    The JSON is rewritten after each run, so an interrupted experiment loses at most the run
    in progress, and a rerun skips anything already recorded.
    """

    def __init__(self, results_path: Path, scores_dir: Path) -> None:
        self.results_path = results_path
        self.scores_dir = scores_dir
        self.runs: dict[str, dict[str, Any]] = {}
        if results_path.exists():
            self.runs = json.loads(results_path.read_text(encoding="utf-8"))

    def has(self, run_id: str) -> bool:
        """Return True if this run has already finished, successfully or not."""
        return run_id in self.runs

    def add(self, run_id: str, record: dict[str, Any], scores: np.ndarray | None = None) -> None:
        """Save a record and, optionally, its validation scores."""
        if scores is not None:
            self.scores_dir.mkdir(parents=True, exist_ok=True)
            np.save(self._scores_path(run_id), scores.astype("float32"))
        self.runs[run_id] = record
        write_json(self.results_path, self.runs)

    def load_scores(self, run_id: str) -> np.ndarray:
        """Load a run's saved validation scores, in single precision."""
        return np.load(self._scores_path(run_id))

    def _scores_path(self, run_id: str) -> Path:
        return self.scores_dir / f"{run_id}.npy"


def evaluate_candidate(
    spec: CandidateSpec,
    stage: str,
    train: PartitionData,
    evaluation: PartitionData,
    slices: dict[str, np.ndarray],
    settings: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    """Fit on one set of rows, evaluate on later rows, and return a record and the scores."""
    fitted = fit_candidate(
        spec,
        train.features,
        train.labels.to_numpy(),
        settings["threads"],
        settings["oversampling"]["k_neighbors"],
    )
    scores, inference = measure_inference(
        fitted.pipeline,
        evaluation.features,
        settings["threads"],
        settings["timing"]["single_row_samples"],
    )
    labels = evaluation.labels.to_numpy()
    record = {
        "status": "ok",
        "stage": stage,
        "spec": spec.identity(),
        "training": fitted.report,
        "inference": inference,
        "evaluation": evaluate_scores(
            labels, scores, slices, settings["threshold"]["operational_fpr_cap"]
        ),
        "scores_sha256": scores_digest(scores),
    }
    return record, scores


def run_candidate(
    spec: CandidateSpec,
    stage: str,
    store: RunStore,
    run: Callable[[], tuple[dict[str, Any], np.ndarray]],
    run_id: str | None = None,
    keep_scores: bool = True,
) -> dict[str, Any]:
    """Run once and save the outcome. A failure is recorded rather than dropped from the results."""
    key = run_id or spec.run_id
    if store.has(key):
        return store.runs[key]
    print(f"[{stage}] {key}", flush=True)
    try:
        record, scores = run()
    except Exception as exc:  # Each library has its own error types; every failure must be kept.
        record = {
            "status": "failed",
            "stage": stage,
            "spec": spec.identity(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"[{stage}] {key} FAILED: {record['error']}", flush=True)
        store.add(key, record)
        return record
    store.add(key, record, scores if keep_scores else None)
    ranking = record["evaluation"]["ranking"]
    print(
        f"[{stage}] {key} pr_auc={ranking['pr_auc']:.4f} roc_auc={ranking['roc_auc']:.4f} "
        f"fit={record['training']['total_seconds']:.0f}s",
        flush=True,
    )
    return record
