"""Telegram publishing endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from kalibr_publisher.api.deps import TelegramClientDep
from kalibr_publisher.schemas.telegram import (
    TelegramPublishRequest,
    TelegramPublishResponse,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post(
    "/publish",
    response_model=TelegramPublishResponse,
    summary="Publish a message to a Telegram channel",
)
async def publish_to_telegram(
    payload: TelegramPublishRequest,
    client: TelegramClientDep,
) -> TelegramPublishResponse:
    """Send ``payload.text`` to the resolved Telegram channel."""
    chat_id = payload.chat_id if payload.target == "custom" else None
    result = await client.send_message(
        payload.text,
        chat_id=chat_id,
        parse_mode=payload.parse_mode,
        disable_web_page_preview=payload.disable_web_page_preview,
    )
    return TelegramPublishResponse(
        ok=result.ok,
        chat_id=result.chat_id,
        message_id=result.message_id,
    )
