from __future__ import annotations

import json
from pathlib import Path
from typing import Any


NOVELTY_REVIEW_DIR = "candidate_novelty_reviews"
NOVELTY_VERDICTS = {
    "new_enough",
    "likely_known",
    "direct_corollary",
    "too_close_to_input",
    "insufficient_evidence",
}


def build_novelty_review_prompt(output_dir: Path, batch_id: str, n: int, b: int) -> str:
    payload = _review_payload(output_dir, n=n, b=b)
    return f"""Please run QAgent Codex novelty review only.

Scope:
- Work only under `outputs/{batch_id}/paper_###/{NOVELTY_REVIEW_DIR}/`.
- Do not modify candidate_questions.json, ranked_questions.json, hard_review.json, selected outputs, or evidence files.
- Do not create final selected questions.

Goal:
Act as a strict mathematical novelty referee. For each listed candidate, decide whether the proposed theorem-level problem is likely new enough, already known, a direct corollary, too close to the input paper, or insufficiently evidenced. Your default stance is adversarial: first try to reject the candidate as already known, then allow it only if the candidate survives that attack.

Important:
- Be conservative. If a candidate is probably a standard theorem, a direct corollary, or too close to the input paper, do not mark it `new_enough`.
- Before any positive verdict, identify the strongest "killer known theorem" candidate: the input-paper theorem, a classical theorem, or an external result that would make the problem already known.
- A cosmetic change is not novelty. Boundary/parameter/coefficient/domain changes count only if they create a named obstruction that changes at least one proof module.
- If the candidate differs only by wording, notation, restating a lemma, adding routine assumptions, or applying a standard theorem directly, use `direct_corollary` or `too_close_to_input`.
- If external search is available in the Codex CLI context, search arXiv/CVGMT/OpenAlex/Semantic Scholar/web using sharp theorem-level queries.
- For every top candidate, make an explicit search attempt unless the Codex CLI context has no search/web capability. Search arXiv, CVGMT, OpenAlex, Semantic Scholar, Crossref, and the general web when available.
- If external search is unavailable, still perform an adversarial novelty review from mathematical knowledge, set search_attempted = false, explain search_limitations, and mark confidence accordingly.
- This reviewer is evidence for hard review; do not write long prose reports.

Adversarial review checklist:
1. Compare the candidate against the closest theorem card from the input paper.
2. Try to kill it with the nearest standard theorem in the field.
3. Try to kill it with a direct corollary argument from the input proof method.
4. Try to kill it with a likely arXiv/CVGMT/OpenAlex/Semantic Scholar hit, if search is available.
5. State the exact non-cosmetic difference that survives these attacks.
6. If step 5 is weak, vague, or absent, do not use `new_enough`.

For every candidate below, write exactly one JSON file:

`outputs/{batch_id}/{{paper_id}}/{NOVELTY_REVIEW_DIR}/{{question_id}}.json`

Required JSON schema:
{{
  "question_id": "c01",
  "verdict": "new_enough | likely_known | direct_corollary | too_close_to_input | insufficient_evidence",
  "duplicate_risk": "low | medium | high | unknown",
  "recommended_action": "keep | revise | remove",
  "confidence": "high | medium | low",
  "closest_input_result": "...",
  "closest_external_result": "...",
  "killer_known_theorem_attempt": "...",
  "non_cosmetic_difference": "...",
  "why_not_direct_corollary": "...",
  "why_not_standard_theorem": "...",
  "novelty_axis": "...",
  "search_attempted": true,
  "search_backend_used": "Codex CLI web/search | arXiv/CVGMT/OpenAlex/Semantic Scholar/Crossref | unavailable",
  "search_limitations": "...",
  "searched_queries": ["..."],
  "reviewer_summary": "one concise paragraph",
  "strict_novelty_pass": true
}}

Rules:
- `strict_novelty_pass` may be true only when verdict is `new_enough`, duplicate_risk is `low`, recommended_action is `keep`, and confidence is at least `medium`.
- `strict_novelty_pass` also requires a concrete `killer_known_theorem_attempt`, `non_cosmetic_difference`, `why_not_direct_corollary`, and `why_not_standard_theorem`.
- If search_attempted is false or search_limitations are severe, do not use confidence `high`.
- `likely_known`, `direct_corollary`, `too_close_to_input`, and `insufficient_evidence` must have `strict_novelty_pass = false`.
- If unsure, use `insufficient_evidence`, not `new_enough`.

Candidates to review:
```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```

When finished, summarize the JSON files written."""


def ensure_novelty_review_outputs(output_dir: Path, n: int, b: int, reviewer_result: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _review_payload(output_dir, n=n, b=b, include_non_top=True)
    reviewed = 0
    degraded = 0
    not_selected = 0
    strict_pass = 0
    reviewer_ok = bool((reviewer_result or {}).get("ok"))
    reviewer_error = str((reviewer_result or {}).get("error_message", ""))

    for paper in payload["papers"]:
        paper_dir = output_dir / paper["paper_id"]
        review_dir = paper_dir / NOVELTY_REVIEW_DIR
        review_dir.mkdir(parents=True, exist_ok=True)
        top_ids = set(paper.get("top_question_ids", []))
        for candidate in paper.get("candidates", []):
            question_id = str(candidate.get("question_id", "")).strip()
            if not question_id:
                continue
            path = review_dir / f"{question_id}.json"
            existing = _read_json(path)
            if question_id in top_ids:
                if _valid_review(existing, question_id):
                    reviewed += 1
                    if _strict_review_pass(existing):
                        strict_pass += 1
                    continue
                _write_json(path, _degraded_review(candidate, reviewer_error, reviewer_ok))
                degraded += 1
            elif not _valid_review(existing, question_id):
                _write_json(path, _not_selected_review(candidate))
                not_selected += 1

    summary = {
        "ok": True,
        "reviewer_ok": reviewer_ok,
        "reviewed_or_existing_top_candidates": reviewed,
        "degraded_top_candidates": degraded,
        "not_selected_for_ai_review": not_selected,
        "strict_novelty_pass": strict_pass,
        "top_candidates_per_paper": max(2 * b, b + 2),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "novelty_review_summary.json", summary)
    return summary


def _review_payload(output_dir: Path, n: int, b: int, include_non_top: bool = False) -> dict[str, Any]:
    top_k = max(2 * b, b + 2)
    papers: list[dict[str, Any]] = []
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        candidates = _read_json(paper_dir / "candidate_questions.json")
        if not isinstance(candidates, list):
            candidates = []
        normalized = [item for item in candidates if isinstance(item, dict)]
        ranked = sorted(normalized, key=_candidate_score, reverse=True)
        top = ranked[:top_k]
        selected = normalized if include_non_top else top
        papers.append(
            {
                "paper_id": paper_id,
                "paper_profile": _read_json(paper_dir / "paper_profile.json") or {},
                "theorem_cards": _read_json(paper_dir / "theorem_cards.json") or [],
                "gap_cards": _read_json(paper_dir / "gap_cards.json") or [],
                "top_question_ids": [str(item.get("question_id", "")) for item in top],
                "candidates": [_compact_candidate(item) for item in selected],
            }
        )
    return {"papers": papers}


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "question_id",
        "title",
        "precise_problem_statement",
        "novelty_assessment",
        "novelty_axis",
        "closest_input_result",
        "closest_external_result",
        "killer_known_theorem_attempt",
        "non_cosmetic_difference",
        "why_not_direct_corollary",
        "why_not_standard_theorem",
        "method_delta",
        "fast_sci_route",
        "journal_fit",
        "transfer_pattern_used",
        "source_theorem_or_method",
        "target_model",
        "new_obstruction",
        "minimal_publishable_version",
        "final_score",
        "weighted_score",
    ]
    return {key: candidate.get(key, "") for key in keys if key in candidate}


def _degraded_review(candidate: dict[str, Any], reviewer_error: str, reviewer_ok: bool) -> dict[str, Any]:
    question_id = str(candidate.get("question_id", "")).strip()
    reason = "Codex novelty reviewer did not produce a valid JSON review."
    if reviewer_error:
        reason += f" Error: {reviewer_error}"
    elif reviewer_ok:
        reason += " Reviewer returned successfully but this candidate review file was missing or invalid."
    return {
        "question_id": question_id,
        "verdict": "insufficient_evidence",
        "duplicate_risk": "unknown",
        "recommended_action": "revise",
        "confidence": "low",
        "closest_input_result": str(candidate.get("closest_input_result", "")),
        "closest_external_result": "not established by Codex novelty reviewer",
        "killer_known_theorem_attempt": "not established by Codex novelty reviewer",
        "non_cosmetic_difference": "",
        "why_not_direct_corollary": str(candidate.get("why_not_direct_corollary", "")),
        "why_not_standard_theorem": str(candidate.get("why_not_standard_theorem", "")),
        "novelty_axis": str(candidate.get("novelty_axis", "")),
        "searched_queries": [],
        "search_attempted": False,
        "search_backend_used": "unavailable",
        "search_limitations": "Codex novelty reviewer did not produce a valid searchable review.",
        "reviewer_summary": reason,
        "strict_novelty_pass": False,
        "review_degraded": True,
    }


def _not_selected_review(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": str(candidate.get("question_id", "")).strip(),
        "verdict": "insufficient_evidence",
        "duplicate_risk": "unknown",
        "recommended_action": "revise",
        "confidence": "low",
        "closest_input_result": str(candidate.get("closest_input_result", "")),
        "closest_external_result": "not reviewed because this candidate was below the Codex novelty-review cutoff",
        "killer_known_theorem_attempt": "not reviewed because this candidate was below the Codex novelty-review cutoff",
        "non_cosmetic_difference": "",
        "why_not_direct_corollary": str(candidate.get("why_not_direct_corollary", "")),
        "why_not_standard_theorem": str(candidate.get("why_not_standard_theorem", "")),
        "novelty_axis": str(candidate.get("novelty_axis", "")),
        "searched_queries": [],
        "search_attempted": False,
        "search_backend_used": "not reviewed",
        "search_limitations": "Candidate was below the Codex novelty-review cutoff.",
        "reviewer_summary": "Candidate was not in the top novelty-review pool; it may only be used as low-confidence fallback.",
        "strict_novelty_pass": False,
        "review_degraded": True,
        "not_selected_for_ai_review": True,
    }


def _valid_review(data: Any, question_id: str) -> bool:
    if not isinstance(data, dict):
        return False
    verdict = str(data.get("verdict", "")).strip()
    if verdict not in NOVELTY_VERDICTS:
        return False
    return str(data.get("question_id", "")).strip() == question_id


def _strict_review_pass(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return (
        str(data.get("verdict", "")).strip() == "new_enough"
        and str(data.get("duplicate_risk", "")).strip().lower() == "low"
        and str(data.get("recommended_action", "")).strip().lower() == "keep"
        and str(data.get("confidence", "")).strip().lower() in {"medium", "high"}
        and _specific_review_field(data, "killer_known_theorem_attempt")
        and _specific_review_field(data, "non_cosmetic_difference")
        and _specific_review_field(data, "why_not_direct_corollary")
        and _specific_review_field(data, "why_not_standard_theorem")
    )


def _specific_review_field(review: dict[str, Any], key: str) -> bool:
    value = str(review.get(key, "")).strip().lower()
    if len(value) < 20:
        return False
    vague_fragments = [
        "not established",
        "not reviewed",
        "not selected",
        "not available",
        "insufficient evidence",
        "no evidence",
        "unclear",
        "unknown",
    ]
    return not any(fragment in value for fragment in vague_fragments)


def _candidate_score(candidate: dict[str, Any]) -> float:
    for key in ["weighted_score", "final_score", "score"]:
        value = candidate.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                pass
    return 0.0


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
