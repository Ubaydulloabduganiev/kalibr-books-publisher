"""Tests for the scheduler loop and publisher integration."""

from __future__ import annotations

import asyncio

import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.store import Schedule, create_post, due_posts, list_posts
from kalibr_publisher.services import scheduler
from kalibr_publisher.services.publisher import publish_post


class FakeTg:
    def __init__(self):
        self.sent = []
    async def send_message(self, text, *, chat_id=None, parse_mode=None, disable_web_page_preview=False):
        self.sent.append(text)
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 1})()
    async def send_photo(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(caption)
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 2})()
    async def send_video(self, path, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(caption)
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 3})()
    async def send_album(self, media, *, caption=None, chat_id=None, parse_mode=None):
        self.sent.append(caption)
        return type("R", (), {"ok": True, "chat_id": chat_id, "message_id": 4})()


def setup_function(fn):
    import kalibr_publisher.core.store as store
    store._STORE_PATH = None
    import os
    p = os.path.join(store.get_settings().storage_root, "posts.json")
    if os.path.exists(p):
        os.remove(p)


def make_settings():
    return Settings(ai_enabled=False, telegram_default_channel="@inglizguru",
                    gemini_api_key="", gemini_model="gemini-1.5-flash",
                    ai_caption_language="uz")


async def test_tick_sends_due_post():
    tg = FakeTg()
    p = create_post(text="due now", schedule=Schedule(mode="once"))
    due = due_posts()
    assert any(x.id == p.id for x in due)
    await scheduler._tick(tg_client=tg)
    # after tick, post should be marked sent
    got = [x for x in list_posts() if x.id == p.id][0]
    assert got.status == "sent"
    assert tg.sent  # something was sent


async def test_recurring_advances():
    from kalibr_publisher.core.store import advance_recurring, get_post
    p = create_post(text="r", schedule=Schedule(mode="recurring", every_hours=24))
    p.status = "pending"
    await publish_post(p, settings=make_settings(), tg_client=FakeTg())
    got = get_post(p.id)
    assert got.status == "pending"  # recurring stays pending, next_run pushed


async def test_ai_disabled_no_gemini_call():
    p = create_post(text="plain", schedule=Schedule(mode="once"))
    tg = FakeTg()
    res = await publish_post(p, settings=make_settings(), tg_client=tg)
    assert res["ok"] is True
    assert tg.sent[0] == "plain"  # no AI rewrite
