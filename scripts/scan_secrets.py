"""Scan every line ever added in the repository's history for secrets (Phase 5 M5).

    python scripts/scan_secrets.py              # all commits on all branches
    python scripts/scan_secrets.py --staged     # only what is staged now

Looks for private keys, cloud and GitHub tokens, database URLs that carry a password, and
non-placeholder values assigned to secret-looking names, and checks that no ignored secret file
(.env, keys) was ever committed. Values that are deliberately fake test fixtures are listed in
ALLOWED with the reason; anything else is reported and fails the run. Matched values are never
printed in full.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "database URL with a password": re.compile(
        r"postgres(?:ql)?(?:\+\w+)?://[^:/\s\"'@]+:(?P<value>[^@\s\"'/]+)@"
    ),
    "secret assignment": re.compile(
        r"(?i)\b(?:secret_key|password|passwd|api_key|access_token|private_key|jwt_secret)"
        r"\s*[:=]\s*[\"']?(?P<value>[A-Za-z0-9_\-+/=.]{16,})"
    ),
}

# Fake values used deliberately, with why each is safe. A finding is allowed only if its value
# contains one of these markers.
ALLOWED = {
    "${": "a placeholder filled from the environment",
    "unused": "a throwaway URL for code that never connects",
    "realpassword": "a fake password in a configuration test",
    "test-only-signing-key": "the test suite's signing key",
    "multiprocess-test-signing-key": "the multi-process tests' signing key",
    "migration-only-": "a key used only to run migrations in tests",
    "seed-script-unused-signing-key": "a key the seed script sets but never uses",
    "explain-only-": "a key for a local measurement script",
    "change-me": "the .env.example placeholder",
    "replace-with": "the .env.example placeholder",
    "xxxxxxxx": "padding in a fake key",
    "<": "a documentation placeholder",
    "//u:p@": "a two-letter fake credential in tests",
    "a-long-password-1": "a password in a request the test expects to be refused",
    "secret internal detail": "a fake URL proving error messages hide internal details",
}
# Not literal secrets: a constant's name, or an f-string placeholder.
_CONSTANT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
SECRET_FILES = re.compile(r"(^|/)(\.env(\.[^/]+)?|[^/]+\.pem|[^/]+\.key)$")
SAFE_FILES = {".env.example", ".env.example.explanation.md"}


@dataclass(frozen=True)
class Finding:
    kind: str
    where: str
    preview: str


def _mask(value: str) -> str:
    return value[:3] + "…" if len(value) > 3 else "…"


def scan_lines(lines: list[tuple[str, str]]) -> list[Finding]:
    """Check (location, added line) pairs."""
    findings = []
    for where, line in lines:
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                value = match.groupdict().get("value") or match.group(0)
                if any(marker in value or marker in line for marker in ALLOWED):
                    continue
                if kind in ("secret assignment", "database URL with a password"):
                    # Only for assignments: a call (token_urlsafe(18)), an f-string placeholder,
                    # or a constant's name is not a literal secret. Token patterns keep no such
                    # exception: real AWS keys are capitals too.
                    generated = line[match.end() : match.end() + 1] == "("
                    if generated or value.startswith("{") or _CONSTANT_NAME.match(value):
                        continue
                findings.append(Finding(kind, where, _mask(value)))
    return findings


def added_lines(staged: bool) -> list[tuple[str, str]]:
    """Every added line with its commit and file (or only staged lines)."""
    command = (
        ["git", "diff", "--cached", "-U0"]
        if staged
        else ["git", "log", "-p", "-U0", "--all", "--format=COMMIT %h"]
    )
    output = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    lines, commit, path = [], "staged" if staged else "?", "?"
    for raw in output.splitlines():
        if raw.startswith("COMMIT "):
            commit = raw.split(" ", 1)[1]
        elif raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("+") and not raw.startswith("+++"):
            lines.append((f"{commit} {path}", raw[1:]))
    return lines


def committed_secret_files() -> list[str]:
    output = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--name-only", "--format="],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    names = {name for name in output.splitlines() if name}
    return sorted(n for n in names if SECRET_FILES.search(n) and Path(n).name not in SAFE_FILES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--staged", action="store_true")
    arguments = parser.parse_args(argv)
    lines = added_lines(arguments.staged)
    findings = scan_lines(lines)
    files = [] if arguments.staged else committed_secret_files()
    scope = "staged changes" if arguments.staged else "all history"
    print(f"Scanned {len(lines):,} added lines ({scope}).")
    for finding in findings:
        print(f"FOUND {finding.kind}: {finding.where} ({finding.preview})")
    for name in files:
        print(f"FOUND committed secret file: {name}")
    print(f"{len(findings)} findings, {len(files)} secret files.")
    return 1 if findings or files else 0


if __name__ == "__main__":
    sys.exit(main())
