"""Build chronological, leakage-free Parquet partitions from the raw CSV.

Only schema.PIPELINE_RAW_COLUMNS are read from disk, so balance columns and the origin
account never enter memory, let alone a processed file. Feature names, labels and the rule
flag are stored in separate columns; load_partition returns them as separate objects.
"""

import hashlib
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.ml.features import engineer_features, raw_to_prediction_inputs
from app.ml.pipeline_io import DEFAULT_CHUNK_SIZE, sha256_file
from app.ml.schema import (
    CATEGORICAL_FEATURES,
    DESTINATION_CATEGORIES,
    FEATURE_COLUMNS,
    FEATURE_SCHEMA_VERSION,
    LEAKY_BALANCE_COLUMNS,
    PIPELINE_RAW_COLUMNS,
    PROCESSED_LABEL_COLUMN,
    PROCESSED_ROW_COLUMN,
    PROCESSED_RULE_FLAG_COLUMN,
    PROCESSED_STEP_COLUMN,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
    TRANSACTION_TYPES,
)
from app.ml.splitting import (
    PARTITIONS,
    SplitBoundaries,
    SplitConfig,
    compute_boundaries,
    count_rows_per_step,
    partition_masks,
)

_PIPELINE_DTYPES = {
    "step": "int32",
    "type": "category",
    "amount": "float64",
    "nameDest": "object",
    TARGET_COLUMN: "int8",
    RULE_FLAG_COLUMN: "int8",
}


@dataclass
class PartitionData:
    """One partition, with the label kept out of the feature frame."""

    features: pd.DataFrame
    labels: pd.Series
    rule_flags: pd.Series
    steps: pd.Series
    source_rows: pd.Series


def partition_path(processed_dir: Path, partition: str) -> Path:
    """Return the Parquet path for a partition name."""
    return processed_dir / f"{partition}.parquet"


def _build_processed_chunk(chunk: pd.DataFrame, first_row: int) -> pd.DataFrame:
    """Create features plus the non-feature tracking columns for one raw chunk."""
    features = engineer_features(raw_to_prediction_inputs(chunk))
    features[PROCESSED_LABEL_COLUMN] = chunk[TARGET_COLUMN].to_numpy()
    features[PROCESSED_RULE_FLAG_COLUMN] = chunk[RULE_FLAG_COLUMN].to_numpy()
    features[PROCESSED_STEP_COLUMN] = chunk["step"].to_numpy()
    features[PROCESSED_ROW_COLUMN] = np.arange(first_row, first_row + len(chunk), dtype="int64")
    return features


def _new_partition_stats() -> dict[str, Any]:
    return {
        "rows": 0,
        "fraud_rows": 0,
        "rule_flagged_rows": 0,
        "rule_flagged_fraud_rows": 0,
        "first_step": None,
        "last_step": None,
    }


def _update_partition_stats(stats: dict[str, Any], rows: pd.DataFrame) -> None:
    is_fraud = rows[PROCESSED_LABEL_COLUMN] == 1
    is_flagged = rows[PROCESSED_RULE_FLAG_COLUMN] == 1
    stats["rows"] += len(rows)
    stats["fraud_rows"] += int(is_fraud.sum())
    stats["rule_flagged_rows"] += int(is_flagged.sum())
    stats["rule_flagged_fraud_rows"] += int((is_fraud & is_flagged).sum())
    first, last = int(rows[PROCESSED_STEP_COLUMN].min()), int(rows[PROCESSED_STEP_COLUMN].max())
    stats["first_step"] = first if stats["first_step"] is None else min(stats["first_step"], first)
    stats["last_step"] = last if stats["last_step"] is None else max(stats["last_step"], last)


def _write_partitions(
    raw_path: Path,
    processed_dir: Path,
    boundaries: SplitBoundaries,
    chunk_size: int,
) -> dict[str, dict[str, Any]]:
    """Stream the raw file into one Parquet file per partition and return partition stats."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    writers: dict[str, pq.ParquetWriter] = {}
    digests = {name: hashlib.sha256() for name in PARTITIONS}
    stats = {name: _new_partition_stats() for name in PARTITIONS}
    next_row = 0

    try:
        reader = pd.read_csv(
            raw_path,
            usecols=list(PIPELINE_RAW_COLUMNS),
            dtype=_PIPELINE_DTYPES,
            chunksize=chunk_size,
        )
        for chunk in reader:
            processed = _build_processed_chunk(chunk, next_row)
            next_row += len(chunk)
            masks = partition_masks(processed[PROCESSED_STEP_COLUMN], boundaries)
            for name, mask in masks.items():
                rows = processed.loc[mask]
                if rows.empty:
                    continue
                table = pa.Table.from_pandas(rows, preserve_index=False)
                if name not in writers:
                    writers[name] = pq.ParquetWriter(
                        partition_path(processed_dir, name), table.schema
                    )
                writers[name].write_table(table)
                row_hashes = pd.util.hash_pandas_object(rows, index=False).to_numpy()
                digests[name].update(row_hashes.tobytes())
                _update_partition_stats(stats[name], rows)
    finally:
        for writer in writers.values():
            writer.close()

    for name in PARTITIONS:
        rows = stats[name]["rows"]
        stats[name]["fraud_rate"] = stats[name]["fraud_rows"] / rows if rows else None
        stats[name]["content_sha256"] = digests[name].hexdigest()
    return stats


def prepare_dataset(
    raw_path: Path,
    processed_dir: Path,
    config: SplitConfig,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    """Create the partitions and return preprocessing metadata.

    The metadata contains no timestamps, so an identical rerun produces identical JSON and
    reproducibility can be checked with a plain diff.
    """
    boundaries = compute_boundaries(count_rows_per_step(raw_path, chunk_size), config)
    partition_stats = _write_partitions(raw_path, processed_dir, boundaries, chunk_size)
    return {
        "preprocessing_version": config.version,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "source_file": raw_path.name,
        "source_sha256": sha256_file(raw_path),
        "feature_columns": list(FEATURE_COLUMNS),
        "columns_never_read": sorted({*LEAKY_BALANCE_COLUMNS, "nameOrig"}),
        "split_config": asdict(config),
        "split_boundaries": asdict(boundaries),
        "partitions": partition_stats,
        "chunk_size": chunk_size,
        "library_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pyarrow": pa.__version__,
        },
    }


def load_partition(path: Path) -> PartitionData:
    """Load a processed partition with fixed category orders and a separated label."""
    frame = pq.read_table(path).to_pandas()
    category_orders = {
        "transaction_type": TRANSACTION_TYPES,
        "destination_category": DESTINATION_CATEGORIES,
    }
    for column in CATEGORICAL_FEATURES:
        frame[column] = pd.Categorical(frame[column], categories=category_orders[column])
    return PartitionData(
        features=frame[list(FEATURE_COLUMNS)],
        labels=frame[PROCESSED_LABEL_COLUMN],
        rule_flags=frame[PROCESSED_RULE_FLAG_COLUMN],
        steps=frame[PROCESSED_STEP_COLUMN],
        source_rows=frame[PROCESSED_ROW_COLUMN],
    )
