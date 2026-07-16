"""Extra coverage for gemini / telegram edge paths."""

from __future__ import annotations
import os

import asyncio

import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.integrations.gemini import GeminiClient
from kalibr_publisher.integrations.telegram import TelegramClient


# --- sync client for Gemini (GeminiClient._generate calls post() without await) ---
class SyncResp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p

    @property
    def status_code(self):
        return 200

    @property
    def text(self):
        return "{}"


class SyncClient:
    def __init__(self, payload=None):
        self._payload = payload or {
            "candidates": [{"content": {"parts": [{"text": "OUT"}]}}]
        }
        self.calls = []

    def post(self, url, json=None, data=None, files=None):
        self.calls.append(url)
        return SyncResp(self._payload)


# --- async client for Telegram (TelegramClient awaits post()) ---
class AsyncResp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p

    @property
    def status_code(self):
        return 200


class AsyncClient:
    def __init__(self, payload=None):
        self._payload = payload or {"ok": True, "result": {"message_id": 1}}
        self.calls = []

    async def post(self, url, json=None, data=None, files=None):
        self.calls.append(url)
        if "MediaGroup" in url:
            return AsyncResp({"ok": True, "result": [{"message_id": 1}]})
        if "send" in url:
            return AsyncResp({"ok": True, "result": {"message_id": 1}})
        return AsyncResp(self._payload)


def make_settings(**kw):
    base = dict(
        ai_enabled=True,
        ai_caption_language="uz",
        gemini_model="gemini-1.5-flash",
        gemini_api_key="fake",
        telegram_bot_token="123:abc",
        telegram_default_channel="@inglizguru",
    )
    base.update(kw)
    return Settings(**base)


def test_gemini_suggest_time():
    fc = SyncClient(
        {"candidates": [{"content": {"parts": [{"text": "2030-01-01T09:00:00+05:00"}]}}]}
    )
    g = GeminiClient(settings=make_settings(), client=fc)
    out = g.suggest_time("post")
    assert out.startswith("2030")


def test_gemini_empty_text_returns_result():
    fc = SyncClient({"candidates": [{"content": {"parts": [{"text": ""}]}}]})
    g = GeminiClient(settings=make_settings(), client=fc)
    res = g.rewrite_caption("x")
    assert res.text == ""


def test_gemini_missing_key_raises():
    fc = SyncClient({"unexpected": True})
    g = GeminiClient(settings=make_settings(), client=fc)
    with pytest.raises(Exception):
        g.rewrite_caption("x")


def test_telegram_send_message():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    res = asyncio.run(tg.send_message("hi", chat_id="@inglizguru"))
    assert res.ok is True


def test_telegram_send_photo():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import tempfile, os
    p = os.path.join(tempfile.gettempdir(), "t.png")
    open(p, "wb").write(b"\x89PNG\r\n\x1a\n fake")
    res = asyncio.run(tg.send_photo(p, chat_id="@inglizguru"))
    assert res.ok is True
    os.remove(p)


def test_telegram_no_token_raises():
    tg = TelegramClient(
        settings=make_settings(telegram_bot_token=""), http_client=AsyncClient()
    )
    with pytest.raises(Exception):
        asyncio.run(tg.send_message("hi"))


def test_telegram_api_error():
    class BadClient:
        async def post(self, *a, **k):
            return type(
                "R",
                (),
                {"ok": False, "status_code": 400, "json": lambda: {"description": "bad"}},
            )()

    tg = TelegramClient(settings=make_settings(), http_client=BadClient())
    with pytest.raises(Exception):
        asyncio.run(tg.send_message("hi", chat_id="@inglizguru"))


def test_telegram_send_video():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "t.mp4")
    open(p, "wb").write(b"\x00\x00\x00\x18 fake mp4")
    res = asyncio.run(tg.send_video(p, chat_id="@inglizguru"))
    assert res.ok is True
    os.remove(p)


def test_telegram_send_album():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    import tempfile
    p1 = os.path.join(tempfile.gettempdir(), "a.png")
    p2 = os.path.join(tempfile.gettempdir(), "b.mp4")
    open(p1, "wb").write(b"\x89PNG\r\n\x1a\n fake")
    open(p2, "wb").write(b"\x00\x00\x00\x18 fake mp4")
    media = [
        {"kind": "photo", "path": p1},
        {"kind": "video", "path": p2},
    ]
    res = asyncio.run(tg.send_album(media, caption="hi", chat_id="@inglizguru"))
    assert res.ok is True
    os.remove(p1)
    os.remove(p2)


def test_telegram_no_target_raises():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(telegram_default_channel=""), http_client=fc)
    with pytest.raises(Exception):
        asyncio.run(tg.send_message("hi"))


def test_telegram_album_no_media_raises():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    with pytest.raises(Exception):
        asyncio.run(tg.send_album([], chat_id="@inglizguru"))


def test_telegram_send_message_preview():
    fc = AsyncClient()
    tg = TelegramClient(settings=make_settings(), http_client=fc)
    res = asyncio.run(tg.send_message("hi", chat_id="@inglizguru", disable_web_page_preview=True))
    assert res.ok is True


def test_telegram_publish_route():
    from fastapi.testclient import TestClient
    from kalibr_publisher.main import create_app
    from kalibr_publisher.integrations.telegram import TelegramClient

    app = create_app()
    # Inject an async-fake telegram client into the app state/dep
    class RouteAsyncClient:
        async def post(self, url, json=None, data=None, files=None):
            return type("R", (), {"ok": True, "json": lambda: {"ok": True, "result": {"message_id": 9}}})()

    # monkeypatch the dependency used by the route
    from kalibr_publisher.api import deps
    orig = deps.get_telegram_client
    deps.get_telegram_client = lambda: TelegramClient(settings=make_settings(), http_client=RouteAsyncClient())
    try:
        c = TestClient(app)
        r = c.post("/api/v1/telegram/publish", json={"text": "hello", "target": "default"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    finally:
        deps.get_telegram_client = orig


def test_gemini_context_manager_closes():
    fc = SyncClient()
    with GeminiClient(settings=make_settings(), client=fc) as g:
        res = g.rewrite_caption("hi")
        assert res.text == "OUT"


def test_gemini_choose_order_valid():
    fc = SyncClient({"candidates": [{"content": {"parts": [{"text": "[2, 0, 1]"}]}}]})
    g = GeminiClient(settings=make_settings(), client=fc)
    order = g.choose_order([{"text": "a"}, {"text": "b"}, {"text": "c"}])
    assert order == [2, 0, 1]


def test_gemini_choose_order_fallback():
    fc = SyncClient({"candidates": [{"content": {"parts": [{"text": "not a list"}]}}]})
    g = GeminiClient(settings=make_settings(), client=fc)
    order = g.choose_order([{"text": "a"}, {"text": "b"}, {"text": "c"}])
    assert order == [0, 1, 2]
