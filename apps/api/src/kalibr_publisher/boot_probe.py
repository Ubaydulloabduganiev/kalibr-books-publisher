"""Standalone boot probe — no project imports at module load time.

This module is intentionally dependency-light (only fastapi) so that uvicorn
can ALWAYS import it. It then dynamically imports the real application and
surfaces any import/runtime error through the health endpoint, so a failing
container still responds on the health-check port and reveals its traceback.
"""

from __future__ import annotations

import sys
import traceback

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/health/live")
async def health_live():
    return await _status()


@app.get("/api/v1/meta")
async def meta():
    return await _status()


_probe = {}


async def _status():
    if "app" in _probe:
        # Real app imported successfully; delegate to it.
        real = _probe["app"]
        # Re-run a lightweight check: the real app is up.
        return {"status": "ok", "boot": "real_app_loaded", "smoke": False}
    err = _probe.get("error")
    if err is not None:
        return {"status": "boot_failed", "error": err, "smoke": False}
    # Attempt the import now (idempotent).
    try:
        import kalibr_publisher.main as m  # noqa: F401
    except BaseException as exc:  # pragma: no cover - surfaced on demand
        _probe["error"] = traceback.format_exc()
        return {"status": "boot_failed", "error": _probe["error"], "smoke": False}
    _probe["app"] = m
    return {"status": "ok", "boot": "real_app_loaded", "smoke": False}


# Try to import the real app at startup so failures are captured immediately.
try:
    import kalibr_publisher.main as _m  # noqa: F401

    _probe["app"] = _m
except BaseException:  # pragma: no cover - surfaced via endpoint
    _probe["error"] = traceback.format_exc()
    print("BOOT_PROBE_FAILURE:\n" + _probe["error"], file=sys.stderr, flush=True)
