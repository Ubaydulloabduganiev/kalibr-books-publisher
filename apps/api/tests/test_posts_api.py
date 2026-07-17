"""API endpoint tests for posts and uploads."""

from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.store import claim_post, get_post, update_post
from kalibr_publisher.main import create_app


async def test_create_list_get_schedule_and_delete(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/posts",
        json={
            "text": "hello world",
            "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
        },
    )
    assert created.status_code == 201, created.text
    post_id = created.json()["id"]

    listed = await client.get("/api/v1/posts")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    fetched = await client.get(f"/api/v1/posts/{post_id}")
    assert fetched.json()["text"] == "hello world"

    scheduled = await client.post(
        f"/api/v1/posts/{post_id}/schedule",
        json={"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["schedule"]["run_at"].startswith("2030-01-01T12:00:00")

    deleted = await client.delete(f"/api/v1/posts/{post_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404


async def test_bulk_create(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/posts/bulk",
        json={
            "posts": [
                {"text": "a", "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"}},
                {"text": "b", "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"}},
            ]
        },
    )
    assert response.status_code == 201
    assert response.json()["created"] == 2


async def test_schedule_validation(client: AsyncClient) -> None:
    recurring = await client.post(
        "/api/v1/posts", json={"text": "bad", "schedule": {"mode": "recurring"}}
    )
    assert recurring.status_code == 422

    recurring_without_start = await client.post(
        "/api/v1/posts",
        json={"text": "bad", "schedule": {"mode": "recurring", "every_hours": 24}},
    )
    assert recurring_without_start.status_code == 422

    missing_time = await client.post(
        "/api/v1/posts", json={"text": "bad", "schedule": {"mode": "once"}}
    )
    assert missing_time.status_code == 422

    naive = await client.post(
        "/api/v1/posts",
        json={"text": "bad", "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00"}},
    )
    assert naive.status_code == 422


async def test_media_path_and_album_validation(client: AsyncClient) -> None:
    outside = await client.post(
        "/api/v1/posts",
        json={
            "text": "bad",
            "media": [{"kind": "photo", "path": "../secret.jpg"}],
            "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
        },
    )
    assert outside.status_code == 422

    invalid_album = await client.post(
        "/api/v1/posts",
        json={
            "text": "bad",
            "media": [
                {"kind": "document", "path": "media/a.pdf"},
                {"kind": "photo", "path": "media/b.jpg"},
            ],
            "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
        },
    )
    assert invalid_album.status_code == 422


async def test_upload_supported_media(client: AsyncClient, settings: Settings) -> None:
    png = await client.post(
        "/api/v1/posts/upload",
        files={"file": ("cover.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert png.status_code == 201, png.text
    assert png.json()["kind"] == "photo"
    assert (settings.storage_root / png.json()["path"]).is_file()

    pdf = await client.post(
        "/api/v1/posts/upload",
        files={"file": ("book.pdf", b"%PDF-1.7\ncontent", "application/pdf")},
    )
    assert pdf.status_code == 201
    assert pdf.json()["kind"] == "document"


async def test_upload_rejects_spoofed_and_empty_files(client: AsyncClient) -> None:
    spoofed = await client.post(
        "/api/v1/posts/upload",
        files={"file": ("fake.png", b"not a png", "image/png")},
    )
    assert spoofed.status_code == 400

    empty = await client.post(
        "/api/v1/posts/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty.status_code == 400


async def test_production_write_endpoint_requires_gateway_key(tmp_path: Path) -> None:
    settings = Settings(
        app_env="production",
        allowed_hosts=["testserver"],
        cors_origins=[],
        internal_api_key="correct-secret",
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        scheduler_poll_seconds=3600,
        _env_file=None,
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        rejected = await client.post(
            "/api/v1/posts",
            json={
                "text": "no key",
                "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
            },
        )
        accepted = await client.post(
            "/api/v1/posts",
            json={
                "text": "with key",
                "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
            },
            headers={"X-Internal-API-Key": "correct-secret"},
        )

    assert rejected.status_code == 401
    assert accepted.status_code == 201


async def test_publishing_post_cannot_be_deleted_or_rescheduled(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/posts",
        json={
            "text": "in flight",
            "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
        },
    )
    post_id = created.json()["id"]
    assert claim_post(post_id) is not None

    deleted = await client.delete(f"/api/v1/posts/{post_id}")
    rescheduled = await client.post(
        f"/api/v1/posts/{post_id}/schedule",
        json={"mode": "once", "run_at": "2031-01-01T12:00:00+05:00"},
    )

    assert deleted.status_code == 409
    assert rescheduled.status_code == 409
    assert deleted.json()["error"]["code"] == "post_is_publishing"


async def test_published_history_cannot_be_deleted_or_rescheduled(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/posts",
        json={
            "text": "already sent",
            "schedule": {"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"},
        },
    )
    post_id = created.json()["id"]
    post = get_post(post_id)
    assert post is not None
    post.status = "sent"
    update_post(post)

    deleted = await client.delete(f"/api/v1/posts/{post_id}")
    rescheduled = await client.post(
        f"/api/v1/posts/{post_id}/schedule",
        json={"mode": "once", "run_at": "2031-01-01T12:00:00+05:00"},
    )

    assert deleted.status_code == 409
    assert deleted.json()["error"]["code"] == "post_history_protected"
    assert rescheduled.status_code == 409
    assert rescheduled.json()["error"]["code"] == "post_already_published"
