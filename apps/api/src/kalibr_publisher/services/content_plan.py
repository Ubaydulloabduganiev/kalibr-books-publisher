"""Content-plan processing: turn an uploaded CSV into scheduled AI-generated posts.

Expected CSV columns (header row required):
    text          - the post copy (used to generate the caption)
    image_prompt  - prompt for the AI image (only used when AI_GENERATE_IMAGES is on)
    schedule      - ISO datetime (one-off) or "EVERY <hours>h" (recurring)

Each uploaded plan is recorded so it can be listed and deleted later.
"""

from __future__ import annotations

import csv
import io
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kalibr_publisher.core.config import get_settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.store import MediaRef, PostDraft, Schedule, create_posts
from kalibr_publisher.integrations.gemini import GeminiClient

# --------------------------------------------------------------------------- #
# Plan store (lightweight JSON ledger of uploaded plans)
# --------------------------------------------------------------------------- #

_plan_lock = threading.RLock()
_plan_path: Path | None = None


def configure_plan_store(path: Path | None) -> None:
    global _plan_path
    with _plan_lock:
        _plan_path = path


@dataclass(slots=True)
class PlanItem:
    row: int
    text: str
    image_prompt: str
    schedule: str
    post_id: str | None = None
    caption: str | None = None
    media_count: int = 0


@dataclass(slots=True)
class ContentPlanRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    filename: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    items: list[PlanItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "created_at": self.created_at,
            "items": [asdict(i) for i in self.items],
            "post_count": sum(1 for i in self.items if i.post_id),
        }


def _plans_file() -> Path:
    path = _plan_path or (get_settings().storage_root / "content_plans.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    return path


def _load_plans() -> list[ContentPlanRecord]:
    raw = json.loads(_plans_file().read_text(encoding="utf-8") or "[]")
    out: list[ContentPlanRecord] = []
    for item in raw:
        rec = ContentPlanRecord(
            id=item.get("id", uuid.uuid4().hex),
            filename=item.get("filename", ""),
            created_at=item.get("created_at", datetime.now(UTC).isoformat()),
        )
        rec.items = [PlanItem(**i) for i in item.get("items", [])]
        out.append(rec)
    return out


def _save_plans(plans: list[ContentPlanRecord]) -> None:
    data = json.dumps([p.to_dict() for p in plans], ensure_ascii=False, indent=2)
    tmp = _plans_file().with_name(f".plans.{uuid.uuid4().hex}.tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(_plans_file())


def list_plans() -> list[ContentPlanRecord]:
    with _plan_lock:
        return _load_plans()


def get_plan(plan_id: str) -> ContentPlanRecord | None:
    with _plan_lock:
        return next((p for p in _load_plans() if p.id == plan_id), None)


def delete_plan(plan_id: str) -> bool:
    """Remove the plan ledger entry. Caller is responsible for deleting posts."""
    with _plan_lock:
        plans = _load_plans()
        remaining = [p for p in plans if p.id != plan_id]
        if len(remaining) == len(plans):
            return False
        _save_plans(remaining)
        return True


# --------------------------------------------------------------------------- #
# CSV parsing
# --------------------------------------------------------------------------- #

REQUIRED_COLUMNS = ("text", "image_prompt", "schedule")


def parse_csv(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ApiError(
            status_code=422,
            code="invalid_content_plan",
            message=f"Missing required column(s): {', '.join(missing)}",
            recovery_suggestion="CSV must have columns: text, image_prompt, schedule",
        )
    rows: list[dict[str, str]] = []
    for i, row in enumerate(reader):
        row = {k: (v or "").strip() for k, v in row.items()}
        if not row.get("text") or not row.get("schedule"):
            continue
        rows.append(row)
    if not rows:
        raise ApiError(
            status_code=422,
            code="invalid_content_plan",
            message="No valid rows found in the content plan.",
            recovery_suggestion="Each row needs a non-empty 'text' and 'schedule'.",
        )
    return rows


def _parse_schedule(value: str) -> Schedule:
    value = (value or "").strip()
    lowered = value.lower()
    if lowered.startswith("every"):
        rest = lowered.replace("every", "").strip()
        num = ""
        for ch in rest:
            if ch.isdigit() or ch == ".":
                num += ch
            elif ch == "h":
                break
        hours = float(num) if num else 24.0
        return Schedule(mode="recurring", every_hours=hours)
    try:
        run_at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_schedule",
            message=f"Invalid schedule value: {value!r}",
            recovery_suggestion="Use an ISO datetime (e.g. 2026-07-20T09:00:00+05:00) or EVERY 24h.",
        ) from exc
    return Schedule(mode="once", run_at=run_at.isoformat())


# --------------------------------------------------------------------------- #
# Processing
# --------------------------------------------------------------------------- #


def process_content_plan(raw: bytes, filename: str = "plan.csv") -> ContentPlanRecord:
    """Parse CSV, generate captions (and optional images), schedule posts, record the plan."""
    settings = get_settings()
    if not (settings.ai_enabled and settings.gemini_api_key):
        raise ApiError(
            status_code=503,
            code="ai_not_configured",
            message="AI generation is disabled or GEMINI_API_KEY is not set.",
            recovery_suggestion="Set GEMINI_API_KEY on the API service.",
        )

    rows = parse_csv(raw)
    record = ContentPlanRecord(filename=filename)
    drafts: list[PostDraft] = []
    gemini = GeminiClient()

    for index, row in enumerate(rows):
        base_text = row["text"]
        try:
            caption = gemini.rewrite_caption(base_text, language=settings.ai_caption_language).text
        except Exception:
            caption = base_text

        media: list[MediaRef] = []
        if settings.ai_generate_images and row.get("image_prompt"):
            try:
                image = gemini.generate_image(row["image_prompt"])
                ext = "png" if "png" in image.mime_type else "jpg"
                media_path = settings.media_root / f"{uuid.uuid4().hex}.{ext}"
                media_path.parent.mkdir(parents=True, exist_ok=True)
                media_path.write_bytes(image.data)
                media.append(MediaRef(kind="image", path=str(media_path)))
            except Exception:
                media = []

        schedule = _parse_schedule(row["schedule"])
        draft = PostDraft(
            index=index,
            text=caption,
            media=media,
            target=settings.telegram_default_channel,
            parse_mode="HTML",
            schedule=schedule,
        )
        drafts.append(draft)
        record.items.append(
            PlanItem(
                row=index,
                text=base_text,
                image_prompt=row.get("image_prompt", ""),
                schedule=row["schedule"],
                caption=caption,
                media_count=len(media),
            )
        )

    created = create_posts(drafts)
    by_index = {draft.index: post.id for draft, post in zip(drafts, created)}
    for item in record.items:
        item.post_id = by_index.get(item.row)

    with _plan_lock:
        plans = _load_plans()
        plans.insert(0, record)
        _save_plans(plans)

    return record
