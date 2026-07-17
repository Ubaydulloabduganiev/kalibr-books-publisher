"""Tests for the manual publisher orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import MediaRef, Schedule, configure_store, create_post, get_post
from kalibr_publisher.services.publisher import publish_post


class FakeTelegram:
    def __init__(self, error: ApiError | None = None) -> None:
        self.sent: list[tuple[str, object]] = []
        self.error = error

    def _result(self, method: str, payload: object):
        if self.error:
            raise self.error
        self.sent.append((method, payload))
        return type("Result", (), {"ok": True, "chat_id": "@kalibr_books", "message_id": 7})()

    async def send_message(self, text: str, **_: object):
        return self._result("message", text)

    async def send_photo(self, path: str, **_: object):
        return self._result("photo", path)

    async def send_video(self, path: str, **_: object):
        return self._result("video", path)

    async def send_animation(self, path: str, **_: object):
        return self._result("animation", path)

    async def send_document(self, path: str, **_: object):
        return self._result("document", path)

    async def send_album(self, media: list[dict[str, str]], **_: object):
        return self._result("album", media)


@pytest.fixture
def publisher_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        app_env="test",
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        telegram_default_channel="@kalibr_books",
        _env_file=None,
    )
    settings.media_root.mkdir(parents=True)
    configure_store(settings.storage_root / "posts.json")
    return settings


def media_file(settings: Settings, name: str, content: bytes = b"data") -> str:
    path = settings.media_root / name
    path.write_bytes(content)
    return path.relative_to(settings.storage_root).as_posix()


@pytest.mark.parametrize(
    ("kind", "name", "expected"),
    [
        ("photo", "a.jpg", "photo"),
        ("video", "a.mp4", "video"),
        ("animation", "a.gif", "animation"),
        ("document", "a.pdf", "document"),
    ],
)
async def test_publish_single_media(
    publisher_settings: Settings, kind: str, name: str, expected: str
) -> None:
    telegram = FakeTelegram()
    post = create_post(
        text="caption",
        media=[MediaRef(kind=kind, path=media_file(publisher_settings, name))],
    )

    result = await publish_post(post, settings=publisher_settings, tg_client=telegram)  # type: ignore[arg-type]

    assert result["ok"] is True
    assert telegram.sent[0][0] == expected
    assert get_post(post.id).status == "sent"  # type: ignore[union-attr]


async def test_publish_text_and_album(publisher_settings: Settings) -> None:
    telegram = FakeTelegram()
    text = create_post(text="hello")
    assert (await publish_post(text, settings=publisher_settings, tg_client=telegram))["ok"] is True  # type: ignore[arg-type]

    album = create_post(
        text="album",
        media=[
            MediaRef(kind="photo", path=media_file(publisher_settings, "a.jpg")),
            MediaRef(kind="video", path=media_file(publisher_settings, "b.mp4")),
        ],
    )
    assert (await publish_post(album, settings=publisher_settings, tg_client=telegram))[
        "ok"
    ] is True  # type: ignore[arg-type]
    assert [item[0] for item in telegram.sent] == ["message", "album"]


async def test_missing_media_is_failed_not_silently_sent(publisher_settings: Settings) -> None:
    post = create_post(text="missing", media=[MediaRef(kind="photo", path="media/missing.jpg")])
    result = await publish_post(post, settings=publisher_settings, tg_client=FakeTelegram())  # type: ignore[arg-type]

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert get_post(post.id).status == "failed"  # type: ignore[union-attr]


async def test_uncertain_delivery_has_distinct_status(publisher_settings: Settings) -> None:
    error = ApiError(
        status_code=502,
        code="telegram_delivery_uncertain",
        message="uncertain",
        recovery_suggestion="check channel",
    )
    post = create_post(text="maybe")
    result = await publish_post(
        post,
        settings=publisher_settings,
        tg_client=FakeTelegram(error),  # type: ignore[arg-type]
    )

    assert result["status"] == "delivery_uncertain"
    assert get_post(post.id).status == "delivery_uncertain"  # type: ignore[union-attr]


async def test_recurring_post_remains_pending(publisher_settings: Settings) -> None:
    post = create_post(text="repeat", schedule=Schedule(mode="recurring", every_hours=24))
    await publish_post(post, settings=publisher_settings, tg_client=FakeTelegram())  # type: ignore[arg-type]
    stored = get_post(post.id)
    assert stored is not None
    assert stored.status == "pending"
    assert stored.send_count == 1
