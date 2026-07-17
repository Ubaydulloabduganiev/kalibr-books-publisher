"""Content-plan upload endpoints: parse a CSV and schedule AI-generated posts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from kalibr_publisher.api.deps import require_internal_api_key
from kalibr_publisher.core.config import Settings, get_settings
from kalibr_publisher.services.content_plan import parse_csv, process_content_plan

router = APIRouter(prefix="/content-plan", tags=["content-plan"])


class PreviewItem(BaseModel):
    row: int
    text: str
    image_prompt: str
    schedule: str


class PreviewResponse(BaseModel):
    count: int
    items: list[PreviewItem]


@router.post(
    "/preview",
    response_model=PreviewResponse,
    summary="Preview a content plan without scheduling",
)
async def preview_content_plan(
    file: UploadFile = File(...),
    _: None = Depends(require_internal_api_key),
) -> PreviewResponse:
    raw = await file.read()
    try:
        rows = parse_csv(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"code": "bad_content_plan", "message": str(exc)})
    items = [
        PreviewItem(
            row=i,
            text=row.get("text", "")[:120],
            image_prompt=row.get("image_prompt", "")[:120],
            schedule=row.get("schedule", ""),
        )
        for i, row in enumerate(rows)
    ]
    return PreviewResponse(count=len(items), items=items)


@router.post(
    "/upload",
    response_model=dict[str, object],
    summary="Generate posts from a content plan and schedule them",
)
async def upload_content_plan(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_internal_api_key),
) -> dict[str, object]:
    raw = await file.read()
    return process_content_plan(raw, settings=settings)
