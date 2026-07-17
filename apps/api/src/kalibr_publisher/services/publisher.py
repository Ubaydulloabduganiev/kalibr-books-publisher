"""Manual Telegram post publishing orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import Post, advance_recurring, claim_post, update_post
from kalibr_publisher.integrations.telegram import TelegramClient

logger = structlog.get_logger(__name__)


def _resolve_media_path(settings: Settings, stored_path: str) -> Path:
    candidate = Path(stored_path)
    if not candidate.is_absolute():
        candidate = settings.storage_root / candidate
    resolved = candidate.resolve()
    storage_root = settings.storage_root.resolve()
    if resolved != storage_root and storage_root not in resolved.parents:
        raise ApiError(
            status_code=400,
            code="invalid_media_path",
            message="A post references media outside the managed storage directory.",
            recovery_suggestion="Remove the media and upload it again through the media library.",
        )
    if not resolved.is_file():
        raise ApiError(
            status_code=409,
            code="media_missing",
            message="A media file required by this post is missing.",
            recovery_suggestion="Restore the media file or replace it before publishing.",
        )
    return resolved


def _mark_failure(post: Post, exc: ApiError) -> dict[str, Any]:
    post.status = "delivery_uncertain" if exc.code == "telegram_delivery_uncertain" else "failed"
    post.last_error = exc.message
    update_post(post)
    logger.error("publish_failed", post_id=post.id, code=exc.code, status=post.status)
    return {"ok": False, "post_id": post.id, "error": exc.message, "status": post.status}


async def publish_post(
    post: Post,
    *,
    settings: Settings | None = None,
    tg_client: TelegramClient | None = None,
) -> dict[str, Any]:
    """Publish the exact text and media supplied by the marketing team."""
    resolved_settings = settings or get_settings()
    if post.status == "pending":
        claimed = claim_post(post.id)
        if claimed is None:
            return {
                "ok": False,
                "post_id": post.id,
                "error": "The post is no longer pending.",
                "status": "skipped",
            }
        post = claimed
    elif post.status != "publishing":
        return {
            "ok": False,
            "post_id": post.id,
            "error": "The post is not in a publishable state.",
            "status": "skipped",
        }

    target = post.target or resolved_settings.telegram_default_channel
    telegram = tg_client or TelegramClient(resolved_settings)

    try:
        media = [
            {"kind": item.kind, "path": str(_resolve_media_path(resolved_settings, item.path))}
            for item in post.media
        ]
        if len(media) == 1:
            item = media[0]
            senders = {
                "photo": telegram.send_photo,
                "video": telegram.send_video,
                "animation": telegram.send_animation,
                "document": telegram.send_document,
            }
            sender = senders.get(item["kind"])
            if sender is None:
                raise ApiError(
                    status_code=400,
                    code="unsupported_media_kind",
                    message="The post contains an unsupported media type.",
                    recovery_suggestion="Remove the media and upload a supported file.",
                )
            result = await sender(
                item["path"], caption=post.text, chat_id=target, parse_mode=post.parse_mode
            )
        elif media:
            if any(item["kind"] not in {"photo", "video"} for item in media):
                raise ApiError(
                    status_code=400,
                    code="unsupported_album_media",
                    message="Telegram albums can contain only photos and videos.",
                    recovery_suggestion="Publish documents and GIF animations as separate posts.",
                )
            result = await telegram.send_album(
                media, chat_id=target, caption=post.text, parse_mode=post.parse_mode
            )
        else:
            result = await telegram.send_message(
                post.text, chat_id=target, parse_mode=post.parse_mode
            )
    except ApiError as exc:
        return _mark_failure(post, exc)
    except Exception as exc:
        logger.exception(
            "publish_unexpected_failure", post_id=post.id, exception_type=type(exc).__name__
        )
        return _mark_failure(
            post,
            ApiError(
                status_code=500,
                code="publisher_internal_error",
                message="The post could not be published because of an internal error.",
                recovery_suggestion="Inspect the server logs before retrying the post.",
            ),
        )

    advance_recurring(post)
    post.last_error = None
    update_post(post)
    logger.info("publish_succeeded", post_id=post.id, message_id=result.message_id)
    return {
        "ok": True,
        "post_id": post.id,
        "chat_id": result.chat_id,
        "message_id": result.message_id,
    }
