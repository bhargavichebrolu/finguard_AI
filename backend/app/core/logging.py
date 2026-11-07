"""Structured JSON logging. Request bodies are never logged, so inputs and passwords stay out."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_EXTRA_FIELDS = ("request_id", "method", "path", "status_code", "duration_ms", "user_id")


class JsonFormatter(logging.Formatter):
    """Write each log record as one JSON object, which log services can search."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Send application logs to standard output as JSON, replacing any existing handlers."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("finguard")
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
