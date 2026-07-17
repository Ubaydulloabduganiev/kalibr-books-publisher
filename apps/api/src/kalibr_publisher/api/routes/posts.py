"""Manual post, media upload, and scheduling endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from kalibr_publisher.api.deps import get_app_settings, require_internal_api_key
from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import (
    MediaRef,
    Post,
    PostDraft,
    Schedule,
    create_post,
    create_posts,
    delete_post,
    get_post,
    list_posts,
    update_post,
)
from kalibr_publisher.schemas.posts import PostCreate, PostOut, ScheduleIn

logger = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/posts",
    tags=["posts"],
    dependencies=[Depends(require_internal_api_key)],
)

_ALLOWED_MEDIA: dict[str, tuple[str, set[str]]] = {
    ".jpg": ("photo", {"image/jpeg"}),
    ".jpeg": ("photo", {"image/jpeg"}),
    ".png": ("photo", {"image/png"}),
    ".webp": ("photo", {"image/webp"}),
    ".gif": ("animation", {"image/gif"}),
    ".mp4": ("video", {"video/mp4", "application/octet-stream"}),
    ".mov": ("video", {"video/quicktime", "application/octet-stream"}),
    ".webm": ("video", {"video/webm", "application/octet-stream"}),
    ".pdf": ("document", {"application/pdf", "application/octet-stream"}),
    ".doc": ("document", {"application/msword", "application/octet-stream"}),
    ".docx": (
        "document",
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        },
    ),
}


def _to_out(post: Post) -> PostOut:
    return PostOut.model_validate(
        {
            "id": post.id,
            "text": post.text,
            "media": [{"kind": item.kind, "path": item.path} for item in post.media],
            "target": post.target,
            "parse_mode": post.parse_mode,
            "schedule": {
                "mode": post.schedule.mode,
                "run_at": post.schedule.run_at,
                "every_hours": post.schedule.every_hours,
                "end_at": post.schedule.end_at,
                "next_run": post.schedule.next_run,
            },
            "status": post.status,
            "created_at": post.created_at,
            "sent_at": post.sent_at,
            "last_error": post.last_error,
            "send_count": post.send_count,
        }
    )


def _has_expected_signature(extension: str, header: bytes) -> bool:
    checks = {
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        ".gif": header.startswith((b"GIF87a", b"GIF89a")),
        ".webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
        ".pdf": header.startswith(b"%PDF-"),
        ".doc": header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".docx": header.startswith(b"PK\x03\x04"),
        ".webm": header.startswith(b"\x1aE\xdf\xa3"),
        ".mp4": len(header) >= 12 and header[4:8] == b"ftyp",
        ".mov": len(header) >= 12 and header[4:8] == b"ftyp",
    }
    return checks.get(extension, True)


def _schedule(payload: ScheduleIn) -> Schedule:
    return Schedule(**payload.to_store_dict())


@router.post("/upload", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: Annotated[UploadFile, File()],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, Any]:
    """Stream one supported media file to persistent storage."""
    extension = Path(file.filename or "").suffix.lower()
    definition = _ALLOWED_MEDIA.get(extension)
    if definition is None:
        raise HTTPException(status_code=400, detail="Unsupported media type")
    kind, allowed_mime = definition
    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in allowed_mime:
        raise HTTPException(
            status_code=400, detail="File content type does not match its extension"
        )

    settings.media_root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = settings.media_root / filename
    temporary = settings.media_root / f".upload-{uuid.uuid4().hex}.part"
    limit = settings.max_upload_mb * 1024 * 1024
    total = 0
    header = bytearray()

    try:
        with temporary.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.max_upload_mb} MB limit",
                    )
                if len(header) < 32:
                    header.extend(chunk[: 32 - len(header)])
                output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if not _has_expected_signature(extension, bytes(header)):
            raise HTTPException(
                status_code=400, detail="File signature does not match its extension"
            )
        temporary.replace(destination)
    finally:
        await file.close()
        temporary.unlink(missing_ok=True)

    relative_path = destination.relative_to(settings.storage_root).as_posix()
    logger.info("media_uploaded", kind=kind, size_bytes=total, path=relative_path)
    return {"path": relative_path, "kind": kind, "size": total}


class BulkCreate(BaseModel):
    posts: list[PostCreate] = Field(min_length=1, max_length=100)


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_one(payload: PostCreate) -> PostOut:
    post = create_post(
        text=payload.text,
        target=payload.target,
        parse_mode=payload.parse_mode,
        media=[MediaRef(kind=item.kind, path=item.path) for item in payload.media],
        schedule=_schedule(payload.schedule),
    )
    return _to_out(post)


@router.post("/bulk", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_bulk(payload: BulkCreate) -> dict[str, Any]:
    posts = create_posts(
        [
            PostDraft(
                text=item.text,
                target=item.target,
                parse_mode=item.parse_mode,
                media=[MediaRef(kind=media.kind, path=media.path) for media in item.media],
                schedule=_schedule(item.schedule),
            )
            for item in payload.posts
        ]
    )
    return {"created": len(posts), "ids": [post.id for post in posts]}


@router.get("", response_model=dict[str, Any])
async def list_all(
    status_filter: str | None = Query(default=None, alias="status"),
) -> dict[str, Any]:
    posts = list_posts(status_filter)
    return {"count": len(posts), "posts": [_to_out(post) for post in posts]}


@router.get("/{post_id}", response_model=PostOut)
async def get_one(post_id: str) -> PostOut:
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_out(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(post_id: str) -> None:
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == "publishing":
        raise ApiError(
            status_code=409,
            code="post_is_publishing",
            message="The post is currently being published and cannot be deleted.",
            recovery_suggestion="Wait for the delivery result, then retry if needed.",
        )
    if post.status in {"sent", "delivery_uncertain"}:
        raise ApiError(
            status_code=409,
            code="post_history_protected",
            message="This post is part of the delivery history and cannot be deleted.",
            recovery_suggestion="Keep the record until archive support is available.",
        )
    delete_post(post_id)


@router.post("/{post_id}/schedule", response_model=PostOut)
async def reschedule(post_id: str, schedule: ScheduleIn) -> PostOut:
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == "publishing":
        raise ApiError(
            status_code=409,
            code="post_is_publishing",
            message="The post is currently being published and cannot be rescheduled.",
            recovery_suggestion="Wait for the delivery result, then retry if needed.",
        )
    if post.status == "sent":
        raise ApiError(
            status_code=409,
            code="post_already_published",
            message="A published post cannot be rescheduled in place.",
            recovery_suggestion="Duplicate the post before scheduling another publication.",
        )
    post.schedule = _schedule(schedule)
    post.status = "pending"
    post.last_error = None
    update_post(post)
    return _to_out(post)
