"""System endpoint and middleware tests."""

from httpx import AsyncClient

from kalibr_publisher.core.config import Settings


async def test_root_explains_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health/ready"


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Kalibr Publisher"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert len(response.headers["x-request-id"]) == 32


async def test_readiness_checks_every_runtime_directory(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["checks"]) == {"storage", "media", "backups", "temporary", "logs"}
    assert all(check["status"] == "pass" for check in body["checks"].values())
    assert all(check["details"]["free_bytes"] > 0 for check in body["checks"].values())
    assert all("path" not in check["details"] for check in body["checks"].values())


async def test_valid_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "browser-session:request-1"},
    )

    assert response.headers["x-request-id"] == "browser-session:request-1"


async def test_unsafe_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "unsafe value with spaces"},
    )

    assert response.headers["x-request-id"] != "unsafe value with spaces"
    assert len(response.headers["x-request-id"]) == 32


async def test_application_metadata_contains_no_runtime_paths(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["default_locale"] == "uz"
    assert body["supported_locales"] == ["uz", "ru"]
    assert "storage_root" not in body
    assert "backup_root" not in body


async def test_not_found_uses_standard_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_404"
    assert error["request_id"] == response.headers["x-request-id"]
    assert error["recovery_suggestion"]


async def test_readiness_reports_unwritable_runtime_path(
    client: AsyncClient,
    settings: Settings,
) -> None:
    storage_root = settings.storage_root
    for item in storage_root.iterdir():
        if item.is_dir():
            item.rmdir()
        else:
            item.unlink()
    storage_root.rmdir()
    storage_root.write_text("not a directory", encoding="utf-8")

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["storage"]["status"] == "fail"


async def test_corrupt_post_store_prevents_application_startup(
    settings: Settings,
) -> None:
    import pytest

    from kalibr_publisher.main import create_app

    settings.storage_root.mkdir(parents=True, exist_ok=True)
    (settings.storage_root / "posts.json").write_text("not-json", encoding="utf-8")
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="corrupted"):
        async with app.router.lifespan_context(app):
            pass
