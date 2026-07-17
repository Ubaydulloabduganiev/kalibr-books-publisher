"""Single-process background scheduler for the current file-store phase."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import structlog

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.store import due_posts
from kalibr_publisher.integrations.telegram import TelegramClient
from kalibr_publisher.services.publisher import publish_post

logger = structlog.get_logger(__name__)
_scheduler_task: asyncio.Task[None] | None = None


async def _tick(settings: Settings | None = None, tg_client: TelegramClient | None = None) -> None:
    resolved_settings = settings or get_settings()
    for post in due_posts():
        try:
            await publish_post(post, settings=resolved_settings, tg_client=tg_client)
        except Exception as exc:  # Defensive boundary: one bad post must not stop the scheduler.
            logger.exception(
                "scheduler_dispatch_error", post_id=post.id, exception_type=type(exc).__name__
            )


async def scheduler_loop(settings: Settings) -> None:
    interval = settings.scheduler_poll_seconds
    logger.info("scheduler_started", interval_seconds=interval)
    try:
        while True:
            try:
                await _tick(settings)
            except Exception as exc:
                logger.exception("scheduler_tick_failed", exception_type=type(exc).__name__)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        raise
    finally:
        logger.info("scheduler_stopped")


def start_scheduler(settings: Settings) -> asyncio.Task[None]:
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return _scheduler_task
    _scheduler_task = asyncio.get_running_loop().create_task(
        scheduler_loop(settings), name="kalibr-scheduler"
    )
    return _scheduler_task


async def stop_scheduler(task: asyncio.Task[None] | None = None) -> None:
    global _scheduler_task
    current = task or _scheduler_task
    if current is None:
        return
    current.cancel()
    with suppress(asyncio.CancelledError):
        await current
    if current is _scheduler_task:
        _scheduler_task = None
