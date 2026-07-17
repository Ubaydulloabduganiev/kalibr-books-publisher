"""Background scheduler worker.

Runs an asyncio loop that, every ``scheduler_poll_seconds``:
  1. finds posts whose next_run is due,
  2. optionally reorders them via AI (choose_order),
  3. dispatches each through the publisher (AI caption + Telegram send).

Start it once alongside the API (see run_worker / lifespan hook).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from kalibr_publisher.core.config import get_settings
from kalibr_publisher.core.store import due_posts
from kalibr_publisher.services.publisher import order_posts_with_ai, publish_post

logger = structlog.get_logger(__name__)

_running = False


async def _tick(tg_client=None) -> None:
    settings = get_settings()
    posts = due_posts()
    if not posts:
        return
    # AI ordering across the due batch
    ordered = order_posts_with_ai(posts)
    for post in ordered:
        try:
            await publish_post(post, settings=settings, tg_client=tg_client)
        except Exception as exc:  # noqa: BLE001
            logger.error("scheduler_dispatch_error", post_id=post.id, error=str(exc))


async def scheduler_loop() -> None:
    global _running
    _running = True
    settings = get_settings()
    interval = max(5, getattr(settings, "scheduler_poll_seconds", 30))
    logger.info("scheduler_started", interval_seconds=interval)
    try:
        while _running:
            try:
                await _tick()
            except Exception as exc:  # noqa: BLE001
                logger.error("scheduler_tick_error", error=str(exc))
            await asyncio.sleep(interval)
    finally:
        _running = False
        logger.info("scheduler_stopped")


def start_scheduler() -> asyncio.Task | None:
    """Start the scheduler as a background task on the running event loop.

    Must be called from within the running asyncio event loop (the lifespan),
    so we use ``asyncio.get_running_loop()``. Falls back gracefully if no loop
    is running so startup can never crash on this call.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (e.g. called outside the event loop) — skip scheduling.
        logger.warning("scheduler_no_running_loop")
        return None
    if _running:
        return None
    task = loop.create_task(scheduler_loop())
    logger.info("scheduler_task_created")
    return task


def stop_scheduler() -> None:
    global _running
    _running = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
