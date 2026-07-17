"""TEMP SMOKE TEST - minimal app, no project imports."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/v1/health/live")
async def health():
    return {"status": "ok", "smoke": True}

@app.get("/api/v1/meta")
async def meta():
    return {"status": "ok", "smoke": True}
