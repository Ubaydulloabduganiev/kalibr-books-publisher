"""Content-plan automation agent.

Given a parsed content plan, expands each item into a complete post:
  1. generate a supporting image via Gemini (text-to-image),
  2. generate an engaging caption via Gemini (in the channel language),
  3. create a scheduled Post (staggered so posts don't all fire at once).

The scheduler (already running in the API) then sends each post to the
configured Telegram channel at its scheduled time.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.store import MediaRef, Schedule, create_post
from kalibr_publisher.integrations.gemini import GeminiClient
from kalibr_publisher.integrations.gemini_image import GeminiImageClient
from kalibr_publisher.services.document_parser import ParsedPlan, PlanItem

logger = structlog.get_logger(__name__)

# Stagger auto-scheduled posts this far apart (hours) unless the plan hints times.
DEFAULT_STAGGER_HOURS = 24
MAX_ITEMS = 50


def _image_prompt(item: PlanItem, language: str) -> str:
    return (
        f"Editorial social-media illustration for an English-learning book brand "
        f"(Kalibr Books). Subject: {item.title}. "
        f"Style: clean, minimalist, warm beige and forest-green palette, "
        f"flat vector, no text in the image. Suitable for Telegram post."
    )


def _save_image(data: bytes, mime: str, media_root: Path) -> str:
    ext = "svg" if "svg" in mime else "png"
    media_root.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.{ext}"
    (media_root / fname).write_bytes(data)
    return f"{media_root.as_posix()}/{fname}"


def run_automation(
    plan: ParsedPlan,
    *,
    settings: Optional[Settings] = None,
    language: str = "uz",
    start_from: Optional[datetime] = None,
    stagger_hours: int = DEFAULT_STAGGER_HOURS,
) -> list[dict]:
    """Expand a parsed plan into scheduled posts. Returns created post summaries."""
    settings = settings or get_settings()
    gemini = GeminiClient(settings=settings)
    imager = GeminiImageClient(settings=settings)

    media_root = Path(getattr(settings, "media_root", "storage/media"))
    target = getattr(settings, "telegram_default_channel", None)
    base = start_from or (datetime.now(timezone.utc) + timedelta(hours=1))

    created: list[dict] = []
    for idx, item in enumerate(plan.items[:MAX_ITEMS]):
        # 1) image
        img = imager.generate(_image_prompt(item, language))
        img_path = _save_image(img.data, img.mime, media_root)
        # 2) caption
        caption = gemini.rewrite_caption(item.title, language=language)
        if not caption or not caption.text.strip():
            caption_text = item.title
        else:
            caption_text = caption.text
        # 3) schedule (staggered)
        run_at = base + timedelta(hours=idx * stagger_hours)
        post = create_post(
            text=caption_text,
            media=[MediaRef(kind="photo", path=img_path)],
            target=target,
            parse_mode="HTML",
            schedule=Schedule(mode="once", run_at=run_at.isoformat()),
        )
        created.append(
            {
                "id": post.id,
                "title": item.title,
                "run_at": run_at.isoformat(),
                "image": img_path,
                "text": caption_text[:120],
            }
        )
        logger.info("automation_item_created", index=idx, title=item.title)
    return created
