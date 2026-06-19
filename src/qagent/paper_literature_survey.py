from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .survey import (
    _arxiv_search,
    _crossref_search,
    _dedupe_papers,
    _openalex_search,
    _semantic_scholar_search,
    _survey_headers,
)


PAPER_SURVEY_JSON = "paper_literature_survey.json"
PAPER_SURVEY_MD = "paper_literature_survey.md"
LOCAL_SURVEY_ROWS = 40


def run_local_paper_literature_survey(output_dir: Path, n: int, try_online: bool = True, timeout: int = 8) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        survey = _local_survey_for_paper(paper_dir, paper_id, try_online=try_online, timeout=timeout)
        _write_json(paper_dir / PAPER_SURVEY_JSON, survey)
        (paper_dir / PAPER_SURVEY_MD).write_text(_survey_markdown(survey), encoding="utf-8")
        reports.append(
            {
                "paper_id": paper_id,
                "survey_confidence": survey.get("survey_confidence", "low"),
                "related_papers": len(survey.get("related_papers", [])),
                "online_attempted": try_online,
                "survey_degraded": bool(survey.get("survey_degraded")),
            }
        )
    summary = {"ok": True, "stage": "local_paper_literature_survey", "papers": reports}
    _write_json(output_dir / "paper_literature_survey_local_summary.json", summary)
    return summary


def build_paper_literature_survey_prompt(output_dir: Path, batch_id: str, n: int) -> str:
    payload = _survey_payload(output_dir, n)
    return f"""Please run QAgent paper-level literature survey only.

Scope:
- Work only under `outputs/{batch_id}/paper_###/`.
- Do not write candidate_questions.json, ranked_questions.json, selected folders, hard_review, or final outputs.
- For each paper, write:
  - `outputs/{batch_id}/{{paper_id}}/{PAPER_SURVEY_JSON}`
  - `outputs/{batch_id}/{{paper_id}}/{PAPER_SURVEY_MD}`

Goal:
Before QAgent generates candidate research questions, identify nearby literature that could make natural questions already known. This is a pre-generation survey, not a post-hoc justification.

Use a QED/ProofQED-style adversarial survey workflow:
1. Difficulty and novelty-risk evaluation. Decide whether this paper's natural follow-up questions are likely Easy, Medium, or Hard to make genuinely new.
2. Deep related-work collection. Search the exact paper title, authors, arXiv/CVGMT identifiers, theorem keywords, model equation, proof method, and conclusion phrases.
3. Search arXiv, CVGMT, OpenAlex, Semantic Scholar, Crossref, MathOverflow, Wikipedia/textbook references, and the general web if available in the Codex CLI context. Do not scrape Google Scholar.
4. Collect every relevant paper, theorem, lemma, counterexample, and technique that could kill or guide a generated research question.
5. For each theorem/result you cite, record the full hypotheses and explain what candidate direction it would make trivial or already known.
6. Identify counterexamples and pitfalls: hypotheses that cannot be dropped, false stronger versions, and common mistakes.
7. Self-verify citations: re-check URLs, titles, authors, and theorem statements. Remove unverifiable claims rather than keeping hallucinated references.
8. If external search is unavailable, still create the files from local paper evidence, mark confidence low, and explicitly state what could not be verified.

Required JSON schema for every paper:
{{
  "paper_id": "paper_001",
  "paper_title": "...",
  "survey_confidence": "high | medium | low",
  "difficulty_for_new_questions": "easy | medium | hard | unknown",
  "difficulty_justification": "...",
  "search_queries": ["..."],
  "related_papers": [
    {{
      "title": "...",
      "authors": "...",
      "year": "...",
      "source": "arXiv | CVGMT | OpenAlex | Semantic Scholar | Crossref | web | local evidence",
      "url": "...",
      "relationship": "input paper | same theorem | same model | same method | related extension | possible duplicate",
      "matched_theorem_or_method": "...",
      "duplicate_warning": "..."
    }}
  ],
  "directly_applicable_theorems": [
    {{
      "theorem_name": "...",
      "precise_statement": "...",
      "source": "...",
      "url": "...",
      "relevance": "...",
      "conditions_to_check": ["..."],
      "candidate_directions_killed": ["..."]
    }}
  ],
  "useful_lemmas_and_inequalities": ["..."],
  "counterexamples_and_pitfalls": ["..."],
  "likely_known_directions": ["..."],
  "safe_novelty_gaps": ["..."],
  "do_not_generate": ["..."],
  "recommended_candidate_angles": ["..."],
  "self_verification": {{
    "entries_checked": 0,
    "entries_removed_after_verification": [],
    "source_inaccessible_caveats": [],
    "confidence_in_remaining_entries": "high | medium | low"
  }},
  "survey_summary": "one concise paragraph"
}}

Hard survey standards:
- `related_papers` should include the input paper and as many genuinely nearby public hits as the search context can find.
- `directly_applicable_theorems` must be theorem-level, with hypotheses and exact relevance, not vague names.
- `counterexamples_and_pitfalls` must be concrete enough to prevent fake generalizations.
- `do_not_generate` must be concrete enough to block obvious duplicate candidate ideas.
- `recommended_candidate_angles` must prefer small, paper-specific extensions with a real obstruction.
- Do not claim high confidence if no external search was possible.
- The Markdown file must include QED-style sections: Difficulty Evaluation, Directly Applicable Theorems, Related Papers, Useful Lemmas and Inequalities, Counterexamples and Pitfalls, Self-Verification, Do Not Generate, Recommended Candidate Angles.

Papers to survey:
```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```

When finished, summarize the survey files written."""


def ensure_paper_literature_survey_outputs(output_dir: Path, n: int, survey_result: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewer_ok = bool((survey_result or {}).get("ok"))
    reviewer_error = str((survey_result or {}).get("error_message", ""))
    present = 0
    degraded = 0
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)
        json_path = paper_dir / PAPER_SURVEY_JSON
        md_path = paper_dir / PAPER_SURVEY_MD
        existing = _read_json(json_path)
        if _valid_survey(existing, paper_id):
            present += 1
            if not md_path.exists():
                md_path.write_text(_survey_markdown(existing), encoding="utf-8")
            continue
        degraded_survey = _degraded_survey(paper_dir, paper_id, reviewer_ok, reviewer_error)
        _write_json(json_path, degraded_survey)
        md_path.write_text(_survey_markdown(degraded_survey), encoding="utf-8")
        degraded += 1

    summary = {
        "ok": True,
        "reviewer_ok": reviewer_ok,
        "papers_with_valid_survey": present,
        "degraded_surveys": degraded,
    }
    _write_json(output_dir / "paper_literature_survey_summary.json", summary)
    return summary


def _local_survey_for_paper(paper_dir: Path, paper_id: str, try_online: bool, timeout: int) -> dict[str, Any]:
    profile = _read_json(paper_dir / "paper_profile.json") or {}
    theorem_cards = _read_json(paper_dir / "theorem_cards.json") or []
    proof_cards = _read_json(paper_dir / "proof_cards.json") or []
    method_cards = _read_json(paper_dir / "method_cards.json") or []
    gap_cards = _read_json(paper_dir / "gap_cards.json") or []
    title = str(profile.get("title") or profile.get("paper_title") or paper_id)
    authors = str(profile.get("authors", ""))
    queries = _paper_survey_queries(profile, theorem_cards, proof_cards, method_cards, gap_cards)
    related: list[dict[str, Any]] = [
        {
            "title": title,
            "authors": authors,
            "year": str(profile.get("year", "")),
            "source": "local evidence",
            "url": str(profile.get("url", "")),
            "relationship": "input paper",
            "matched_theorem_or_method": "input paper",
            "duplicate_warning": "Do not reproduce the input paper's main theorem or proof module.",
        }
    ]
    log: list[str] = []
    if try_online:
        try:
            import requests

            session = requests.Session()
            session.headers.update(_survey_headers())
            for query in queries[:8]:
                for search_fn in [_crossref_search, _openalex_search, _arxiv_search, _semantic_scholar_search]:
                    items, source_log = search_fn(session, query, timeout)
                    related.extend(items)
                    log.extend(source_log)
        except ImportError:
            log.append("requests is not installed; online metadata survey skipped")
        except Exception as exc:
            log.append(f"online metadata survey failed: {type(exc).__name__}: {exc}")
    else:
        log.append("online metadata survey disabled")

    related = _annotate_relationships(_dedupe_papers(related), title, theorem_cards, proof_cards, method_cards)
    external = [paper for paper in related if paper.get("source") != "local evidence"]
    confidence = "medium" if len(external) >= 3 else "low"
    if len(external) >= 10:
        confidence = "high"
    return {
        "paper_id": paper_id,
        "paper_title": title,
        "survey_confidence": confidence,
        "difficulty_for_new_questions": "unknown" if confidence == "low" else "medium",
        "difficulty_justification": (
            "Local metadata survey can identify nearby papers and obvious duplicate directions, "
            "but full difficulty depends on theorem-level comparison by the Codex survey agent."
        ),
        "search_queries": queries,
        "related_papers": related[:LOCAL_SURVEY_ROWS],
        "directly_applicable_theorems": _directly_applicable_theorems(theorem_cards, related),
        "useful_lemmas_and_inequalities": _useful_lemmas(proof_cards, method_cards),
        "counterexamples_and_pitfalls": _counterexamples_and_pitfalls(theorem_cards, gap_cards),
        "likely_known_directions": _likely_known_directions(profile, theorem_cards, proof_cards, method_cards, related),
        "safe_novelty_gaps": _safe_novelty_gaps(gap_cards, theorem_cards),
        "do_not_generate": _do_not_generate(profile, theorem_cards, proof_cards, related),
        "recommended_candidate_angles": _recommended_candidate_angles(gap_cards, method_cards),
        "self_verification": {
            "entries_checked": len(related[:LOCAL_SURVEY_ROWS]),
            "entries_removed_after_verification": [],
            "source_inaccessible_caveats": [
                "Local metadata survey verifies metadata records but not full theorem statements unless present in extracted paper evidence."
            ],
            "confidence_in_remaining_entries": confidence,
        },
        "survey_summary": (
            f"Local metadata survey found {len(external)} external related hits from public metadata sources. "
            f"Confidence is {confidence}; use this as a pre-generation negative map, not as a complete literature review."
        ),
        "survey_log": log[-60:],
        "survey_degraded": False,
    }


def _survey_payload(output_dir: Path, n: int) -> dict[str, Any]:
    papers: list[dict[str, Any]] = []
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        papers.append(
            {
                "paper_id": paper_id,
                "paper_profile": _read_json(paper_dir / "paper_profile.json") or {},
                "paper_reading_quality": _read_json(paper_dir / "paper_reading_quality.json") or {},
                "theorem_cards": _read_json(paper_dir / "theorem_cards.json") or [],
                "proof_cards": _read_json(paper_dir / "proof_cards.json") or [],
                "method_cards": _read_json(paper_dir / "method_cards.json") or [],
                "limitation_cards": _read_json(paper_dir / "limitation_cards.json") or [],
                "gap_cards": _read_json(paper_dir / "gap_cards.json") or [],
                "local_paper_literature_survey": _read_json(paper_dir / PAPER_SURVEY_JSON) or {},
            }
        )
    return {"papers": papers}


def _paper_survey_queries(
    profile: dict[str, Any],
    theorem_cards: list[Any],
    proof_cards: list[Any],
    method_cards: list[Any],
    gap_cards: list[Any],
) -> list[str]:
    title = str(profile.get("title") or profile.get("paper_title") or "").strip()
    authors = str(profile.get("authors", "")).strip()
    keywords = str(profile.get("matched_keywords") or profile.get("keywords") or "").strip()
    snippets = [
        _card_text(theorem_cards, ["theorem_label", "statement", "conclusion", "main_estimate"]),
        _card_text(proof_cards, ["proof_label", "key_estimate", "method", "proof_mechanism"]),
        _card_text(method_cards, ["method_label", "method", "tool", "estimate"]),
        _card_text(gap_cards, ["gap_title", "gap", "obstruction"]),
    ]
    raw = [
        f'"{title}"' if title else "",
        title,
        f"{title} {authors}",
        f"{title} theorem",
        f"{title} arXiv",
        f"{title} CVGMT",
        f"{authors} {keywords}",
        *snippets,
        f"{keywords} theorem",
        f"{keywords} {snippets[0]}",
    ]
    queries: list[str] = []
    for item in raw:
        clean = re.sub(r"\s+", " ", str(item)).strip()
        if clean and clean not in queries:
            queries.append(clean[:260])
    return queries[:14]


def _card_text(cards: list[Any], keys: list[str]) -> str:
    for card in cards:
        if not isinstance(card, dict):
            continue
        parts = [str(card.get(key, "")).strip() for key in keys if str(card.get(key, "")).strip()]
        if parts:
            return " ".join(parts)[:180]
    return ""


def _annotate_relationships(
    related: list[dict[str, Any]],
    input_title: str,
    theorem_cards: list[Any],
    proof_cards: list[Any],
    method_cards: list[Any],
) -> list[dict[str, Any]]:
    theorem_text = _card_text(theorem_cards, ["statement", "conclusion", "main_estimate"])
    method_text = _card_text(proof_cards + method_cards, ["method", "tool", "key_estimate", "proof_mechanism"])
    for paper in related:
        title = str(paper.get("title", ""))
        relationship = "related extension"
        warning = ""
        if _title_overlap(title, input_title) > 0.86:
            relationship = "input paper"
            warning = "This is the input or near-identical title; do not reproduce it."
        elif theorem_text and _word_overlap(title, theorem_text) >= 2:
            relationship = "same theorem"
            warning = "Candidate directions matching this theorem language may already be known."
        elif method_text and _word_overlap(title, method_text) >= 2:
            relationship = "same method"
            warning = "Method-only variants may be too close unless a new obstruction is explicit."
        paper.setdefault("relationship", relationship)
        paper.setdefault("matched_theorem_or_method", theorem_text or method_text or "metadata title match")
        paper.setdefault("duplicate_warning", warning)
    return related


def _likely_known_directions(
    profile: dict[str, Any],
    theorem_cards: list[Any],
    proof_cards: list[Any],
    method_cards: list[Any],
    related: list[dict[str, Any]],
) -> list[str]:
    title = str(profile.get("title") or profile.get("paper_title") or "the input paper")
    directions = [
        f"Direct restatement or routine parameter variation of {title}.",
        "Proof modules, estimates, or lemmas that are already used as internal steps in the input paper.",
    ]
    for text in [
        _card_text(theorem_cards, ["statement", "conclusion", "main_estimate"]),
        _card_text(proof_cards, ["key_estimate", "proof_mechanism"]),
        _card_text(method_cards, ["method", "tool"]),
    ]:
        if text:
            directions.append(f"Already-near direction: {text}")
    for paper in related[:8]:
        if paper.get("source") != "local evidence":
            directions.append(f"Check before generating: {paper.get('title', '')}")
    return _unique(directions)[:16]


def _safe_novelty_gaps(gap_cards: list[Any], theorem_cards: list[Any]) -> list[str]:
    gaps = []
    for card in gap_cards:
        if isinstance(card, dict):
            text = " ".join(str(card.get(key, "")).strip() for key in ["gap_title", "gap", "obstruction", "candidate_direction"] if str(card.get(key, "")).strip())
            if text:
                gaps.append(text)
    if not gaps:
        theorem = _card_text(theorem_cards, ["limitation", "hypotheses", "conclusion"])
        if theorem:
            gaps.append(f"Only narrow extensions beyond the extracted theorem hypotheses: {theorem}")
    return _unique(gaps)[:10] or ["No safe novelty gap found by local survey; prefer needs deeper reading."]


def _do_not_generate(
    profile: dict[str, Any],
    theorem_cards: list[Any],
    proof_cards: list[Any],
    related: list[dict[str, Any]],
) -> list[str]:
    title = str(profile.get("title") or profile.get("paper_title") or "the input paper")
    blocked = [
        f"Do not ask to prove the main theorem of {title}.",
        "Do not generate a problem that only packages a lemma/proof module from the input paper as a new theorem.",
    ]
    for text in [
        _card_text(theorem_cards, ["statement", "conclusion", "main_estimate"]),
        _card_text(proof_cards, ["key_estimate", "proof_mechanism"]),
    ]:
        if text:
            blocked.append(f"Do not generate routine corollaries of: {text}")
    for paper in related[:8]:
        warning = str(paper.get("duplicate_warning", "")).strip()
        if warning:
            blocked.append(warning)
    return _unique(blocked)[:14]


def _recommended_candidate_angles(gap_cards: list[Any], method_cards: list[Any]) -> list[str]:
    angles = []
    for gap in _safe_novelty_gaps(gap_cards, []):
        angles.append(f"Use gap with one explicit new obstruction: {gap}")
    method = _card_text(method_cards, ["method", "tool", "estimate"])
    if method:
        angles.append(f"Keep method delta small by adapting: {method}")
    return _unique(angles)[:10]


def _directly_applicable_theorems(theorem_cards: list[Any], related: list[dict[str, Any]]) -> list[dict[str, Any]]:
    theorems: list[dict[str, Any]] = []
    for index, card in enumerate(theorem_cards[:8], 1):
        if not isinstance(card, dict):
            continue
        statement = _card_text([card], ["statement", "conclusion", "main_estimate", "theorem_statement"])
        if not statement:
            continue
        source = "input paper theorem card"
        url = ""
        if related:
            source = str(related[0].get("title", source))
            url = str(related[0].get("url", ""))
        theorems.append(
            {
                "theorem_name": str(card.get("theorem_label") or card.get("name") or f"Input theorem card {index}"),
                "precise_statement": statement,
                "source": source,
                "url": url,
                "relevance": "This theorem is already present in the input-paper evidence and should not be regenerated as a new question.",
                "conditions_to_check": _unique([str(card.get(key, "")).strip() for key in ["hypotheses", "assumptions", "setting"]])[:5],
                "candidate_directions_killed": [f"Direct restatement or routine corollary of {statement[:180]}"],
            }
        )
    return theorems


def _useful_lemmas(proof_cards: list[Any], method_cards: list[Any]) -> list[str]:
    lemmas = []
    for card in proof_cards + method_cards:
        if isinstance(card, dict):
            text = _card_text([card], ["key_estimate", "lemma", "method", "tool", "proof_mechanism"])
            if text:
                lemmas.append(text)
    return _unique(lemmas)[:12]


def _counterexamples_and_pitfalls(theorem_cards: list[Any], gap_cards: list[Any]) -> list[str]:
    pitfalls = []
    for card in theorem_cards + gap_cards:
        if isinstance(card, dict):
            text = _card_text([card], ["counterexample", "pitfall", "limitation", "obstruction", "failure_mode"])
            if text:
                pitfalls.append(text)
    if not pitfalls:
        pitfalls.append("Avoid dropping input-paper hypotheses without a named replacement estimate or counterexample check.")
        pitfalls.append("Avoid cosmetic parameter changes that follow by the same proof module.")
    return _unique(pitfalls)[:10]


def _title_overlap(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _word_overlap(a: str, b: str) -> int:
    stop = {"the", "and", "for", "with", "from", "that", "this", "some", "into", "over", "under", "problem", "problems"}
    aa = {word for word in re.findall(r"[a-zA-Z]{4,}", a.lower()) if word not in stop}
    bb = {word for word in re.findall(r"[a-zA-Z]{4,}", b.lower()) if word not in stop}
    return len(aa & bb)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        clean = re.sub(r"\s+", " ", str(item)).strip()
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def _valid_survey(data: Any, paper_id: str) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("paper_id", "")).strip() != paper_id:
        return False
    required = ["search_queries", "related_papers", "likely_known_directions", "safe_novelty_gaps", "do_not_generate", "recommended_candidate_angles"]
    return all(isinstance(data.get(key), list) for key in required)


def _degraded_survey(paper_dir: Path, paper_id: str, reviewer_ok: bool, reviewer_error: str) -> dict[str, Any]:
    profile = _read_json(paper_dir / "paper_profile.json") or {}
    title = str(profile.get("title") or profile.get("paper_title") or paper_id)
    authors = str(profile.get("authors", ""))
    url = str(profile.get("url", ""))
    reason = "External pre-generation survey was not available."
    if reviewer_error:
        reason += f" Codex survey error: {reviewer_error}"
    elif reviewer_ok:
        reason += " Codex survey returned but did not produce a valid survey file."
    return {
        "paper_id": paper_id,
        "paper_title": title,
        "survey_confidence": "low",
        "difficulty_for_new_questions": "unknown",
        "difficulty_justification": "External survey did not complete; only local paper evidence is available.",
        "search_queries": [
            title,
            f"{title} arXiv",
            f"{title} CVGMT",
            f"{title} theorem",
            f"{title} related theorem",
        ],
        "directly_applicable_theorems": [],
        "useful_lemmas_and_inequalities": [],
        "counterexamples_and_pitfalls": [],
        "related_papers": [
            {
                "title": title,
                "authors": authors,
                "year": str(profile.get("year", "")),
                "source": "local evidence",
                "url": url,
                "relationship": "input paper",
                "matched_theorem_or_method": "input paper evidence only",
                "duplicate_warning": "Do not reproduce the input paper's main theorem or proof module.",
            }
        ],
        "likely_known_directions": ["The input paper's main theorem and immediate proof modules are already known in this context."],
        "safe_novelty_gaps": ["Only paper-specific extensions supported by theorem/proof/gap cards should be generated."],
        "do_not_generate": ["Do not generate direct restatements of the input theorem or routine corollaries of its proof."],
        "recommended_candidate_angles": ["Use the extracted gap cards and require one explicit new obstruction."],
        "self_verification": {
            "entries_checked": 1,
            "entries_removed_after_verification": [],
            "source_inaccessible_caveats": ["Only input-paper metadata was available."],
            "confidence_in_remaining_entries": "low",
        },
        "survey_summary": reason,
        "survey_degraded": True,
    }


def _survey_markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# Paper Literature Survey: {data.get('paper_id', 'paper')}",
        "",
        f"- Title: {data.get('paper_title', '')}",
        f"- Confidence: {data.get('survey_confidence', 'low')}",
        "",
        "## Difficulty Evaluation",
        "",
        f"- Classification: {data.get('difficulty_for_new_questions', 'unknown')}",
        f"- Justification: {data.get('difficulty_justification', '')}",
        "",
        "## Search Queries",
        "",
        *[f"- {query}" for query in data.get("search_queries", [])],
        "",
        "## Related Papers",
        "",
    ]
    for paper in data.get("related_papers", []):
        if isinstance(paper, dict):
            lines.extend(
                [
                    f"- **{paper.get('title', 'untitled')}**",
                    f"  - Authors: {paper.get('authors', '')}",
                    f"  - Year: {paper.get('year', '')}",
                    f"  - Source: {paper.get('source', '')}",
                    f"  - URL: {paper.get('url', '')}",
                    f"  - Relationship: {paper.get('relationship', '')}",
                    f"  - Duplicate warning: {paper.get('duplicate_warning', '')}",
                ]
            )
    lines.extend(["", "## Directly Applicable Theorems", ""])
    for theorem in data.get("directly_applicable_theorems", []):
        if isinstance(theorem, dict):
            lines.extend(
                [
                    f"### {theorem.get('theorem_name', 'Unnamed theorem')}",
                    f"- Statement: {theorem.get('precise_statement', '')}",
                    f"- Source: {theorem.get('source', '')}",
                    f"- URL: {theorem.get('url', '')}",
                    f"- Relevance: {theorem.get('relevance', '')}",
                    f"- Conditions to check: {', '.join(str(x) for x in theorem.get('conditions_to_check', []))}",
                    f"- Candidate directions killed: {', '.join(str(x) for x in theorem.get('candidate_directions_killed', []))}",
                    "",
                ]
            )
    for title, key in [
        ("Useful Lemmas and Inequalities", "useful_lemmas_and_inequalities"),
        ("Counterexamples and Pitfalls", "counterexamples_and_pitfalls"),
    ]:
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in data.get(key, []))
    for title, key in [
        ("Likely Known Directions", "likely_known_directions"),
        ("Safe Novelty Gaps", "safe_novelty_gaps"),
        ("Do Not Generate", "do_not_generate"),
        ("Recommended Candidate Angles", "recommended_candidate_angles"),
    ]:
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in data.get(key, []))
    verification = data.get("self_verification", {})
    lines.extend(["", "## Self-Verification", ""])
    if isinstance(verification, dict):
        lines.extend(
            [
                f"- Entries checked: {verification.get('entries_checked', 0)}",
                f"- Entries removed after verification: {verification.get('entries_removed_after_verification', [])}",
                f"- Source inaccessible caveats: {verification.get('source_inaccessible_caveats', [])}",
                f"- Confidence in remaining entries: {verification.get('confidence_in_remaining_entries', 'low')}",
            ]
        )
    lines.extend(["", "## Summary", "", str(data.get("survey_summary", "")), ""])
    return "\n".join(lines)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
