"""Check that a fresh clone, without the dataset, model binary or .env, installs and tests cleanly.

  python scripts/verify_clean_clone.py [--ref HEAD] [--skip-frontend] [--keep] [--report FILE]

Clones the committed repository into a temporary folder, confirms the ignored inputs are absent,
installs from the lockfiles only (uv sync --frozen, npm ci), and runs the backend suite, the
frontend checks and the repository checks. It records exactly which tests skip and why, which
is what CI on a clean checkout will see. Database tests use TEST_DATABASE_URL (environment or
this repository's .env), whose name must end in _test.
"""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import make_url

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report import read_junit  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_PARTITION_CHECK = (
    "tests/integration/test_real_models.py"
    "::test_test_results_can_be_recalculated_from_the_saved_model"
)
MUST_BE_ABSENT = (
    ".env",
    "artifacts/models/fraud_detector_v1/model.joblib",
    "data/raw/PS_20174392719_1491204439457_log.csv",
)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> int:
    print(f"$ {' '.join(command)}", flush=True)
    executable = shutil.which(command[0]) or command[0]
    return subprocess.run([executable, *command[1:]], cwd=cwd, env=env, check=False).returncode


def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(REPO_ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url or not (make_url(url).database or "").endswith("_test"):
        raise SystemExit("TEST_DATABASE_URL must be set and name a database ending in _test.")
    return url


def remove_tree(path: Path) -> None:
    """Delete a folder, including Git's read-only object files on Windows."""

    def make_writable(function, target, _info):
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onerror=make_writable)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the temporary clone")
    parser.add_argument("--report", type=Path, help="write the results as JSON here")
    arguments = parser.parse_args(argv)

    workspace = Path(tempfile.mkdtemp(prefix="finguard-clean-"))
    clone = workspace / "repo"
    results: dict[str, object] = {"ref": arguments.ref, "steps": {}}
    steps: dict[str, int] = results["steps"]  # type: ignore[assignment]
    try:
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"DATABASE_URL", "SECRET_KEY", "VIRTUAL_ENV"}
        }
        env["TEST_DATABASE_URL"] = test_database_url()
        steps["clone"] = run(
            ["git", "clone", "--quiet", "--no-local", str(REPO_ROOT), str(clone)], workspace, env
        )
        steps["checkout"] = run(["git", "checkout", "--quiet", arguments.ref], clone, env)
        results["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=clone, capture_output=True, text=True, check=True
        ).stdout.strip()
        present = [name for name in MUST_BE_ABSENT if (clone / name).exists()]
        results["ignored_inputs_present"] = present
        if present:
            print(f"Expected these to be absent from a clone: {present}")
            return 1

        steps["uv sync --frozen"] = run(
            ["uv", "sync", "--frozen", "--project", "backend"], clone, env
        )
        junit = workspace / "pytest.xml"
        steps["pytest"] = run(
            [
                "uv",
                "run",
                "--frozen",
                "--project",
                "backend",
                "pytest",
                "backend/tests",
                "--rootdir",
                "backend",
                "-c",
                "backend/pyproject.toml",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit}",
                "--deselect",
                TEST_PARTITION_CHECK,
            ],
            clone,
            env,
        )
        report = read_junit(junit, clone / "backend")
        results["pytest"] = {
            "tests": report.tests,
            "passed": report.passed,
            "failed": report.failures,
            "errors": report.errors,
            "skipped": report.skipped,
        }

        python = ["uv", "run", "--frozen", "--project", "backend", "python"]
        steps["check_explanations"] = run([*python, "scripts/check_explanations.py"], clone, env)
        steps["export_openapi --check"] = run(
            [*python, "scripts/export_openapi.py", "--check"], clone, env
        )
        steps["export_model_report --check"] = run(
            [*python, "scripts/export_model_report.py", "--check"], clone, env
        )

        if not arguments.skip_frontend:
            frontend = clone / "frontend"
            for name, command in (
                ("npm ci", ["npm", "ci", "--no-audit", "--no-fund"]),
                ("npm run typecheck", ["npm", "run", "typecheck"]),
                ("npm test", ["npm", "test"]),
                ("npm run build", ["npm", "run", "build"]),
            ):
                steps[name] = run(command, frontend, env)
    finally:
        if arguments.report:
            arguments.report.write_text(json.dumps(results, indent=2), encoding="utf-8")
        if arguments.keep:
            print(f"Kept {workspace}")
        else:
            remove_tree(workspace)

    pytest_results = results.get("pytest", {})
    print(json.dumps({"commit": results.get("commit"), "steps": steps}, indent=2))
    if isinstance(pytest_results, dict):
        print(
            f"pytest: {pytest_results['passed']} passed, {pytest_results['failed']} failed, "
            f"{pytest_results['errors']} errors, {len(pytest_results['skipped'])} skipped"
        )
    return 0 if all(code == 0 for code in steps.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
