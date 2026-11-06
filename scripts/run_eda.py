"""Compute the EDA summary and charts using the boundaries from preprocessing metadata."""

import argparse
import json
from pathlib import Path

from app.ml.eda import compute_eda, render_eda_figures
from app.ml.pipeline_io import (
    EDA_FIGURES_DIR,
    EDA_SUMMARY_PATH,
    PREPROCESSING_METADATA_PATH,
    RAW_CSV_PATH,
    write_json,
)
from app.ml.splitting import SplitBoundaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_CSV_PATH)
    parser.add_argument("--metadata", type=Path, default=PREPROCESSING_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=EDA_SUMMARY_PATH)
    parser.add_argument("--figures-dir", type=Path, default=EDA_FIGURES_DIR)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    boundaries = SplitBoundaries(**metadata["split_boundaries"])
    summary = compute_eda(args.input, boundaries)
    write_json(args.output, summary)
    figures = render_eda_figures(summary, args.figures_dir)

    print(f"Summary: {args.output}")
    for figure in figures:
        print(f"Figure: {figure}")


if __name__ == "__main__":
    main()
