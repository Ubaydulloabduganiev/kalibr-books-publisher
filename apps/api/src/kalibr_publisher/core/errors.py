"""Consistent public error responses and exception handlers."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from structlog.contextvars import get_contextvars

from kalibr_publisher.core.config import Settings

logger = structlog.get_logger(__name__)


class ErrorDetail(BaseModel):
    """Public error information returned by every API failure."""

    code: str
    message: str
    technical_details: Any | None = None
    recovery_suggestion: str
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    """Top-level API error envelope."""

    error: ErrorDetail


class ApiError(Exception):
    """Expected service-layer failure safe to expose to API clients."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        recovery_suggestion: str,
        technical_details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.recovery_suggestion = recovery_suggestion
        self.technical_details = technical_details


def _request_id() -> str | None:
    value = get_contextvars().get("request_id")
    return value if isinstance(value, str) else None


def _response(
    *,
    status_code: int,
    code: str,
    message: str,
    recovery_suggestion: str,
    technical_details: Any | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            technical_details=technical_details,
            recovery_suggestion=recovery_suggestion,
            request_id=_request_id(),
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Install handlers without leaking sensitive internals in production."""

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        logger.warning("api_error", code=exc.code, status_code=exc.status_code)
        return _response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            recovery_suggestion=exc.recovery_suggestion,
            technical_details=exc.technical_details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _response(
            status_code=422,
            code="validation_error",
            message="The request contains invalid or missing values.",
            recovery_suggestion="Correct the highlighted fields and submit the request again.",
            technical_details=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = (
            exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        )
        return _response(
            status_code=exc.status_code,
            code=f"http_{exc.status_code}",
            message=detail,
            recovery_suggestion="Verify the request URL and permissions, then try again.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", exception_type=type(exc).__name__)
        technical_details = None
        if not settings.is_production:
            technical_details = {"exception_type": type(exc).__name__}
        return _response(
            status_code=500,
            code="internal_server_error",
            message="The server encountered an unexpected error.",
            recovery_suggestion=(
                "Retry once. If the problem continues, provide the request ID to the administrator."
            ),
            technical_details=technical_details,
        )
