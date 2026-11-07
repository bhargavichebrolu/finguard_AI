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


def test_checker_accepts_a_sibling_explanation(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "def run():\n    return 1\n", None)
    sibling = root / "scripts" / "tool.py.explanation.md"
    sibling.write_text(COMPLETE_SECTIONS + "\n`run`\n", encoding="utf-8")
    assert checker.run_check(root, docs)[1] == []


def test_checker_checks_the_content_of_a_sibling_explanation(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "def run():\n    return 1\n", None)
    sibling = root / "scripts" / "tool.py.explanation.md"
    sibling.write_text(COMPLETE_SECTIONS, encoding="utf-8")
    assert checker.run_check(root, docs)[1] == ["scripts/tool.py: 'run' is not explained"]


def test_checker_reports_a_source_documented_in_both_places(tmp_path, load_script):
    checker = load_script("check_explanations")
    text = COMPLETE_SECTIONS + "\n`run`\n"
    root, docs = make_repo(tmp_path, "def run():\n    return 1\n", text)
    (root / "scripts" / "tool.py.explanation.md").write_text(text, encoding="utf-8")
    _, problems = checker.run_check(root, docs)
    assert problems == ["scripts/tool.py: documented in both the sibling and mirrored locations"]


def test_checker_reports_an_orphan_sibling(tmp_path, load_script):
    checker = load_script("check_explanations")
    root, docs = make_repo(tmp_path, "VALUE = 1\n", COMPLETE_SECTIONS)
    (root / "scripts" / "gone.py.explanation.md").write_text("old", encoding="utf-8")
    _, problems = checker.run_check(root, docs)
    assert problems == ["Orphan explanation: scripts/gone.py.explanation.md"]


def test_checker_covers_configuration_files(tmp_path, load_script):
    checker = load_script("check_explanations")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    _, problems = checker.run_check(tmp_path, tmp_path / "docs" / "file-explanations")
    assert problems == [
        "docker-compose.yml: explanation missing (docker-compose.yml.explanation.md)"
    ]


def test_generate_env_fills_every_secret_without_placeholders(load_script):
    generator = load_script("generate_env")
    template = (generator.REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    rendered = generator.render_env(template, 55432, 8010)
    assert "change-me" not in rendered
    assert "replace-with" not in rendered
    assert "POSTGRES_HOST_PORT=55432" in rendered
    assert "API_HOST_PORT=8010" in rendered
    assert "@127.0.0.1:55432/finguard_test" in rendered


def test_generate_env_creates_different_secrets_each_time(load_script):
    generator = load_script("generate_env")
    template = (generator.REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert generator.render_env(template, 1, 2) != generator.render_env(template, 1, 2)


def test_generate_env_refuses_to_overwrite(tmp_path, monkeypatch, load_script):
    generator = load_script("generate_env")
    existing = tmp_path / ".env"
    existing.write_text("KEEP=1\n", encoding="utf-8")
    monkeypatch.setattr(generator, "ENV_PATH", existing)
    monkeypatch.setattr("sys.argv", ["generate_env.py"])
    assert generator.main() == 1
    assert existing.read_text(encoding="utf-8") == "KEEP=1\n"


def test_generate_env_refuses_a_file_git_would_track(tmp_path, monkeypatch, load_script):
    generator = load_script("generate_env")
    monkeypatch.setattr(generator, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(generator, "is_git_ignored", lambda path, root: False)
    monkeypatch.setattr("sys.argv", ["generate_env.py"])
    assert generator.main() == 1
    assert not (tmp_path / ".env").exists()


def test_env_template_contains_only_placeholders():
    repo_root = Path(__file__).resolve().parents[3]
    values = {}
    for line in (repo_root / ".env.example").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            name, value = line.split("=", 1)
            values[name] = value
    assert values["POSTGRES_PASSWORD"] == "change-me"
    assert values["APP_DB_PASSWORD"] == "change-me"
    assert values["SECRET_KEY"].startswith("replace-with")
    assert ":change-me@" in values["DATABASE_URL"]


def test_no_explanation_document_is_ignored_by_git():
    import shutil
    import subprocess

    if shutil.which("git") is None:
        pytest.skip("git is not available")
    repo_root = Path(__file__).resolve().parents[3]
    ignored = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert [name for name in ignored if name.endswith(".explanation.md")] == []


def test_compose_sets_scram_at_initialisation_and_stores_no_credentials():
    repo_root = Path(__file__).resolve().parents[3]
    text = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'POSTGRES_INITDB_ARGS: "--auth-local=scram-sha-256 --auth-host=scram-sha-256"' in text
    assert "POSTGRES_HOST_AUTH_METHOD" not in text
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in text
    assert "127.0.0.1:${POSTGRES_HOST_PORT" in text


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
