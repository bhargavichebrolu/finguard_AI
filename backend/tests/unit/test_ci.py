"""Phase 5 M8: the CI workflow and the check that fails it on unexpected skips or missing tests.

The workflow cannot run until it is pushed, so these tests check what can be checked locally:
the skip comparison itself, the committed expectations, and the workflow's safety rules.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
EXPECTATIONS = REPO_ROOT / ".github" / "expected-tests.json"
TEST_PARTITION_CHECK = (
    "tests/integration/test_real_models.py"
    "::test_test_results_can_be_recalculated_from_the_saved_model"
)
ACCEPTABLE_SKIP_REASONS = {
    "frozen model file is absent",
    "The frozen model binary is absent (not stored in Git)",
    "Full dataset and processed partitions are not present",
}


@pytest.fixture
def checker(load_script):
    return load_script("check_test_run")


def write_junit(tmp_path: Path, cases: str) -> Path:
    (tmp_path / "tests" / "unit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "unit" / "test_x.py").write_text("", encoding="utf-8")
    junit = tmp_path / "report.xml"
    junit.write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>", encoding="utf-8")
    return junit


PASSING = '<testcase classname="tests.unit.test_x" name="test_ok"/>'
SKIPPED_MODEL = (
    '<testcase classname="tests.unit.test_x" name="test_model">'
    '<skipped message="frozen model file is absent"/></testcase>'
)
EXPECTED = {
    "minimum_passed": 1,
    "skipped": {"tests/unit/test_x.py::test_model": "frozen model file is absent"},
    "notes": ["Real-model inference is NOT verified in CI."],
}


def run_compare(checker, tmp_path, cases, expected=EXPECTED):
    report = checker.read_junit(write_junit(tmp_path, cases), tmp_path)
    return checker.compare(report, expected)


def test_the_expected_run_passes_and_states_what_was_not_verified(checker, tmp_path):
    outcome = run_compare(checker, tmp_path, PASSING + SKIPPED_MODEL)
    assert outcome.passed, outcome.problems
    summary = checker.render_summary("backend", outcome)
    assert "backend tests: passed" in summary
    assert "Skipped 1: frozen model file is absent" in summary
    assert "Real-model inference is NOT verified in CI." in summary


def test_an_unexpected_skip_fails(checker, tmp_path):
    extra = (
        '<testcase classname="tests.unit.test_x" name="test_db">'
        '<skipped message="TEST_DATABASE_URL is not set"/></testcase>'
    )
    outcome = run_compare(checker, tmp_path, PASSING + SKIPPED_MODEL + extra)
    assert not outcome.passed
    assert outcome.problems == [
        "Unexpected skip: tests/unit/test_x.py::test_db (TEST_DATABASE_URL is not set)"
    ]


def test_an_expected_skip_that_ran_or_disappeared_fails(checker, tmp_path):
    outcome = run_compare(checker, tmp_path, PASSING)
    assert not outcome.passed
    assert "Expected to skip but did not" in outcome.problems[0]


def test_a_skip_for_a_different_reason_fails(checker, tmp_path):
    other_reason = SKIPPED_MODEL.replace(
        "frozen model file is absent", "TEST_DATABASE_URL is not set"
    )
    outcome = run_compare(checker, tmp_path, PASSING + other_reason)
    assert not outcome.passed
    assert "Skipped for a different reason" in outcome.problems[0]


def test_failures_and_errors_fail(checker, tmp_path):
    failing = (
        '<testcase classname="tests.unit.test_x" name="test_bad"><failure message="x"/></testcase>'
    )
    outcome = run_compare(checker, tmp_path, PASSING + SKIPPED_MODEL + failing)
    assert "1 failed and 0 errored." in outcome.problems


def test_fewer_passing_tests_than_recorded_fails(checker, tmp_path):
    outcome = run_compare(checker, tmp_path, SKIPPED_MODEL)
    assert not outcome.passed
    assert "Only 0 tests passed; at least 1 are expected" in outcome.problems[0]


def test_missing_or_empty_results_fail(checker, tmp_path):
    missing = checker.compare(None, EXPECTED)
    assert missing.problems == ["No test results were written: the tests did not run."]
    empty = run_compare(checker, tmp_path, "", {**EXPECTED, "skipped": {}, "minimum_passed": 0})
    assert empty.problems == ["The results hold no tests: none were collected."]


def test_main_fails_without_results_and_writes_the_summary(checker, tmp_path):
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({"backend": EXPECTED}), encoding="utf-8")
    summary = tmp_path / "summary.md"
    absent = str(tmp_path / "absent.xml")
    code = checker.main(["backend", absent, "--expected", str(expected), "--summary", str(summary)])
    assert code == 1
    assert "backend tests: FAILED" in summary.read_text(encoding="utf-8")


def test_update_records_the_run_but_refuses_failures(checker, tmp_path):
    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps({"backend": {"minimum_passed": 0, "skipped": {}, "notes": ["kept"]}}),
        encoding="utf-8",
    )
    junit = write_junit(tmp_path, PASSING + SKIPPED_MODEL)
    checker.SUITE_ROOTS["backend"] = tmp_path
    assert checker.main(["backend", str(junit), "--expected", str(expected), "--update"]) == 0
    recorded = json.loads(expected.read_text(encoding="utf-8"))["backend"]
    assert recorded == {**EXPECTED, "notes": ["kept"]}

    errored = '<testcase classname="a" name="b"><error/></testcase>'
    failing = write_junit(tmp_path, PASSING + errored)
    assert checker.main(["backend", str(failing), "--expected", str(expected), "--update"]) == 1


def test_committed_expectations_are_consistent():
    expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    assert set(expectations) == {"backend", "frontend"}
    backend = expectations["backend"]
    assert backend["minimum_passed"] > 0
    assert expectations["frontend"]["minimum_passed"] > 0
    assert expectations["frontend"]["skipped"] == {}
    # Only two causes are acceptable on a clean checkout with a database: no model, no dataset.
    # Exact strings, so a skip such as "TEST_DATABASE_URL is not set" can never be recorded.
    assert set(backend["skipped"].values()) <= ACCEPTABLE_SKIP_REASONS
    for node in backend["skipped"]:
        assert (REPO_ROOT / "backend" / node.split("::")[0]).is_file(), node
    assert TEST_PARTITION_CHECK not in backend["skipped"]
    assert any("NOT verified in CI" in note for note in backend["notes"])


def test_workflow_pins_actions_and_keeps_permissions_read_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*(\S+)", workflow)
    assert uses, "no actions found"
    for action in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), action
    assert re.search(r"^permissions:\n  contents: read$", workflow, re.MULTILINE)
    assert "${{ secrets." not in workflow
    assert "persist-credentials: false" in workflow
    assert "trust" not in workflow.lower()


def test_workflow_runs_every_required_check():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for command in (
        "uv sync --frozen --project backend",
        "docker compose up -d --wait db",
        "ruff check backend scripts",
        "ruff format --check",
        f"--deselect {TEST_PARTITION_CHECK}",
        "scripts/check_test_run.py backend",
        "scripts/check_explanations.py",
        "scripts/export_openapi.py --check",
        "scripts/export_model_report.py --check",
        "scripts/scan_secrets.py",
        "pip-audit",
        "npm ci",
        "npm run typecheck",
        "--reporter=junit",
        "scripts/check_test_run.py frontend",
        "npm run build",
        "npm audit",
    ):
        assert command in workflow, command
    # The checks after the tests still report when an earlier step failed.
    assert workflow.count("if: ${{ !cancelled() }}") >= 8


def test_workflow_and_clean_clone_check_agree_on_absent_inputs(load_script):
    clean = load_script("verify_clean_clone")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for name in clean.MUST_BE_ABSENT:
        assert name in workflow, name
