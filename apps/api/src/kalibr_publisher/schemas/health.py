"""Health and application metadata response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Result of one readiness dependency check."""

    status: Literal["pass", "fail"]
    details: dict[str, Any]


class HealthResponse(BaseModel):
    """Liveness or readiness response."""

    status: Literal["ok", "degraded"]
    service: str
    version: str
    timestamp: datetime
    checks: dict[str, HealthCheck] = Field(default_factory=dict)


class ApplicationMetaResponse(BaseModel):
    """Non-sensitive application settings required by the frontend."""

    name: str
    version: str
    environment: str
    timezone: str
    default_locale: str
    supported_locales: list[str]
