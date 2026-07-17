"""Prepare mounted data directories, drop root privileges, and start the service."""
from __future__ import annotations

import os
import pwd
import sys
from pathlib import Path


def _configured_paths() -> list[Path]:
    defaults = {
        "STORAGE_ROOT": "/data/storage",
        "BACKUP_ROOT": "/data/backups",
        "TEMP_ROOT": "/data/tmp",
        "LOG_ROOT": "/data/logs",
    }
    return [Path(os.getenv(name, default)) for name, default in defaults.items()]


def _chown_tree(path: Path, uid: int, gid: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if path.stat().st_uid == uid and path.stat().st_gid == gid:
        return
    for root, directories, files in os.walk(path):
        root_path = Path(root)
        os.chown(root_path, uid, gid, follow_symlinks=False)
        for name in directories:
            os.chown(root_path / name, uid, gid, follow_symlinks=False)
        for name in files:
            os.chown(root_path / name, uid, gid, follow_symlinks=False)


def _prepare_and_drop_privileges(username: str = "kalibr") -> None:
    if os.geteuid() != 0:
        return
    account = pwd.getpwnam(username)
    for path in _configured_paths():
        _chown_tree(path, account.pw_uid, account.pw_gid)
    os.initgroups(username, account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("No command supplied")
    _prepare_and_drop_privileges()
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
