"""Gemini AI client for caption tasks and image generation.

Uses the Gemini REST API directly (no SDK dependency) via httpx.

* ``rewrite_caption`` - produce an engaging Telegram-ready caption (HTML).
* ``generate_image`` - produce an image from a prompt using the multimodal
  image-generation model and return raw bytes + MIME type.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.errors import ApiError

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class CaptionResult:
    text: str
    parse_mode: Optional[str] = "HTML"


@dataclass
class ImageResult:
    data: bytes
    mime_type: str


class GeminiClient:
    """Minimal Gemini client for caption and image generation."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[httpx.Client] = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> "GeminiClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=httpx.Timeout(120.0, connect=20.0))
        return self._client

    def _api_key(self) -> str:
        key = getattr(self._settings, "gemini_api_key", None)
        key = key.get_secret_value() if hasattr(key, "get_secret_value") else (key or "")
        if not key:
            raise ApiError(
                status_code=500,
                code="gemini_not_configured",
                message="Gemini API key is not configured.",
                recovery_suggestion="Set GEMINI_API_KEY in the environment.",
            )
        return key

    def _post(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{GEMINI_URL}/{model}:generateContent?key={self._api_key()}"
        try:
            resp = self.client.post(url, json=payload)
        except httpx.HTTPError as ex:
            raise ApiError(
                status_code=502,
                code="gemini_request_failed",
                message=f"Gemini request failed: {ex}",
                recovery_suggestion="Check network connectivity to Google APIs.",
            )
        if resp.status_code != 200:
            raise ApiError(
                status_code=502,
                code="gemini_request_failed",
                message=f"Gemini rejected the request ({resp.status_code}).",
                technical_details=resp.text[:500],
                recovery_suggestion="Verify the Gemini API key and model name.",
            )
        try:
            return resp.json()
        except ValueError as ex:
            raise ApiError(
                status_code=502,
                code="gemini_invalid_response",
                message="Gemini returned an unreadable response.",
                technical_details=str(ex),
            )

    def _text_from(self, data: dict[str, Any]) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as ex:
            raise ApiError(
                status_code=502,
                code="gemini_request_failed",
                message="Gemini returned an unexpected response shape.",
                technical_details=str(ex),
            )

    def rewrite_caption(self, text: str, language: str = "uz") -> CaptionResult:
        prompt = (
            f"You are a social media editor for an English-learning book publisher "
            f"(Kalibr Books). Rewrite the following post for a Telegram channel "
            f"audience, in language '{language}'. Keep it engaging, concise, and "
            f"use only Telegram-supported HTML tags: <b>, <i>, <u>, <code>, <pre>, "
            f"<a href='...'>. Do NOT use <br>, <div>, or <p>. Return ONLY the final "
            f"caption text, nothing else.\n\nPOST:\n{text}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        }
        out = self._text_from(self._post(self._settings.gemini_text_model, payload))
        return CaptionResult(text=out, parse_mode="HTML")

    def generate_image(self, prompt: str) -> ImageResult:
        """Generate an image from ``prompt`` using the multimodal image model."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "responseModalities": ["IMAGE", "TEXT"]},
        }
        data = self._post(self._settings.gemini_model, payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as ex:
            raise ApiError(
                status_code=502,
                code="gemini_request_failed",
                message="Gemini returned an unexpected response shape.",
                technical_details=str(ex),
            )
        for part in parts:
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                try:
                    raw = base64.b64decode(inline["data"])
                except (binascii.Error, ValueError) as ex:
                    raise ApiError(
                        status_code=502,
                        code="gemini_request_failed",
                        message="Gemini returned corrupt image data.",
                        technical_details=str(ex),
                    )
                mime = inline.get("mimeType", "image/png")
                return ImageResult(data=raw, mime_type=mime)
        raise ApiError(
            status_code=502,
            code="gemini_no_image",
            message="Gemini did not return an image for the prompt.",
            recovery_suggestion="Try a more descriptive image prompt.",
        )
