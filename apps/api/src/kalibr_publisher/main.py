"""FastAPI application factory and process entry point."""

from __future__ import annotations

try:
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    import structlog
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    from kalibr_publisher.api.router import api_router
    from kalibr_publisher.core.config import Settings, get_settings
    from kalibr_publisher.core.errors import register_exception_handlers
    from kalibr_publisher.core.logging import configure_logging
    from kalibr_publisher.core.middleware import (
        RequestContextMiddleware,
        SecurityHeadersMiddleware,
    )
    from kalibr_publisher.core.runtime import ensure_runtime_directories
    from kalibr_publisher.services.scheduler import start_scheduler, stop_scheduler

    logger = structlog.get_logger(__name__)

    def create_app(settings: Settings | None = None) -> FastAPI:
        """Build an isolated application instance for production and tests."""
        resolved_settings = settings or get_settings()
        configure_logging(resolved_settings)

        @asynccontextmanager
        async def lifespan(_: FastAPI) -> AsyncIterator[None]:
            ensure_runtime_directories(resolved_settings)
            logger.info(
                "application_started",
                app_name=resolved_settings.app_name,
                version=resolved_settings.app_version,
                environment=resolved_settings.app_env,
            )
            scheduler_task = start_scheduler()
            try:
                yield
            finally:
                if scheduler_task is not None:
                    stop_scheduler()
                    scheduler_task.cancel()
            logger.info("application_stopped", app_name=resolved_settings.app_name)

        docs_url = "/docs" if resolved_settings.docs_enabled else None
        redoc_url = "/redoc" if resolved_settings.docs_enabled else None
        openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None

        application = FastAPI(
            title=resolved_settings.app_name,
            version=resolved_settings.app_version,
            description="Internal publishing and Telegram scheduling platform for Kalibr Books.",
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
            lifespan=lifespan,
        )
        application.state.settings = resolved_settings

        application.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        )
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=resolved_settings.allowed_hosts,
        )
        application.add_middleware(SecurityHeadersMiddleware)
        application.add_middleware(
            RequestContextMiddleware,
            request_id_header=resolved_settings.request_id_header,
        )

        register_exception_handlers(application, resolved_settings)
        application.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
        return application

    app = create_app()
except BaseException as _boot_err:  # pragma: no cover - defensive boot guard
    import traceback

    _tb = traceback.format_exc()
    print("BOOT_FAILURE:\n" + _tb, flush=True)

    from fastapi import FastAPI as _F

    app = _F()

    @app.get("/api/v1/health/live")
    async def _boot_health():
        return {"status": "boot_failed", "error": _tb}

    @app.get("/api/v1/meta")
    async def _boot_meta():
        return {"status": "boot_failed", "error": _tb}
