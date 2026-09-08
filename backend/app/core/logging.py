"""Structured logging with request correlation.

Every log record carries the correlation id of the request that produced it, so
a learner-reported failure can be traced end to end. In production the
formatter emits JSON for ingestion by a log aggregator; locally it emits a
compact human-readable line.

This module is also the subject of the *Logging & Observability* curriculum
module — it is written to be worth reading.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.core.config import get_settings

#: Correlation id for the in-flight request, set by ``CorrelationIdMiddleware``.
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

#: Keys present on every ``LogRecord``; anything else is treated as structured extra.
_RESERVED = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class CorrelationIdFilter(logging.Filter):
    """Attach the current correlation id to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True always; the record is mutated in place."""
        record.correlation_id = correlation_id.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialise ``record`` including any structured ``extra`` fields."""
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key != "correlation_id":
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Readable single-line output for local development."""

    _FMT = "%(asctime)s %(levelname)-7s [%(correlation_id)s] %(name)s: %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt="%H:%M:%S")


def configure_logging() -> None:
    """Install the root logging configuration. Idempotent."""
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_json else ConsoleFormatter())
    handler.addFilter(CorrelationIdFilter())
    root.addHandler(handler)

    # Uvicorn installs its own handlers; route them through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)
