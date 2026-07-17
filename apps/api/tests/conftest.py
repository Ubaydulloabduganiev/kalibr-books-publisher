"""Shared API test fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("API_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
os.environ.setdefault("APP_ENV", "test")

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.store import configure_store
from kalibr_publisher.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create isolated settings whose runtime paths never touch developer data."""
    return Settings(
        app_env="test",
        allowed_hosts=["testserver", "localhost"],
        cors_origins=["http://localhost:3000"],
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        log_format="json",
        scheduler_poll_seconds=3600,
        _env_file=None,
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """Yield an async client with explicit application lifespan handling."""
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as test_client,
    ):
        yield test_client
    configure_store(None)
