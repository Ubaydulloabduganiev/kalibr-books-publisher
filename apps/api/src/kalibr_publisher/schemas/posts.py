"""Schemas for manual posts, media, and scheduling."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MediaKind = Literal["photo", "video", "animation", "document"]
ScheduleMode = Literal["once", "recurring"]
ParseMode = Literal["Markdown", "MarkdownV2", "HTML"]
_TARGET_PATTERN = re.compile(r"^(?:@[A-Za-z0-9_]{5,32}|-?\d{1,20})$")


class MediaItem(BaseModel):
    kind: MediaKind
    path: str = Field(min_length=1, max_length=512)

    @field_validator("path")
    @classmethod
    def validate_managed_path(cls, value: str) -> str:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "media":
            raise ValueError("media path must be a relative path inside the media directory")
        return path.as_posix()


class ScheduleIn(BaseModel):
    mode: ScheduleMode = "once"
    run_at: datetime | None = None
    every_hours: int | None = Field(default=None, ge=1, le=8760)
    end_at: datetime | None = None

    @field_validator("run_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("scheduled timestamps must include a timezone offset")
        return value

    @model_validator(mode="after")
    def validate_schedule(self) -> ScheduleIn:
        if self.run_at is None:
            raise ValueError("run_at is required for every schedule")
        if self.mode == "recurring" and self.every_hours is None:
            raise ValueError("every_hours is required for recurring schedules")
        if self.mode == "once" and self.every_hours is not None:
            raise ValueError("every_hours is valid only for recurring schedules")
        if self.run_at and self.end_at and self.end_at <= self.run_at:
            raise ValueError("end_at must be later than run_at")
        return self

    def to_store_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "every_hours": self.every_hours,
            "end_at": self.end_at.isoformat() if self.end_at else None,
        }


class ScheduleOut(ScheduleIn):
    next_run: datetime | None = None


class PostCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    media: list[MediaItem] = Field(default_factory=list, max_length=10)
    target: str | None = Field(default=None, min_length=2, max_length=128)
    parse_mode: ParseMode | None = None
    schedule: ScheduleIn

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str | None) -> str | None:
        if value is not None and not _TARGET_PATTERN.fullmatch(value):
            raise ValueError("target must be a Telegram @channel username or numeric chat ID")
        return value

    @model_validator(mode="after")
    def validate_telegram_limits(self) -> PostCreate:
        if self.media and len(self.text) > 1024:
            raise ValueError("Telegram media captions cannot exceed 1024 characters")
        if len(self.media) > 1 and any(item.kind not in {"photo", "video"} for item in self.media):
            raise ValueError("Telegram albums can contain only photos and videos")
        return self


class PostOut(BaseModel):
    id: str
    text: str
    media: list[MediaItem]
    target: str | None
    parse_mode: ParseMode | None
    schedule: ScheduleOut
    status: str
    created_at: str
    sent_at: str | None
    last_error: str | None
    send_count: int
