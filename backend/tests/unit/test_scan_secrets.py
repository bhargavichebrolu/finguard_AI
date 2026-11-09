"""The history secret scanner still catches real secrets after its false-positive rules.

Secret-shaped values are assembled at run time, so this file never contains one literally and
does not trip the scanner itself.
"""

import pytest

FAKE = "Zq8" + "Lm2Vx9" + "Rt4Kp7Nw"  # 17 characters, not a placeholder


@pytest.fixture
def scanner(load_script):
    return load_script("scan_secrets")


@pytest.mark.parametrize(
    "line,kind",
    [
        ("-----BEGIN RSA " + "PRIVATE KEY-----", "private key"),
        ("aws = 'AKIA" + "ABCDEFGHIJKLMNOP'", "AWS access key"),
        ("token = 'ghp_" + "a" * 36 + "'", "GitHub token"),
        (
            "DATABASE_URL=postgresql+psycopg://app:" + FAKE + "@db:5432/finguard",
            "database URL with a password",
        ),
        ("SECRET_KEY=" + FAKE, "secret assignment"),
        ('password = "' + FAKE + '"', "secret assignment"),
    ],
)
def test_real_looking_secrets_are_found(scanner, line, kind):
    findings = scanner.scan_lines([("abc file.py", line)])
    assert [finding.kind for finding in findings] == [kind]
    assert FAKE not in findings[0].preview  # values are never printed in full


@pytest.mark.parametrize(
    "line",
    [
        "password = secrets.token_urlsafe(18)",
        "def sign_in(client, email, password=DEFAULT_PASSWORD):",
        'f"postgresql+psycopg://finguard_app:{app_password}@127.0.0.1:5432/finguard"',
        "SECRET_KEY=${SECRET_KEY}",
        "DATABASE_URL=postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
    ],
)
def test_generated_values_references_and_placeholders_are_not_findings(scanner, line):
    assert scanner.scan_lines([("abc file.py", line)]) == []


def test_secret_files_are_recognised(scanner):
    for name in (".env", "backend/.env.production", "certs/server.key", "deploy/tls.pem"):
        assert scanner.SECRET_FILES.search(name), name
    assert not scanner.SECRET_FILES.search("docs/environment.md")
