"""Atomic JSON post store used until the SQLAlchemy phase is introduced.

The store is intentionally single-process. Production must run exactly one API worker
until scheduled posts are migrated to a transactional database-backed queue.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from kalibr_publisher.core.config import get_settings

_lock = threading.RLock()
_STORE_PATH: Path | None = None


def configure_store(path: Path | None) -> None:
    """Set the process-wide store path before serving requests."""
    global _STORE_PATH
    with _lock:
        _STORE_PATH = path


def _store_path() -> Path:
    path = _STORE_PATH or (get_settings().storage_root / "posts.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _atomic_write(path, "[]")
    return path


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(slots=True)
class MediaRef:
    kind: str
    path: str


@dataclass(slots=True)
class Schedule:
    mode: str = "once"
    run_at: str | None = None
    every_hours: int | None = None
    next_run: str | None = None
    end_at: str | None = None


@dataclass(slots=True)
class PostDraft:
    text: str
    index: int = 0
    media: list[MediaRef] = field(default_factory=list)
    target: str | None = None
    parse_mode: str | None = None
    schedule: Schedule = field(default_factory=Schedule)


@dataclass(slots=True)
class Post:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    text: str = ""
    media: list[MediaRef] = field(default_factory=list)
    target: str | None = None
    parse_mode: str | None = None
    schedule: Schedule = field(default_factory=Schedule)
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    sent_at: str | None = None
    last_error: str | None = None
    send_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Post:
        data = dict(raw)
        allowed = {item.name for item in fields(cls)}
        data = {key: value for key, value in data.items() if key in allowed}
        data["media"] = [MediaRef(**item) for item in data.get("media", [])]
        data["schedule"] = Schedule(**(data.get("schedule") or {}))
        return cls(**data)


def _load_unlocked() -> list[Post]:
    path = _store_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Post store is corrupted: {path}") from exc
    if not isinstance(raw, list):
        raise RuntimeError(f"Post store must contain a JSON array: {path}")
    return [Post.from_dict(item) for item in raw]


def _save_unlocked(posts: list[Post]) -> None:
    data = json.dumps([post.to_dict() for post in posts], ensure_ascii=False, indent=2)
    _atomic_write(_store_path(), data)


def list_posts(status: str | None = None) -> list[Post]:
    with _lock:
        posts = _load_unlocked()
    if status:
        posts = [post for post in posts if post.status == status]
    return sorted(posts, key=lambda post: (post.schedule.next_run or "", post.created_at, post.id))


def get_post(post_id: str) -> Post | None:
    with _lock:
        return next((post for post in _load_unlocked() if post.id == post_id), None)


def create_posts(drafts: list[PostDraft]) -> list[Post]:
    """Create multiple posts with one store read and one atomic write."""
    if not drafts:
        return []
    created = [
        Post(
            text=draft.text,
            media=list(draft.media),
            target=draft.target,
            parse_mode=draft.parse_mode,
            schedule=draft.schedule,
        )
        for draft in drafts
    ]
    for post in created:
        _compute_next_run(post)
    with _lock:
        posts = _load_unlocked()
        posts.extend(created)
        _save_unlocked(posts)
    return created


def create_post(
    text: str,
    media: list[MediaRef] | None = None,
    target: str | None = None,
    parse_mode: str | None = None,
    schedule: Schedule | None = None,
) -> Post:
    return create_posts(
        [
            PostDraft(
                text=text,
                media=media or [],
                target=target,
                parse_mode=parse_mode,
                schedule=schedule or Schedule(),
            )
        ]
    )[0]


def update_post(post: Post) -> None:
    _compute_next_run(post)
    with _lock:
        posts = _load_unlocked()
        for index, current in enumerate(posts):
            if current.id == post.id:
                posts[index] = post
                _save_unlocked(posts)
                return
        raise KeyError(f"Post not found: {post.id}")


def claim_post(post_id: str) -> Post | None:
    """Atomically move a pending post into the publishing state."""
    with _lock:
        posts = _load_unlocked()
        for post in posts:
            if post.id != post_id or post.status != "pending":
                continue
            post.status = "publishing"
            post.last_error = None
            _save_unlocked(posts)
            return post
    return None


def recover_interrupted_publications() -> int:
    """Mark in-flight posts as uncertain after an unclean process restart."""
    with _lock:
        posts = _load_unlocked()
        recovered = 0
        for post in posts:
            if post.status != "publishing":
                continue
            post.status = "delivery_uncertain"
            post.last_error = (
                "The service restarted while Telegram delivery was in progress. "
                "Check the channel before retrying."
            )
            recovered += 1
        if recovered:
            _save_unlocked(posts)
        return recovered


def delete_post(post_id: str) -> bool:
    with _lock:
        posts = _load_unlocked()
        remaining = [post for post in posts if post.id != post_id]
        if len(remaining) == len(posts):
            return False
        _save_unlocked(remaining)
        return True


def _compute_next_run(post: Post) -> None:
    schedule = post.schedule
    now = datetime.now(UTC)
    if schedule.mode == "once":
        schedule.next_run = (_parse_dt(schedule.run_at) or now).isoformat()
        return
    if schedule.next_run and (_parse_dt(schedule.next_run) or now) > now:
        return
    schedule.next_run = (_parse_dt(schedule.run_at) or now).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def due_posts(now: datetime | None = None) -> list[Post]:
    threshold = now or datetime.now(UTC)
    return [
        post
        for post in list_posts(status="pending")
        if (next_run := _parse_dt(post.schedule.next_run)) is not None and next_run <= threshold
    ]


def advance_recurring(post: Post) -> None:
    sent_at = datetime.now(UTC)
    post.send_count += 1
    post.sent_at = sent_at.isoformat()
    if post.schedule.mode != "recurring":
        post.status = "sent"
        return
    next_run = sent_at + timedelta(hours=post.schedule.every_hours or 24)
    end_at = _parse_dt(post.schedule.end_at)
    if end_at and next_run >= end_at:
        post.status = "sent"
        return
    post.status = "pending"
    post.schedule.next_run = next_run.isoformat()
