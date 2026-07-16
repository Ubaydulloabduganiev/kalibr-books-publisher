"""Tests for the Telegram integration client and publishing route."""

from __future__ import annotations

import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.integrations.telegram import TelegramClient
from kalibr_publisher.schemas.telegram import TelegramPublishRequest


class _FakeResponse:
    def __init__(self, data: dict) -> None:
        self._data = data

    def json(self) -> dict:
        return self._data


class _FakeClient:
    """httpx-like async client that records the last request."""

    def __init__(self, response_data: dict) -> None:
        self._response = _FakeResponse(response_data)
        self.last_url: str | None = None
        self.last_json: dict | None = None
        self.closed = False

    async def post(self, url: str, json: dict) -> _FakeResponse:  # noqa: A002
        self.last_url = url
        self.last_json = json
        return self._response

    async def aclose(self) -> None:
        self.closed = True


def _settings(**overrides: object) -> Settings:
    """Build isolated settings that ignore the real .env and environment."""
    import os as _os

    env_backup = {k: _os.environ.pop(k, None) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_DEFAULT_CHANNEL")}
    try:
        base = dict(
            app_env="test",
            storage_root="storage",
            backup_root="backups",
            temp_root="tmp",
            log_root="logs",
            _env_file=None,  # type: ignore[call-arg]
        )
        base.update(overrides)  # type: ignore[arg-type]
        return Settings(**base)  # type: ignore[arg-type]
    finally:
        for k, v in env_backup.items():
            if v is not None:
                _os.environ[k] = v


def test_configured_requires_token() -> None:
    client = TelegramClient(_settings())
    assert client.configured is False
    assert client.default_channel is None


def test_configured_true_with_token() -> None:
    client = TelegramClient(_settings(telegram_bot_token="123:abc"))
    assert client.configured is True


async def test_send_raises_when_token_missing() -> None:
    client = TelegramClient(_settings())
    with pytest.raises(Exception) as exc:
        await client.send_message("hi")
    assert exc.value.code == "telegram_not_configured"


async def test_send_raises_when_no_target() -> None:
    client = TelegramClient(_settings(telegram_bot_token="123:abc"))
    with pytest.raises(Exception) as exc:
        await client.send_message("hi")
    assert exc.value.code == "telegram_no_target"


async def test_send_success_uses_default_channel() -> None:
    fake = _FakeClient({"ok": True, "result": {"message_id": 42}})
    client = TelegramClient(
        _settings(telegram_bot_token="123:abc", telegram_default_channel="@inglizguru"),
        http_client=fake,
    )
    result = await client.send_message("Salom", parse_mode="Markdown")
    assert result.ok is True
    assert result.message_id == 42
    assert result.chat_id == "@inglizguru"
    assert "bot123:abc/sendMessage" in (fake.last_url or "")  # type: ignore[operator]
    assert fake.last_json == {  # type: ignore[index]
        "chat_id": "@inglizguru",
        "text": "Salom",
        "parse_mode": "Markdown",
    }
    # Injected client is owned by the caller and must not be closed here.
    assert fake.closed is False


async def test_send_success_custom_target() -> None:
    fake = _FakeClient({"ok": True, "result": {"message_id": 7}})
    client = TelegramClient(
        _settings(telegram_bot_token="123:abc", telegram_default_channel="@inglizguru"),
        http_client=fake,
    )
    result = await client.send_message("Hi", chat_id="@other")
    assert result.chat_id == "@other"


async def test_send_propagates_api_error() -> None:
    fake = _FakeClient({"ok": False, "description": "Forbidden"})
    client = TelegramClient(
        _settings(telegram_bot_token="123:abc", telegram_default_channel="@inglizguru"),
        http_client=fake,
    )
    with pytest.raises(Exception) as exc:
        await client.send_message("Hi")
    assert exc.value.code == "telegram_api_error"
