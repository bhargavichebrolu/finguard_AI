"""Shared fixtures: a small, hand-built PaySim-shaped CSV so tests never need the real file."""

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

from app.ml.schema import RAW_COLUMNS, TRANSACTION_TYPES
from app.ml.splitting import SplitConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_STEPS = 30
FIXTURE_ROWS_PER_STEP = 20


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
