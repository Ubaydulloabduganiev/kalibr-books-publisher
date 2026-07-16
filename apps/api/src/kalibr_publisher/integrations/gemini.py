"""Gemini AI client for caption tasks.

Uses the Gemini REST API directly (no SDK dependency) via httpx.
Handles: rewrite/translate caption, suggest posting time, choose post order.
"""

from __future__ import annotations

import json
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


class GeminiClient:
    """Minimal Gemini client for caption AI."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[httpx.Client] = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    # --- context manager so tests can inject a mock client ---
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
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def _api_key(self) -> str:
        key = getattr(self._settings, "gemini_api_key", "") or ""
        if not key:
            raise ApiError(
                status_code=500,
                code="gemini_not_configured",
                message="Gemini API key is not configured.",
                recovery_suggestion="Set GEMINI_API_KEY in the environment.",
            )
        return key

    def _model(self) -> str:
        return getattr(self._settings, "gemini_model", "gemini-1.5-flash") or "gemini-1.5-flash"

    def _generate(self, prompt: str) -> str:
        url = f"{GEMINI_URL}/{self._model()}:generateContent?key={self._api_key()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        }
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
        data = resp.json()
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
        out = self._generate(prompt)
        return CaptionResult(text=out, parse_mode="HTML")

    def suggest_time(self, text: str, tz_hint: str = "Asia/Tashkent") -> str:
        """Suggest the best posting time (ISO8601) for the given content."""
        prompt = (
            f"Given this Telegram post for an English-learning audience in Uzbekistan "
            f"(timezone {tz_hint}), suggest the single best date/time to publish in the "
            f"next 48 hours. Respond with ONLY an ISO8601 timestamp (e.g. "
            f"2026-07-18T09:00:00+05:00), nothing else.\n\nPOST:\n{text}"
        )
        return self._generate(prompt).strip()

    def choose_order(self, posts: list[dict[str, Any]]) -> list[int]:
        """Return the optimal send order as a list of original indices."""
        brief = "\n".join(f"{i}. {p.get('text', '')[:200]}" for i, p in enumerate(posts))
        prompt = (
            "You are scheduling a Telegram channel. Given these posts, return the best "
            "publishing order as a JSON array of the original indices, e.g. [2,0,1]. "
            "Consider variety and narrative flow. Respond with ONLY the JSON array."
            f"\n\nPOSTS:\n{brief}"
        )
        raw = self._generate(prompt).strip()
        # tolerate code fences
        raw = raw.strip("`").replace("json", "", 1).strip()
        try:
            order = json.loads(raw)
            return [int(x) for x in order if isinstance(x, (int, float))]
        except (json.JSONDecodeError, ValueError):
            return list(range(len(posts)))
