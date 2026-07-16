"""Shared API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from kalibr_publisher.core.config import Settings
from kalibr_publisher.integrations.telegram import TelegramClient


def get_settings(request: Request) -> Settings:
    """Return validated application settings stored on the app state."""
    value = request.app.state.settings
    if not isinstance(value, Settings):
        msg = "Application settings are unavailable"
        raise RuntimeError(msg)
    return value


def get_telegram_client(request: Request) -> TelegramClient:
    """Provide a Telegram client bound to the current request's settings."""
    return TelegramClient(get_settings(request))


TelegramClientDep = Annotated[TelegramClient, Depends(get_telegram_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
