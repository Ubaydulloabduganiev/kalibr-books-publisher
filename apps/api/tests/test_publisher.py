"""Tests for the publisher orchestrator (mocked telegram + gemini)."""

from __future__ import annotations

import httpx

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.store import MediaRef, Schedule, create_post
from kalibr_publisher.services.publisher import publish_post


class FakeTg:
    def __init__(self):
        self.sent = []
    async def send_message(self, text, *, chat_id=None, parse_mode=None, disable_web_page_preview=False):
        self.sent.append(("msg", text))
        return type("R", (), {"ok": True, "chat_id": chat_id or "@inglizguru", "message_id": 1})()
    async def send_photo(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("photo", caption))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 2})()
    async def send_video(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("video", caption))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 3})()
    async def send_album(self, media, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(("album", caption, len(media)))
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 4})()


def make_settings(**kw):
    base = dict(ai_enabled=False, telegram_default_channel="@inglizguru",
                gemini_api_key="", gemini_model="gemini-1.5-flash", ai_caption_language="uz")
    base.update(kw)
    return Settings(**base)


async def test_publish_text():
    tg = FakeTg()
    p = create_post(text="hi")
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0][0] == "msg"


async def test_publish_photo():
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    tg = FakeTg()
    p = create_post(text="pic", media=[MediaRef(kind="photo", path=path)])
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0][0] == "photo"


async def test_publish_album():
    import tempfile, os
    fd1, p1 = tempfile.mkstemp(suffix=".jpg"); os.close(fd1)
    fd2, p2 = tempfile.mkstemp(suffix=".mp4"); os.close(fd2)
    tg = FakeTg()
    p = create_post(text="a", media=[MediaRef(kind="photo", path=p1),
                                      MediaRef(kind="video", path=p2)])
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0][0] == "album"
