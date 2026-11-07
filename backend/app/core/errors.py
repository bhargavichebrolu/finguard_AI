"""Application errors, and handlers that turn every failure into a safe JSON response.

Clients get a clear message and a request ID. Stack traces and submitted values stay out of
responses, and unexpected errors are logged on the server only.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("finguard.errors")


class AppError(Exception):
    """Base class for an expected failure with a message that is safe to show."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers


class NotFoundError(AppError):
    """The requested record does not exist, or this user may not know that it exists."""

    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    """The request clashes with existing data, such as a repeated transaction identifier."""

    status_code = status.HTTP_409_CONFLICT


class AuthenticationError(AppError):
    """The caller did not prove who they are."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class PermissionDeniedError(AppError):
    """The caller is known but this role may not do this."""

    status_code = status.HTTP_403_FORBIDDEN


class InvalidInputError(AppError):
    """The request is well formed but its content is not acceptable."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class PayloadTooLargeError(AppError):
    """An upload exceeds the configured limit."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class RateLimitedError(AppError):
    """Too many requests in the current window."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            "Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after_seconds)},
        )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _safe_validation_errors(error: RequestValidationError) -> list[dict[str, Any]]:
    """Keep where and why validation failed, and drop the submitted value, such as a password."""
    return [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handlers that define the API's error format."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.message, "request_id": _request_id(request)},
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "The request is not valid.",
                "errors": _safe_validation_errors(error),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "request_id": _request_id(request)},
            headers=error.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
            exc_info=error,
            extra={"request_id": _request_id(request)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error.", "request_id": _request_id(request)},
        )
