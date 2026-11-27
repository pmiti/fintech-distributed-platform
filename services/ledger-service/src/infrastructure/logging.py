"""Structured JSON logging with request correlation."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# One value per asyncio task, so concurrent requests never see each other's ID.
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Optional fields callers may attach through logger.info(..., extra={...}).
_EXTRA_FIELDS = ("method", "path", "status_code", "duration_ms")


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        payload.update(
            {key: record.__dict__[key] for key in _EXTRA_FIELDS if key in record.__dict__}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(service_name: str, level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Route uvicorn's own logs through the JSON handler too.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
