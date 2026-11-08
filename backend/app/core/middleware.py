"""Per-request context: an ID, an access log line, security headers and a request size limit.

This is plain ASGI middleware. Request bodies are never read or logged here.
"""

import json
import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

logger = logging.getLogger("finguard.request")

_SIZE_ALLOWANCE_BYTES = 1024 * 1024
_SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
)
_NO_STORE = (b"cache-control", b"no-store")
# The API returns data, never pages, so its responses may load nothing at all.
API_CONTENT_SECURITY_POLICY = b"default-src 'none'; frame-ancestors 'none'"
# FastAPI's documentation pages load Swagger UI and ReDoc from a CDN and start with inline script.
DOCS_CONTENT_SECURITY_POLICY = (
    b"default-src 'none'; "
    b"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    b"font-src https://fonts.gstatic.com; "
    b"img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    b"worker-src blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
)
DOCS_PATHS = ("/docs", "/redoc")


def content_security_policy(path: str) -> bytes:
    """Return the policy for a path: a looser one only for the documentation pages."""
    if path.startswith(DOCS_PATHS):
        return DOCS_CONTENT_SECURITY_POLICY
    return API_CONTENT_SECURITY_POLICY


def _declared_size(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


class RequestContextMiddleware:
    """Wrap every HTTP request with the context described in the module docstring."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_holder = {"code": 500}

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.extend(_SECURITY_HEADERS)
                headers.append((b"content-security-policy", content_security_policy(scope["path"])))
                headers.append((b"x-request-id", request_id.encode()))
                if scope["path"].startswith("/api/"):
                    headers.append(_NO_STORE)
                message["headers"] = headers
            await send(message)

        limit = get_settings().max_upload_bytes + _SIZE_ALLOWANCE_BYTES
        size = _declared_size(scope)
        try:
            if size is not None and size > limit:
                await _send_too_large(send_with_headers, request_id)
            else:
                await self.app(scope, receive, send_with_headers)
        finally:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_holder["code"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )


async def _send_too_large(send: Send, request_id: str) -> None:
    body = json.dumps({"detail": "The request is too large.", "request_id": request_id}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
