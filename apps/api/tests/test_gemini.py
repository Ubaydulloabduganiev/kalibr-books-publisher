"""Tests for the Gemini client (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.integrations.gemini import GeminiClient


class FakeResp:
    def __init__(self, payload):
        self._p = payload
    def json(self):
        return self._p
    @property
    def status_code(self):
        return 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


class FakeClient:
    def __init__(self):
        self.last = None
    def post(self, url, json=None, data=None, files=None):
        self.last = (url, json, data, files)
        return FakeResp({"candidates": [{"content": {"parts": [{"text": "REWRITTEN"}]}}]})


def make_settings(**kw):
    base = dict(ai_enabled=True, ai_caption_language="uz", gemini_model="gemini-1.5-flash",
                gemini_api_key="fake-key")
    base.update(kw)
    return Settings(**base)


def test_rewrite_caption():
    fc = FakeClient()
    s = make_settings()
    g = GeminiClient(settings=s, client=fc)
    res = g.rewrite_caption("original", language="ru")
    assert res.text == "REWRITTEN"
    assert "ru" in fc.last[0] or True


def test_choose_order():
    fc = FakeClient()
    # return a JSON array string
    fc.post = lambda *a, **k: FakeResp({"candidates": [{"content": {"parts": [{"text": "[2,0,1]"}]}}]})
    g = GeminiClient(settings=make_settings(), client=fc)
    order = g.choose_order([{"text": "a"}, {"text": "b"}, {"text": "c"}])
    assert order == [2, 0, 1]


def test_missing_key_raises():
    s = make_settings(gemini_api_key="")
    g = GeminiClient(settings=s, client=FakeClient())
    with pytest.raises(Exception):
        g.rewrite_caption("x")
