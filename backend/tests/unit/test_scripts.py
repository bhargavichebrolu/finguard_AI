"""Tests for logic that lives in scripts/: dataset placement and the documentation checker."""

from pathlib import Path

import pytest

COMPLETE_SECTIONS = "\n".join(
    f"## {title}\nFiller words describing this section in some detail for the checker to count."
    for title in (
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
)


def make_repo(tmp_path: Path, source: str, explanation: str | None) -> tuple[Path, Path]:
    source_path = tmp_path / "scripts" / "tool.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(source, encoding="utf-8")
    explanations = tmp_path / "docs" / "file-explanations"
    if explanation is not None:
        doc = explanations / "scripts" / "tool.py.explanation.md"
        doc.parent.mkdir(parents=True)
        doc.write_text(explanation, encoding="utf-8")
    return tmp_path, explanations


def test_checker_accepts_a_complete_explanation(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "def run():\n    return 1\n", COMPLETE_SECTIONS + "\n`run`\n")
    sources, problems = checker.run_check(root, docs)
    assert [path.as_posix() for path in sources] == ["scripts/tool.py"]
    assert problems == []


def test_checker_reports_a_missing_explanation(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "def run():\n    return 1\n", None)
    _, problems = checker.run_check(root, docs)
    assert "explanation missing" in problems[0]


def test_checker_reports_an_undocumented_function(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "def added_later():\n    return 1\n", COMPLETE_SECTIONS)
    _, problems = checker.run_check(root, docs)
    assert problems == ["scripts/tool.py: 'added_later' is not explained"]


def test_checker_reports_a_missing_section(tmp_path, load_script):
    checker = load_script("check_explanations")
    text = COMPLETE_SECTIONS.replace("## I. Example", "## Example")
    root, docs = make_repo(tmp_path, "VALUE = 1\n", text)
    _, problems = checker.run_check(root, docs)
    assert problems == ["scripts/tool.py: missing section 'I. Example'"]


def test_checker_reports_a_thin_explanation(tmp_path, load_script):
    checker = load_script("check_explanations")
    thin = "\n".join(f"## {section}" for section in checker.REQUIRED_SECTIONS)
    root, docs = make_repo(tmp_path, "VALUE = 1\n", thin)
    _, problems = checker.run_check(root, docs)
    assert any("fewer than" in problem for problem in problems)


def test_checker_reports_orphan_documents(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "VALUE = 1\n", COMPLETE_SECTIONS)
    orphan = docs / "scripts" / "deleted.py.explanation.md"
    orphan.write_text("old", encoding="utf-8")
    _, problems = checker.run_check(root, docs)
    assert len(problems) == 1
    assert problems[0].startswith("Orphan explanation:")
    assert problems[0].endswith("scripts/deleted.py.explanation.md")


def test_checker_reports_broken_links_and_accepts_valid_ones(tmp_path, load_script):
    checker = load_script("check_explanations")
    (tmp_path / "docs").mkdir()
    (tmp_path / "exists.md").write_text("target", encoding="utf-8")
    links = "[good](exists.md) [web](https://example.com) [section](#a) [bad](missing.md)"
    (tmp_path / "README.md").write_text(links, encoding="utf-8")
    problems = checker.find_broken_links(tmp_path, tmp_path / "docs")
    assert problems == ["README.md: broken link to missing.md"]


def test_checker_skips_docstring_only_package_markers(tmp_path, load_script):
    checker = load_script("check_explanations")
    marker = tmp_path / "__init__.py"
    marker.write_text('"""Package."""\n', encoding="utf-8")
    assert checker.is_package_marker(marker) is True
    code = tmp_path / "code.py"
    code.write_text('"""Module."""\nVALUE = 1\n', encoding="utf-8")
    assert checker.is_package_marker(code) is False


def test_checker_finds_typescript_definitions(load_script):
    checker = load_script("check_explanations")
    source = (
        "export default function App() {}\n"
        "const loadData = async () => {};\n"
        "export const add = (a: number) => a;\n"
        "export class Client {}\n"
        "const VALUE = 1;\n"
    )
    assert sorted(checker.typescript_definition_names(source)) == [
        "App",
        "Client",
        "add",
        "loadData",
    ]


def test_copy_local_file_copies_content(tmp_path, load_script):
    downloader = load_script("download_dataset")
    source = tmp_path / "source.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    destination = tmp_path / "nested" / "target.csv"
    downloader.copy_local_file(source, destination)
    assert destination.read_text(encoding="utf-8") == "a,b\n1,2\n"


def test_copy_local_file_refuses_to_overwrite(tmp_path, load_script):
    downloader = load_script("download_dataset")
    source = tmp_path / "source.csv"
    source.write_text("new", encoding="utf-8")
    destination = tmp_path / "target.csv"
    destination.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        downloader.copy_local_file(source, destination)
    assert destination.read_text(encoding="utf-8") == "existing"


def test_copy_local_file_requires_a_source(tmp_path, load_script):
    downloader = load_script("download_dataset")
    with pytest.raises(FileNotFoundError):
        downloader.copy_local_file(tmp_path / "absent.csv", tmp_path / "target.csv")


def test_kaggle_download_explains_a_missing_cli(tmp_path, load_script, monkeypatch):
    downloader = load_script("download_dataset")
    monkeypatch.setattr(downloader.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="kaggle CLI is not installed"):
        downloader.download_from_kaggle(tmp_path / "target.csv")
