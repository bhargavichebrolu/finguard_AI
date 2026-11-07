"""Shared fixtures: a small, hand-built PaySim-shaped CSV so tests never need the real file.

Database fixtures use TEST_DATABASE_URL only. They delete rows, so they refuse any database whose
name does not end in _test. The environment is set before anything can read the settings.
"""

import importlib.util
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.database.base import Base
from app.ml.dataset_preparation import PartitionData
from app.ml.features import engineer_features
from app.ml.preprocessing import compact_features
from app.ml.schema import RAW_COLUMNS, TRANSACTION_TYPES
from app.ml.splitting import SplitConfig
from app.models import records  # noqa: F401  (importing registers the tables on Base.metadata)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FIXTURE_STEPS = 30
FIXTURE_ROWS_PER_STEP = 20
_UNUSED_DATABASE_URL = "postgresql+psycopg://unused:unused@127.0.0.1:1/unused_test"


def configure_test_environment() -> str | None:
    """Point the settings at the test database, and return its address if there is one."""
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(REPO_ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = url or _UNUSED_DATABASE_URL
    os.environ["SECRET_KEY"] = "test-only-signing-key-" + "x" * 32
    return url


TEST_DATABASE_URL = configure_test_environment()


def require_test_database_name(url: str) -> None:
    """Refuse to touch a database that is not clearly a test database."""
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise RuntimeError(f"Refusing to run tests against the database named {name!r}")


def alembic_config() -> Config:
    """Return an Alembic configuration that works from any folder."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    """Return an engine for the migrated test database, or skip if none is configured."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    require_test_database_name(TEST_DATABASE_URL)
    command.upgrade(alembic_config(), "head")
    engine = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
    yield engine
    engine.dispose()


def empty_all_tables(engine: Engine) -> None:
    """Delete every row in the application tables."""
    names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {names} CASCADE"))


@pytest.fixture
def db_session(db_engine: Engine) -> Session:
    """Return a session on an empty test database."""
    empty_all_tables(db_engine)
    with Session(db_engine, expire_on_commit=False) as session:
        yield session


def build_raw_frame() -> pd.DataFrame:
    """Build 600 synthetic rows over 30 steps; one TRANSFER row per step is labelled fraud."""
    rows = []
    for step in range(1, FIXTURE_STEPS + 1):
        for position in range(FIXTURE_ROWS_PER_STEP):
            transaction_type = TRANSACTION_TYPES[position % len(TRANSACTION_TYPES)]
            amount = float(1000 + step * 10 + position)
            is_fraud = int(transaction_type == "TRANSFER" and position == 4)
            prefix = "M" if transaction_type == "PAYMENT" else "C"
            rows.append(
                {
                    "step": step,
                    "type": transaction_type,
                    "amount": amount,
                    "nameOrig": f"C{step:04d}{position:04d}",
                    "oldbalanceOrg": amount + 500.0,
                    "newbalanceOrig": 500.0 if not is_fraud else 0.0,
                    "nameDest": f"{prefix}9{step:04d}{position:04d}",
                    "oldbalanceDest": 50.0,
                    "newbalanceDest": 50.0 + amount,
                    "isFraud": is_fraud,
                    "isFlaggedFraud": 0,
                }
            )
    return pd.DataFrame(rows, columns=list(RAW_COLUMNS))


def build_model_partition(
    rows: int, first_step: int, last_step: int, seed: int, fraud_rate: float = 0.04
) -> PartitionData:
    """Build a synthetic partition where fraud has larger amounts, in two types only."""
    generator = np.random.default_rng(seed)
    steps = generator.integers(first_step, last_step + 1, rows)
    types = generator.choice(TRANSACTION_TYPES, rows)
    eligible = np.isin(types, ["CASH_OUT", "TRANSFER"])
    labels = (eligible & (generator.random(rows) < fraud_rate / 0.4)).astype("int8")
    amounts = np.exp(generator.normal(7.0 + 2.5 * labels, 1.0))
    inputs = pd.DataFrame(
        {
            "amount": amounts,
            "transaction_type": types,
            "step": steps,
            "destination_category": np.where(types == "PAYMENT", "merchant", "customer"),
        }
    )
    frame = compact_features(engineer_features(inputs))
    flags = np.zeros(rows, dtype="int8")
    return PartitionData(
        features=frame,
        labels=pd.Series(labels, name="is_fraud"),
        rule_flags=pd.Series(flags, name="is_flagged_fraud"),
        steps=pd.Series(steps, name="step"),
        source_rows=pd.Series(np.arange(rows), name="source_row"),
    )


def write_partition(partition: PartitionData, directory: Path, name: str) -> Path:
    """Save a partition in the same format as the real pipeline."""
    frame = partition.features.copy()
    frame["is_fraud"] = partition.labels.to_numpy()
    frame["is_flagged_fraud"] = partition.rule_flags.to_numpy()
    frame["step"] = partition.steps.to_numpy()
    frame["source_row"] = partition.source_rows.to_numpy()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.parquet"
    frame.to_parquet(path, index=False)
    return path


def small_experiment_config() -> dict[str, Any]:
    """Return a complete experiment config with models small enough for unit tests."""
    return {
        "version": "test",
        "primary_seed": 42,
        "stability_seeds": [42, 7],
        "threads": 1,
        "oversampling": {"target_minority_ratio": 0.2, "k_neighbors": 3},
        "timing": {"single_row_samples": 3},
        "baseline_hyperparameters": {
            "logistic_regression": {"C": 1.0, "max_iter": 300},
            "decision_tree": {"max_depth": 4, "min_samples_leaf": 5},
            "random_forest": {"n_estimators": 5, "max_depth": 4},
            "xgboost": {"n_estimators": 5, "max_depth": 2},
            "lightgbm": {"n_estimators": 5, "num_leaves": 7, "min_child_samples": 5},
            "catboost": {"iterations": 5, "depth": 2},
        },
        "tuning": {
            "logistic_regression": {"samples": 1, "grid": {"C": [0.1]}},
            "decision_tree": {"samples": 1, "grid": {"max_depth": [3]}},
            "random_forest": {"samples": 1, "grid": {"max_depth": [3]}},
            "xgboost": {"samples": 1, "grid": {"max_depth": [3]}},
            "lightgbm": {"samples": 1, "grid": {"num_leaves": [15]}},
            "catboost": {"samples": 1, "grid": {"depth": [3]}},
        },
        "sensitivity": {"oversampling_family": "lightgbm", "oversampling_ratios": [0.3]},
        "rolling_origin": {"row_share_anchors": [0.5, 0.75, 1.0]},
        "threshold": {"operational_fpr_cap": 0.05, "alternative_fpr_caps": [0.1]},
        "selection": {"max_seed_coefficient_of_variation": 0.5, "recall_tie_margin": 0.01},
        "regimes": {"sparse_step_max_rows": 20, "sensitivity_cutoffs": [10, 40]},
        "bootstrap": {"replicates": 50, "threshold_replicates": 20, "seed": 42},
        "shap": {"legitimate_sample_rows": 100, "seed": 42},
    }


@pytest.fixture
def model_partition() -> PartitionData:
    return build_model_partition(rows=3000, first_step=1, last_step=60, seed=1)


@pytest.fixture
def later_partition() -> PartitionData:
    return build_model_partition(rows=1500, first_step=61, last_step=90, seed=2)


@pytest.fixture
def experiment_config() -> dict[str, Any]:
    return small_experiment_config()


@pytest.fixture
def raw_frame() -> pd.DataFrame:
    return build_raw_frame()


@pytest.fixture
def raw_csv(tmp_path: Path, raw_frame: pd.DataFrame) -> Path:
    path = tmp_path / "paysim_fixture.csv"
    raw_frame.to_csv(path, index=False)
    return path


@pytest.fixture
def split_config() -> SplitConfig:
    return SplitConfig(version="test-split", train_row_fraction=0.7, validation_row_fraction=0.15)


@pytest.fixture
def load_script() -> Callable[[str], ModuleType]:
    """Import a file from scripts/ by name, since that folder is not an installed package."""

    def _load(name: str) -> ModuleType:
        path = REPO_ROOT / "scripts" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"finguard_scripts_{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    return _load
