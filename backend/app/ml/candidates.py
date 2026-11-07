"""The six model families and the description of one experiment.

Libraries are imported inside build_estimator, so that using one family does not require the
others to be installed. A candidate is fully described by CandidateSpec, and its run_id is
derived from that description, so changing a setting can never reuse an old result.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sklearn.pipeline import Pipeline

from app.ml.imbalance import OVERSAMPLING_METHODS
from app.ml.preprocessing import build_preprocessor

MODEL_FAMILIES: tuple[str, ...] = (
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)
ORIGINAL = "original"
CLASS_WEIGHT = "class_weight"
IMBALANCE_STRATEGIES: tuple[str, ...] = (ORIGINAL, CLASS_WEIGHT, *OVERSAMPLING_METHODS)
_SCALE_NUMERIC_FAMILIES = {"logistic_regression"}


@dataclass(frozen=True)
class CandidateSpec:
    """Everything that defines one fitted model, apart from the data it is fitted on."""

    family: str
    strategy: str
    hyperparameters: Mapping[str, Any]
    seed: int
    target_ratio: float | None = None
    dropped_features: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.family not in MODEL_FAMILIES:
            raise ValueError(f"Unknown model family: {self.family}")
        if self.strategy not in IMBALANCE_STRATEGIES:
            raise ValueError(f"Unknown imbalance strategy: {self.strategy}")
        if (self.strategy in OVERSAMPLING_METHODS) != (self.target_ratio is not None):
            raise ValueError("target_ratio must be set for oversampling, and only for oversampling")

    def identity(self) -> dict[str, Any]:
        """Return the JSON form of this spec, as saved with its results."""
        return {
            "family": self.family,
            "strategy": self.strategy,
            "hyperparameters": dict(self.hyperparameters),
            "seed": self.seed,
            "target_ratio": self.target_ratio,
            "dropped_features": list(self.dropped_features),
        }

    @property
    def run_id(self) -> str:
        """A stable, readable identifier derived from every field."""
        text = json.dumps(self.identity(), sort_keys=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        return f"{self.family}-{self.strategy}-{digest}"


def build_estimator(
    family: str,
    hyperparameters: Mapping[str, Any],
    class_weighted: bool,
    positive_weight: float,
    seed: int,
    threads: int,
) -> Any:
    """Create one unfitted estimator.

    positive_weight is legitimate rows divided by fraud rows in the fold being fitted. It is
    applied only if class_weighted is True, which is the same balance as sklearn's "balanced".
    """
    params = dict(hyperparameters)
    sklearn_weight = "balanced" if class_weighted else None
    booster_weight = positive_weight if class_weighted else 1.0

    if family == "logistic_regression":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(class_weight=sklearn_weight, random_state=seed, **params)
    if family == "decision_tree":
        from sklearn.tree import DecisionTreeClassifier

        return DecisionTreeClassifier(class_weight=sklearn_weight, random_state=seed, **params)
    if family == "random_forest":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            class_weight=sklearn_weight, random_state=seed, n_jobs=threads, **params
        )
    if family == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            scale_pos_weight=booster_weight,
            random_state=seed,
            n_jobs=threads,
            tree_method="hist",
            eval_metric="aucpr",
            **params,
        )
    if family == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            scale_pos_weight=booster_weight,
            random_state=seed,
            n_jobs=threads,
            verbose=-1,
            deterministic=True,
            force_row_wise=True,
            **params,
        )
    if family == "catboost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(
            scale_pos_weight=booster_weight,
            random_seed=seed,
            thread_count=threads,
            verbose=False,
            allow_writing_files=False,
            **params,
        )
    raise ValueError(f"Unknown model family: {family}")


def build_pipeline(spec: CandidateSpec, positive_weight: float, threads: int) -> Pipeline:
    """Join preprocessing and an estimator. Samplers are not part of it, so they cannot run on
    anything passed to predict."""
    estimator = build_estimator(
        spec.family,
        spec.hyperparameters,
        class_weighted=spec.strategy == CLASS_WEIGHT,
        positive_weight=positive_weight,
        seed=spec.seed,
        threads=threads,
    )
    preprocessor = build_preprocessor(
        scale_numeric=spec.family in _SCALE_NUMERIC_FAMILIES,
        dropped_features=spec.dropped_features,
    )
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def set_inference_threads(pipeline: Pipeline, threads: int) -> None:
    """Change a fitted model's thread count, because single rows need only one.

    CatBoost refuses parameter changes after fitting, so it keeps the count it was fitted with.
    """
    model = pipeline.named_steps["model"]
    params = model.get_params()
    if "n_jobs" in params and "thread_count" not in params:
        model.set_params(n_jobs=threads)
