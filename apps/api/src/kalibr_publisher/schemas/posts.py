"""Schemas for bulk posts, media, and scheduling."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from kalibr_publisher.core.store import AiConfig, MediaRef, Schedule


class MediaItem(BaseModel):
    kind: str = Field(..., description="'photo' or 'video'")
    path: str = Field(..., description="Server-side relative path, e.g. storage/media/uuid.jpg")


class ScheduleIn(BaseModel):
    mode: str = Field(default="once", description="'once' or 'recurring'")
    run_at: Optional[str] = Field(default=None, description="ISO8601 for once-mode.")
    every_hours: Optional[int] = Field(default=None, description="Hours between sends for recurring.")
    end_at: Optional[str] = Field(default=None, description="ISO8601 stop for recurring.")


class AiConfigIn(BaseModel):
    rewrite: bool = True
    language: str = "uz"
    choose_order: bool = True
    choose_time: bool = False


class PostCreate(BaseModel):
    text: str = Field(..., min_length=1, description="Post caption/text.")
    media: list[MediaItem] = Field(default_factory=list)
    target: Optional[str] = Field(default=None, description="Channel override; null -> default.")
    parse_mode: Optional[str] = Field(default="HTML")
    schedule: ScheduleIn = Field(default_factory=ScheduleIn)
    ai: AiConfigIn = Field(default_factory=AiConfigIn)


class PostOut(BaseModel):
    id: str
    text: str
    media: list[MediaItem]
    target: Optional[str]
    parse_mode: Optional[str]
    schedule: ScheduleIn
    ai: AiConfigIn
    status: str
    created_at: str
    sent_at: Optional[str]
    last_error: Optional[str]
    send_count: int
