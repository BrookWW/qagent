from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gap_extractor import extract_gap_cards, extract_limitation_cards
from .paper_fetcher import fetch_best_source, _source_cache_key
from .paper_text_extractor import extract_paper_text
from .reading_quality import assess_reading_quality
from .theorem_extractor import extract_method_cards, extract_proof_cards, extract_theorem_cards


def read_paper_deeply(entry: dict[str, Any], batch_id: str = "batch_001", try_online: bool = True) -> dict[str, Any]:
    paper_id = entry.get("paper_id") or _paper_id(entry)
    output_dir = Path("outputs") / batch_id / paper_id
    output_dir.mkdir(parents=True, exist_ok=True)

    fetch_result = fetch_best_source(
        entry,
        try_online=try_online,
        cache_key=_source_cache_key(entry, paper_id),
    ).to_dict()
    text_result = extract_paper_text(fetch_result, entry).to_dict()
    text = Path(text_result["text_path"]).read_text(encoding="utf-8", errors="ignore")

    profile = build_paper_profile(entry, fetch_result, text_result)
    theorem_cards = extract_theorem_cards(text, profile)
    proof_cards = extract_proof_cards(text, theorem_cards)
    method_cards = extract_method_cards(text)
    limitation_cards = extract_limitation_cards(text, theorem_cards)
    gap_cards = extract_gap_cards(theorem_cards, limitation_cards, method_cards)
    reading_quality = assess_reading_quality(text, text_result, theorem_cards, proof_cards, method_cards, limitation_cards, gap_cards)
    profile = enrich_paper_profile(profile, theorem_cards, proof_cards, method_cards, limitation_cards, gap_cards, reading_quality)

    _write_json(output_dir / "paper_profile.json", profile)
    _write_json(output_dir / "theorem_cards.json", theorem_cards)
    _write_json(output_dir / "proof_cards.json", proof_cards)
    _write_json(output_dir / "method_cards.json", method_cards)
    _write_json(output_dir / "limitation_cards.json", limitation_cards)
    _write_json(output_dir / "gap_cards.json", gap_cards)
    _write_json(output_dir / "paper_reading_quality.json", reading_quality)
    _write_json(output_dir / "source_fetch_result.json", fetch_result)
    _write_json(output_dir / "text_extraction_result.json", text_result)
    (output_dir / "paper_reader_report.md").write_text(
        _report(profile, theorem_cards, method_cards, limitation_cards, gap_cards, fetch_result, text_result),
        encoding="utf-8",
    )
    return {
        "paper_profile": profile,
        "theorem_cards": theorem_cards,
        "proof_cards": proof_cards,
        "method_cards": method_cards,
        "limitation_cards": limitation_cards,
        "gap_cards": gap_cards,
        "paper_reading_quality": reading_quality,
        "fetch_result": fetch_result,
        "text_result": text_result,
    }


def build_paper_profile(entry: dict[str, Any], fetch_result: dict[str, Any], text_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": entry.get("title", "not provided"),
        "authors": entry.get("authors", "not provided"),
        "year": entry.get("year", "not provided"),
        "source": fetch_result.get("source_type", "not provided"),
        "abstract": entry.get("abstract", "not provided"),
        "mathematical_area": _area(entry),
        "model_class": entry.get("matched_keywords", "not specified"),
        "equation_or_functional": "infer from theorem_cards and method_cards; automatic reader may be uncertain",
        "main_objects": "infer from abstract/full text",
        "main_results": "infer from theorem_cards",
        "methods": "infer from method_cards",
        "confidence_level": text_result.get("extraction_confidence", "low"),
        "paper_reading_confidence": text_result.get("extraction_confidence", "low"),
        "full_text_was_read": bool(text_result.get("full_text_read")),
    }


def enrich_paper_profile(
    profile: dict[str, Any],
    theorem_cards: list[dict[str, Any]],
    proof_cards: list[dict[str, Any]],
    method_cards: list[dict[str, Any]],
    limitation_cards: list[dict[str, Any]],
    gap_cards: list[dict[str, Any]],
    reading_quality: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(profile)
    enriched["paper_reading_confidence"] = reading_quality.get("paper_reading_confidence", profile.get("paper_reading_confidence", "low"))
    enriched["confidence_level"] = enriched["paper_reading_confidence"]
    enriched["main_results"] = _summarize_theorems(theorem_cards)
    enriched["methods"] = _summarize_methods(method_cards, proof_cards)
    enriched["main_objects"] = _summarize_objects(theorem_cards, profile)
    enriched["equation_or_functional"] = _summarize_equation_or_functional(theorem_cards, profile)
    enriched["limitations_or_possible_gaps"] = _summarize_limitations_and_gaps(limitation_cards, gap_cards)
    enriched["reading_quality_summary"] = reading_quality.get("downstream_policy", {}).get("policy_summary", "")
    enriched["reading_warnings"] = reading_quality.get("warnings", [])
    return enriched


def _area(entry: dict[str, Any]) -> str:
    text = " ".join(str(entry.get(key, "")) for key in ["title", "matched_keywords", "abstract"]).lower()
    if "varifold" in text or "minimal" in text:
        return "varifold/minimal surface/GMT"
    if "parabolic" in text or "fokker" in text or "keller" in text:
        return "nonlocal/parabolic PDE"
    if "metric" in text or "laplacian" in text or "elliptic" in text:
        return "elliptic/geometric PDE"
    if "gamma" in text or "materials" in text or "elastic" in text:
        return "calculus of variations/materials science"
    return "other"


def _paper_id(entry: dict[str, Any]) -> str:
    cvgmt = str(entry.get("cvgmt_id", "")).strip()
    if cvgmt and cvgmt != "not provided":
        return f"cvgmt_{cvgmt}"
    return "paper"


def _summarize_theorems(theorem_cards: list[dict[str, Any]]) -> str:
    if not theorem_cards:
        return "not specified"
    pieces = []
    for card in theorem_cards[:4]:
        label = card.get("theorem_label", "result")
        conclusion = str(card.get("conclusion") or card.get("source_excerpt_or_summary") or "").strip()
        pieces.append(f"{label}: {conclusion[:450]}")
    return " | ".join(pieces)


def _summarize_methods(method_cards: list[dict[str, Any]], proof_cards: list[dict[str, Any]]) -> str:
    methods = [str(card.get("method", "")).strip() for card in method_cards if str(card.get("method", "")).strip()]
    if methods:
        return ", ".join(list(dict.fromkeys(methods))[:8])
    reusable = []
    for card in proof_cards:
        value = card.get("likely_reusable_tools")
        if isinstance(value, list):
            reusable.extend(str(item) for item in value)
    reusable = [item for item in reusable if item and item != "not identified automatically"]
    return ", ".join(list(dict.fromkeys(reusable))[:8]) if reusable else "not specified by automatic extraction"


def _summarize_objects(theorem_cards: list[dict[str, Any]], profile: dict[str, Any]) -> str:
    text = " ".join(str(card.get("source_excerpt_or_summary", "")) for card in theorem_cards[:3]).lower()
    object_terms = [
        "weak solution",
        "minimizer",
        "critical point",
        "varifold",
        "current",
        "harmonic map",
        "hypersurface",
        "free boundary",
        "measure-valued solution",
        "stationary state",
    ]
    found = [term for term in object_terms if term in text]
    return ", ".join(found) if found else str(profile.get("main_objects", "not specified"))


def _summarize_equation_or_functional(theorem_cards: list[dict[str, Any]], profile: dict[str, Any]) -> str:
    text = " ".join(str(card.get("source_excerpt_or_summary", "")) for card in theorem_cards[:3])
    equation_markers = ["=", "\\Delta", "div", "minimize", "energy", "functional", "Euler", "curvature", "mean curvature"]
    if any(marker.lower() in text.lower() for marker in equation_markers):
        return text[:700]
    return str(profile.get("equation_or_functional", "not specified"))


def _summarize_limitations_and_gaps(limitation_cards: list[dict[str, Any]], gap_cards: list[dict[str, Any]]) -> str:
    limitations = [str(card.get("limitation_type", "")).strip() for card in limitation_cards[:5] if str(card.get("limitation_type", "")).strip()]
    gaps = [str(card.get("gap_title", "")).strip() for card in gap_cards[:5] if str(card.get("gap_title", "")).strip()]
    return "Limitations: " + ", ".join(limitations or ["not extracted"]) + " | Gaps: " + ", ".join(gaps or ["not extracted"])


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _report(
    profile: dict[str, Any],
    theorem_cards: list[dict[str, Any]],
    method_cards: list[dict[str, Any]],
    limitation_cards: list[dict[str, Any]],
    gap_cards: list[dict[str, Any]],
    fetch_result: dict[str, Any],
    text_result: dict[str, Any],
) -> str:
    warnings = profile.get("reading_warnings", [])
    warning_lines = [f"- {line}" for line in warnings] if warnings else ["- No major reading-quality warnings."]
    return "\n".join(
        [
            f"# Paper Reader Report: {profile.get('title', 'untitled')}",
            "",
            f"- Source type: {fetch_result.get('source_type')}",
            f"- Source URL: {fetch_result.get('source_url') or 'not provided'}",
            f"- PDF path: {fetch_result.get('pdf_path') or 'not available'}",
            f"- Text path: {text_result.get('text_path') or 'not available'}",
            f"- Full text read: {profile.get('full_text_was_read')}",
            f"- Confidence: {profile.get('paper_reading_confidence')}",
            f"- Theorem cards: {len(theorem_cards)}",
            f"- Method cards: {len(method_cards)}",
            f"- Limitation cards: {len(limitation_cards)}",
            f"- Gap cards: {len(gap_cards)}",
            f"- Reading quality summary: {profile.get('reading_quality_summary', 'not available')}",
            "",
            "## Reading Warnings",
            "",
            *warning_lines,
            "",
            "## Fetch Log",
            "",
            *[f"- {line}" for line in fetch_result.get("log", [])],
            "",
            "## Extraction Log",
            "",
            *[f"- {line}" for line in text_result.get("log", [])],
            "",
            "If full text was unavailable, downstream final outputs must record a lower-confidence source note in metadata and feasibility files, not in problem_statement.tex.",
            "",
        ]
    )
