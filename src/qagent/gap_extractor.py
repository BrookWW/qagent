from __future__ import annotations

from typing import Any


def extract_limitation_cards(text: str, theorem_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lower = text.lower()
    cards = []
    checks = [
        ("dimension restriction", ["dimension", "two dimensions", "d=", "n="]),
        ("smoothness restriction", ["smooth", "lipschitz", "c^", "regularity"]),
        ("boundary restriction", ["boundary", "dirichlet", "neumann", "free boundary"]),
        ("compactness assumption", ["compact", "closed manifold", "bounded domain"]),
        ("smallness assumption", ["small", "subcritical", "critical mass"]),
        ("topology assumption", ["topology", "simply connected", "orientable"]),
        ("no rate or quantitative gap", ["converges", "stability", "rate"]),
        ("possible sharpness issue", ["sharp", "optimal", "counterexample", "threshold"]),
    ]
    for label, terms in checks:
        if any(term in lower for term in terms):
            cards.append(
                {
                    "limitation_type": label,
                    "description": f"Automatic extraction found terms suggesting a {label}.",
                    "linked_theorems": [card["theorem_label"] for card in theorem_cards[:3]],
                    "source_summary": "verify against full text before treating as a real limitation",
                    "confidence": "medium",
                }
            )
    if not cards:
        cards.append(
            {
                "limitation_type": "abstract-level uncertainty",
                "description": "No concrete limitation was extracted automatically; full text or human review is needed.",
                "linked_theorems": [card["theorem_label"] for card in theorem_cards[:1]],
                "source_summary": "metadata/abstract only",
                "confidence": "low",
            }
        )
    return cards


def extract_gap_cards(theorem_cards: list[dict[str, Any]], limitation_cards: list[dict[str, Any]], method_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = []
    tools = ", ".join(card.get("method", "") for card in method_cards[:4]) or "methods from the input theorem cards"
    for index, limitation in enumerate(limitation_cards[:6], 1):
        known = theorem_cards[min(index - 1, len(theorem_cards) - 1)] if theorem_cards else {}
        gap_type = limitation.get("limitation_type", "possible extension")
        gaps.append(
            {
                "gap_title": f"Model extension beyond {gap_type}",
                "gap_type": gap_type,
                "evidence_basis": {
                    "linked_theorem_label": known.get("theorem_label", "not specified"),
                    "linked_limitation_type": gap_type,
                    "method_card_count": len(method_cards),
                    "limitation_confidence": limitation.get("confidence", "low"),
                },
                "evidence_strength": _gap_evidence_strength(known, limitation, method_cards),
                "known_result_from_input": known.get("conclusion", known.get("source_excerpt_or_summary", "not specified")),
                "missing_case": limitation.get("description", "not specified"),
                "why_not_direct_restatement": "The gap asks for a narrowed extension, quantitative strengthening, or missing case rather than repeating the extracted theorem.",
                "expected_tools": tools,
                "possible_obstacles": "the extracted limitation may be sharp; endpoint estimates, compactness, or boundary terms may fail",
                "duplicate_risk_queries": [
                    f"{gap_type} {known.get('theorem_label', '')}",
                    f"{tools} {gap_type}",
                    f"sharpness {gap_type} theorem",
                ],
                "qed_gpt_attackability_guess": "medium",
                "sci_publishable_potential_guess": "medium",
                "nontriviality_guess": "medium",
            }
        )
    return gaps


def _gap_evidence_strength(known: dict[str, Any], limitation: dict[str, Any], method_cards: list[dict[str, Any]]) -> str:
    known_text = str(known.get("conclusion") or known.get("source_excerpt_or_summary") or "").lower()
    limitation_text = str(limitation.get("description") or "").lower()
    weak_known = not known_text or "not specified" in known_text or "infer from" in known_text
    weak_limitation = not limitation_text or "automatic extraction found terms" in limitation_text
    has_methods = bool(method_cards)
    if not weak_known and not weak_limitation and has_methods:
        return "medium"
    if not weak_known and has_methods:
        return "low_to_medium"
    return "low"
