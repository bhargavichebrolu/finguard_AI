"""Enforce the PRD section 12 documentation rule. Exits 1 if any explanation is missing or stale.

Every authored source and configuration file needs an explanation with sections A to K, and
every function, class and method in the source must be named in it. From Phase 3 the document
sits beside its source as <file>.explanation.md; Phase 1 and 2 documents remain in
docs/file-explanations/<source path>.explanation.md. Either location is accepted, but not both.
Relative links in project documents must also resolve. This catches missing and out-of-date
documents. Reviewers still judge whether the text is good.
"""

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPLANATIONS_DIR = REPO_ROOT / "docs" / "file-explanations"
SOURCE_DIRECTORIES = (
    "backend/app",
    "backend/migrations",
    "backend/tests",
    "docker",
    "scripts",
    "frontend/src",
    "frontend/tests",
)
SOURCE_FILES = (
    "frontend/vite.config.ts",
    "frontend/index.html",
    "Makefile",
    "docker-compose.yml",
    "docker/caddy/Caddyfile",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "backend/Dockerfile",
    "backend/.dockerignore",
    "backend/alembic.ini",
    "backend/pyproject.toml",
    "frontend/package.json",
    "frontend/tsconfig.json",
    "frontend/vitest.config.ts",
    "frontend/playwright.config.ts",
    "frontend/playwright.perf.config.ts",
    "frontend/playwright.prodlike.config.ts",
    ".github/workflows/ci.yml",
    ".github/expected-tests.json",
)
# Generated from frontend/openapi.json by openapi-typescript. Never edited by hand, so exempt
# (PRD 12.2), and a frontend test fails if it falls out of step with the schema.
GENERATED_FILES = frozenset({"frontend/src/types/api.generated.ts"})
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".css", ".sql", ".mako"}
IGNORED_PARTS = {"__pycache__", "node_modules", "dist", ".venv", ".pytest_cache", ".ruff_cache"}
EXPLANATION_SUFFIX = ".explanation.md"
MINIMUM_WORDS = 80
REQUIRED_SECTIONS = (
    "A. File Purpose",
    "B. Why This File Exists",
    "C. Dependencies",
    "D. Every Function Explained",
    "E. Classes Explained",
    "F. Execution Flow",
    "G. Input and Output",
    "H. Important Technical Concepts",
    "I. Example",
    "J. Maintenance Notes",
    "K. Related Files",
)
_MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
_TYPESCRIPT_NAME_PATTERNS = (
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?\(", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE),
)


def python_definition_names(source: str) -> list[str]:
    """Return every function, class and method name in Python source, at any nesting level."""
    tree = ast.parse(source)
    definitions = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    return [node.name for node in ast.walk(tree) if isinstance(node, definitions)]


def typescript_definition_names(source: str) -> list[str]:
    """Return named functions, arrow-function constants and classes in TypeScript source."""
    names: list[str] = []
    for pattern in _TYPESCRIPT_NAME_PATTERNS:
        names.extend(pattern.findall(source))
    return names


def is_package_marker(path: Path) -> bool:
    """A Python file holding only a docstring has no behaviour to explain."""
    if path.suffix != ".py":
        return False
    body = ast.parse(path.read_text(encoding="utf-8")).body
    return all(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for node in body
    )


def is_documented_source(path: Path) -> bool:
    """Decide whether a file falls under the per-file explanation rule."""
    if IGNORED_PARTS & set(path.parts) or path.name.endswith(".d.ts"):
        return False
    if path.as_posix().endswith(tuple(GENERATED_FILES)):
        return False
    return path.suffix in SOURCE_SUFFIXES and not is_package_marker(path)


def find_source_files(root: Path) -> list[Path]:
    """List all files that must have an explanation, relative to the repository root."""
    found: list[Path] = []
    for directory in SOURCE_DIRECTORIES:
        base = root / directory
        if base.is_dir():
            found.extend(
                path.relative_to(root)
                for path in base.rglob("*")
                if path.is_file() and is_documented_source(path)
            )
    found.extend(Path(name) for name in SOURCE_FILES if (root / name).is_file())
    return sorted(found)


def explanation_path(source: Path, explanations_dir: Path) -> Path:
    """Return where the explanation for a repository-relative source path lives."""
    return explanations_dir / source.parent / (source.name + EXPLANATION_SUFFIX)


def sibling_path(source: Path) -> Path:
    """Return where a document beside its source file lives."""
    return source.with_name(source.name + EXPLANATION_SUFFIX)


def locate_explanation(root: Path, source: Path, explanations_dir: Path) -> Path:
    """Return the sibling document if there is one, otherwise the mirrored location."""
    sibling = root / sibling_path(source)
    return sibling if sibling.is_file() else explanation_path(source, explanations_dir)


def check_explanation(source_path: Path, explanation: Path, label: str) -> list[str]:
    """Return every problem with one source file's explanation document."""
    if not explanation.is_file():
        return [f"{label}: explanation missing ({explanation.name})"]

    text = explanation.read_text(encoding="utf-8")
    problems: list[str] = []
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, re.MULTILINE):
            problems.append(f"{label}: missing section '{section}'")
    if len(text.split()) < MINIMUM_WORDS:
        problems.append(f"{label}: explanation has fewer than {MINIMUM_WORDS} words")

    source = source_path.read_text(encoding="utf-8")
    if source_path.suffix == ".py":
        names = python_definition_names(source)
    elif source_path.suffix in {".ts", ".tsx"}:
        names = typescript_definition_names(source)
    else:
        names = []
    for name in sorted(set(names)):
        if not re.search(rf"`{re.escape(name)}\b", text):
            problems.append(f"{label}: '{name}' is not explained")
    return problems


def find_orphans(root: Path, explanations_dir: Path, sources: list[Path]) -> list[str]:
    """Find documents whose source no longer exists, and sources documented in both places."""
    mirrored = {explanation_path(source, explanations_dir) for source in sources}
    siblings = {root / sibling_path(source) for source in sources}
    problems = [
        f"Orphan explanation: {path.relative_to(root).as_posix()}"
        for path in sibling_documents(root, explanations_dir)
        if path not in siblings
    ]
    if explanations_dir.is_dir():
        problems.extend(
            f"Orphan explanation: {path.relative_to(root).as_posix()}"
            for path in sorted(explanations_dir.rglob(f"*{EXPLANATION_SUFFIX}"))
            if path not in mirrored
        )
    problems.extend(
        f"{source.as_posix()}: documented in both the sibling and mirrored locations"
        for source in sources
        if (root / sibling_path(source)).is_file()
        and explanation_path(source, explanations_dir).is_file()
    )
    return problems


def sibling_documents(root: Path, explanations_dir: Path) -> list[Path]:
    """List explanation documents outside the mirrored folder and dependency folders."""
    found = []
    for path in root.rglob(f"*{EXPLANATION_SUFFIX}"):
        if IGNORED_PARTS & set(path.parts) or explanations_dir in path.parents:
            continue
        found.append(path)
    return sorted(found)


def find_broken_links(root: Path, explanations_dir: Path) -> list[str]:
    """Find relative Markdown links that point at a missing file."""
    documents = sorted(
        {
            *root.glob("*.md"),
            *(root / "docs").rglob("*.md"),
            *sibling_documents(root, explanations_dir),
        }
    )
    problems: list[str] = []
    for document in documents:
        for target in _MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                label = document.relative_to(root).as_posix()
                problems.append(f"{label}: broken link to {target}")
    return problems


def run_check(root: Path, explanations_dir: Path) -> tuple[list[Path], list[str]]:
    """Check a whole repository and return (source files checked, problems)."""
    sources = find_source_files(root)
    problems: list[str] = []
    for source in sources:
        problems.extend(
            check_explanation(
                root / source, locate_explanation(root, source, explanations_dir), source.as_posix()
            )
        )
    problems.extend(find_orphans(root, explanations_dir, sources))
    problems.extend(find_broken_links(root, explanations_dir))
    return sources, problems


def main() -> int:
    sources, problems = run_check(REPO_ROOT, EXPLANATIONS_DIR)
    for problem in problems:
        print(problem)
    print(f"Checked {len(sources)} source files: {len(problems)} problems.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
