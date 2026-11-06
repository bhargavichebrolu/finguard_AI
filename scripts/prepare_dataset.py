"""Build the chronological Parquet partitions and save preprocessing metadata."""

import argparse
from pathlib import Path

from app.ml.dataset_preparation import prepare_dataset
from app.ml.pipeline_io import (
    FEATURE_DICTIONARY_PATH,
    PREPROCESSING_METADATA_PATH,
    PROCESSED_DIR,
    RAW_CSV_PATH,
    SPLIT_CONFIG_PATH,
    write_json,
)
from app.ml.schema import feature_dictionary_records
from app.ml.splitting import SplitConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_CSV_PATH)
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--config", type=Path, default=SPLIT_CONFIG_PATH)
    parser.add_argument("--metadata", type=Path, default=PREPROCESSING_METADATA_PATH)
    args = parser.parse_args()

    metadata = prepare_dataset(args.input, args.output_dir, SplitConfig.from_json(args.config))
    write_json(args.metadata, metadata)
    write_json(FEATURE_DICTIONARY_PATH, feature_dictionary_records())

    for name, stats in metadata["partitions"].items():
        print(
            f"{name:<10} steps {stats['first_step']}-{stats['last_step']}  "
            f"rows {stats['rows']:>9,}  fraud {stats['fraud_rows']:>5,}  "
            f"rate {stats['fraud_rate']:.4%}"
        )
    print(f"Metadata: {args.metadata}")


if __name__ == "__main__":
    main()
