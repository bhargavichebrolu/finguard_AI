"""Check a running FinGuard deployment through its public HTTPS origin (Phase 6).

    python scripts/verify_deployment.py --origin https://finguard.example.com --email admin@...
    python scripts/verify_deployment.py --origin https://127.0.0.1:9443 --ca-file root.crt \\
        --email admin@example.com --write

The password comes from FINGUARD_ADMIN_PASSWORD, or a prompt that does not echo. It checks what
a browser relies on: health, security headers, no API documentation, sign-in with Secure,
prefixed, HttpOnly cookies, the CSRF and origin checks, the frozen model's identity, and sign-out.
With --write it also scores one transaction and runs a three-row batch: both are stored, with
identifiers starting VERIFY-, so use it on a new or demonstration deployment.

Only the standard library is used, so it runs from any computer with Python 3.11. Certificates are
verified: pass --ca-file for a private authority (Caddy's "internal" rehearsal). Nothing secret is
printed. The exit code is the number of failed checks.
"""

import argparse
import getpass
import http.cookiejar
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

FROZEN_HASH_PREFIX = "69813c17"
FROZEN_THRESHOLD = 0.02841914258897305
SESSION_COOKIE = "__Secure-finguard_session"
CSRF_COOKIE = "__Host-finguard_csrf"


@dataclass
class Answer:
    status: int
    headers: dict[str, str]
    set_cookies: list[str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


@dataclass
class Client:
    origin: str
    context: ssl.SSLContext
    jar: http.cookiejar.CookieJar = field(default_factory=http.cookiejar.CookieJar)

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        follow: bool = True,
    ) -> Answer:
        handlers: list[urllib.request.BaseHandler] = [
            urllib.request.HTTPSHandler(context=self.context),
            urllib.request.HTTPCookieProcessor(self.jar),
        ]
        if not follow:
            handlers.append(_NoRedirect())
        opener = urllib.request.build_opener(*handlers)
        request = urllib.request.Request(
            self.origin + path, data=body, method=method, headers=headers or {}
        )
        try:
            with opener.open(request, timeout=30) as response:
                return _answer(response.status, response.headers, response.read())
        except urllib.error.HTTPError as error:
            return _answer(error.code, error.headers, error.read())

    def cookie(self, name: str) -> str | None:
        return next((cookie.value for cookie in self.jar if cookie.name == name), None)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _answer(status: int, headers: Any, body: bytes) -> Answer:
    flat = {name.lower(): value for name, value in headers.items()}
    return Answer(status, flat, headers.get_all("Set-Cookie") or [], body)


class Report:
    """Collects check results and prints one line per check."""

    def __init__(self) -> None:
        self.failures = 0

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        print(f"{'PASS' if passed else 'FAIL'}  {name}{f' ({detail})' if detail else ''}")
        self.failures += not passed
        return passed


def check_site(client: Client, report: Report) -> None:
    health = client.request("GET", "/health")
    report.check("health answers ok", health.status == 200 and health.json() == {"status": "ok"})

    page = client.request("GET", "/")
    report.check("the interface is served", page.status == 200 and b"<html" in page.body.lower())
    report.check("HSTS is sent", "max-age=" in page.headers.get("strict-transport-security", ""))
    policy = page.headers.get("content-security-policy", "")
    report.check(
        "the page has a strict content security policy",
        "script-src 'self'" in policy and "frame-ancestors 'none'" in policy,
    )
    report.check("nosniff is sent", page.headers.get("x-content-type-options") == "nosniff")
    report.check("the server does not name itself", "server" not in page.headers)

    schema = client.request("GET", "/openapi.json")
    report.check(
        "the API schema is not published",
        b'"openapi"' not in schema.body,
        f"status {schema.status}",
    )
    api_policy = client.request("GET", "/api/v1/auth/me").headers.get("content-security-policy")
    report.check(
        "API answers carry the API's own policy",
        api_policy == "default-src 'none'; frame-ancestors 'none'",
    )


def sign_in(client: Client, report: Report, email: str, password: str) -> bool:
    body = json.dumps({"email": email, "password": password}).encode()
    headers = {"Content-Type": "application/json", "Origin": client.origin}
    answer = client.request("POST", "/api/v1/auth/session", body, headers)
    if not report.check("sign-in succeeds", answer.status == 200, f"status {answer.status}"):
        return False
    session = next((c for c in answer.set_cookies if c.startswith(SESSION_COOKIE + "=")), "")
    csrf = next((c for c in answer.set_cookies if c.startswith(CSRF_COOKIE + "=")), "")
    lowered = session.lower()
    report.check(
        "the session cookie is __Secure-, HttpOnly, Secure, SameSite=Strict, Path=/api",
        all(part in lowered for part in ("httponly", "secure", "samesite=strict", "path=/api")),
    )
    report.check(
        "the CSRF cookie is __Host-, Secure, SameSite=Strict, Path=/ and readable by the page",
        csrf != ""
        and "httponly" not in csrf.lower()
        and all(part in csrf.lower() for part in ("secure", "samesite=strict", "path=/")),
    )
    report.check("the token is not in the response body", b"token" not in answer.body.lower())
    return True


def check_signed_in(client: Client, report: Report) -> None:
    me = client.request("GET", "/api/v1/auth/me")
    report.check("the session reads the account", me.status == 200)
    status = client.request("GET", "/api/v1/system/status")
    if report.check("system status is readable", status.status == 200, f"status {status.status}"):
        body = status.json()
        report.check("the API runs with production settings", body["environment"] == "production")
        report.check("the database is available", body["database_available"] is True)
        report.check(
            "the frozen model is loaded",
            body["model_sha256"].startswith(FROZEN_HASH_PREFIX)
            and body["threshold"] == FROZEN_THRESHOLD,
            f"{body['model_version']}, {body['model_sha256'][:8]}..., {body['threshold']}",
        )


def _write_headers(client: Client, origin: str | None = None, csrf: bool = True) -> dict:
    headers = {"Content-Type": "application/json", "Origin": origin or client.origin}
    if csrf:
        headers["X-CSRF-Token"] = client.cookie(CSRF_COOKIE) or ""
    return headers


SAMPLE = {
    "amount": 181.0,
    "transaction_type": "TRANSFER",
    "step": 1,
    "destination_category": "customer",
}


def check_csrf(client: Client, report: Report) -> None:
    body = json.dumps(SAMPLE).encode()
    no_token = client.request(
        "POST", "/api/v1/transactions/predict", body, _write_headers(client, csrf=False)
    )
    report.check("a change without the CSRF token is refused", no_token.status == 403)
    other_origin = client.request(
        "POST",
        "/api/v1/transactions/predict",
        body,
        _write_headers(client, origin="https://attacker.example"),
    )
    report.check("a change from another origin is refused", other_origin.status == 403)


def check_writes(client: Client, report: Report) -> None:
    tag = uuid.uuid4().hex[:10].upper()
    payload = {**SAMPLE, "external_transaction_id": f"VERIFY-{tag}-0"}
    scored = client.request(
        "POST", "/api/v1/transactions/predict", json.dumps(payload).encode(), _write_headers(client)
    )
    if report.check(
        "one transaction is scored and stored", scored.status == 201, f"status {scored.status}"
    ):
        body = scored.json()
        report.check(
            "the score is reported as uncalibrated, with the frozen threshold",
            body["score_is_calibrated"] is False and body["threshold_used"] == FROZEN_THRESHOLD,
        )
        report.check(
            "the decision is one of the two workflow decisions",
            body["prediction"] in {"FLAG_FOR_REVIEW", "NOT_FLAGGED"},
            f"{body['prediction']}, model_score {body['model_score']:.6f}",
        )

    rows = "\n".join(
        f"VERIFY-{tag}-{index},{1000 + index * 250}.00,CASH_OUT,{index + 1},customer"
        for index in range(1, 4)
    )
    csv = f"external_transaction_id,amount,transaction_type,step,destination_category\n{rows}\n"
    boundary = uuid.uuid4().hex
    multipart = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="verify.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n{csv}\r\n--{boundary}--\r\n"
    ).encode()
    headers = _write_headers(client)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    upload = client.request("POST", "/api/v1/batches/upload", multipart, headers)
    if not report.check("a CSV batch is accepted", upload.status == 202, f"status {upload.status}"):
        return
    batch_id = upload.json()["id"]
    deadline = time.monotonic() + 60
    status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status = client.request("GET", f"/api/v1/batches/{batch_id}").json()
        if status["status"] in {"COMPLETED", "FAILED"}:
            break
        time.sleep(1)
    report.check(
        "the batch is processed by the queue",
        status.get("status") == "COMPLETED" and status.get("succeeded_records") == 3,
        f"{status.get('status')}, {status.get('succeeded_records')} of 3 rows",
    )


def sign_out(client: Client, report: Report) -> None:
    answer = client.request("DELETE", "/api/v1/auth/session", headers=_write_headers(client))
    report.check("sign-out succeeds", answer.status == 204)
    report.check(
        "the session no longer works", client.request("GET", "/api/v1/auth/me").status == 401
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--origin", required=True, help="the site's https:// origin")
    parser.add_argument("--email", required=True, help="an administrator's email address")
    parser.add_argument("--ca-file", help="certificate authority to trust (private CA only)")
    parser.add_argument("--write", action="store_true", help="also score and run a small batch")
    arguments = parser.parse_args(argv)
    if not arguments.origin.startswith("https://"):
        print("The origin must be https://: production cookies are sent over HTTPS only.")
        return 1

    context = ssl.create_default_context(cafile=arguments.ca_file)
    client = Client(arguments.origin.rstrip("/"), context)
    password = os.environ.get("FINGUARD_ADMIN_PASSWORD") or getpass.getpass("Password: ")
    report = Report()
    check_site(client, report)
    if sign_in(client, report, arguments.email, password):
        check_signed_in(client, report)
        check_csrf(client, report)
        if arguments.write:
            check_writes(client, report)
        sign_out(client, report)
    print(f"{report.failures} check(s) failed." if report.failures else "All checks passed.")
    return report.failures


if __name__ == "__main__":
    sys.exit(main())
