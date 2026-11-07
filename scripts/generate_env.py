"""Create a local .env with freshly generated secrets, and refuse to overwrite an existing one.

Secrets are never printed. .env is ignored by Git, and the script checks that before writing.
"""

import argparse
import secrets
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
TEMPLATE_PATH = REPO_ROOT / ".env.example"
PASSWORD_BYTES = 24
SECRET_KEY_BYTES = 48


def is_git_ignored(path: Path, root: Path) -> bool:
    """Return True if Git would ignore this path."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", path.name], cwd=root, capture_output=True, check=False
    )
    return result.returncode == 0


def render_env(template: str, host_port: int, api_port: int) -> str:
    """Fill the template's placeholders with new secrets and the chosen host ports."""
    admin_password = secrets.token_hex(PASSWORD_BYTES)
    app_password = secrets.token_hex(PASSWORD_BYTES)
    values = {
        "POSTGRES_PASSWORD": admin_password,
        "APP_DB_PASSWORD": app_password,
        "POSTGRES_HOST_PORT": str(host_port),
        "API_HOST_PORT": str(api_port),
        "SECRET_KEY": secrets.token_urlsafe(SECRET_KEY_BYTES),
        "DATABASE_URL": (
            f"postgresql+psycopg://finguard_app:{app_password}@127.0.0.1:{host_port}/finguard"
        ),
        "TEST_DATABASE_URL": (
            f"postgresql+psycopg://finguard_app:{app_password}@127.0.0.1:{host_port}/finguard_test"
        ),
    }
    lines = []
    for line in template.splitlines():
        name = line.split("=", 1)[0]
        lines.append(f"{name}={values[name]}" if name in values and "=" in line else line)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-port", type=int, default=5432, help="host port for PostgreSQL")
    parser.add_argument("--api-port", type=int, default=8000, help="host port for the API")
    arguments = parser.parse_args()

    if ENV_PATH.exists():
        print(f"{ENV_PATH.name} already exists. Delete it yourself to generate new secrets.")
        return 1
    if not is_git_ignored(ENV_PATH, REPO_ROOT):
        print(f"Refusing to write secrets: Git does not ignore {ENV_PATH.name}.")
        return 1

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    ENV_PATH.write_text(
        render_env(template, arguments.db_port, arguments.api_port), encoding="utf-8", newline="\n"
    )
    print(f"Wrote {ENV_PATH.name} with new secrets. They are not displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
