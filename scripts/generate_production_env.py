"""Create .env.production for docker-compose.prod.yml, with new secrets; never overwrite one.

    python scripts/generate_production_env.py --domain finguard.example.com --tls ops@example.com
    python scripts/generate_production_env.py --domain 127.0.0.1 --tls internal --https-port 9443

--tls takes an email address, for a public certificate that Caddy obtains and renews (the host
name must resolve to this server, with ports 80 and 443 reachable), or "internal" for Caddy's own
authority, which browsers do not trust: a local rehearsal only. Secrets are never printed, and the
file is written only if Git ignores it.
"""

import argparse
import re
import secrets
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / ".env.production"
PASSWORD_BYTES = 24
SECRET_KEY_BYTES = 48
_HOST_NAME = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9-]{1,63})*$")
_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def public_origin(domain: str, https_port: int) -> str:
    """The browser-visible origin: the port is shown only when it is not the HTTPS default."""
    return f"https://{domain}" if https_port == 443 else f"https://{domain}:{https_port}"


def check_inputs(domain: str, tls: str) -> None:
    """Refuse values the API or Caddy would reject later, with a clearer message now."""
    if not (_HOST_NAME.match(domain) or _IPV4.match(domain)):
        raise ValueError(f"{domain!r} is not a host name or IPv4 address (lower case, no scheme)")
    if "localhost" in domain:
        # Production start-up refuses localhost origins (app/core/config.py).
        raise ValueError("Production refuses localhost; use 127.0.0.1 for a local rehearsal")
    if tls != "internal" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", tls):
        raise ValueError("--tls must be an email address (public certificate) or 'internal'")


def render(
    domain: str, tls: str, http_port: int, https_port: int, bind_address: str, artifacts: str
) -> str:
    """Return the file's text: new random secrets and the site's settings."""
    values = {
        "FINGUARD_DOMAIN": domain,
        "FINGUARD_TLS": tls,
        "FINGUARD_PUBLIC_ORIGIN": public_origin(domain, https_port),
        "FINGUARD_HTTP_PORT": str(http_port),
        "FINGUARD_HTTPS_PORT": str(https_port),
        "FINGUARD_BIND_ADDRESS": bind_address,
        "FINGUARD_ARTIFACTS_DIR": artifacts,
        "POSTGRES_USER": "finguard_admin",
        "POSTGRES_PASSWORD": secrets.token_hex(PASSWORD_BYTES),
        "POSTGRES_DB": "finguard",
        "APP_DB_USER": "finguard_app",
        "APP_DB_PASSWORD": secrets.token_hex(PASSWORD_BYTES),
        "SECRET_KEY": secrets.token_urlsafe(SECRET_KEY_BYTES),
        "WEB_CONCURRENCY": "1",
    }
    header = [
        "# Production settings for docker-compose.prod.yml. Generated; contains secrets.",
        "# Never commit this file. Changing the database passwords here after the first start",
        "# has no effect on the existing volume (see DEPLOYMENT.md).",
    ]
    return "\n".join(header + [f"{name}={value}" for name, value in values.items()]) + "\n"


def is_git_ignored(path: Path) -> bool:
    """Return True if Git would ignore this path."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)], cwd=REPO_ROOT, capture_output=True, check=False
    )
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--domain", required=True, help="public host name, or 127.0.0.1")
    parser.add_argument("--tls", required=True, help="email address for ACME, or 'internal'")
    parser.add_argument("--http-port", type=int, default=80)
    parser.add_argument("--https-port", type=int, default=443)
    parser.add_argument(
        "--bind-address", default="0.0.0.0", help="host address Caddy listens on (default all)"
    )
    parser.add_argument(
        "--artifacts-dir", default="./artifacts", help="folder holding the frozen model files"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)

    try:
        check_inputs(arguments.domain, arguments.tls)
    except ValueError as error:
        print(error)
        return 2
    output = arguments.output.resolve()
    if output.exists():
        print(f"{output.name} already exists. Delete it yourself to generate new secrets.")
        return 1
    if output.is_relative_to(REPO_ROOT) and not is_git_ignored(output):
        print(f"Refusing to write secrets: Git does not ignore {output.name}.")
        return 1
    text = render(
        arguments.domain,
        arguments.tls,
        arguments.http_port,
        arguments.https_port,
        arguments.bind_address,
        arguments.artifacts_dir,
    )
    output.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {output.name} for {public_origin(arguments.domain, arguments.https_port)}.")
    print("Secrets are not displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
