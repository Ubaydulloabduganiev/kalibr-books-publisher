"""Tests for the Telegram integration client and publishing route."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from kalibr_publisher.api.deps import get_telegram_client
from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.integrations.telegram import TelegramClient
from kalibr_publisher.main import create_app


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeHttpClient:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)

    async def aclose(self) -> None:
        self.closed = True


def settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "storage_root": tmp_path / "storage",
        "backup_root": tmp_path / "backups",
        "temp_root": tmp_path / "tmp",
        "log_root": tmp_path / "logs",
        "telegram_bot_token": "123:abc",
        "telegram_default_channel": "@kalibr_books",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_configured_properties(tmp_path: Path) -> None:
    missing = TelegramClient(settings(tmp_path, telegram_bot_token=None))
    configured = TelegramClient(settings(tmp_path))
    assert missing.configured is False
    assert configured.configured is True
    assert configured.default_channel == "@kalibr_books"


async def test_send_message_payload(tmp_path: Path) -> None:
    fake = FakeHttpClient({"ok": True, "result": {"message_id": 42}})
    client = TelegramClient(settings(tmp_path), http_client=fake)

    result = await client.send_message(
        "Salom",
        parse_mode="HTML",
        disable_web_page_preview=True,
        disable_notification=True,
    )

    assert result.message_id == 42
    url, kwargs = fake.calls[0]
    assert url.endswith("/bot123:abc/sendMessage")
    assert kwargs["json"] == {
        "chat_id": "@kalibr_books",
        "text": "Salom",
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
        "disable_notification": True,
    }
    assert fake.closed is False


async def test_missing_configuration_and_target(tmp_path: Path) -> None:
    no_token = TelegramClient(settings(tmp_path, telegram_bot_token=None))
    with pytest.raises(ApiError, match="not configured"):
        await no_token.send_message("hello")

    no_target = TelegramClient(settings(tmp_path, telegram_default_channel=None))
    with pytest.raises(ApiError, match="No destination"):
        await no_target.send_message("hello")


async def test_api_and_invalid_response_errors(tmp_path: Path) -> None:
    rejected = TelegramClient(
        settings(tmp_path),
        http_client=FakeHttpClient({"ok": False, "error_code": 403, "description": "Forbidden"}),
    )
    with pytest.raises(ApiError) as rejected_error:
        await rejected.send_message("hello")
    assert rejected_error.value.code == "telegram_api_error"
    assert rejected_error.value.technical_details["error_code"] == 403

    invalid = TelegramClient(settings(tmp_path), http_client=FakeHttpClient(ValueError("not json")))
    with pytest.raises(ApiError) as invalid_error:
        await invalid.send_message("hello")
    assert invalid_error.value.code == "telegram_invalid_response"


class RaisingClient:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    async def post(self, _: str, **__: Any) -> FakeResponse:
        raise self.exception


async def test_network_error_classification(tmp_path: Path) -> None:
    request = httpx.Request("POST", "https://api.telegram.org")
    unreachable = TelegramClient(
        settings(tmp_path),
        http_client=RaisingClient(httpx.ConnectError("offline", request=request)),
    )
    with pytest.raises(ApiError) as connect_error:
        await unreachable.send_message("hello")
    assert connect_error.value.code == "telegram_unreachable"

    uncertain = TelegramClient(
        settings(tmp_path),
        http_client=RaisingClient(httpx.ReadTimeout("late", request=request)),
    )
    with pytest.raises(ApiError) as timeout_error:
        await uncertain.send_message("hello")
    assert timeout_error.value.code == "telegram_delivery_uncertain"


@pytest.mark.parametrize(
    ("method", "filename", "telegram_method", "field"),
    [
        ("send_photo", "cover.jpg", "sendPhoto", "photo"),
        ("send_video", "clip.mp4", "sendVideo", "video"),
        ("send_animation", "promo.gif", "sendAnimation", "animation"),
        ("send_document", "book.pdf", "sendDocument", "document"),
    ],
)
async def test_single_file_methods(
    tmp_path: Path,
    method: str,
    filename: str,
    telegram_method: str,
    field: str,
) -> None:
    path = tmp_path / filename
    path.write_bytes(b"content")
    fake = FakeHttpClient({"ok": True, "result": {"message_id": 5}})
    client = TelegramClient(settings(tmp_path), http_client=fake)

    result = await getattr(client, method)(str(path), caption="caption")

    assert result.ok is True
    url, kwargs = fake.calls[0]
    assert url.endswith(telegram_method)
    assert field in kwargs["files"]


async def test_missing_file_and_album_validation(tmp_path: Path) -> None:
    client = TelegramClient(settings(tmp_path), http_client=FakeHttpClient({"ok": True}))
    with pytest.raises(ApiError) as missing:
        await client.send_photo(str(tmp_path / "missing.jpg"))
    assert missing.value.code == "media_missing"

    with pytest.raises(ApiError) as size:
        await client.send_album([], caption="none")
    assert size.value.code == "telegram_album_size"


async def test_album_uses_matching_attach_names(tmp_path: Path) -> None:
    photo = tmp_path / "a.jpg"
    video = tmp_path / "b.mp4"
    photo.write_bytes(b"photo")
    video.write_bytes(b"video")
    fake = FakeHttpClient({"ok": True, "result": [{"message_id": 9}]})
    client = TelegramClient(settings(tmp_path), http_client=fake)

    result = await client.send_album(
        [
            {"kind": "photo", "path": str(photo)},
            {"kind": "video", "path": str(video)},
        ],
        caption="album",
        parse_mode="HTML",
    )

    assert result.message_id == 9
    _, kwargs = fake.calls[0]
    assert [item[0] for item in kwargs["files"]] == ["file0", "file1"]
    media_json = kwargs["data"]["media"]
    assert "attach://file0" in media_json
    assert "attach://file1" in media_json


async def test_publish_route_uses_dependency_override(tmp_path: Path) -> None:
    app_settings = settings(tmp_path)
    app = create_app(app_settings)
    fake = FakeHttpClient({"ok": True, "result": {"message_id": 11}})
    app.dependency_overrides[get_telegram_client] = lambda: TelegramClient(
        app_settings, http_client=fake
    )
    transport = ASGITransport(app=app)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.post(
            "/api/v1/telegram/publish",
            json={"text": "hello", "target": "default"},
        )

    assert response.status_code == 200
    assert response.json()["message_id"] == 11


async def test_publish_request_rejects_invalid_custom_target(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/telegram/publish",
        json={"text": "hello", "target": "custom", "chat_id": "not valid"},
    )
    assert response.status_code == 422
