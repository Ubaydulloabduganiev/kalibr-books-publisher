"""Tests for Telegram media send methods (mocked httpx)."""

from __future__ import annotations

import os
import tempfile

from kalibr_publisher.core.config import Settings
from kalibr_publisher.integrations.telegram import TelegramClient


class FakeClient:
    def __init__(self):
        self.calls = []
    async def post(self, url, json=None, data=None, files=None):
        self.calls.append((url, files is not None))
        # Telegram returns result as a list for media groups, dict for single send
        if "MediaGroup" in url:
            result = [{"message_id": 1}]
        else:
            result = {"message_id": 1}
        payload = {"ok": True, "result": result}
        return type("R", (), {"ok": True, "json": lambda self=None: payload})()


def make_settings():
    return Settings(telegram_bot_token="123:abc", telegram_default_channel="@inglizguru")


def test_send_photo():
    fd, p = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
    fc = FakeClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import asyncio
    res = asyncio.run(tg.send_photo(p, chat_id="@inglizguru"))
    assert res.ok is True
    assert fc.calls[-1][1] is True  # multipart


def test_send_video():
    fd, p = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
    fc = FakeClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import asyncio
    res = asyncio.run(tg.send_video(p, chat_id="@inglizguru"))
    assert res.ok is True


def test_send_album():
    fd1, p1 = tempfile.mkstemp(suffix=".jpg"); os.close(fd1)
    fd2, p2 = tempfile.mkstemp(suffix=".mp4"); os.close(fd2)
    fc = FakeClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import asyncio
    res = asyncio.run(tg.send_album([{"kind": "photo", "path": p1}, {"kind": "video", "path": p2}], chat_id="@inglizguru"))
    assert res.ok is True
    os.remove(p1); os.remove(p2)
