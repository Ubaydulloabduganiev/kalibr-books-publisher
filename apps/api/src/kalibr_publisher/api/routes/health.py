"""Liveness, readiness, and public application metadata endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response, status

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.runtime import check_writable_directory
from kalibr_publisher.schemas.health import (
    ApplicationMetaResponse,
    HealthCheck,
    HealthResponse,
)

router = APIRouter(tags=["system"])


def _settings(request: Request) -> Settings:
    value = request.app.state.settings
    if not isinstance(value, Settings):
        msg = "Application settings are unavailable"
        raise RuntimeError(msg)
    return value


@router.get("/health/live", response_model=HealthResponse, summary="Process liveness")
async def liveness(request: Request) -> HealthResponse:
    """Confirm the API process is running and able to serve requests."""
    settings = _settings(request)
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    summary="Dependency readiness",
    responses={503: {"model": HealthResponse}},
)
async def readiness(request: Request, response: Response) -> HealthResponse:
    """Verify all Phase 1 persistent directories are writable."""
    settings = _settings(request)
    checks: dict[str, HealthCheck] = {}
    paths = {
        "storage": settings.storage_root,
        "backups": settings.backup_root,
        "temporary": settings.temp_root,
        "logs": settings.log_root,
    }

    for name, path in paths.items():
        try:
            checks[name] = HealthCheck(status="pass", details=check_writable_directory(path))
        except OSError as exc:
            checks[name] = HealthCheck(
                status="fail",
                details={"path": str(path), "error": type(exc).__name__},
            )

    all_checks_pass = all(check.status == "pass" for check in checks.values())
    overall_status: Literal["ok", "degraded"] = "ok" if all_checks_pass else "degraded"
    if overall_status == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        checks=checks,
    )


@router.get("/meta", response_model=ApplicationMetaResponse, summary="Application metadata")
async def application_metadata(request: Request) -> ApplicationMetaResponse:
    """Expose non-sensitive settings used to configure the administration UI."""
    settings = _settings(request)
    return ApplicationMetaResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timezone=settings.timezone,
        default_locale=settings.default_locale,
        supported_locales=list(settings.supported_locales),
    )
