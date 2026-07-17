"""Request and response models for Telegram publishing endpoints."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PublishTarget = Literal["default", "custom"]
_TARGET_PATTERN = re.compile(r"^(?:@[A-Za-z0-9_]{5,32}|-?\d{1,20})$")


class TelegramPublishRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    target: PublishTarget = "default"
    chat_id: str | None = Field(default=None, min_length=2, max_length=128)
    parse_mode: Literal["Markdown", "MarkdownV2", "HTML"] | None = None
    disable_web_page_preview: bool = False
    disable_notification: bool = False

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, value: str | None) -> str | None:
        if value is not None and not _TARGET_PATTERN.fullmatch(value):
            raise ValueError("chat_id must be a Telegram @channel username or numeric chat ID")
        return value

    @model_validator(mode="after")
    def validate_custom_target(self) -> TelegramPublishRequest:
        if self.target == "custom" and not self.chat_id:
            raise ValueError("chat_id is required when target is custom")
        if self.target == "default" and self.chat_id is not None:
            raise ValueError("chat_id must be omitted when target is default")
        return self


class TelegramPublishResponse(BaseModel):
    ok: bool
    chat_id: str
    message_id: int | None = None
