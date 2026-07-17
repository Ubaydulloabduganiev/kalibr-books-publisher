"""Telegram Bot API client for text, media, documents, and mixed albums."""

from __future__ import annotations

import json
import mimetypes
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError

TELEGRAM_API_BASE = "https://api.telegram.org"
logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TelegramSendResult:
    ok: bool
    chat_id: str
    message_id: int | None


class TelegramClient:
    """Minimal async Telegram Bot API client with explicit resource ownership."""

    def __init__(self, settings: Settings, http_client: Any | None = None) -> None:
        self._token = settings.telegram_token_value()
        self._default_channel = settings.telegram_default_channel
        self._client = http_client

    @property
    def configured(self) -> bool:
        return bool(self._token)

    @property
    def default_channel(self) -> str | None:
        return self._default_channel

    def _target(self, chat_id: str | None) -> str:
        if not self._token:
            raise ApiError(
                status_code=503,
                code="telegram_not_configured",
                message="Telegram publishing is not configured on the server.",
                recovery_suggestion="Set TELEGRAM_BOT_TOKEN in the deployment environment.",
            )
        target = chat_id or self._default_channel
        if not target:
            raise ApiError(
                status_code=400,
                code="telegram_no_target",
                message="No destination channel was provided or configured.",
                recovery_suggestion="Choose a channel or configure TELEGRAM_DEFAULT_CHANNEL.",
            )
        return target

    async def _post(self, method: str, **kwargs: Any) -> dict[str, Any]:
        if not self._token:
            raise ApiError(
                status_code=503,
                code="telegram_not_configured",
                message="Telegram publishing is not configured on the server.",
                recovery_suggestion="Set TELEGRAM_BOT_TOKEN in the deployment environment.",
            )
        owns_client = self._client is None
        if self._client is None:
            client: Any = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
        else:
            client = self._client
        try:
            response = await client.post(f"{TELEGRAM_API_BASE}/bot{self._token}/{method}", **kwargs)
            try:
                payload = response.json()
            except Exception as exc:
                raise ApiError(
                    status_code=502,
                    code="telegram_invalid_response",
                    message="Telegram returned an unreadable response.",
                    recovery_suggestion="Retry later and inspect the server logs if it continues.",
                ) from exc
        except ApiError:
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning("telegram_connect_failed", exception_type=type(exc).__name__)
            raise ApiError(
                status_code=502,
                code="telegram_unreachable",
                message="The Telegram API could not be reached.",
                recovery_suggestion="Check network connectivity and retry.",
            ) from exc
        except Exception as exc:
            # Once an upload begins, a timeout can leave delivery state uncertain.
            logger.warning("telegram_delivery_uncertain", exception_type=type(exc).__name__)
            raise ApiError(
                status_code=502,
                code="telegram_delivery_uncertain",
                message="Telegram delivery could not be confirmed.",
                recovery_suggestion="Check the channel before retrying to avoid a duplicate post.",
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        if not isinstance(payload, dict) or not payload.get("ok"):
            description = payload.get("description") if isinstance(payload, dict) else None
            error_code = payload.get("error_code") if isinstance(payload, dict) else None
            raise ApiError(
                status_code=502,
                code="telegram_api_error",
                message="Telegram rejected the request.",
                recovery_suggestion=(
                    "Verify the bot token, channel permissions, and content format."
                ),
                technical_details={"error_code": error_code, "description": description},
            )
        return payload

    async def send_message(
        self,
        text: str,
        *,
        chat_id: str | None = None,
        parse_mode: str | None = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> TelegramSendResult:
        target = self._target(chat_id)
        payload: dict[str, Any] = {"chat_id": target, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview:
            payload["link_preview_options"] = {"is_disabled": True}
        if disable_notification:
            payload["disable_notification"] = True
        data = await self._post("sendMessage", json=payload)
        result = data.get("result") or {}
        return TelegramSendResult(True, target, result.get("message_id"))

    async def send_photo(
        self,
        photo_path: str,
        *,
        caption: str | None = None,
        chat_id: str | None = None,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        return await self._send_file("sendPhoto", "photo", photo_path, caption, chat_id, parse_mode)

    async def send_video(
        self,
        video_path: str,
        *,
        caption: str | None = None,
        chat_id: str | None = None,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        return await self._send_file("sendVideo", "video", video_path, caption, chat_id, parse_mode)

    async def send_animation(
        self,
        animation_path: str,
        *,
        caption: str | None = None,
        chat_id: str | None = None,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        return await self._send_file(
            "sendAnimation", "animation", animation_path, caption, chat_id, parse_mode
        )

    async def send_document(
        self,
        document_path: str,
        *,
        caption: str | None = None,
        chat_id: str | None = None,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        return await self._send_file(
            "sendDocument", "document", document_path, caption, chat_id, parse_mode
        )

    async def _send_file(
        self,
        method: str,
        field: str,
        file_path: str,
        caption: str | None,
        chat_id: str | None,
        parse_mode: str | None,
    ) -> TelegramSendResult:
        target = self._target(chat_id)
        path = Path(file_path)
        if not path.is_file():
            raise ApiError(
                status_code=409,
                code="media_missing",
                message="The selected media file is missing.",
                recovery_suggestion="Upload or replace the media file and retry.",
            )
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        form: dict[str, Any] = {"chat_id": target}
        if caption:
            form["caption"] = caption
        if parse_mode:
            form["parse_mode"] = parse_mode
        with path.open("rb") as handle:
            data = await self._post(
                method,
                data=form,
                files={field: (path.name, handle, mime)},
            )
        result = data.get("result") or {}
        return TelegramSendResult(True, target, result.get("message_id"))

    async def send_album(
        self,
        media: list[dict[str, str]],
        *,
        chat_id: str | None = None,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> TelegramSendResult:
        target = self._target(chat_id)
        if not 2 <= len(media) <= 10:
            raise ApiError(
                status_code=400,
                code="telegram_album_size",
                message="Telegram albums must contain between 2 and 10 items.",
                recovery_suggestion="Adjust the album size and retry.",
            )

        with ExitStack() as stack:
            files: list[tuple[str, tuple[str, Any, str]]] = []
            media_payload: list[dict[str, Any]] = []
            for index, item in enumerate(media):
                kind = item.get("kind")
                if kind not in {"photo", "video"}:
                    raise ApiError(
                        status_code=400,
                        code="telegram_media_kind",
                        message="An album contains an unsupported media type.",
                        recovery_suggestion="Use only photos and videos in albums.",
                    )
                path = Path(item["path"])
                if not path.is_file():
                    raise ApiError(
                        status_code=409,
                        code="media_missing",
                        message="An album media file is missing.",
                        recovery_suggestion=(
                            "Restore or replace the missing media before publishing."
                        ),
                    )
                field_name = f"file{index}"
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                handle = stack.enter_context(path.open("rb"))
                files.append((field_name, (path.name, handle, mime)))
                entry: dict[str, Any] = {"type": kind, "media": f"attach://{field_name}"}
                if index == 0 and caption:
                    entry["caption"] = caption
                    if parse_mode:
                        entry["parse_mode"] = parse_mode
                media_payload.append(entry)

            data = await self._post(
                "sendMediaGroup",
                data={"chat_id": target, "media": json.dumps(media_payload)},
                files=files,
            )
        result = data.get("result") or []
        first = result[0] if isinstance(result, list) and result else {}
        return TelegramSendResult(True, target, first.get("message_id"))
