"""Write the API's OpenAPI schema to frontend/openapi.json, the contract the frontend's types follow.

Building the schema starts no server and opens no database connection.

    uv run --project backend python scripts/export_openapi.py           # write it
    uv run --project backend python scripts/export_openapi.py --check   # verify it is current
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "frontend" / "openapi.json"


def current_schema() -> dict[str, Any]:
    """Return the schema FastAPI generates from the routes."""
    from app.main import create_app

    return create_app().openapi()


def render(schema: dict[str, Any]) -> str:
    """Format the schema with sorted keys, so a regenerated file only differs if the API did."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the saved schema is stale")
    arguments = parser.parse_args()

    text = render(current_schema())
    if arguments.check:
        if SCHEMA_PATH.read_text(encoding="utf-8") != text:
            print("frontend/openapi.json differs from the API. Regenerate it and the types.")
            return 1
        print("frontend/openapi.json matches the API.")
        return 0
    SCHEMA_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {SCHEMA_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
