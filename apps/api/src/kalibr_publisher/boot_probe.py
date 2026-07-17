"""Diagnostic boot probe — runs the REAL startup steps explicitly with timeouts
and reports exactly which step hangs or fails, via the health endpoint.

This lets us see the container's real startup error without Render's hidden logs.
"""

from __future__ import annotations

import threading
import time
import traceback

from fastapi import FastAPI

app = FastAPI()

_STATE = {"done": False, "report": "pending", "steps": []}


def _run_startup():
    steps = []
    try:
        from kalibr_publisher.core.config import get_settings
        from kalibr_publisher.core.runtime import ensure_runtime_directories
        from kalibr_publisher.services.scheduler import start_scheduler
        from kalibr_publisher.main import create_app

        t = time.time()
        settings = get_settings()
        steps.append(f"get_settings OK ({time.time()-t:.2f}s) storage_root={settings.storage_root}")

        t = time.time()
        try:
            ensure_runtime_directories(settings)
            steps.append(f"ensure_runtime_directories OK ({time.time()-t:.2f}s)")
        except BaseException as e:
            steps.append(f"ensure_runtime_directories RAISED ({time.time()-t:.2f}s): {repr(e)}")

        t = time.time()
        try:
            app_real = create_app(settings)
            steps.append(f"create_app OK ({time.time()-t:.2f}s)")
        except BaseException as e:
            steps.append(f"create_app RAISED ({time.time()-t:.2f}s): {repr(e)}")
            _STATE["report"] = "\n".join(steps) + "\n\nTRACEBACK:\n" + traceback.format_exc()
            return

        t = time.time()
        try:
            task = start_scheduler()
            steps.append(f"start_scheduler returned {task} ({time.time()-t:.2f}s)")
        except BaseException as e:
            steps.append(f"start_scheduler RAISED ({time.time()-t:.2f}s): {repr(e)}")

        _STATE["report"] = "STARTUP_OK\n" + "\n".join(steps)
        _STATE["app_real"] = app_real
    except BaseException as e:
        _STATE["report"] = "STARTUP_IMPORT_FAIL\n" + "\n".join(steps) + "\n\n" + traceback.format_exc()


def _ensure_run():
    if not _STATE["done"]:
        _STATE["done"] = True
        th = threading.Thread(target=_run_startup, daemon=True)
        th.start()
        th.join(timeout=25)
        if not _STATE.get("app_real") and "STARTUP_OK" not in _STATE["report"]:
            if th.is_alive():
                _STATE["report"] = "HANG_DETECTED (startup blocked >25s)\n" + "\n".join(_STATE["steps"])


@app.get("/api/v1/health/live")
async def health():
    _ensure_run()
    return {"status": "diag", "report": _STATE["report"]}


@app.get("/api/v1/meta")
async def meta():
    _ensure_run()
    return {"status": "diag", "report": _STATE["report"]}
