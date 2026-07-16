"""Low-overhead ASGI middleware for tracing, logs, and security headers."""

from __future__ import annotations

import re
import time
from typing import Final
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars

_REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
logger = structlog.get_logger(__name__)


class RequestContextMiddleware:
    """Attach a safe request ID and emit one structured access log per request."""

    def __init__(self, app: ASGIApp, request_id_header: str = "X-Request-ID") -> None:
        self.app = app
        self.request_id_header = request_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        candidate = headers.get(self.request_id_header)
        request_id = (
            candidate if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex
        )
        started_at = time.perf_counter()
        status_code = 500

        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            method=scope["method"],
            path=scope["path"],
        )

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = MutableHeaders(scope=message)
                response_headers[self.request_id_header] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        except Exception:
            logger.exception("request_failed", status_code=500)
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request_completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
            clear_contextvars()


class SecurityHeadersMiddleware:
    """Add API-safe browser security headers to every HTTP response."""

    _HEADERS: Final[dict[str, str]] = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self._HEADERS.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
