from __future__ import annotations

import re
from typing import Any


GENERIC_EVIDENCE_PHRASES = [
    "not specified",
    "not fully specified",
    "automatic extraction uncertain",
    "metadata/abstract only",
    "infer from",
]


def assess_reading_quality(
    text: str,
    text_result: dict[str, Any],
    theorem_cards: list[dict[str, Any]],
    proof_cards: list[dict[str, Any]],
    method_cards: list[dict[str, Any]],
    limitation_cards: list[dict[str, Any]],
    gap_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess whether the reading evidence is strong enough for question generation."""
    text_length = len(re.sub(r"\s+", " ", text).strip())
    full_text_read = bool(text_result.get("full_text_read"))
    extraction_confidence = str(text_result.get("extraction_confidence", "low"))
    theorem_quality = [_theorem_card_quality(card) for card in theorem_cards]
    strong_theorems = sum(1 for item in theorem_quality if item["quality"] == "strong")
    usable_theorems = sum(1 for item in theorem_quality if item["quality"] in {"strong", "usable"})
    proof_coverage = _proof_coverage(proof_cards)
    method_coverage = _method_coverage(method_cards)
    limitation_coverage = _limitation_coverage(limitation_cards)
    gap_coverage = _gap_coverage(gap_cards)
    warnings = _warnings(
        full_text_read,
        extraction_confidence,
        text_length,
        theorem_cards,
        strong_theorems,
        usable_theorems,
        proof_coverage,
        method_coverage,
        gap_coverage,
    )
    evidence_score = _evidence_score(
        full_text_read,
        extraction_confidence,
        text_length,
        strong_theorems,
        usable_theorems,
        proof_coverage,
        method_coverage,
        limitation_coverage,
        gap_coverage,
    )
    evidence_level = _evidence_level(evidence_score)
    return {
        "paper_reading_confidence": evidence_level,
        "evidence_score": evidence_score,
        "full_text_read": full_text_read,
        "text_length": text_length,
        "extraction_confidence": extraction_confidence,
        "theorem_card_count": len(theorem_cards),
        "strong_theorem_card_count": strong_theorems,
        "usable_theorem_card_count": usable_theorems,
        "proof_coverage": proof_coverage,
        "method_coverage": method_coverage,
        "limitation_coverage": limitation_coverage,
        "gap_coverage": gap_coverage,
        "theorem_card_quality": theorem_quality,
        "warnings": warnings,
        "downstream_policy": _downstream_policy(evidence_level, full_text_read, usable_theorems),
    }


def _theorem_card_quality(card: dict[str, Any]) -> dict[str, Any]:
    assumptions = str(card.get("assumptions", ""))
    conclusion = str(card.get("conclusion", ""))
    excerpt = str(card.get("source_excerpt_or_summary", ""))
    weak_fields = []
    if _is_generic(assumptions):
        weak_fields.append("assumptions")
    if _is_generic(conclusion):
        weak_fields.append("conclusion")
    if len(excerpt.strip()) < 250:
        weak_fields.append("source_excerpt")
    if str(card.get("confidence", "")).lower() == "low":
        weak_fields.append("confidence")
    if not weak_fields:
        quality = "strong"
    elif len(weak_fields) <= 2 and len(excerpt.strip()) >= 150:
        quality = "usable"
    else:
        quality = "weak"
    return {
        "theorem_label": card.get("theorem_label", "unknown"),
        "quality": quality,
        "weak_fields": weak_fields,
    }


def _proof_coverage(proof_cards: list[dict[str, Any]]) -> str:
    if not proof_cards:
        return "none"
    reusable = sum(
        1
        for card in proof_cards
        if not _is_generic(str(card.get("proof_strategy", "")))
        or _nonempty_list(card.get("key_lemmas"))
        or _nonempty_list(card.get("key_estimates"))
    )
    if reusable >= max(1, len(proof_cards) // 2):
        return "usable"
    return "weak"


def _method_coverage(method_cards: list[dict[str, Any]]) -> str:
    if not method_cards:
        return "none"
    reusable = sum(1 for card in method_cards if str(card.get("method", "")).strip())
    return "usable" if reusable else "weak"


def _limitation_coverage(limitation_cards: list[dict[str, Any]]) -> str:
    if not limitation_cards:
        return "none"
    concrete = sum(1 for card in limitation_cards if "abstract-level uncertainty" not in str(card.get("limitation_type", "")).lower())
    return "usable" if concrete else "weak"


def _gap_coverage(gap_cards: list[dict[str, Any]]) -> str:
    if not gap_cards:
        return "none"
    concrete = sum(
        1
        for card in gap_cards
        if not _is_generic(str(card.get("known_result_from_input", "")))
        and not _is_generic(str(card.get("missing_case", "")))
    )
    if concrete >= max(1, len(gap_cards) // 2):
        return "usable"
    return "weak"


def _warnings(
    full_text_read: bool,
    extraction_confidence: str,
    text_length: int,
    theorem_cards: list[dict[str, Any]],
    strong_theorems: int,
    usable_theorems: int,
    proof_coverage: str,
    method_coverage: str,
    gap_coverage: str,
) -> list[str]:
    warnings = []
    if not full_text_read:
        warnings.append("Full text was not read; final questions must be marked lower confidence.")
    if extraction_confidence == "low":
        warnings.append("Text extraction confidence is low.")
    if text_length < 5000:
        warnings.append("Extracted text is short; theorem/proof evidence may be incomplete.")
    if not theorem_cards:
        warnings.append("No theorem cards were extracted.")
    if usable_theorems == 0:
        warnings.append("No usable theorem card with concrete assumptions and conclusion was extracted.")
    elif strong_theorems == 0:
        warnings.append("Theorem cards are usable but weak; require conservative candidate generation.")
    if proof_coverage in {"none", "weak"}:
        warnings.append("Proof-card coverage is weak; proof sprints must be treated as uncertain.")
    if method_coverage in {"none", "weak"}:
        warnings.append("No strong reusable method card was extracted.")
    if gap_coverage in {"none", "weak"}:
        warnings.append("Gap cards are weak; avoid high-confidence novelty claims.")
    return warnings


def _evidence_score(
    full_text_read: bool,
    extraction_confidence: str,
    text_length: int,
    strong_theorems: int,
    usable_theorems: int,
    proof_coverage: str,
    method_coverage: str,
    limitation_coverage: str,
    gap_coverage: str,
) -> int:
    score = 0
    score += 20 if full_text_read else 0
    score += {"high": 20, "medium": 12, "low": 4}.get(extraction_confidence, 4)
    score += 15 if text_length >= 12000 else 8 if text_length >= 5000 else 2
    score += min(20, 10 * strong_theorems + 5 * max(0, usable_theorems - strong_theorems))
    score += 10 if proof_coverage == "usable" else 3 if proof_coverage == "weak" else 0
    score += 8 if method_coverage == "usable" else 2 if method_coverage == "weak" else 0
    score += 5 if limitation_coverage == "usable" else 1 if limitation_coverage == "weak" else 0
    score += 7 if gap_coverage == "usable" else 2 if gap_coverage == "weak" else 0
    return min(score, 100)


def _evidence_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _downstream_policy(evidence_level: str, full_text_read: bool, usable_theorems: int) -> dict[str, Any]:
    high_confidence_allowed = evidence_level == "high" and full_text_read and usable_theorems > 0
    return {
        "candidate_generation_allowed": usable_theorems > 0,
        "high_confidence_final_questions_allowed": high_confidence_allowed,
        "must_mark_metadata_abstract_only": not full_text_read,
        "must_prefer_needs_deeper_reading": usable_theorems == 0,
        "policy_summary": (
            "Evidence supports high-confidence theorem-level generation."
            if high_confidence_allowed
            else "Evidence is incomplete; generate conservatively and mark lower confidence."
        ),
    }


def _is_generic(value: str) -> bool:
    lower = value.lower().strip()
    if not lower:
        return True
    return any(phrase in lower for phrase in GENERIC_EVIDENCE_PHRASES)


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)
