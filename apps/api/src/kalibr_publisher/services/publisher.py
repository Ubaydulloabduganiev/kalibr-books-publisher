"""Post publishing orchestrator.

Ties together: AI caption rewrite/translate, optional time/order suggestions,
and the actual Telegram send (text or media album).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import structlog

from kalibr_publisher.core.config import get_settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import MediaRef, Post, advance_recurring, update_post
from kalibr_publisher.integrations.gemini import GeminiClient
from kalibr_publisher.integrations.telegram import TelegramClient

logger = structlog.get_logger(__name__)


async def publish_post(post: Post, *, settings=None, tg_client=None, gemini_client=None) -> dict[str, Any]:
    """Run AI + send the post to Telegram. Returns a result dict.

    Steps:
      1. If AI enabled and post.ai.rewrite -> rewrite/translate caption via Gemini.
      2. Build media list (photos/videos) from post.media paths.
      3. Send via Telegram (album if media present, else text message).
      4. Update post status (sent / advance recurring / failed).
    """
    settings = settings or get_settings()
    target = post.target or settings.telegram_default_channel
    caption = post.text
    parse_mode = post.parse_mode

    # 1) AI caption rewrite
    if getattr(settings, "ai_enabled", True) and post.ai.rewrite:
        try:
            g = gemini_client or GeminiClient(settings=settings)
            res = g.rewrite_caption(post.text, language=post.ai.language or settings.ai_caption_language)
            caption = res.text
            parse_mode = res.parse_mode or parse_mode
            logger.info("ai_caption_rewritten", post_id=post.id)
        except ApiError as ex:
            logger.warning("ai_rewrite_failed_fallback", post_id=post.id, error=ex.message)
            # fall back to original text

    # 2) media
    media_items = []
    missing = []
    for m in post.media:
        if os.path.exists(m.path):
            media_items.append({"kind": m.kind, "path": m.path})
        else:
            missing.append(m.path)
    if missing:
        logger.warning("media_missing", post_id=post.id, missing=missing)

    # 3) send
    tg = tg_client or TelegramClient(settings)
    try:
        if media_items:
            if len(media_items) == 1:
                m = media_items[0]
                if m["kind"] == "photo":
                    result = await tg.send_photo(m["path"], caption=caption, chat_id=target, parse_mode=parse_mode)
                else:
                    result = await tg.send_video(m["path"], caption=caption, chat_id=target, parse_mode=parse_mode)
            else:
                result = await tg.send_album(media_items, chat_id=target, caption=caption, parse_mode=parse_mode)
        else:
            result = await tg.send_message(caption, chat_id=target, parse_mode=parse_mode)
    except ApiError as ex:
        post.status = "failed"
        post.last_error = ex.message
        update_post(post)
        logger.error("publish_failed", post_id=post.id, error=ex.message)
        return {"ok": False, "post_id": post.id, "error": ex.message}

    # 4) mark sent / advance
    # advance_recurring owns status: non-recurring -> "sent", recurring -> "pending"
    advance_recurring(post)
    if post.status == "sent":
        post.sent_at = datetime.now(timezone.utc).isoformat()
    post.last_error = None
    update_post(post)
    logger.info("publish_ok", post_id=post.id, message_id=result.message_id)
    return {"ok": True, "post_id": post.id, "chat_id": result.chat_id, "message_id": result.message_id}


def order_posts_with_ai(posts: list[Post], gemini_client: GeminiClient | None = None) -> list[Post]:
    """Return posts reordered by AI suggestion (if enabled)."""
    if not posts:
        return posts
    settings = get_settings()
    if not getattr(settings, "ai_enabled", True):
        return posts
    any_order = any(p.ai.choose_order for p in posts)
    if not any_order:
        return posts
    try:
        g = gemini_client or GeminiClient(settings=settings)
        briefs = [{"text": p.text} for p in posts]
        order = g.choose_order(briefs)
        ordered = [posts[i] for i in order if 0 <= i < len(posts)]
        # append any not returned
        seen = set(order)
        ordered += [p for i, p in enumerate(posts) if i not in seen]
        return ordered
    except ApiError as ex:
        logger.warning("ai_order_failed", error=ex.message)
        return posts
