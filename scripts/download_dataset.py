"""Place the PaySim CSV in data/raw, from a local copy or from Kaggle.

The Kaggle route needs the kaggle CLI and an API token set up by the developer. See
DATASET_DOCUMENTATION.md for manual download steps and the licence.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from app.ml.pipeline_io import RAW_CSV_PATH

KAGGLE_DATASET = "ealaxi/paysim1"


def copy_local_file(source: Path, destination: Path) -> None:
    """Copy a downloaded CSV into place. Refuses to overwrite an existing file."""
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing dataset: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def download_from_kaggle(destination: Path) -> None:
    """Download and unzip the dataset with the kaggle CLI."""
    kaggle = shutil.which("kaggle")
    if kaggle is None:
        raise RuntimeError(
            "The kaggle CLI is not installed. Download the CSV manually from "
            f"https://www.kaggle.com/datasets/{KAGGLE_DATASET} and rerun with --from-file."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        kaggle, "datasets", "download", "-d", KAGGLE_DATASET,
        "-p", str(destination.parent), "--unzip",
    ]
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-file", type=Path, help="Path to an already downloaded CSV")
    parser.add_argument("--output", type=Path, default=RAW_CSV_PATH)
    args = parser.parse_args()

    if args.from_file is None and args.output.exists():
        print(f"Dataset already present: {args.output}")
        return 0
    try:
        if args.from_file is not None:
            copy_local_file(args.from_file, args.output)
        else:
            download_from_kaggle(args.output)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Dataset ready: {args.output}. Next, run scripts/validate_dataset.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
