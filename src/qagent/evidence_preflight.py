from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .deep_paper_reader import read_paper_deeply


REQUIRED_EVIDENCE_FILES = [
    "paper_profile.json",
    "theorem_cards.json",
    "proof_cards.json",
    "method_cards.json",
    "limitation_cards.json",
    "gap_cards.json",
    "paper_reading_quality.json",
    "paper_reader_report.md",
    "source_fetch_result.json",
    "text_extraction_result.json",
]


@dataclass
class EvidencePreflightItem:
    paper_id: str
    title: str
    ok: bool
    confidence: str
    full_text_was_read: bool
    source_type: str
    source_url: str
    pdf_path: str
    text_path: str
    output_dir: str
    missing_files: list[str]
    error_message: str
    fetch_log: list[str]
    extraction_log: list[str]


@dataclass
class EvidencePreflightResult:
    ok: bool
    batch_id: str
    papers_processed: int
    items: list[EvidencePreflightItem]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [asdict(item) for item in self.items]
        return data


def run_evidence_preflight(
    entries: list[dict[str, Any]],
    batch_id: str = "batch_001",
    try_online: bool = True,
    require_full_text: bool = False,
) -> EvidencePreflightResult:
    items: list[EvidencePreflightItem] = []

    for index, entry in enumerate(entries, 1):
        prepared = dict(entry)
        prepared["paper_id"] = prepared.get("paper_id") or f"paper_{index:03d}"
        paper_id = str(prepared["paper_id"])
        output_dir = Path("outputs") / batch_id / paper_id
        title = str(prepared.get("title", paper_id))

        try:
            result = read_paper_deeply(prepared, batch_id=batch_id, try_online=try_online)
            missing = _missing_evidence_files(output_dir)
            profile = result.get("paper_profile", {})
            fetch_result = result.get("fetch_result", {})
            text_result = result.get("text_result", {})
            full_text = bool(profile.get("full_text_was_read"))
            pdf_read = bool(fetch_result.get("pdf_path")) and str(fetch_result.get("source_type", "")).lower() in {"pdf", "cached_pdf"}
            fetch_log = list(fetch_result.get("log", []))
            extraction_log = list(text_result.get("log", []))
            if require_full_text and not (full_text and pdf_read):
                extraction_log.append(
                    "Downloaded PDF full text was preferred but unavailable; continuing with low confidence."
                )
            item_ok = not missing
            items.append(
                EvidencePreflightItem(
                    paper_id=paper_id,
                    title=title,
                    ok=item_ok,
                    confidence=str(profile.get("paper_reading_confidence", "unknown")),
                    full_text_was_read=full_text,
                    source_type=str(fetch_result.get("source_type", "unknown")),
                    source_url=str(fetch_result.get("source_url", "")),
                    pdf_path=str(fetch_result.get("pdf_path", "")),
                    text_path=str(text_result.get("text_path", "")),
                    output_dir=output_dir.as_posix(),
                    missing_files=missing,
                    error_message="",
                    fetch_log=fetch_log,
                    extraction_log=extraction_log,
                )
            )
        except Exception as exc:
            fallback = _write_fallback_evidence(output_dir, prepared, str(exc))
            missing = _missing_evidence_files(output_dir)
            items.append(
                EvidencePreflightItem(
                    paper_id=paper_id,
                    title=title,
                    ok=not missing,
                    confidence="low",
                    full_text_was_read=False,
                    source_type="failed_fallback_metadata",
                    source_url="",
                    pdf_path="",
                    text_path=str(fallback.get("text_path", "")),
                    output_dir=output_dir.as_posix(),
                    missing_files=missing,
                    error_message=f"Evidence extraction failed for this paper; continuing with low-confidence metadata fallback. Cause: {exc}",
                    fetch_log=["Primary evidence extraction failed; using metadata fallback for this paper only."],
                    extraction_log=["Full text was not read; theorem/proof/gap cards are fallback low-confidence placeholders."],
                )
            )

    return EvidencePreflightResult(
        ok=bool(items) and any(item.ok for item in items),
        batch_id=batch_id,
        papers_processed=len(items),
        items=items,
    )


def write_evidence_preflight_result(output_dir: Path, result: EvidencePreflightResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "evidence_preflight.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def evidence_summary_markdown(result: EvidencePreflightResult) -> str:
    lines = [
        "# Evidence Preflight",
        "",
        f"- Batch: {result.batch_id}",
        f"- Papers processed: {result.papers_processed}",
        f"- Status: {'passed' if result.ok else 'failed'}",
        "",
    ]
    for item in result.items:
        lines.extend(
            [
                f"## {item.paper_id}: {item.title}",
                "",
                f"- Status: {'passed' if item.ok else 'failed'}",
                f"- Confidence: {item.confidence}",
                f"- Full text was read: {item.full_text_was_read}",
                f"- Source type: {item.source_type}",
                f"- Source URL: `{item.source_url or 'not available'}`",
                f"- PDF path: `{item.pdf_path or 'not available'}`",
                f"- Text path: `{item.text_path or 'not available'}`",
                f"- Output directory: `{item.output_dir}`",
            ]
        )
        if item.missing_files:
            lines.append(f"- Missing files: {', '.join(item.missing_files)}")
        if item.error_message:
            lines.append(f"- Error: {item.error_message}")
        if item.fetch_log:
            lines.extend(["", "Fetch log:"])
            lines.extend(f"- {line}" for line in item.fetch_log)
        if item.extraction_log:
            lines.extend(["", "Extraction log:"])
            lines.extend(f"- {line}" for line in item.extraction_log)
        lines.append("")
    return "\n".join(lines)


def _missing_evidence_files(output_dir: Path) -> list[str]:
    return [name for name in REQUIRED_EVIDENCE_FILES if not (output_dir / name).is_file()]


def _write_fallback_evidence(output_dir: Path, entry: dict[str, Any], reason: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    title = str(entry.get("title") or entry.get("paper_id") or "unknown paper")
    abstract = str(entry.get("abstract") or "Full text and abstract were unavailable during evidence fallback.")
    text_path = output_dir / "fallback_metadata_text.txt"
    text_path.write_text(
        "\n".join(
            [
                f"Title: {title}",
                f"Authors: {entry.get('authors', 'not provided')}",
                f"Year: {entry.get('year', 'not provided')}",
                "",
                "Abstract or user metadata:",
                abstract,
                "",
                f"Evidence extraction failure: {reason}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    profile = {
        "title": title,
        "authors": entry.get("authors", "not provided"),
        "year": entry.get("year", "not provided"),
        "source": "failed_fallback_metadata",
        "abstract": abstract,
        "mathematical_area": entry.get("matched_keywords", "unknown"),
        "model_class": entry.get("matched_keywords", "not specified"),
        "equation_or_functional": "not available; evidence extraction failed",
        "main_objects": "not available; evidence extraction failed",
        "main_results": "not available; evidence extraction failed",
        "methods": "not available; evidence extraction failed",
        "confidence_level": "low",
        "paper_reading_confidence": "low",
        "full_text_was_read": False,
        "evidence_failure_reason": reason,
    }
    theorem_cards = [
        {
            "theorem_label": "fallback_metadata_main_result",
            "theorem_type": "metadata fallback",
            "assumptions": "not available; evidence extraction failed",
            "conclusion": abstract[:500],
            "domain": entry.get("matched_keywords", "not specified"),
            "dimension": "not available",
            "boundary_condition": "not available",
            "regularity_class": "not available",
            "parameter_range": "not available",
            "dependencies": "metadata fallback only",
            "source_excerpt_or_summary": abstract[:2000],
            "confidence": "low",
        }
    ]
    proof_cards = [
        {
            "theorem_label": "fallback_metadata_main_result",
            "proof_strategy": "proof not available because evidence extraction failed",
            "key_lemmas": [],
            "key_estimates": [],
            "where_assumptions_are_used": "not available",
            "possible_fragile_steps": "all proof details require human/full-text verification",
            "likely_reusable_tools": ["not identified automatically"],
        }
    ]
    method_cards = [
        {
            "method": "not identified automatically",
            "where_it_appears": "evidence extraction failed",
            "what_it_proves": "not available",
            "assumptions_needed": "not available",
            "reusability": "low",
        }
    ]
    limitation_cards = [
        {
            "limitation_type": "evidence extraction failure",
            "description": "The paper could not be read deeply; any generated question must be treated as low confidence.",
            "linked_theorems": ["fallback_metadata_main_result"],
            "source_summary": "metadata fallback only",
            "confidence": "low",
        }
    ]
    gap_cards = [
        {
            "gap_title": "Low-confidence metadata fallback gap",
            "gap_type": "evidence extraction failure",
            "known_result_from_input": abstract[:500],
            "missing_case": "requires full text or human reading before trusting the question",
            "why_not_direct_restatement": "not established; fallback evidence is too weak for a high-confidence claim",
            "expected_tools": "not identified automatically",
            "possible_obstacles": "the full theorem, assumptions, and proof mechanisms were not extracted",
            "duplicate_risk_queries": [title, f"{title} arXiv", f"{title} theorem"],
            "qed_gpt_attackability_guess": "low",
            "sci_publishable_potential_guess": "low",
            "nontriviality_guess": "unknown",
        }
    ]
    paper_reading_quality = {
        "paper_reading_confidence": "low",
        "evidence_score": 0,
        "full_text_read": False,
        "text_length": len(abstract),
        "extraction_confidence": "low",
        "theorem_card_count": len(theorem_cards),
        "strong_theorem_card_count": 0,
        "usable_theorem_card_count": 0,
        "proof_coverage": "none",
        "method_coverage": "none",
        "limitation_coverage": "weak",
        "gap_coverage": "weak",
        "theorem_card_quality": [
            {
                "theorem_label": "fallback_metadata_main_result",
                "quality": "weak",
                "weak_fields": ["assumptions", "confidence", "source_excerpt"],
            }
        ],
        "warnings": [
            "Evidence extraction failed; full text was not read.",
            "No usable theorem card with concrete assumptions and conclusion was extracted.",
        ],
        "downstream_policy": {
            "candidate_generation_allowed": False,
            "high_confidence_final_questions_allowed": False,
            "must_mark_metadata_abstract_only": True,
            "must_prefer_needs_deeper_reading": True,
            "policy_summary": "Evidence is insufficient; prefer needs deeper reading.",
        },
    }
    fetch_result = {
        "paper_id": entry.get("paper_id", "paper"),
        "cache_key": entry.get("paper_id", "paper"),
        "source_type": "failed_fallback_metadata",
        "source_url": "",
        "pdf_path": "",
        "html_text": "",
        "confidence": "low",
        "log": [f"Primary evidence extraction failed: {reason}", "Continuing with low-confidence metadata fallback."],
    }
    text_result = {
        "paper_id": entry.get("paper_id", "paper"),
        "text_path": str(text_path),
        "full_text_read": False,
        "extraction_confidence": "low",
        "sections": {},
        "log": [f"Fallback metadata text written after extraction failure: {reason}"],
    }
    _write_json(output_dir / "paper_profile.json", profile)
    _write_json(output_dir / "theorem_cards.json", theorem_cards)
    _write_json(output_dir / "proof_cards.json", proof_cards)
    _write_json(output_dir / "method_cards.json", method_cards)
    _write_json(output_dir / "limitation_cards.json", limitation_cards)
    _write_json(output_dir / "gap_cards.json", gap_cards)
    _write_json(output_dir / "paper_reading_quality.json", paper_reading_quality)
    _write_json(output_dir / "source_fetch_result.json", fetch_result)
    _write_json(output_dir / "text_extraction_result.json", text_result)
    (output_dir / "paper_reader_report.md").write_text(
        "\n".join(
            [
                f"# Paper Reader Report: {title}",
                "",
                "- Status: fallback low confidence",
                "- Full text read: False",
                "- Confidence: low",
                f"- Failure reason: {reason}",
                "",
                "This paper failed during evidence extraction. QAgent continued with metadata-only fallback artifacts so other papers in the batch can proceed.",
                "Any generated question for this paper must be treated as low confidence until the PDF/full text is checked by a human.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"text_path": str(text_path)}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
