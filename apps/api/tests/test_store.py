"""Tests for the JSON post store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kalibr_publisher.core.store import (
    MediaRef,
    Schedule,
    advance_recurring,
    create_post,
    delete_post,
    due_posts,
    get_post,
    list_posts,
    update_post,
)


def setup_function(fn):
    # each test starts clean
    import kalibr_publisher.core.store as store
    store._STORE_PATH = None
    import os
    p = os.path.join(store.get_settings().storage_root, "posts.json")
    if os.path.exists(p):
        os.remove(p)


def test_create_and_get():
    p = create_post(text="hello", target="@inglizguru")
    assert p.id
    got = get_post(p.id)
    assert got is not None
    assert got.text == "hello"


def test_list_and_delete():
    p = create_post(text="x")
    assert any(x.id == p.id for x in list_posts())
    assert delete_post(p.id) is True
    assert get_post(p.id) is None


def test_due_posts_once():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    create_post(text="later", schedule=Schedule(mode="once", run_at=future))
    now = create_post(text="now", schedule=Schedule(mode="once"))
    due = due_posts()
    assert any(x.text == "now" for x in due)
    assert not any(x.text == "later" for x in due)


def test_advance_recurring():
    p = create_post(text="r", schedule=Schedule(mode="recurring", every_hours=24))
    p.status = "pending"
    advance_recurring(p)
    assert p.send_count == 1
    assert p.schedule.next_run is not None


def test_media_ref_persist():
    p = create_post(text="m", media=[MediaRef(kind="photo", path="storage/media/x.jpg")])
    got = get_post(p.id)
    assert got.media[0].kind == "photo"
