"""Check a test run against committed expectations: fail on unexpected skips or missing tests.

  python scripts/check_test_run.py SUITE JUNIT_FILE [--summary FILE]
  python scripts/check_test_run.py SUITE JUNIT_FILE --update

SUITE is a key of .github/expected-tests.json ("backend" or "frontend"). The run passes only if
the JUnit file exists, it holds tests, none failed or errored, the skipped tests and their
reasons equal the committed list exactly, and at least the committed minimum passed. A test that
starts skipping, stops skipping, or skips for a different reason (for example a database test
skipping because the database is missing) fails the check, so the skipped set cannot change
silently. --update rewrites the suite's entry from the run, for a deliberate, reviewed change.

Uses only the standard library, so CI can run it without installing the backend.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report import TestReport, read_junit  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTATIONS_PATH = REPO_ROOT / ".github" / "expected-tests.json"
# Folder each suite's tests run from, which turns JUnit class names back into node ids.
SUITE_ROOTS = {"backend": REPO_ROOT / "backend", "frontend": REPO_ROOT / "frontend"}


@dataclass
class Outcome:
    """What a comparison found. Problems make the check fail; notes are reported either way."""

    problems: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.problems


def load_expectations(path: Path, suite: str) -> dict:
    """Return one suite's committed expectations: minimum_passed, skipped and notes."""
    expectations = json.loads(path.read_text(encoding="utf-8"))
    if suite not in expectations:
        raise SystemExit(f"{suite!r} is not a suite in {path.name}")
    return expectations[suite]


def compare(report: TestReport | None, expected: dict) -> Outcome:
    """Compare one run with its expectations."""
    outcome = Outcome()
    if report is None:
        outcome.problems.append("No test results were written: the tests did not run.")
        return outcome
    if report.tests == 0:
        outcome.problems.append("The results hold no tests: none were collected.")
    if report.failures or report.errors:
        outcome.problems.append(f"{report.failures} failed and {report.errors} errored.")

    expected_skips: dict[str, str] = expected["skipped"]
    unexpected = sorted(set(report.skipped) - set(expected_skips))
    no_longer_skipped = sorted(set(expected_skips) - set(report.skipped))
    changed_reason = sorted(
        name
        for name in set(report.skipped) & set(expected_skips)
        if report.skipped[name] != expected_skips[name]
    )
    for name in unexpected:
        outcome.problems.append(f"Unexpected skip: {name} ({report.skipped[name]})")
    for name in no_longer_skipped:
        outcome.problems.append(
            f"Expected to skip but did not (it ran, or no longer exists): {name}"
        )
    for name in changed_reason:
        outcome.problems.append(
            f"Skipped for a different reason: {name}: expected "
            f"{expected_skips[name]!r}, got {report.skipped[name]!r}"
        )

    minimum = expected["minimum_passed"]
    if report.passed < minimum:
        outcome.problems.append(
            f"Only {report.passed} tests passed; at least {minimum} are expected. "
            "Tests were lost or not collected."
        )

    outcome.lines.append(
        f"{report.tests} tests: {report.passed} passed, {report.failures} failed, "
        f"{report.errors} errored, {len(report.skipped)} skipped "
        f"({len(expected_skips)} expected, at least {minimum} passing expected)."
    )
    for reason, count in sorted(Counter(report.skipped.values()).items()):
        outcome.lines.append(f"Skipped {count}: {reason}")
    outcome.lines.extend(expected.get("notes", []))
    return outcome


def updated_expectations(report: TestReport, previous: dict) -> dict:
    """Return the suite's expectations as observed in this run, keeping its notes."""
    return {
        "minimum_passed": report.passed,
        "skipped": dict(sorted(report.skipped.items())),
        "notes": previous.get("notes", []),
    }


def render_summary(suite: str, outcome: Outcome) -> str:
    """Return a Markdown summary for the job page."""
    verdict = "passed" if outcome.passed else "FAILED"
    lines = [f"### {suite} tests: {verdict}", ""]
    lines.extend(f"- {line}" for line in outcome.lines)
    if outcome.problems:
        lines.extend(["", "Problems:", ""])
        lines.extend(f"- {problem}" for problem in outcome.problems)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("suite", choices=sorted(SUITE_ROOTS))
    parser.add_argument("junit", type=Path)
    parser.add_argument("--expected", type=Path, default=EXPECTATIONS_PATH)
    parser.add_argument("--summary", type=Path, help="append a Markdown summary to this file")
    parser.add_argument("--update", action="store_true", help="record this run as expected")
    arguments = parser.parse_args(argv)

    expected = load_expectations(arguments.expected, arguments.suite)
    report = (
        read_junit(arguments.junit, SUITE_ROOTS[arguments.suite])
        if arguments.junit.is_file()
        else None
    )

    if arguments.update:
        if report is None or report.failures or report.errors:
            print("Refusing to record a run that is missing or has failures.")
            return 1
        everything = json.loads(arguments.expected.read_text(encoding="utf-8"))
        everything[arguments.suite] = updated_expectations(report, expected)
        arguments.expected.write_text(json.dumps(everything, indent=2) + "\n", encoding="utf-8")
        print(f"Recorded {len(report.skipped)} skips and {report.passed} passing tests.")
        return 0

    outcome = compare(report, expected)
    summary = render_summary(arguments.suite, outcome)
    print(summary)
    if arguments.summary:
        with arguments.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary)
    return 0 if outcome.passed else 1


if __name__ == "__main__":
    sys.exit(main())
