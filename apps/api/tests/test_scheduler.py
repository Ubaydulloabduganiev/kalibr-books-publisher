"""Scheduler tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.store import configure_store, create_post, get_post
from kalibr_publisher.services import scheduler


class FakeTelegram:
    async def send_message(self, text: str, **_: object):
        return type("Result", (), {"ok": True, "chat_id": "@kalibr_books", "message_id": 1})()


async def test_tick_publishes_due_post(tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        telegram_default_channel="@kalibr_books",
        _env_file=None,
    )
    configure_store(settings.storage_root / "posts.json")
    post = create_post(text="due")

    await scheduler._tick(settings, tg_client=FakeTelegram())

    stored = get_post(post.id)
    assert stored is not None
    assert stored.status == "sent"


async def test_scheduler_loop_survives_a_failed_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        app_env="test",
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        scheduler_poll_seconds=5,
        _env_file=None,
    )
    calls = 0

    async def flaky_tick(*_: object, **__: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary store read failure")
        raise asyncio.CancelledError

    async def no_wait(_: float) -> None:
        return None

    monkeypatch.setattr(scheduler, "_tick", flaky_tick)
    monkeypatch.setattr(scheduler.asyncio, "sleep", no_wait)

    with pytest.raises(asyncio.CancelledError):
        await scheduler.scheduler_loop(settings)

    assert calls == 2
