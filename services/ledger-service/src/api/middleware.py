"""X-Correlation-ID propagation and request logging (pure ASGI middleware)."""

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.infrastructure.logging import correlation_id_var

CORRELATION_ID_HEADER = "X-Correlation-ID"
# Client-provided values end up in logs and headers, so restrict them.
_VALID_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(CORRELATION_ID_HEADER, "")
        correlation_id = incoming if _VALID_ID.fullmatch(incoming) else str(uuid4())
        token = correlation_id_var.set(correlation_id)
        started_at = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_header(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        try:
            await self._app(scope, receive, send_with_header)
        except Exception:
            # Handled here so that 500 responses and their logs keep the ID.
            logger.exception("Unhandled error")
            if response_started:
                raise
            response = JSONResponse({"detail": "Internal server error"}, 500)
            await response(scope, receive, send_with_header)
        finally:
            logger.info(
                "Request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            correlation_id_var.reset(token)
