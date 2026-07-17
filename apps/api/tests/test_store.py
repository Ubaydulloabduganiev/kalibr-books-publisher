"""Tests for the atomic JSON post store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from kalibr_publisher.core import store
from kalibr_publisher.core.store import (
    MediaRef,
    PostDraft,
    Schedule,
    advance_recurring,
    claim_post,
    configure_store,
    create_post,
    create_posts,
    delete_post,
    due_posts,
    get_post,
    list_posts,
    recover_interrupted_publications,
    update_post,
)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path: Path):
    configure_store(tmp_path / "posts.json")
    yield
    configure_store(None)


def test_create_get_list_update_and_delete() -> None:
    post = create_post(text="hello", target="@kalibr_books")
    assert get_post(post.id) is not None
    assert list_posts()[0].text == "hello"

    post.text = "updated"
    update_post(post)
    assert get_post(post.id).text == "updated"  # type: ignore[union-attr]

    assert delete_post(post.id) is True
    assert delete_post(post.id) is False


def test_due_posts_and_future_post() -> None:
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    create_post(text="later", schedule=Schedule(mode="once", run_at=future))
    immediate = create_post(text="now", schedule=Schedule(mode="once"))

    due = due_posts()
    assert [post.id for post in due] == [immediate.id]


def test_advance_recurring_and_end_date() -> None:
    recurring = create_post(text="repeat", schedule=Schedule(mode="recurring", every_hours=24))
    advance_recurring(recurring)
    assert recurring.status == "pending"
    assert recurring.send_count == 1
    assert recurring.schedule.next_run is not None

    ending = create_post(
        text="ending",
        schedule=Schedule(
            mode="recurring",
            every_hours=24,
            end_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        ),
    )
    advance_recurring(ending)
    assert ending.status == "sent"


def test_media_ref_persists_and_unknown_legacy_field_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(
        '[{"id":"1","text":"m","media":[{"kind":"photo","path":"media/x.jpg"}],'
        '"schedule":{},"legacy_extra":{"enabled":true}}]',
        encoding="utf-8",
    )
    configure_store(path)

    post = list_posts()[0]
    assert post.media == [MediaRef(kind="photo", path="media/x.jpg")]


def test_corrupt_store_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("not-json", encoding="utf-8")
    configure_store(path)
    with pytest.raises(RuntimeError, match="corrupted"):
        store.list_posts()


def test_claim_is_atomic_and_interrupted_claim_is_recovered() -> None:
    post = create_post(text="claim me")

    claimed = claim_post(post.id)
    assert claimed is not None
    assert claimed.status == "publishing"
    assert claim_post(post.id) is None

    assert recover_interrupted_publications() == 1
    recovered = get_post(post.id)
    assert recovered is not None
    assert recovered.status == "delivery_uncertain"
    assert "Check the channel" in (recovered.last_error or "")


def test_batch_create_writes_all_posts() -> None:
    created = create_posts([PostDraft(text="one"), PostDraft(text="two")])

    assert [post.text for post in created] == ["one", "two"]
    assert [post.text for post in list_posts()] == ["one", "two"]
