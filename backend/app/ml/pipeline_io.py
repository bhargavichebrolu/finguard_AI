"""Default file locations for the offline data pipeline, plus shared file helpers.

Only offline scripts use these paths. The API service will get its locations from
environment configuration in Phase 3, because a container has no repository layout.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

RAW_CSV_PATH = REPO_ROOT / "data" / "raw" / "PS_20174392719_1491204439457_log.csv"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SPLIT_CONFIG_PATH = REPO_ROOT / "experiments" / "experiment-configs" / "split_v1.json"

VALIDATION_REPORT_PATH = REPO_ROOT / "experiments" / "results" / "dataset_validation.json"
EDA_SUMMARY_PATH = REPO_ROOT / "experiments" / "results" / "eda_summary.json"
LEAKAGE_REPORT_PATH = REPO_ROOT / "experiments" / "results" / "leakage_audit.json"
EDA_FIGURES_DIR = REPO_ROOT / "experiments" / "figures" / "eda"

PREPROCESSING_METADATA_PATH = REPO_ROOT / "artifacts" / "metadata" / "preprocessing_v1.json"
FEATURE_DICTIONARY_PATH = REPO_ROOT / "artifacts" / "metadata" / "feature_dictionary_v1.json"

DEFAULT_CHUNK_SIZE = 500_000
_HASH_READ_BYTES = 1024 * 1024


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable, human-diffable JSON so reruns can be compared with git diff."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_HASH_READ_BYTES):
            digest.update(block)
    return digest.hexdigest()
