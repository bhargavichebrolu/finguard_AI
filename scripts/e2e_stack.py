"""Start or stop the browser-test API: the normal image, on 127.0.0.1:8011, using the test database.

  python scripts/e2e_stack.py up     build the image, migrate the test database, start the API
  python scripts/e2e_stack.py down   stop and remove the browser-test containers

Each start generates a new signing key, passed to Docker Compose in the environment of this
process only. It is never printed or written to disk, so old test sessions stop working.
"""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = ["--profile", "e2e"]


def compose(*arguments: str, env: dict[str, str] | None = None) -> int:
    docker = shutil.which("docker")
    if docker is None:
        print("Docker is not on PATH.")
        return 1
    command = [docker, "compose", *PROFILE, *arguments]
    return subprocess.run(command, cwd=REPO_ROOT, env=env, check=False).returncode


def up() -> int:
    if compose("build", "migrate") != 0:
        return 1
    env = {**os.environ, "E2E_SECRET_KEY": secrets.token_urlsafe(48)}
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
