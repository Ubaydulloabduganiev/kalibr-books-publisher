"""Content-plan automation endpoints."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, UploadFile
from pydantic import BaseModel

from kalibr_publisher.api.deps import get_settings
from kalibr_publisher.core.config import Settings
from kalibr_publisher.services.automation import run_automation
from kalibr_publisher.services.document_parser import parse_plan

router = APIRouter(prefix="/automation", tags=["automation"])


class PlanTextIn(BaseModel):
    text: str
    language: str = "uz"
    stagger_hours: int = 24


class AutomationResult(BaseModel):
    source: str
    created: int
    items: list[dict[str, Any]]


@router.post("/plan-file", response_model=AutomationResult)
async def automate_from_file(
    file: UploadFile = File(...),
    language: str = "uz",
    stagger_hours: int = 24,
    settings: Settings = Depends(get_settings),
) -> AutomationResult:
    """Upload a content-plan document (.txt/.docx/.pdf) and auto-generate+schedule posts."""
    data = await file.read()
    plan = parse_plan(file.filename or "plan.txt", data)
    if not plan.items:
        return AutomationResult(source=file.filename or "plan", created=0, items=[])
    created = run_automation(
        plan, settings=settings, language=language, stagger_hours=stagger_hours
    )
    return AutomationResult(
        source=file.filename or "plan", created=len(created), items=created
    )


@router.post("/plan-text", response_model=AutomationResult)
async def automate_from_text(
    payload: PlanTextIn,
    settings: Settings = Depends(get_settings),
) -> AutomationResult:
    """Same as /plan-file but accepts raw plan text (one topic per line)."""
    from kalibr_publisher.services.document_parser import parse_text

    plan = parse_text(payload.text)
    if not plan.items:
        return AutomationResult(source="text", created=0, items=[])
    created = run_automation(
        plan, settings=settings, language=payload.language, stagger_hours=payload.stagger_hours
    )
    return AutomationResult(source="text", created=len(created), items=created)
