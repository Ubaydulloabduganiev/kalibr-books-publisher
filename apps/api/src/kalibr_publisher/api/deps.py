"""Reusable FastAPI dependencies."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, Request

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.integrations.telegram import TelegramClient


def get_app_settings(request: Request) -> Settings:
    value = request.app.state.settings
    if not isinstance(value, Settings):
        raise RuntimeError("Application settings are unavailable")
    return value


def get_telegram_client(settings: Annotated[Settings, Depends(get_app_settings)]) -> TelegramClient:
    return TelegramClient(settings)


async def require_internal_api_key(
    settings: Annotated[Settings, Depends(get_app_settings)],
    provided: Annotated[str | None, Header(alias="X-Internal-API-Key")] = None,
) -> None:
    """Protect write endpoints from direct public access."""
    expected = settings.internal_api_key_value()
    if not expected:
        if settings.is_production:
            raise ApiError(
                status_code=503,
                code="internal_gateway_not_configured",
                message="The publishing gateway is not configured.",
                recovery_suggestion="Set INTERNAL_API_KEY on both API and web services.",
            )
        return
    if not provided or not secrets.compare_digest(provided, expected):
        raise ApiError(
            status_code=401,
            code="invalid_internal_api_key",
            message="This endpoint is available only through the administration gateway.",
            recovery_suggestion="Open Kalibr Publisher and retry the action there.",
        )


TelegramClientDep = Annotated[TelegramClient, Depends(get_telegram_client)]
WriteAccessDep = Annotated[None, Depends(require_internal_api_key)]
