"""DB-free JSON file store for scheduled posts.

Posts are persisted to ``storage/posts.json``. Each post record:

    {
        "id": "uuid4",
        "text": "caption text",
        "media": [{"kind": "photo|video", "path": "storage/media/xxx.jpg"}],
        "target": "@inglizguru" | null,
        "parse_mode": "HTML" | null,
        "schedule": {
            "mode": "once" | "recurring",
            "run_at": "ISO8601" (once) | null,
            "every_hours": 24 (recurring) | null,
            "next_run": "ISO8601" (computed),
            "end_at": "ISO8601" | null,
        },
        "ai": {"rewrite": true, "language": "uz", "choose_order": true, "choose_time": false},
        "status": "pending" | "sent" | "failed" | "paused",
        "created_at": "ISO8601",
        "sent_at": "ISO8601" | null,
        "last_error": str | null,
        "send_count": int,
    }
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from kalibr_publisher.core.config import get_settings

_lock = threading.RLock()
_STORE_PATH: Optional[Path] = None


def _store_path() -> Path:
    global _STORE_PATH
    if _STORE_PATH is None:
        settings = get_settings()
        root = Path(getattr(settings, "storage_root", "storage"))
        _STORE_PATH = root / "posts.json"
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not _STORE_PATH.exists():
            _STORE_PATH.write_text("[]", encoding="utf-8")
    return _STORE_PATH


@dataclass
class MediaRef:
    kind: str  # "photo" | "video"
    path: str  # relative to media_root, e.g. "storage/media/uuid.jpg"


@dataclass
class Schedule:
    mode: str = "once"  # "once" | "recurring"
    run_at: Optional[str] = None  # ISO8601 for once
    every_hours: Optional[int] = None  # for recurring
    next_run: Optional[str] = None
    end_at: Optional[str] = None


@dataclass
class AiConfig:
    rewrite: bool = True
    language: str = "uz"
    choose_order: bool = True
    choose_time: bool = False


@dataclass
class Post:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    text: str = ""
    media: list[MediaRef] = field(default_factory=list)
    target: Optional[str] = None
    parse_mode: Optional[str] = "HTML"
    schedule: Schedule = field(default_factory=Schedule)
    ai: AiConfig = field(default_factory=AiConfig)
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_at: Optional[str] = None
    last_error: Optional[str] = None
    send_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def to_out(self) -> dict[str, Any]:
        """Dict shaped for the PostOut API schema."""
        return {
            "id": self.id,
            "text": self.text,
            "media": [{"kind": m.kind, "path": m.path} for m in self.media],
            "target": self.target,
            "parse_mode": self.parse_mode,
            "schedule": {
                "mode": self.schedule.mode,
                "run_at": self.schedule.run_at,
                "every_hours": self.schedule.every_hours,
                "end_at": self.schedule.end_at,
            },
            "ai": {
                "rewrite": self.ai.rewrite,
                "language": self.ai.language,
                "choose_order": self.ai.choose_order,
                "choose_time": self.ai.choose_time,
            },
            "status": self.status,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "last_error": self.last_error,
            "send_count": self.send_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Post":
        d = dict(d)
        d["media"] = [MediaRef(**m) for m in d.get("media", [])]
        d["schedule"] = Schedule(**(d.get("schedule") or {}))
        d["ai"] = AiConfig(**(d.get("ai") or {}))
        return cls(**d)


def _load() -> list[Post]:
    with _lock:
        raw = _store_path().read_text(encoding="utf-8") or "[]"
        return [Post.from_dict(x) for x in json.loads(raw)]


def _save(posts: list[Post]) -> None:
    with _lock:
        data = json.dumps([p.to_dict() for p in posts], ensure_ascii=False, indent=2)
        _store_path().write_text(data, encoding="utf-8")


def list_posts(status: Optional[str] = None) -> list[Post]:
    posts = _load()
    if status:
        posts = [p for p in posts if p.status == status]
    return sorted(posts, key=lambda p: p.created_at)


def get_post(post_id: str) -> Optional[Post]:
    for p in _load():
        if p.id == post_id:
            return p
    return None


def create_post(
    text: str,
    media: Optional[list[MediaRef]] = None,
    target: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    schedule: Optional[Schedule] = None,
    ai: Optional[AiConfig] = None,
) -> Post:
    post = Post(
        text=text,
        media=media or [],
        target=target,
        parse_mode=parse_mode,
        schedule=schedule or Schedule(),
        ai=ai or AiConfig(),
    )
    _compute_next_run(post)
    with _lock:
        posts = _load()
        posts.append(post)
        _save(posts)
    return post


def update_post(post: Post) -> None:
    _compute_next_run(post)
    with _lock:
        posts = _load()
        for i, p in enumerate(posts):
            if p.id == post.id:
                posts[i] = post
                break
        _save(posts)


def delete_post(post_id: str) -> bool:
    with _lock:
        posts = _load()
        new = [p for p in posts if p.id != post_id]
        if len(new) == len(posts):
            return False
        _save(new)
        return True


def _compute_next_run(post: Post) -> None:
    """Set schedule.next_run based on mode."""
    sched = post.schedule
    now = datetime.now(timezone.utc)
    if sched.mode == "once":
        if sched.run_at:
            parsed = _parse_dt(sched.run_at)
            sched.next_run = (parsed or now).isoformat()
        else:
            sched.next_run = now.isoformat()
    elif sched.mode == "recurring":
        if sched.next_run and datetime.fromisoformat(sched.next_run) > now:
            return  # keep existing future run
        sched.next_run = now.isoformat()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO8601 string into an aware (UTC) datetime.

    Naive values (no timezone, e.g. from a datetime-local input) are
    interpreted as UTC so comparisons against ``datetime.now(timezone.utc)``
    never raise TypeError.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def due_posts(now: Optional[datetime] = None) -> list[Post]:
    now = now or datetime.now(timezone.utc)
    out = []
    for p in _load():
        if p.status != "pending":
            continue
        nxt = _parse_dt(p.schedule.next_run)
        if nxt is None:
            continue
        if nxt <= now:
            out.append(p)
    return out


def advance_recurring(post: Post) -> None:
    """After sending a recurring post, push next_run forward."""
    sched = post.schedule
    last = datetime.now(timezone.utc)
    post.send_count += 1
    post.sent_at = last.isoformat()
    if sched.mode != "recurring":
        post.status = "sent"
        return
    every = sched.every_hours or 24
    nxt = last + timedelta(hours=every)
    end = _parse_dt(sched.end_at)
    if end and nxt >= end:
        post.status = "sent"
    else:
        sched.next_run = nxt.isoformat()
