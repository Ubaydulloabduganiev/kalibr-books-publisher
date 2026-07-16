"""API endpoint tests for posts router."""

from __future__ import annotations

import os
import tempfile

from fastapi.testclient import TestClient

from kalibr_publisher.main import create_app


def setup_function(fn):
    import kalibr_publisher.core.store as store
    store._STORE_PATH = None
    p = os.path.join(store.get_settings().storage_root, "posts.json")
    if os.path.exists(p):
        os.remove(p)


def _client():
    return TestClient(create_app())


def test_create_post():
    c = _client()
    r = c.post("/api/v1/posts", json={"text": "hello world", "target": "default"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["text"] == "hello world"
    assert body["id"]


def test_bulk_create():
    c = _client()
    r = c.post("/api/v1/posts/bulk", json={"posts": [{"text": "a"}, {"text": "b"}]})
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2


def test_list_posts():
    c = _client()
    c.post("/api/v1/posts", json={"text": "x"})
    r = c.get("/api/v1/posts")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
    assert len(r.json()["posts"]) >= 1


def test_get_and_delete():
    c = _client()
    pid = c.post("/api/v1/posts", json={"text": "y"}).json()["id"]
    r = c.get(f"/api/v1/posts/{pid}")
    assert r.status_code == 200 and r.json()["text"] == "y"
    d = c.delete(f"/api/v1/posts/{pid}")
    assert d.status_code == 200 and d.json()["deleted"] is True
    missing = c.get(f"/api/v1/posts/{pid}")
    assert missing.status_code == 404


def test_schedule_endpoint():
    c = _client()
    pid = c.post("/api/v1/posts", json={"text": "s"}).json()["id"]
    r = c.post(f"/api/v1/posts/{pid}/schedule", json={"mode": "once", "run_at": "2030-01-01T12:00:00+05:00"})
    assert r.status_code == 200, r.text
    assert r.json()["schedule"]["mode"] == "once"


def test_upload_endpoint():
    c = _client()
    fd, path = tempfile.mkstemp(suffix=".png")
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n fake")
    os.close(fd)
    with open(path, "rb") as f:
        r = c.post("/api/v1/posts/upload", files={"file": ("t.png", f, "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"].endswith(".png")
    assert body["kind"] == "photo"
    os.remove(path)
