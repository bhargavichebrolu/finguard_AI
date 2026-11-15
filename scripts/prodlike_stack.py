"""Start or stop the production-like stack: HTTPS through Caddy, APP_ENV=production (Phase 5 M5).

  python scripts/prodlike_stack.py up     create the database, build the frontend and image,
                                          migrate, start the API and Caddy
  python scripts/prodlike_stack.py down   stop and remove the production-like containers

The site is https://127.0.0.1:8443 (Caddy's own local certificate), with plain HTTP on 8082
redirecting to it. The API is also on 127.0.0.1:8012, only so tests can show that requests
bypassing the proxy cannot claim another client's address. It uses its own database,
finguard_prodlike_test (or PRODLIKE_DB_NAME), and a new random signing key on every start.
"""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_stack import ensure_database  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = "finguard_prodlike_test"
PROFILE = ["--profile", "prodlike"]


def database_name() -> str:
    name = os.environ.get("PRODLIKE_DB_NAME", DEFAULT_DATABASE)
    if not name.endswith("_test") or not name.replace("_", "").isalnum() or name != name.lower():
        raise SystemExit(f"Refusing the database name {name!r}: use lower case ending in _test.")
    return name


def compose(*arguments: str, env: dict[str, str] | None = None) -> int:
    docker = shutil.which("docker")
    if docker is None:
        print("Docker is not on PATH.")
        return 1
    command = [docker, "compose", *PROFILE, *arguments]
    return subprocess.run(command, cwd=REPO_ROOT, env=env, check=False).returncode


def build_frontend() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("npm is not on PATH.")
        return 1
    return subprocess.run([npm, "run", "build"], cwd=REPO_ROOT / "frontend", check=False).returncode


def up() -> int:
    name = database_name()
    if ensure_database(name) != 0 or build_frontend() != 0 or compose("build", "migrate") != 0:
        return 1
    env = {**os.environ, "PRODLIKE_SECRET_KEY": secrets.token_urlsafe(48), "PRODLIKE_DB_NAME": name}
    return compose(
        "up", "-d", "--force-recreate", "--wait", "api-prodlike", "caddy-prodlike", env=env
    )


def down() -> int:
    return compose("rm", "--stop", "--force", "caddy-prodlike", "api-prodlike", "migrate-prodlike")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("action", choices=["up", "down"])
    arguments = parser.parse_args(argv)
    return up() if arguments.action == "up" else down()


if __name__ == "__main__":
    sys.exit(main())
