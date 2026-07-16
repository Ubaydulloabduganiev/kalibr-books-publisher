"""Extra publisher/scheduler coverage to clear the 90% gate."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import AiConfig, MediaRef, Schedule, create_post, due_posts
from kalibr_publisher.integrations.gemini import CaptionResult
from kalibr_publisher.services.publisher import order_posts_with_ai, publish_post


class FakeTg:
    def __init__(self):
        self.sent = []

    async def send_message(self, text, *, chat_id=None, parse_mode=None, disable_web_page_preview=False):
        self.sent.append(("msg", text))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 1})()

    async def send_photo(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("photo", caption))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 2})()

    async def send_video(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("video", caption))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 3})()

    async def send_album(self, media, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("album", caption, len(media)))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 4})()


class FakeGemini:
    def rewrite_caption(self, text, language="uz"):
        return CaptionResult(text=f"[ai]{text}", parse_mode="HTML")


def make_settings(**kw):
    base = dict(
        ai_enabled=True,
        telegram_default_channel="@kalibr_books",
        gemini_api_key="x",
        gemini_model="gemini-1.5-flash",
        ai_caption_language="uz",
    )
    base.update(kw)
    return Settings(**base)


async def test_publish_with_ai_rewrite():
    tg = FakeTg()
    p = create_post(text="hello", ai=AiConfig(rewrite=True, language="uz", choose_order=False))
    res = await publish_post(p, settings=make_settings(), tg_client=tg, gemini_client=FakeGemini())
    assert res["ok"] is True
    assert "[ai]hello" in tg.sent[0][1]


async def test_publish_video():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    import os

    os.close(fd)
    tg = FakeTg()
    p = create_post(text="v", media=[MediaRef(kind="video", path=path)])
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0][0] == "video"


async def test_publish_missing_media_falls_back_to_message():
    tg = FakeTg()
    # non-existent file -> missing -> falls back to send_message
    p = create_post(text="x", media=[MediaRef(kind="photo", path="storage_test/nope.png")])
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0][0] == "msg"


async def test_publish_api_error_records_failure():
    class BoomTg(FakeTg):
        async def send_message(self, text, *, chat_id=None, parse_mode=None, disable_web_page_preview=False):
            raise ApiError(
                status_code=500,
                code="boom",
                message="boom",
                recovery_suggestion="none",
            )

    p = create_post(text="fail")
    res = await publish_post(p, settings=make_settings(), tg_client=BoomTg())
    assert res["ok"] is False
    assert p.status == "failed"


async def test_order_posts_with_ai():
    from kalibr_publisher.integrations.gemini import GeminiClient

    class OrderGemini(GeminiClient):
        def choose_order(self, briefs):
            return [1, 0]  # reverse

    p0 = create_post(text="a", ai=AiConfig(choose_order=True))
    p1 = create_post(text="b", ai=AiConfig(choose_order=True))
    ordered = order_posts_with_ai([p0, p1], gemini_client=OrderGemini(make_settings()))
    assert [p.text for p in ordered] == ["b", "a"]


def test_due_posts_selects_ready():
    p = create_post(
        text="due",
        schedule=Schedule(mode="once", run_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()),
    )
    due = due_posts()
    assert any(x.id == p.id for x in due)
