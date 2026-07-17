"""Telegram publishing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kalibr_publisher.api.deps import TelegramClientDep, require_internal_api_key
from kalibr_publisher.schemas.telegram import TelegramPublishRequest, TelegramPublishResponse

router = APIRouter(
    prefix="/telegram",
    tags=["telegram"],
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("/publish", response_model=TelegramPublishResponse)
async def publish_to_telegram(
    payload: TelegramPublishRequest, client: TelegramClientDep
) -> TelegramPublishResponse:
    result = await client.send_message(
        payload.text,
        chat_id=payload.chat_id if payload.target == "custom" else None,
        parse_mode=payload.parse_mode,
        disable_web_page_preview=payload.disable_web_page_preview,
        disable_notification=payload.disable_notification,
    )
    return TelegramPublishResponse(
        ok=result.ok, chat_id=result.chat_id, message_id=result.message_id
    )
