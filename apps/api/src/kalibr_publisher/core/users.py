"""JSON-backed user account store.

Mirrors :mod:`kalibr_publisher.core.store` (atomic writes, single-process). Until a
database is introduced this is the source of truth for admin-managed accounts.
Passwords are never stored in clear text (see :mod:`kalibr_publisher.core.security`).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kalibr_publisher.core.config import get_settings
from kalibr_publisher.core.security import generate_secure_token, hash_password

_lock = threading.RLock()
_STORE_PATH: Path | None = None


def configure_user_store(path: Path | None) -> None:
    """Set the process-wide user store path before serving requests."""
    global _STORE_PATH
    with _lock:
        _STORE_PATH = path


@dataclass(slots=True)
class User:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    username: str = ""
    display_name: str = ""
    role: str = "editor"  # "admin" | "editor"
    password_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> User:
        allowed = {"id", "username", "display_name", "role", "password_hash", "created_at", "updated_at"}
        data = {key: value for key, value in raw.items() if key in allowed}
        if "id" not in data:
            data["id"] = uuid.uuid4().hex
        if "role" not in data:
            data["role"] = "editor"
        return cls(**data)


def _store_path() -> Path:
    path = _STORE_PATH or (get_settings().storage_root / "users.json")
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


def _load_unlocked() -> list[User]:
    path = _store_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"User store is corrupted: {path}") from exc
    if not isinstance(raw, list):
        raise RuntimeError(f"User store must contain a JSON array: {path}")
    return [User.from_dict(item) for item in raw]


def _save_unlocked(users: list[User]) -> None:
    data = json.dumps([asdict(user) for user in users], ensure_ascii=False, indent=2)
    _atomic_write(_store_path(), data)


def list_users() -> list[User]:
    with _lock:
        return _load_unlocked()


def get_user(user_id: str) -> User | None:
    with _lock:
        return next((user for user in _load_unlocked() if user.id == user_id), None)


def get_user_by_username(username: str) -> User | None:
    needle = username.strip().lower()
    with _lock:
        return next((user for user in _load_unlocked() if user.username.lower() == needle), None)


def create_user(
    *,
    username: str,
    password: str,
    display_name: str = "",
    role: str = "editor",
) -> User:
    if not username or not username.strip():
        raise ValueError("username is required")
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if role not in {"admin", "editor"}:
        raise ValueError("role must be 'admin' or 'editor'")
    username = username.strip()
    with _lock:
        users = _load_unlocked()
        if any(user.username.lower() == username.lower() for user in users):
            raise ValueError("username already exists")
        user = User(
            username=username,
            display_name=display_name.strip() or username,
            role=role,
            password_hash=hash_password(password),
        )
        users.append(user)
        _save_unlocked(users)
        return user


def update_password(user_id: str, new_password: str) -> User:
    if not new_password or len(new_password) < 8:
        raise ValueError("password must be at least 8 characters")
    with _lock:
        users = _load_unlocked()
        for index, user in enumerate(users):
            if user.id == user_id:
                user.password_hash = hash_password(new_password)
                user.updated_at = datetime.now(UTC).isoformat()
                users[index] = user
                _save_unlocked(users)
                return user
        raise KeyError(f"User not found: {user_id}")


def delete_user(user_id: str) -> bool:
    with _lock:
        users = _load_unlocked()
        remaining = [user for user in users if user.id != user_id]
        if len(remaining) == len(users):
            return False
        _save_unlocked(remaining)
        return True


def seed_admin_from_env() -> None:
    """Ensure the bootstrap admin account exists from ADMIN_BASIC_* env vars.

    Runs at startup so the very first admin can log in even before any account is
    created through the UI. If the account already exists, its password is refreshed
    from the environment so dashboard rotations take effect.
    """
    settings = get_settings()
    username = (os.environ.get("ADMIN_BASIC_USERNAME") or "admin").strip()
    password = os.environ.get("ADMIN_BASIC_PASSWORD")
    if not password:
        return
    with _lock:
        users = _load_unlocked()
        existing = next((user for user in users if user.username.lower() == username.lower()), None)
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.updated_at = datetime.now(UTC).isoformat()
        else:
            users.append(
                User(
                    username=username,
                    display_name="Administrator",
                    role="admin",
                    password_hash=hash_password(password),
                )
            )
        _save_unlocked(users)
