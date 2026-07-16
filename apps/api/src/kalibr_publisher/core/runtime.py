"""Runtime filesystem preparation and health verification."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from kalibr_publisher.core.config import Settings


def ensure_runtime_directories(settings: Settings) -> None:
    """Create configured runtime directories; best-effort so startup never fails.

    On platforms where the configured paths are not writable (e.g. a missing
    persistent disk), we log and continue rather than crashing the process.
    """
    import logging

    logger = logging.getLogger(__name__)
    for directory in settings.runtime_directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("runtime_directory_unavailable", path=str(directory), error=str(exc))
        if not directory.is_dir():
            logger.warning("runtime_path_not_a_directory", path=str(directory))


def check_writable_directory(path: Path) -> dict[str, int | str]:
    """Verify a directory can create files and report free disk capacity."""
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".kalibr-health-", dir=path) as probe:
        probe.write(b"ok")
        probe.flush()

    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "free_bytes": usage.free,
        "total_bytes": usage.total,
    }
