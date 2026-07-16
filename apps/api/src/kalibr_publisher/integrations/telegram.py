"""Telegram Bot API client for publishing posts to channels."""

from __future__ import annotations
import os

from dataclasses import dataclass
from typing import Any
import json

import structlog

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError

logger = structlog.get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


@dataclass(slots=True)
class TelegramSendResult:
    """Outcome of a single Telegram send operation."""

    ok: bool
    chat_id: str
    message_id: int | None = None
    error_code: int | None = None
    description: str | None = None


class TelegramClient:
    """Thin async client around the Telegram Bot API sendMessage method.

    The bot token is supplied by settings and never written to logs.
    """

    def __init__(self, settings: Settings, http_client: Any | None = None) -> None:
        self._token = settings.telegram_bot_token
        self._default_channel = settings.telegram_default_channel
        self._client = http_client

    @property
    def configured(self) -> bool:
        """Return True when a token is available for sending."""
        return bool(self._token)

    @property
    def default_channel(self) -> str | None:
        return self._default_channel

    async def send_message(
        self,
        text: str,
        *,
        chat_id: str | None = None,
        parse_mode: str | None = None,
        disable_web_page_preview: bool = False,
    ) -> TelegramSendResult:
        """Publish ``text`` to ``chat_id`` (or the configured default channel)."""
        target = chat_id or self._default_channel
        if not self._token:
            raise ApiError(
                status_code=503,
                code="telegram_not_configured",
                message="Telegram publishing is not configured on the server.",
                recovery_suggestion="Set TELEGRAM_BOT_TOKEN in the deployment environment.",
            )
        if not target:
            raise ApiError(
                status_code=400,
                code="telegram_no_target",
                message="No destination channel was provided or configured.",
                recovery_suggestion="Pass a chat_id or set TELEGRAM_DEFAULT_CHANNEL.",
            )

        payload: dict[str, Any] = {"chat_id": target, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview:
            payload["disable_web_page_preview"] = True

        client = self._client
        if client is None:
            import httpx

            client = httpx.AsyncClient(timeout=15.0)

        try:
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{self._token}/sendMessage",
                json=payload,
            )
            data = response.json()
        except Exception as exc:  # noqa: BLE001 - surface network failures as ApiError
            logger.warning("telegram_request_failed", error=str(exc))
            raise ApiError(
                status_code=502,
                code="telegram_unreachable",
                message="The Telegram API could not be reached.",
                recovery_suggestion="Check network connectivity and try again.",
                technical_details=str(exc),
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()

        if not data.get("ok"):
            raise ApiError(
                status_code=502,
                code="telegram_api_error",
                message="Telegram rejected the message.",
                recovery_suggestion="Verify the bot token and channel permissions.",
                technical_details=data.get("description"),
            )

        result = data.get("result", {})
        return TelegramSendResult(
            ok=True,
            chat_id=str(target),
            message_id=result.get("message_id"),
        )
    async def send_photo(self, photo_path: str, *, caption: str | None = None,
                        chat_id: str | None = None, parse_mode: str | None = None) -> TelegramSendResult:
        """Send a single photo (path on disk) with optional caption."""
        return await self._send_file("sendPhoto", "photo", photo_path, caption, chat_id, parse_mode)

    async def send_video(self, video_path: str, *, caption: str | None = None,
                        chat_id: str | None = None, parse_mode: str | None = None) -> TelegramSendResult:
        """Send a single video (path on disk) with optional caption."""
        return await self._send_file("sendVideo", "video", video_path, caption, chat_id, parse_mode)

    async def send_album(self, media: list[dict[str, str]], *, chat_id: str | None = None,
                         caption: str | None = None, parse_mode: str | None = None) -> TelegramSendResult:
        """Send a mixed album (photos + videos) as one message group.

        ``media`` is a list of {"kind": "photo"|"video", "path": "..."}.
        Caption is attached to the first item only (Telegram constraint).
        """
        import httpx
        target = chat_id or self._default_channel
        if not self._token:
            raise ApiError(status_code=503, code="telegram_not_configured",
                           message="Telegram publishing is not configured on the server.",
                           recovery_suggestion="Set TELEGRAM_BOT_TOKEN in the deployment environment.")
        if not target:
            raise ApiError(status_code=400, code="telegram_no_target",
                           message="No destination channel was provided or configured.",
                           recovery_suggestion="Pass a chat_id or set TELEGRAM_DEFAULT_CHANNEL.")
        if not media:
            raise ApiError(status_code=400, code="telegram_no_media",
                           message="No media items were provided.",
                           recovery_suggestion="Attach at least one photo or video.")

        read = _read_all(media)
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        media_json: list[dict[str, Any]] = []
        for i, (kind, data, mime) in enumerate(read):
            ext = ".jpg" if kind == "photo" else ".mp4"
            field = f"file{i}"
            files.append((kind, (field + ext, data, mime)))
            entry: dict[str, Any] = {"type": kind, "media": f"attach://{field}"}
            if i == 0 and caption:
                entry["caption"] = caption
                if parse_mode:
                    entry["parse_mode"] = parse_mode
            media_json.append(entry)

        form: dict[str, str] = {"chat_id": target, "media": json.dumps(media_json)}
        client = self._client
        own = client is None
        if own:
            client = httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{self._token}/sendMediaGroup",
                data=form, files=files,
            )
            rdata = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("telegram_album_failed", error=str(exc))
            raise ApiError(status_code=502, code="telegram_unreachable",
                           message="The Telegram API could not be reached.",
                           recovery_suggestion="Check network connectivity and try again.",
                           technical_details=str(exc)) from exc
        finally:
            if own:
                await client.aclose()
        if not rdata.get("ok"):
            raise ApiError(status_code=502, code="telegram_api_error",
                           message="Telegram rejected the album.",
                           recovery_suggestion="Verify the bot token, channel permissions, and media formats.",
                           technical_details=rdata.get("description"))
        result = (rdata.get("result") or [{}])[0]
        return TelegramSendResult(ok=True, chat_id=str(target), message_id=result.get("message_id"))

    async def _send_file(self, method: str, field: str, path: str, caption, chat_id, parse_mode) -> TelegramSendResult:
        target = chat_id or self._default_channel
        if not self._token:
            raise ApiError(status_code=503, code="telegram_not_configured",
                           message="Telegram publishing is not configured on the server.",
                           recovery_suggestion="Set TELEGRAM_BOT_TOKEN in the deployment environment.")
        if not target:
            raise ApiError(status_code=400, code="telegram_no_target",
                           message="No destination channel was provided or configured.",
                           recovery_suggestion="Pass a chat_id or set TELEGRAM_DEFAULT_CHANNEL.")
        ext = os.path.splitext(path)[1] or ".jpg"
        mime = ("image/jpeg" if field == "photo" else "video/mp4")
        import httpx
        client = self._client
        own = client is None
        if own:
            client = httpx.AsyncClient(timeout=30.0)
        try:
            with open(path, "rb") as fh:
                filedata = fh.read()
            files = {field: (f"file{ext}", filedata, mime)}
            data: dict[str, Any] = {"chat_id": target}
            if caption:
                data["caption"] = caption
            if parse_mode:
                data["parse_mode"] = parse_mode
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{self._token}/{method}", data=data, files=files)
            rdata = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("telegram_file_failed", error=str(exc))
            raise ApiError(status_code=502, code="telegram_unreachable",
                           message="The Telegram API could not be reached.",
                           recovery_suggestion="Check network connectivity and try again.",
                           technical_details=str(exc)) from exc
        finally:
            if own:
                await client.aclose()
        if not rdata.get("ok"):
            raise ApiError(status_code=502, code="telegram_api_error",
                           message="Telegram rejected the media.",
                           recovery_suggestion="Verify the bot token, channel permissions, and file format.",
                           technical_details=rdata.get("description"))
        result = rdata.get("result", {})
        return TelegramSendResult(ok=True, chat_id=str(target), message_id=result.get("message_id"))


def _read_all(media: list[dict[str, str]]) -> list[tuple[str, bytes, str]]:
    out = []
    for item in media:
        kind = "photo" if item["kind"] == "photo" else "video"
        ext = os.path.splitext(item["path"])[1] or ".jpg"
        mime = "image/jpeg" if kind == "photo" else "video/mp4"
        with open(item["path"], "rb") as fh:
            out.append((kind, fh.read(), mime))
    return out
