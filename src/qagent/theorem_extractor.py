from __future__ import annotations

import re
from typing import Any


THEOREM_PATTERN = r"(?ims)^\s*(Theorem|Proposition|Lemma|Corollary|Main Theorem)\s*([\w.\-]*)\s*(.*?)(?=^\s*(?:Theorem|Proposition|Lemma|Corollary|Main Theorem|Remark|Proof|Section|\d+\.|\Z))"


def extract_theorem_cards(text: str, paper_profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cards = []
    for index, match in enumerate(re.finditer(THEOREM_PATTERN, text), 1):
        theorem_type, number, body = match.groups()
        summary = re.sub(r"\s+", " ", body).strip()
        cards.append(
            {
                "theorem_label": f"{theorem_type} {number}".strip() or f"theorem_{index}",
                "theorem_type": theorem_type,
                "assumptions": _guess_assumptions(summary),
                "conclusion": _guess_conclusion(summary),
                "domain": _unknown_or_profile(paper_profile, "domain"),
                "dimension": _guess_dimension(summary),
                "boundary_condition": _guess_boundary(summary),
                "regularity_class": _guess_regularities(summary),
                "parameter_range": _guess_parameters(summary),
                "dependencies": "uncertain from automatic extraction",
                "source_excerpt_or_summary": summary[:2000],
                "evidence_source": "full text theorem-like block",
                "confidence": _theorem_confidence(summary),
            }
        )
    if cards:
        return cards
    return [
        {
            "theorem_label": "abstract_main_result",
            "theorem_type": "abstract summary",
            "assumptions": "not fully specified in available text",
            "conclusion": (paper_profile or {}).get("main_results", "not specified"),
            "domain": _unknown_or_profile(paper_profile, "mathematical_area"),
            "dimension": "not specified",
            "boundary_condition": "not specified",
            "regularity_class": "not specified",
            "parameter_range": "not specified",
            "dependencies": "metadata/abstract only",
            "source_excerpt_or_summary": (paper_profile or {}).get("abstract", ""),
            "evidence_source": "metadata/abstract fallback",
            "confidence": "low",
        }
    ]


def extract_proof_cards(text: str, theorem_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proof_text = _proof_regions(text)
    return [
        {
            "theorem_label": card["theorem_label"],
            "proof_strategy": _strategy_from_text(proof_text),
            "key_lemmas": _find_named_items(proof_text, ["Lemma", "Proposition"]),
            "key_estimates": _find_estimates(proof_text),
            "where_assumptions_are_used": "automatic extraction uncertain; inspect proof around the theorem label",
            "possible_fragile_steps": "compactness, endpoint estimates, boundary terms, and passage to limits",
            "likely_reusable_tools": _find_methods(proof_text),
        }
        for card in theorem_cards
    ]


def extract_method_cards(text: str) -> list[dict[str, Any]]:
    method_names = {
        "De Giorgi iteration": ["De Giorgi", "level set iteration", "oscillation decay"],
        "Caccioppoli inequality": ["Caccioppoli", "reverse Poincare", "energy inequality"],
        "commutator estimate": ["commutator"],
        "monotonicity formula": ["monotonicity formula", "monotonicity"],
        "epiperimetric inequality": ["epiperimetric"],
        "Modica gradient bound": ["Modica", "gradient bound", "gradient estimate"],
        "varifold compactness": ["varifold compactness", "integral varifold", "first variation"],
        "blow-up analysis": ["blow-up", "blow up", "rescaling", "tangent map", "tangent cone"],
        "Schauder estimate": ["Schauder"],
        "Li-Yau estimate": ["Li-Yau", "Li Yau"],
        "Aronson-Benilan estimate": ["Aronson-Benilan", "Aronson Benilan"],
        "Gamma-convergence": ["Gamma-convergence", "Gamma convergence", "\\Gamma-convergence"],
        "Galerkin method": ["Galerkin"],
        "compactness method": ["compactness", "compactness argument"],
        "duality method": ["duality", "dual estimate"],
        "comparison principle": ["comparison principle", "maximum principle"],
    }
    lower = text.lower()
    cards = []
    for name, aliases in method_names.items():
        matched_alias = next((alias for alias in aliases if alias.lower() in lower), "")
        if matched_alias:
            cards.append(
                {
                    "method": name,
                    "matched_text": matched_alias,
                    "where_it_appears": _context(text, matched_alias),
                    "what_it_proves": "automatic extraction: used as part of the paper's main proof strategy",
                    "assumptions_needed": "not fully specified by automatic extraction",
                    "reusability": "medium",
                }
            )
    return cards


def _unknown_or_profile(profile: dict[str, Any] | None, key: str) -> str:
    return str((profile or {}).get(key, "not specified"))


def _guess_assumptions(text: str) -> str:
    match = re.search(r"(?i)(assume|suppose|let|if)\s+(.{0,500})", text)
    return match.group(0) if match else "not fully specified by automatic extraction"


def _guess_conclusion(text: str) -> str:
    match = re.search(r"(?i)(then|we have|there exists|there is|is regular|is smooth|converges|satisfies|admits|holds)\s+(.{0,650})", text)
    return match.group(0) if match else text[:500]


def _guess_dimension(text: str) -> str:
    match = re.search(r"(?i)(dimension|dimensional|d\s*[=<>]\s*\d+|n\s*[=<>]\s*\d+).{0,80}", text)
    return match.group(0) if match else "not specified"


def _guess_boundary(text: str) -> str:
    match = re.search(r"(?i)(Dirichlet|Neumann|Robin|boundary|free boundary|no-flux).{0,120}", text)
    return match.group(0) if match else "not specified"


def _guess_regularities(text: str) -> str:
    found = re.findall(r"(?i)\b(C\^\{?[\w,]+\}?|L\^\{?[\w,]+\}?|W\^\{?[\w,]+\}?|Holder|Lipschitz|smooth|weak)\b", text)
    return ", ".join(dict.fromkeys(found)) if found else "not specified"


def _guess_parameters(text: str) -> str:
    match = re.search(r"(?i)(p\s*(?:in|\\in|=|<|>)\s*.{0,80}|m\s*=\s*.{0,80}|alpha\s*(?:in|=|<|>)\s*.{0,80})", text)
    return match.group(0) if match else "not specified"


def _proof_regions(text: str) -> str:
    matches = re.findall(r"(?ims)^\s*Proof\b.*?(?=^\s*(?:Theorem|Proposition|Lemma|Corollary|Section|\d+\.|\Z))", text)
    return "\n\n".join(matches)[:12000]


def _strategy_from_text(text: str) -> str:
    if not text:
        return "proof not available in extracted text"
    return re.sub(r"\s+", " ", text[:1200]).strip()


def _find_named_items(text: str, names: list[str]) -> list[str]:
    items = []
    for name in names:
        items.extend(re.findall(rf"(?i){name}\s+[\w.\-]+", text))
    return list(dict.fromkeys(items))[:10]


def _find_estimates(text: str) -> list[str]:
    terms = ["Caccioppoli", "Schauder", "Li-Yau", "Aronson-Benilan", "monotonicity", "energy estimate", "gradient bound", "compactness"]
    return [term for term in terms if term.lower() in text.lower()]


def _theorem_confidence(summary: str) -> str:
    lower = summary.lower()
    has_assumption = any(term in lower for term in ["assume", "suppose", "let", "if "])
    has_conclusion = any(term in lower for term in ["then", "there exists", "there is", "converges", "satisfies", "is smooth", "is regular"])
    if len(summary) > 250 and has_assumption and has_conclusion:
        return "high"
    if len(summary) > 100 and (has_assumption or has_conclusion):
        return "medium"
    return "low"


def _find_methods(text: str) -> list[str]:
    return _find_estimates(text) or ["not identified automatically"]


def _context(text: str, needle: str, radius: int = 400) -> str:
    index = text.lower().find(needle.lower())
    if index < 0:
        return ""
    return re.sub(r"\s+", " ", text[max(0, index - radius) : index + radius]).strip()
