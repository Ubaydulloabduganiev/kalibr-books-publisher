"""Standalone boot probe — surfaces kalibr_publisher.main import/startup errors.

Loads the REAL application (kalibr_publisher.main:app) so the full lifespan
(start_scheduler / ensure_runtime_directories) executes. If startup fails, the
error is captured and served via the health endpoint instead of crashing the
process, so the container always responds on the health-check port.
"""

from __future__ import annotations

import sys
import traceback

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/health/live")
async def health_live():
    return _status()


@app.get("/api/v1/meta")
async def meta():
    return _status()


_state = {}


def _status():
    if "app" in _state:
        # Real app is loaded and (if it got here) running.
        return {"status": "ok", "boot": "real_app_loaded", "smoke": False}
    if "error" in _state:
        return {"status": "boot_failed", "error": _state["error"], "smoke": False}
    return {"status": "boot_pending", "smoke": False}


try:
    import kalibr_publisher.main as _m  # noqa: F401

    _state["app"] = _m
except BaseException:  # pragma: no cover - surfaced via endpoint
    _state["error"] = traceback.format_exc()
    print("BOOT_PROBE_FAILURE:\n" + _state["error"], file=sys.stderr, flush=True)

# If the real app imported, serve IT (so the full app + routes are live).
if "app" in _state:
    app = _state["app"].app if hasattr(_state["app"], "app") else _state["app"]
