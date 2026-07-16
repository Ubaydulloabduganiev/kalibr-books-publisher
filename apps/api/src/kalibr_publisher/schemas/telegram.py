"""Request and response models for Telegram publishing endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PublishTarget = Literal["default", "custom"]


class TelegramPublishRequest(BaseModel):
    """Payload for publishing a message to a Telegram channel."""

    text: str = Field(
        min_length=1,
        max_length=4096,
        description="Message body. Markdown is supported when parse_mode is set.",
    )
    target: PublishTarget = Field(default="default")
    chat_id: str | None = Field(
        default=None,
        description="Required when target is 'custom'. A channel username or numeric id.",
    )
    parse_mode: Literal["Markdown", "MarkdownV2", "HTML"] | None = Field(default=None)
    disable_web_page_preview: bool = Field(default=False)


class TelegramPublishResponse(BaseModel):
    """Result returned after a publish attempt."""

    ok: bool
    chat_id: str
    message_id: int | None = None
