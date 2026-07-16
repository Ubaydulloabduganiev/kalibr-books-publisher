"""Bulk post + media upload + scheduling endpoints."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.store import (
    AiConfig,
    MediaRef,
    Post,
    Schedule,
    create_post,
    delete_post,
    get_post,
    list_posts,
    update_post,
)
from kalibr_publisher.schemas.posts import (
    AiConfigIn,
    MediaItem,
    PostCreate,
    PostOut,
    ScheduleIn,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/posts", tags=["posts"])


def _to_out(p: Post) -> PostOut:
    return PostOut(
        id=p.id, text=p.text, media=[MediaItem(kind=m.kind, path=m.path) for m in p.media],
        target=p.target, parse_mode=p.parse_mode,
        schedule=ScheduleIn(mode=p.schedule.mode, run_at=p.schedule.run_at,
                             every_hours=p.schedule.every_hours, end_at=p.schedule.end_at),
        ai=AiConfigIn(rewrite=p.ai.rewrite, language=p.ai.language,
                       choose_order=p.ai.choose_order, choose_time=p.ai.choose_time),
        status=p.status, created_at=p.created_at, sent_at=p.sent_at,
        last_error=p.last_error, send_count=p.send_count,
    )


@router.post("/upload", response_model=dict[str, Any])
async def upload_media(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
):
    """Upload one image/video; returns its server path + kind."""
    allowed_img = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    allowed_vid = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in allowed_img:
        kind = "photo"
    elif ext in allowed_vid:
        kind = "video"
    else:
        raise HTTPException(status_code=400, detail={"code": "bad_file_type",
            "message": "Unsupported file type.", "recovery_suggestion": "Use jpg/png or mp4/mov."})
    max_mb = getattr(settings, "max_upload_mb", 20)
    data = await file.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "file_too_large",
            "message": f"File exceeds {max_mb}MB.", "recovery_suggestion": "Compress the media."})
    media_root = Path(getattr(settings, "media_root", "storage/media"))
    media_root.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}{ext}"
    (media_root / fname).write_bytes(data)
    rel = f"{media_root.as_posix()}/{fname}"
    return {"path": rel, "kind": kind, "size": len(data)}


class BulkCreate(BaseModel):
    posts: list[PostCreate]


@router.post("", response_model=PostOut)
async def create_one(payload: PostCreate):
    """Create a single scheduled post."""
    post = create_post(
        text=payload.text,
        target=payload.target,
        media=[MediaRef(kind=m.kind, path=m.path) for m in (payload.media or [])],
        schedule=Schedule(mode=payload.schedule.mode, run_at=payload.schedule.run_at,
                          every_hours=payload.schedule.every_hours, end_at=payload.schedule.end_at),
        ai=AiConfig(rewrite=payload.ai.rewrite, language=payload.ai.language,
                    choose_order=payload.ai.choose_order, choose_time=payload.ai.choose_time),
    )
    return post.to_out()


@router.post("/bulk", response_model=dict[str, Any])
async def create_bulk(payload: BulkCreate):
    """Create many scheduled posts at once."""
    created = []
    for pc in payload.posts:
        sched = Schedule(mode=pc.schedule.mode, run_at=pc.schedule.run_at,
                         every_hours=pc.schedule.every_hours, end_at=pc.schedule.end_at)
        ai = AiConfig(rewrite=pc.ai.rewrite, language=pc.ai.language,
                      choose_order=pc.ai.choose_order, choose_time=pc.ai.choose_time)
        media = [MediaRef(kind=m.kind, path=m.path) for m in pc.media]
        post = create_post(text=pc.text, media=media, target=pc.target,
                          parse_mode=pc.parse_mode, schedule=sched, ai=ai)
        created.append(post.id)
    return {"created": len(created), "ids": created}


@router.get("", response_model=dict[str, Any])
async def list_all(status: str | None = Query(default=None)):
    posts = list_posts(status)
    return {"count": len(posts), "posts": [_to_out(p) for p in posts]}


@router.get("/{post_id}", response_model=PostOut)
async def get_one(post_id: str):
    p = get_post(post_id)
    if not p:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Post not found."})
    return _to_out(p)


@router.delete("/{post_id}", response_model=dict[str, Any])
async def remove(post_id: str):
    ok = delete_post(post_id)
    return {"deleted": ok}


@router.post("/{post_id}/schedule", response_model=PostOut)
async def reschedule(post_id: str, sched: ScheduleIn):
    p = get_post(post_id)
    if not p:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Post not found."})
    p.schedule = Schedule(mode=sched.mode, run_at=sched.run_at,
                          every_hours=sched.every_hours, end_at=sched.end_at)
    p.status = "pending" if p.status in ("failed", "sent") else p.status
    update_post(p)
    return _to_out(p)
