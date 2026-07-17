"""Runtime filesystem preparation and health verification."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from kalibr_publisher.core.config import Settings


def ensure_runtime_directories(settings: Settings) -> None:
    """Create required directories and fail startup when persistence is unavailable."""
    for directory in settings.runtime_directories:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise OSError(f"Runtime path is not a directory: {directory}")


def check_writable_directory(path: Path) -> dict[str, int | str]:
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".kalibr-health-", dir=path) as probe:
        probe.write(b"ok")
        probe.flush()
    usage = shutil.disk_usage(path)
    return {"path": str(path), "free_bytes": usage.free, "total_bytes": usage.total}
