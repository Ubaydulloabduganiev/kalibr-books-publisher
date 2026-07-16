"""Content-plan document parser.

Turns an uploaded content-plan file (.txt / .docx / .pdf) into a list of
plan items. Each item is a short topic the automation agent will expand into a
fully generated post (image + caption + schedule).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlanItem:
    title: str
    note: str = ""
    # optional explicit schedule hint parsed from the plan (e.g. "Mon 10:00")
    when: Optional[str] = None


@dataclass
class ParsedPlan:
    items: list[PlanItem] = field(default_factory=list)
    source_name: str = ""


def _split_lines(text: str) -> list[str]:
    # normalise and drop empty/whitespace lines
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def _clean_title(raw: str) -> str:
    # strip leading bullets / numbering
    return re.sub(r"^([\-\*\•\u2022]|\d+[.)])\s*", "", raw).strip()


def parse_text(text: str) -> ParsedPlan:
    items: list[PlanItem] = []
    for ln in _split_lines(text):
        # treat lines that look like section headers or bullets as items
        title = _clean_title(ln)
        if not title:
            continue
        items.append(PlanItem(title=title))
    return ParsedPlan(items=items)


def parse_docx(data: bytes) -> ParsedPlan:
    from docx import Document  # python-docx

    doc = Document(io.BytesIO(data))
    lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return parse_text("\n".join(lines))


def parse_pdf(data: bytes) -> ParsedPlan:
    from pypdf import PdfReader  # pypdf

    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        chunks.append(txt)
    return parse_text("\n".join(chunks))


def parse_plan(filename: str, data: bytes) -> ParsedPlan:
    """Dispatch by file extension; default to plain text."""
    lower = filename.lower()
    if lower.endswith(".docx"):
        plan = parse_docx(data)
    elif lower.endswith(".pdf"):
        plan = parse_pdf(data)
    else:
        # .txt and anything else: decode best-effort
        plan = parse_text(data.decode("utf-8", errors="replace"))
    plan.source_name = filename
    return plan
