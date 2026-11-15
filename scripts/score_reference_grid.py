r"""Score a fixed grid of synthetic inputs with the frozen model and print a fingerprint (Phase 6).

Run inside two API images to show that a change to the image (base image, packages, build steps)
leaves inference untouched: identical fingerprints mean identical scores and SHAP values, to the
last bit. The grid is synthetic (every valid type and destination, 11 amounts, 10 steps: 550 rows);
no PaySim row and nothing from the test partition is used.

    docker run --rm --entrypoint python -v ./artifacts:/app/artifacts:ro -v ./scripts:/scripts \
        -e SECRET_KEY=<any 32+ characters> -e DATABASE_URL=postgresql+psycopg://u:p@127.0.0.1:1/x \
        -e MODEL_METADATA_PATH=... (and the other MODEL_* paths, as in docker-compose.yml) \
        finguard-api:local /scripts/score_reference_grid.py [--out /scripts/out.json]

The database is never contacted. --out also writes every score and explanation.
"""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.ml.schema import DESTINATION_CATEGORIES, TRANSACTION_TYPES
from app.services.model_service import load_verified_model

AMOUNTS = (0.01, 1.0, 9.99, 181.0, 1234.56, 10000.0, 99999.99, 250000.0, 1e6, 9.2e6, 5e7)
STEPS = (1, 7, 24, 95, 200, 400, 743, 1000, 50000, 1000000)


def reference_grid() -> pd.DataFrame:
    """Every valid type and destination pair, with each amount and step."""
    rows = [
        {"amount": amount, "transaction_type": kind, "step": step, "destination_category": place}
        for kind in TRANSACTION_TYPES
        for place in DESTINATION_CATEGORIES
        if (place == "merchant") == (kind == "PAYMENT")
        for amount in AMOUNTS
        for step in STEPS
    ]
    return pd.DataFrame(rows)


def fingerprint(scores: list[str], explanations: list[dict]) -> tuple[str, str]:
    """Return the exact serialised outputs and their SHA-256."""
    payload = json.dumps(
        {"scores": scores, "explanations": explanations}, sort_keys=True, default=repr
    )
    return payload, hashlib.sha256(payload.encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="also write every score and explanation here")
    arguments = parser.parse_args(argv)

    model = load_verified_model(get_settings())
    frame = reference_grid()
    scores = [repr(float(score)) for score in model.score(frame)]
    payload, digest = fingerprint(scores, model.explain(frame))
    summary = {
        "rows": len(frame),
        "flagged": sum(float(score) >= model.threshold for score in scores),
        "threshold": repr(model.threshold),
        "xgboost": importlib.metadata.version("xgboost"),
        "scikit-learn": importlib.metadata.version("scikit-learn"),
        "sha256_of_all_outputs": digest,
    }
    print(json.dumps(summary))
    if arguments.out:
        arguments.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
