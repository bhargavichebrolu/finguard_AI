"""Start or stop the browser-test API: the normal image, on 127.0.0.1:8011, using its own database.

  python scripts/e2e_stack.py up     create the browser-test database if needed, build the image,
                                     migrate that database, start the API
  python scripts/e2e_stack.py down   stop and remove the browser-test containers

The browser tests use finguard_e2e_test (or E2E_DB_NAME), apart from finguard_test, which the
backend suite empties. Both names must end in _test.

Each start generates a new signing key, passed to Docker Compose in the environment of this
process only. It is never printed or written to disk, so old test sessions stop working.
"""

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = ["--profile", "e2e"]
DEFAULT_DATABASE = "finguard_e2e_test"
_DATABASE_NAME = re.compile(r"^[a-z][a-z0-9_]*_test$")

# Runs inside the database container, as its superuser, with that container's own credentials,
# so no password passes through this machine's command line. The name is validated before use.
_CREATE_IF_MISSING = r"""
export PGPASSWORD="$POSTGRES_PASSWORD"
run() { psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -tAc "$1"; }
if [ "$(run "SELECT 1 FROM pg_database WHERE datname = '$E2E_DB'")" = "1" ]; then
  echo "Database $E2E_DB exists."
else
  run "CREATE DATABASE \"$E2E_DB\" OWNER \"$APP_DB_USER\"" > /dev/null
  echo "Created database $E2E_DB."
fi
"""


def database_name() -> str:
    """The browser-test database name, refusing anything not clearly a test database."""
    name = os.environ.get("E2E_DB_NAME", DEFAULT_DATABASE)
    if not _DATABASE_NAME.fullmatch(name):
        raise SystemExit(f"Refusing the database name {name!r}: use lower case ending in _test.")
    return name


def compose(*arguments: str, env: dict[str, str] | None = None) -> int:
    docker = shutil.which("docker")
    if docker is None:
        print("Docker is not on PATH.")
        return 1
    command = [docker, "compose", *PROFILE, *arguments]
    return subprocess.run(command, cwd=REPO_ROOT, env=env, check=False).returncode


def ensure_database(name: str) -> int:
    """Create the browser-test database, owned by the application role, if it is missing."""
    if compose("up", "-d", "--wait", "db") != 0:
        return 1
    return compose("exec", "-T", "-e", f"E2E_DB={name}", "db", "sh", "-c", _CREATE_IF_MISSING)


def up() -> int:
    name = database_name()
    if ensure_database(name) != 0 or compose("build", "migrate") != 0:
        return 1
    env = {**os.environ, "E2E_SECRET_KEY": secrets.token_urlsafe(48), "E2E_DB_NAME": name}
    # migrate-e2e runs first, as a dependency; the running database container is not recreated.
    return compose("up", "-d", "--force-recreate", "--wait", "api-e2e", env=env)


def down() -> int:
    return compose("rm", "--stop", "--force", "api-e2e", "migrate-e2e")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("action", choices=["up", "down"])
    arguments = parser.parse_args(argv)
    return up() if arguments.action == "up" else down()


if __name__ == "__main__":
    sys.exit(main())
