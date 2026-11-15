"""Phase 6: the production deployment files keep the security rules the code relies on.

These read the files as text, so they run anywhere without Docker. The running stack itself is
checked by the production rehearsal (DEPLOYMENT.md) and the HTTPS browser tests.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
CADDY_PRODUCTION = (REPO_ROOT / "docker" / "caddy" / "Caddyfile.production").read_text(
    encoding="utf-8"
)
CADDY_PRODLIKE = (REPO_ROOT / "docker" / "caddy" / "Caddyfile").read_text(encoding="utf-8")
WEB_DOCKERFILE = (REPO_ROOT / "docker" / "web" / "Dockerfile").read_text(encoding="utf-8")
WEB_IGNORE = (REPO_ROOT / "docker" / "web" / "Dockerfile.dockerignore").read_text(encoding="utf-8")
API_DOCKERFILE = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
INIT_SQL = (REPO_ROOT / "docker" / "postgres" / "init" / "01_app_role.sql").read_text(
    encoding="utf-8"
)


def service(name: str) -> str:
    """Return one service's block from the production Compose file."""
    match = re.search(rf"^  {name}:\n(.*?)(?=^  \S|^\S)", COMPOSE, re.S | re.M)
    assert match, f"service {name} not found"
    return match.group(1)


def csp(caddyfile: str) -> str:
    return re.search(r'header Content-Security-Policy "([^"]+)"', caddyfile).group(1)


def test_the_site_policy_is_the_same_everywhere():
    # The production-like Caddyfile is compared with vite.config.ts by the HTTPS browser test,
    # so production, production-like and the preview server all send the same policy.
    assert csp(CADDY_PRODUCTION) == csp(CADDY_PRODLIKE)
    assert "Strict-Transport-Security" in CADDY_PRODUCTION
    assert "-Server" in CADDY_PRODUCTION


def test_api_responses_are_never_compressed():
    # BREACH: compression stays inside the static-file handler, after the API handler.
    assert CADDY_PRODUCTION.index("reverse_proxy api:8000") < CADDY_PRODUCTION.index("encode")
    api_block = api_handler()
    assert "reverse_proxy api:8000" in api_block
    assert "encode" not in api_block


def api_handler() -> str:
    """Return the whole `handle @api` block, up to the static-file handler that follows it."""
    start = CADDY_PRODUCTION.index("handle @api")
    return CADDY_PRODUCTION[start : CADDY_PRODUCTION.index("\thandle {", start)]


def test_the_api_trusts_only_caddys_fixed_address():
    caddy_address = re.search(r"ipv4_address: (\S+)", service("web")).group(1)
    assert re.search(rf"TRUSTED_PROXY_IPS: {re.escape(caddy_address)}\n", COMPOSE)
    assert caddy_address.startswith("172.30.240.")
    assert "subnet: 172.30.240.0/24" in COMPOSE


def test_only_caddy_publishes_ports():
    for name in ("db", "migrate", "api", "retention"):
        assert "ports:" not in service(name), name
    assert "ports:" in service("web")
    # The database is on its own network, which Caddy cannot reach.
    assert "networks: [data]" in service("db")
    assert "edge" not in service("db")


def test_production_settings_and_no_committed_secrets():
    assert "APP_ENV: production" in COMPOSE
    for variable in ("SECRET_KEY", "APP_DB_PASSWORD", "POSTGRES_PASSWORD"):
        # Each secret is required from the environment, with no default value.
        assert re.search(rf"\$\{{{variable}:\?", COMPOSE), variable
    assert "API_DOCS_ENABLED" not in COMPOSE  # production keeps the documentation off
    assert 'TEST_DB_NAME: ""' in service("db")


def test_frozen_model_is_mounted_read_only():
    assert "${FINGUARD_ARTIFACTS_DIR:-./artifacts}:/app/artifacts:ro" in service("api")


def test_base_images_are_pinned_by_digest():
    for text in (WEB_DOCKERFILE, API_DOCKERFILE):
        for line in re.findall(r"^FROM .*$", text, re.M):
            assert "@sha256:" in line, line
    assert re.search(r"image: postgres:17-alpine@sha256:[0-9a-f]{64}", service("db"))


def test_the_web_build_context_excludes_data_models_and_secrets():
    lines = [line.strip() for line in WEB_IGNORE.splitlines() if line and not line.startswith("#")]
    assert lines[0] == "*"
    allowed = [line for line in lines if line.startswith("!")]
    assert allowed == ["!frontend/", "!docker/caddy/Caddyfile.production"]
    assert "frontend/node_modules" in lines


def test_the_api_image_ships_no_installer_and_no_gpu_library():
    final_stage = API_DOCKERFILE[API_DOCKERFILE.rindex("FROM ") :]
    assert not re.search(r"pip install .*uv|\buv (sync|pip|run)\b", final_stage)
    assert re.search(r"pip install .*uv==", API_DOCKERFILE)  # only in the build stage
    assert "COPY --from=build /app/.venv /app/.venv" in final_stage
    lock = (REPO_ROOT / "backend" / "uv.lock").read_text(encoding="utf-8")
    assert '{ name = "nvidia-nccl-cu12", marker = "sys_platform == \'never\'" }' in lock


def test_the_database_script_creates_a_test_database_only_when_named():
    assert "\\if :create_test_db" in INIT_SQL
    assert "\\set test_db ''" in INIT_SQL.split("\\getenv test_db")[0]


@pytest.fixture
def generator(load_script):
    return load_script("generate_production_env")


def test_generated_file_supplies_every_required_variable(generator):
    text = generator.render("finguard.example.com", "ops@example.com", 80, 443, "0.0.0.0", "a")
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    required = set(re.findall(r"\$\{([A-Z_]+):\?", COMPOSE))
    assert required <= set(values), required - set(values)
    assert values["FINGUARD_PUBLIC_ORIGIN"] == "https://finguard.example.com"
    assert len(values["SECRET_KEY"]) >= 32
    assert values["APP_DB_PASSWORD"] != values["POSTGRES_PASSWORD"]
    again = dict(
        line.split("=", 1)
        for line in generator.render("a.example", "internal", 80, 443, "0.0.0.0", "a").splitlines()
        if "=" in line
    )
    assert again["SECRET_KEY"] != values["SECRET_KEY"]  # new secrets every time


def test_the_origin_names_a_non_default_port(generator):
    assert generator.public_origin("127.0.0.1", 9443) == "https://127.0.0.1:9443"
    assert generator.public_origin("site.example", 443) == "https://site.example"


@pytest.mark.parametrize(
    ("domain", "tls", "message"),
    [
        ("localhost", "internal", "refuses localhost"),
        ("https://site.example", "internal", "not a host name"),
        ("site.example", "not-an-email", "email address"),
    ],
)
def test_bad_inputs_are_refused_before_anything_is_written(generator, domain, tls, message):
    with pytest.raises(ValueError, match=message):
        generator.check_inputs(domain, tls)


def test_an_existing_file_is_never_overwritten(generator, tmp_path):
    target = tmp_path / ".env.production"
    target.write_text("KEEP=1\n", encoding="utf-8")
    code = generator.main(
        ["--domain", "site.example", "--tls", "internal", "--output", str(target)]
    )
    assert code == 1
    assert target.read_text(encoding="utf-8") == "KEEP=1\n"


def test_the_production_env_file_is_ignored_by_git():
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env.*" in ignore.splitlines()


def test_ci_builds_both_images_and_checks_the_production_configuration():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    images = workflow[workflow.index("\n  images:") :]
    assert "docker build -t finguard-api:ci backend" in images
    assert "docker build -f docker/web/Dockerfile -t finguard-web:ci ." in images
    assert "docker-compose.prod.yml" in images and "config --quiet" in images


def test_the_proxy_caps_request_bodies_above_the_upload_limit():
    # Phase 6: an upload sent without Content-Length is stopped at the proxy while it streams.
    api_block = api_handler()
    match = re.search(r"request_body \{\s*max_size (\d+)MB\s*\}", api_block)
    assert match and int(match.group(1)) == 11
    assert api_block.index("request_body") < api_block.index("reverse_proxy")


@pytest.fixture
def grid(load_script):
    return load_script("score_reference_grid")


def test_the_reference_grid_covers_every_valid_input_kind(grid):
    frame = grid.reference_grid()
    assert len(frame) == 550
    merchant = frame["destination_category"] == "merchant"
    assert ((frame["transaction_type"] == "PAYMENT") == merchant).all()
    assert set(frame["transaction_type"]) == set(grid.TRANSACTION_TYPES)
    assert list(frame.columns) == ["amount", "transaction_type", "step", "destination_category"]


def test_the_fingerprint_changes_with_any_output(grid):
    payload, digest = grid.fingerprint(["0.1", "0.2"], [{"a": 1.0}])
    assert grid.fingerprint(["0.1", "0.2"], [{"a": 1.0}]) == (payload, digest)
    assert grid.fingerprint(["0.1", "0.20000000000000004"], [{"a": 1.0}])[1] != digest
    assert grid.fingerprint(["0.1", "0.2"], [{"a": 1.0000001}])[1] != digest


def test_the_api_build_context_excludes_nested_docs_and_caches():
    # Phase 6: plain patterns match only at the context root, so the image used to contain the
    # explanation documents and local bytecode caches from inside app/ and migrations/.
    lines = (REPO_ROOT / "backend" / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for pattern in ("**/*.md", "**/__pycache__", "**/*.py[cod]", ".env", ".env.*", "tests"):
        assert pattern in lines, pattern
