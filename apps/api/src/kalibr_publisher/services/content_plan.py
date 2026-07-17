"""Content-plan processing: turn an uploaded CSV into scheduled AI-generated posts.

Expected CSV columns (header row required):
    text          - the post copy (used to generate the caption)
    image_prompt  - prompt for the AI image (may be empty to skip image)
    schedule      - ISO datetime (e.g. 2026-07-20T09:00:00+05:00) for a one-off post,
                    or "EVERY 3h" / "EVERY 24h" for a recurring post

For every row we:
    1. ask Gemini to rewrite ``text`` into an engaging caption (HTML),
    2. ask Gemini to generate an image from ``image_prompt`` (if provided),
    3. persist the image under ``media_root``,
    4. create a scheduled Post.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import MediaRef, PostDraft, Schedule, create_posts
from kalibr_publisher.integrations.gemini import GeminiClient

logger = structlog.get_logger(__name__)

_MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _parse_schedule(value: str) -> Schedule:
    value = (value or "").strip()
    if not value:
        return Schedule(mode="once", run_at=datetime.now(UTC).isoformat())
    low = value.lower()
    if low.startswith("every"):
        try:
            hours = int(low.split()[1].rstrip("h"))
        except (IndexError, ValueError):
            raise ApiError(
                status_code=400,
                code="bad_schedule",
                message=f"Invalid recurring schedule: '{value}'. Use e.g. 'EVERY 3h'.",
            )
        return Schedule(mode="recurring", run_at=datetime.now(UTC).isoformat(), every_hours=hours)
    # treat as one-off ISO datetime
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ApiError(
            status_code=400,
            code="bad_schedule",
            message=f"Invalid schedule timestamp: '{value}'. Use ISO8601.",
        )
    return Schedule(mode="once", run_at=value)


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    required = {"text", "image_prompt", "schedule"}
    if reader.fieldnames is None or not required.issubset({f.lower() for f in reader.fieldnames}):
        raise ApiError(
            status_code=400,
            code="bad_content_plan",
            message="CSV must have columns: text, image_prompt, schedule",
            recovery_suggestion="Add a header row with those three columns.",
        )
    rows: list[dict[str, str]] = []
    for row in reader:
        norm = {k.lower(): (v or "").strip() for k, v in row.items()}
        rows.append(norm)
    if not rows:
        raise ApiError(status_code=400, code="empty_content_plan", message="Content plan has no rows.")
    return rows


def process_content_plan(content: bytes, settings: Settings | None = None) -> dict[str, Any]:
    """Parse, generate, and schedule all posts from a CSV content plan."""
    settings = settings or get_settings()
    if not getattr(settings, "ai_enabled", True) or not settings.gemini_api_key:
        raise ApiError(
            status_code=503,
            code="ai_not_configured",
            message="AI generation is disabled or GEMINI_API_KEY is not set.",
            recovery_suggestion="Set GEMINI_API_KEY on the API service.",
        )
    rows = parse_csv(content)
    gemini = GeminiClient(settings=settings)
    media_root: Path = settings.media_root
    media_root.mkdir(parents=True, exist_ok=True)
    lang = getattr(settings, "ai_caption_language", "uz")

    created: list[dict[str, Any]] = []
    drafts: list[PostDraft] = []
    for index, row in enumerate(rows):
        caption_text = row.get("text", "")
        image_prompt = row.get("image_prompt", "")
        try:
            caption = gemini.rewrite_caption(caption_text, language=lang).text
        except ApiError as ex:
            logger.warning("ai_caption_failed", row=index, error=ex.message)
            caption = caption_text  # fall back to original text
        media: list[MediaRef] = []
        if image_prompt:
            try:
                img = gemini.generate_image(image_prompt)
                ext = _MIME_EXT.get(img.mime_type, ".png")
                fname = f"{uuid.uuid4().hex}{ext}"
                (media_root / fname).write_bytes(img.data)
                media.append(MediaRef(kind="photo", path=f"{media_root.as_posix()}/{fname}"))
            except ApiError as ex:
                logger.warning("ai_image_failed", row=index, error=ex.message)
        schedule = _parse_schedule(row.get("schedule", ""))
        drafts.append(
            PostDraft(text=caption, media=media, target=None, parse_mode="HTML", schedule=schedule)
        )
        created.append(
            {
                "row": index,
                "caption": caption[:120],
                "media_count": len(media),
                "mode": schedule.mode,
            }
        )
    posts = create_posts(drafts)
    return {"count": len(posts), "items": created}
