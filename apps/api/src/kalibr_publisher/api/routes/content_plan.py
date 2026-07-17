"""Content-plan upload endpoints: parse a CSV and schedule AI-generated posts."""

from __future__ import annotations

from dataclasses import asdict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from kalibr_publisher.api.deps import require_internal_api_key
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import delete_post, get_post
from kalibr_publisher.services import content_plan as cp

router = APIRouter(
    prefix="/content-plan",
    tags=["content-plan"],
    dependencies=[Depends(require_internal_api_key)],
)


class ContentPlanItemOut(BaseModel):
    row: int
    text: str
    image_prompt: str
    schedule: str
    post_id: str | None = None
    caption: str | None = None
    media_count: int = 0


class ContentPlanOut(BaseModel):
    id: str
    filename: str
    created_at: str
    post_count: int
    items: list[ContentPlanItemOut]


class ContentPlanList(BaseModel):
    count: int
    plans: list[ContentPlanOut]


@router.get("", response_model=ContentPlanList)
async def list_content_plans() -> ContentPlanList:
    plans = cp.list_plans()
    return ContentPlanList(
        count=len(plans),
        plans=[
            ContentPlanOut(
                id=p.id, filename=p.filename, created_at=p.created_at,
                post_count=sum(1 for i in p.items if i.post_id),
                items=[ContentPlanItemOut(**asdict(i)) for i in p.items],
            )
            for p in plans
        ],
    )


@router.get("/{plan_id}", response_model=ContentPlanOut)
async def get_content_plan(plan_id: str) -> ContentPlanOut:
    record = cp.get_plan(plan_id)
    if record is None:
        raise ApiError(
            status_code=404, code="plan_not_found",
            message="The requested content plan does not exist.",
            recovery_suggestion="Refresh the list and try again.",
        )
    return ContentPlanOut(
        id=record.id, filename=record.filename, created_at=record.created_at,
        post_count=sum(1 for i in record.items if i.post_id),
        items=[ContentPlanItemOut(**asdict(i)) for i in record.items],
    )


@router.post("/upload", response_model=ContentPlanOut, status_code=201)
async def upload_content_plan(file: UploadFile = File(...)) -> ContentPlanOut:
    raw = await file.read()
    if not raw:
        raise ApiError(
            status_code=422, code="empty_file", message="Uploaded file is empty.",
            recovery_suggestion="Upload a non-empty CSV with text, image_prompt, schedule columns.",
        )
    record = cp.process_content_plan(raw, filename=file.filename or "plan.csv")
    return ContentPlanOut(
        id=record.id, filename=record.filename, created_at=record.created_at,
        post_count=sum(1 for i in record.items if i.post_id),
        items=[ContentPlanItemOut(**asdict(i)) for i in record.items],
    )


@router.delete("/{plan_id}", status_code=204)
async def delete_content_plan(plan_id: str) -> None:
    record = cp.get_plan(plan_id)
    if record is None:
        raise ApiError(
            status_code=404, code="plan_not_found",
            message="The requested content plan does not exist.",
            recovery_suggestion="Refresh the list and try again.",
        )
    for item in record.items:
        if item.post_id and get_post(item.post_id) is not None:
            try:
                delete_post(item.post_id)
            except Exception:
                pass
    if not cp.delete_plan(plan_id):
        raise ApiError(
            status_code=404, code="plan_not_found",
            message="The requested content plan does not exist.",
            recovery_suggestion="Refresh the list and try again.",
        )
