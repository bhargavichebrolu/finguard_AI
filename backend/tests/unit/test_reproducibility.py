"""Phase 5 M1: test isolation and reproducibility.

Base images are pinned by digest, the browser-test database is kept apart from the backend
suite's and refuses any non-test name, and the clean-clone check reads pytest reports correctly.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


def test_dockerfile_base_image_and_uv_are_pinned():
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    bases = re.findall(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE)
    assert bases, "no FROM line found"
    assert all(DIGEST.search(base) for base in bases), bases
    assert re.search(r'"uv==\d+\.\d+\.\d+"', dockerfile)


def test_compose_images_are_pinned_or_built_locally():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    images = re.findall(r"^\s+image:\s+(\S+)", compose, re.MULTILINE)
    assert images, "no image lines found"
    for image in images:
        assert DIGEST.search(image) or image == "finguard-api:local", image


def test_browser_tests_use_their_own_database(load_script, monkeypatch):
    database = load_script("e2e_database")
    monkeypatch.delenv("E2E_DATABASE_URL", raising=False)
    monkeypatch.delenv("E2E_DB_NAME", raising=False)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432/finguard_test")
    url = database.browser_test_database_url()
    assert url.endswith("/finguard_e2e_test")
    assert ":p@" in url  # the password survives, so the seed script can connect


@pytest.mark.parametrize(
    "variable,value",
    [
        ("E2E_DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432/finguard"),
        ("E2E_DB_NAME", "finguard"),
    ],
)
def test_browser_test_database_must_be_a_test_database(load_script, monkeypatch, variable, value):
    database = load_script("e2e_database")
    monkeypatch.delenv("E2E_DATABASE_URL", raising=False)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432/finguard_test")
    monkeypatch.setenv(variable, value)
    with pytest.raises(SystemExit, match="must end in _test"):
        database.browser_test_database_url()


UNSAFE_NAMES = ["finguard", "Finguard_e2e_test", "x_test; DROP DATABASE y", "_test"]


@pytest.mark.parametrize("name", UNSAFE_NAMES)
def test_stack_refuses_unsafe_database_names(load_script, monkeypatch, name):
    stack = load_script("e2e_stack")
    monkeypatch.setenv("E2E_DB_NAME", name)
    with pytest.raises(SystemExit):
        stack.database_name()


def test_stack_accepts_the_default_name(load_script, monkeypatch):
    stack = load_script("e2e_stack")
    monkeypatch.delenv("E2E_DB_NAME", raising=False)
    assert stack.database_name() == "finguard_e2e_test"


def test_compose_points_browser_tests_at_their_database():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${E2E_DB_NAME:-finguard_e2e_test}" in compose


def test_junit_report_counts_and_names_skips(load_script, tmp_path):
    report_module = load_script("test_report")
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_x.py").write_text("", encoding="utf-8")
    junit = tmp_path / "report.xml"
    junit.write_text(
        """<testsuites><testsuite>
        <testcase classname="tests.unit.test_x" name="test_ok"/>
        <testcase classname="tests.unit.test_x" name="test_param[a]">
          <skipped message="model absent"/></testcase>
        <testcase classname="tests.unit.test_x.TestGroup" name="test_inner">
          <failure message="no"/></testcase>
        <testcase classname="tests.unit.test_x" name="test_error"><error message="boom"/></testcase>
        </testsuite></testsuites>""",
        encoding="utf-8",
    )
    report = report_module.read_junit(junit, tmp_path)
    assert (report.tests, report.passed, report.failures, report.errors) == (4, 1, 1, 1)
    assert report.skipped == {"tests/unit/test_x.py::test_param[a]": "model absent"}
    assert report_module.node_id("tests.unit.test_x.TestGroup", "t", tmp_path) == (
        "tests/unit/test_x.py::TestGroup::t"
    )


def test_inputs_a_clean_clone_lacks_are_ignored_by_git(load_script):
    clean = load_script("verify_clean_clone")
    for name in clean.MUST_BE_ABSENT:
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", name], cwd=REPO_ROOT, check=False
        )
        assert ignored.returncode == 0, f"{name} is not ignored by Git"
