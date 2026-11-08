"""Read a pytest JUnit XML report: counts, and every skipped test with its reason.

Used by verify_clean_clone.py to record what a checkout without the dataset or model skips,
and by CI to compare those skips with the committed expected list.
"""

import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestReport:
    """Totals and skipped tests from one pytest run."""

    __test__ = False  # not a pytest test class

    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> int:
        return self.tests - self.failures - self.errors - len(self.skipped)


def node_id(classname: str, name: str, root: Path) -> str:
    """Turn JUnit's dotted class name back into a pytest node id (tests/unit/test_x.py::name).

    The class name is a module path, optionally followed by test class names. The module part is
    the longest prefix that exists as a file under root.
    """
    parts = classname.split(".")
    for cut in range(len(parts), 0, -1):
        module = Path(*parts[:cut]).with_suffix(".py")
        if (root / module).is_file():
            return "::".join([module.as_posix(), *parts[cut:], name])
    return "::".join([classname, name])


def read_junit(path: Path, root: Path) -> TestReport:
    """Read a JUnit XML file written by pytest. root is the folder pytest ran from."""
    report = TestReport()
    for case in ElementTree.parse(path).getroot().iter("testcase"):
        report.tests += 1
        identifier = node_id(case.get("classname", ""), case.get("name", ""), root)
        if case.find("failure") is not None:
            report.failures += 1
        elif case.find("error") is not None:
            report.errors += 1
        elif (skip := case.find("skipped")) is not None:
            report.skipped[identifier] = skip.get("message", "")
    return report
