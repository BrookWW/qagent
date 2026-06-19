"""Markdown parsing utilities for QAgent batch files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Paper:
    title: str
    paper_id: str
    raw_entry: str
    cvgmt_id: str | None = None
    authors: str | None = None
    year: str | None = None
    url: str | None = None
    matched_keywords: str | None = None
    abstract: str | None = None


HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def parse_batch(path: Path) -> list[Paper]:
    text = path.read_text(encoding="utf-8")
    matches = list(HEADING_RE.finditer(text))
    papers: list[Paper] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entry = text[start:end].strip()
        title = match.group(1).strip()
        cvgmt_id = _field(entry, "CVGMT ID")
        paper_id = f"cvgmt_{cvgmt_id}" if cvgmt_id else slugify(title)

        papers.append(
            Paper(
                title=title,
                paper_id=paper_id,
                raw_entry=entry,
                cvgmt_id=cvgmt_id,
                authors=_field(entry, "Authors"),
                year=_field(entry, "Year"),
                url=_field(entry, "URL"),
                matched_keywords=_field(entry, "Matched keywords"),
                abstract=_abstract(entry),
            )
        )

    return papers


def _field(entry: str, name: str) -> str | None:
    pattern = re.compile(rf"^\s*-\s+\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(entry)
    return match.group(1).strip() if match else None


def _abstract(entry: str) -> str | None:
    marker = re.search(r"^\s*\*\*Abstract:\*\*\s*$", entry, re.MULTILINE)
    if not marker:
        return None
    return entry[marker.end() :].strip() or None
