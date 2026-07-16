"""Gemini image generation client.

Uses the Gemini image model (Nano Banana / gemini-2.5-flash-image) to turn a
text prompt into a PNG. Falls back to a generated SVG placeholder if the model
is unavailable or rate-limited, so automation never hard-fails on imagery.
"""

from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.core.errors import ApiError

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
IMAGE_MODEL = "gemini-2.5-flash-image"


@dataclass
class ImageResult:
    data: bytes
    mime: str


def _placeholder_svg(prompt: str) -> bytes:
    """Self-contained SVG used when image generation is unavailable."""
    safe = (prompt or "Kalibr Books")[:60].replace("&", "&amp;").replace("<", "&lt;")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800">'
        '<rect width="100%" height="100%" fill="#f4ece1"/>'
        '<text x="50%" y="50%" font-family="sans-serif" font-size="34" '
        'fill="#5b4636" text-anchor="middle" dominant-baseline="middle">'
        f"{safe}</text></svg>"
    )
    return svg.encode("utf-8")


class GeminiImageClient:
    """Minimal Gemini image-generation client."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.Client] = None,
        model: str = IMAGE_MODEL,
    ) -> None:
        self._settings = settings or get_settings()
        self._model = model
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> "GeminiImageClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=90.0)
        return self._client

    def _api_key(self) -> str:
        key = getattr(self._settings, "gemini_api_key", "")
        if not key:
            raise ApiError(
                status_code=500,
                code="gemini_not_configured",
                message="Gemini API key is not configured.",
                recovery_suggestion="Set GEMINI_API_KEY in the environment.",
            )
        return key

    def generate(self, prompt: str, max_retries: int = 3) -> ImageResult:
        """Generate an image for ``prompt``. Falls back to an SVG placeholder."""
        url = f"{GEMINI_URL}/{self._model}:generateContent?key={self._api_key()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }
        last_err: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                resp = self.client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    for cand in data.get("candidates", []):
                        for part in cand.get("content", {}).get("parts", []):
                            if "inlineData" in part:
                                raw = base64.b64decode(part["inlineData"]["data"])
                                return ImageResult(
                                    data=raw,
                                    mime=part["inlineData"].get("mimeType", "image/png"),
                                )
                    # Model returned no image part -> treat as generation miss.
                    last_err = RuntimeError("Gemini returned no image part")
                elif resp.status_code in (429, 503):
                    last_err = RuntimeError(f"Gemini transient {resp.status_code}")
                else:
                    last_err = ApiError(
                        status_code=502,
                        code="gemini_image_failed",
                        message=f"Gemini image request failed ({resp.status_code}).",
                        technical_details=resp.text[:400],
                    )
                    break
            except httpx.HTTPError as ex:
                last_err = ex
            # backoff for transient errors
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
        # Hard failure or rate-limit: degrade gracefully to a placeholder.
        if last_err is not None:
            import logging

            logging.getLogger(__name__).warning(
                "gemini_image_fallback", error=str(last_err)
            )
        return ImageResult(data=_placeholder_svg(prompt), mime="image/svg+xml")
