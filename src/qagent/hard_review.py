from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .critic import review_candidate
from .novelty_review import NOVELTY_VERDICTS
from .survey import survey_candidate


@dataclass
class CandidateHardReviewItem:
    paper_id: str
    question_id: str
    ok: bool
    survey_path: str
    critic_path: str
    duplicate_risk: str
    novelty_verdict: str
    critic_verdict: str
    recommended_action: str
    passed_final_gate: bool
    error_message: str
    final_score: float = 0.0
    validation_quality: str = "ok"
    validation_penalty: float = 0.0
    review_score: float = 0.0
    transfer_pattern_used: str = ""
    transfer_pattern_bonus: float = 0.0
    general_strategy_used: str = ""
    general_strategy_bonus: float = 0.0
    novelty_review_path: str = ""
    novelty_review_verdict: str = ""
    novelty_review_confidence: str = ""
    closest_external_result: str = ""
    killer_known_theorem_attempt: str = ""
    non_cosmetic_difference: str = ""
    why_not_direct_corollary: str = ""
    strict_novelty_pass: bool = False
    novelty_review_penalty: float = 0.0
    novelty_review_bonus: float = 0.0
    validation_warnings: list[dict[str, Any]] | None = None
    hard_review_degraded: bool = False
    fallback_selected: bool = False
    killed_early: bool = False
    survey_confidence: str = "unknown"
    survey_search_backend: str = ""
    survey_killer_theorem_attempt: str = ""
    survey_direct_corollary_check: str = ""
    survey_directly_applicable_theorems: list[dict[str, Any]] | None = None
    survey_counterexamples_and_pitfalls: list[str] | None = None
    survey_evidence_penalty: float = 0.0


@dataclass
class PaperHardReviewItem:
    paper_id: str
    ok: bool
    candidate_count: int
    reviewed_count: int
    error_message: str
    candidates: list[CandidateHardReviewItem]


@dataclass
class HardReviewResult:
    ok: bool
    batch_id: str
    papers_reviewed: int
    candidates_reviewed: int
    candidates_passed: int
    papers: list[PaperHardReviewItem]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_hard_review(
    output_dir: Path,
    n: int,
    b: int | None = None,
    batch_id: str = "batch_001",
    try_online: bool = True,
    review_limit_per_paper: int | None = None,
    use_critic: bool = True,
) -> HardReviewResult:
    papers: list[PaperHardReviewItem] = []
    total_reviewed = 0

    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        paper_result = _review_paper(paper_dir, paper_id, batch_id, try_online, review_limit_per_paper, use_critic)
        if b is not None:
            _fill_from_rejected_by_score(paper_result, b)
        if b is not None and _passed_count(paper_result) < b:
            paper_result.ok = True
            paper_result.error_message = (
                f"Only {_passed_count(paper_result)} candidates were available after fallback; "
                f"{b} were requested. Proceeding with the available allowlist and marking the paper underfilled."
            )
        papers.append(paper_result)
        total_reviewed += paper_result.reviewed_count

    total_passed = sum(_passed_count(paper) for paper in papers)
    return HardReviewResult(
        ok=bool(papers) and all(paper.ok for paper in papers),
        batch_id=batch_id,
        papers_reviewed=len(papers),
        candidates_reviewed=total_reviewed,
        candidates_passed=total_passed,
        papers=papers,
    )


def write_hard_review_result(output_dir: Path, result: HardReviewResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "hard_review.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_passed_candidates(output_dir: Path, result: HardReviewResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    papers = []
    for paper in result.papers:
        papers.append(
            {
                "paper_id": paper.paper_id,
                "passed_question_ids": [
                    candidate.question_id for candidate in paper.candidates if _allowed_for_final(candidate)
                ],
                "passed_candidates": [
                    asdict(candidate) for candidate in paper.candidates if _allowed_for_final(candidate)
                ],
            }
        )
    path = output_dir / "hard_review_passed_candidates.json"
    path.write_text(
        json.dumps(
            {
                "batch_id": result.batch_id,
                "candidates_passed": result.candidates_passed,
                "papers": papers,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def hard_review_summary_markdown(result: HardReviewResult) -> str:
    lines = [
        "# Hard Candidate Review",
        "",
        f"- Batch: {result.batch_id}",
        f"- Papers reviewed: {result.papers_reviewed}",
        f"- Candidates reviewed: {result.candidates_reviewed}",
        f"- Candidates allowed for final selection: {result.candidates_passed}",
        f"- Status: {'passed' if result.ok else 'failed'}",
        "",
    ]
    for paper in result.papers:
        lines.extend(
            [
                f"## {paper.paper_id}",
                "",
                f"- Status: {'passed' if paper.ok else 'failed'}",
                f"- Candidate count: {paper.candidate_count}",
                f"- Reviewed count: {paper.reviewed_count}",
                f"- Allowed for final selection: {_passed_count(paper)}",
            ]
        )
        if paper.error_message:
            lines.append(f"- Error: {paper.error_message}")
        lines.append("")
        for candidate in paper.candidates:
            lines.append(
                f"- `{candidate.question_id}`: survey `{candidate.duplicate_risk}` / "
                f"novelty `{candidate.novelty_verdict}` / "
                f"critic `{candidate.critic_verdict}` / action `{candidate.recommended_action}` / "
                f"strict_passed `{candidate.passed_final_gate}` / fallback_selected `{candidate.fallback_selected}` / "
                f"score `{candidate.final_score}` / validation `{candidate.validation_quality}` / "
                f"penalty `{candidate.validation_penalty}` / transfer `{candidate.transfer_pattern_used or 'none'}` / "
                f"transfer_bonus `{candidate.transfer_pattern_bonus}` / novelty_review `{candidate.novelty_review_verdict or 'none'}` / "
                f"strict_novelty `{candidate.strict_novelty_pass}` / review_score `{candidate.review_score}`"
            )
            if candidate.validation_warnings:
                for warning in candidate.validation_warnings:
                    lines.append(f"  Warning: {warning.get('metric', 'validation_quality')}: {warning.get('message', '')}")
            if candidate.error_message:
                lines.append(f"  Error: {candidate.error_message}")
        lines.append("")
    return "\n".join(lines)


def _review_paper(
    paper_dir: Path,
    paper_id: str,
    batch_id: str,
    try_online: bool,
    review_limit_per_paper: int | None = None,
    use_critic: bool = True,
) -> PaperHardReviewItem:
    candidates_data = _read_json(paper_dir / "candidate_questions.json")
    if not isinstance(candidates_data, list):
        return PaperHardReviewItem(paper_id, False, 0, 0, "candidate_questions.json is missing or not a list.", [])

    paper_entry = _paper_entry_from_profile(paper_dir, paper_id)
    quality_flags = _candidate_quality_flags(paper_dir)
    novelty_reviews = _candidate_novelty_reviews(paper_dir)
    items: list[CandidateHardReviewItem] = []
    candidates_to_review = _top_candidates_for_review(candidates_data, review_limit_per_paper)
    review_ids = {
        str(candidate.get("question_id") or candidate.get("id") or "").strip()
        for candidate in candidates_to_review
        if isinstance(candidate, dict)
    }
    for candidate_data in candidates_data:
        if not isinstance(candidate_data, dict):
            items.append(
                CandidateHardReviewItem(
                    paper_id,
                    "unknown",
                    False,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    False,
                    "Candidate is not a JSON object.",
                )
            )
            continue
        candidate = _normalize_candidate(candidate_data)
        _apply_quality_flags(candidate, quality_flags)
        _apply_novelty_review(candidate, novelty_reviews)
        question_id = str(candidate.get("question_id") or candidate.get("id") or "").strip()
        if review_limit_per_paper is not None and question_id not in review_ids:
            items.append(_not_reviewed_candidate(candidate, paper_entry, batch_id))
            continue
        items.append(_review_candidate(candidate, paper_entry, batch_id, _candidate_survey_try_online(candidate, try_online), use_critic))

    reviewed = sum(1 for item in items if item.ok and item.survey_path)
    return PaperHardReviewItem(
        paper_id=paper_id,
        ok=bool(candidates_data) and reviewed == len(candidates_to_review),
        candidate_count=len(candidates_data),
        reviewed_count=reviewed,
        error_message="",
        candidates=items,
    )


def _review_candidate(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str,
    try_online: bool,
    use_critic: bool = True,
) -> CandidateHardReviewItem:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    paper_id = str(paper_entry.get("paper_id", "paper"))
    try:
        survey = survey_candidate(candidate, paper_entry, batch_id=batch_id, try_online=try_online)
        survey_data = survey.to_dict()
        evidence_penalty = _survey_evidence_penalty(survey_data)
        if _survey_evidence_kills(survey_data):
            critic_path = _write_early_kill_critic_report(candidate, paper_entry, batch_id, survey_data)
            return CandidateHardReviewItem(
                paper_id=paper_id,
                question_id=question_id,
                ok=True,
                survey_path=f"outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md",
                critic_path=critic_path,
                duplicate_risk=survey.duplicate_risk,
                novelty_verdict=survey.novelty_verdict,
                critic_verdict="negative",
                recommended_action=survey.recommended_action,
                passed_final_gate=False,
                error_message="Killed early by candidate survey before full critic: direct corollary / known theorem / remove action / high duplicate risk.",
                final_score=_candidate_score(candidate),
                validation_quality=_validation_quality(candidate),
                validation_penalty=_validation_penalty(candidate),
                review_score=max(0.0, _candidate_review_score(candidate) - evidence_penalty),
                transfer_pattern_used=_transfer_pattern_used(candidate),
                transfer_pattern_bonus=_transfer_pattern_bonus(candidate),
                general_strategy_used=_general_strategy_used(candidate),
                general_strategy_bonus=_general_strategy_bonus(candidate),
                novelty_review_path=_novelty_review_path(candidate),
                novelty_review_verdict=_novelty_review_verdict(candidate),
                novelty_review_confidence=_novelty_review_confidence(candidate),
                closest_external_result=_closest_external_result(candidate),
                killer_known_theorem_attempt=_killer_known_theorem_attempt(candidate),
                non_cosmetic_difference=_non_cosmetic_difference(candidate),
                why_not_direct_corollary=_why_not_direct_corollary(candidate),
                strict_novelty_pass=False,
                novelty_review_penalty=_novelty_review_penalty(candidate),
                novelty_review_bonus=0.0,
                validation_warnings=_validation_warnings(candidate),
                survey_confidence=getattr(survey, "survey_confidence", "unknown"),
                survey_search_backend=getattr(survey, "search_backend", ""),
                survey_killer_theorem_attempt=getattr(survey, "killer_theorem_attempt", ""),
                survey_direct_corollary_check=getattr(survey, "direct_corollary_check", ""),
                survey_directly_applicable_theorems=getattr(survey, "directly_applicable_theorems", []),
                survey_counterexamples_and_pitfalls=getattr(survey, "counterexamples_and_pitfalls", []),
                survey_evidence_penalty=evidence_penalty,
                killed_early=True,
            )
        critic = (
            review_candidate(candidate, survey_data, paper_entry, batch_id=batch_id)
            if use_critic
            else _lightweight_critic(candidate, survey_data, paper_entry, batch_id)
        )
        return CandidateHardReviewItem(
            paper_id=paper_id,
            question_id=question_id,
            ok=True,
            survey_path=f"outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md",
            critic_path=f"outputs/{batch_id}/{paper_id}/candidate_critic/{question_id}.md",
            duplicate_risk=survey.duplicate_risk,
            novelty_verdict=survey.novelty_verdict,
            critic_verdict=critic.verdict,
            recommended_action=survey.recommended_action,
            passed_final_gate=_passes_final_gate(
                survey.duplicate_risk,
                survey.recommended_action,
                survey.novelty_verdict,
                critic.verdict,
                candidate,
                survey_data,
            ),
            error_message="",
            final_score=_candidate_score(candidate),
            validation_quality=_validation_quality(candidate),
            validation_penalty=_validation_penalty(candidate),
            review_score=max(0.0, _candidate_review_score(candidate) - evidence_penalty),
            transfer_pattern_used=_transfer_pattern_used(candidate),
            transfer_pattern_bonus=_transfer_pattern_bonus(candidate),
            general_strategy_used=_general_strategy_used(candidate),
            general_strategy_bonus=_general_strategy_bonus(candidate),
            novelty_review_path=_novelty_review_path(candidate),
            novelty_review_verdict=_novelty_review_verdict(candidate),
            novelty_review_confidence=_novelty_review_confidence(candidate),
            closest_external_result=_closest_external_result(candidate),
            killer_known_theorem_attempt=_killer_known_theorem_attempt(candidate),
            non_cosmetic_difference=_non_cosmetic_difference(candidate),
            why_not_direct_corollary=_why_not_direct_corollary(candidate),
            strict_novelty_pass=_strict_novelty_pass(candidate),
            novelty_review_penalty=_novelty_review_penalty(candidate),
            novelty_review_bonus=_novelty_review_bonus(candidate),
            validation_warnings=_validation_warnings(candidate),
            survey_confidence=getattr(survey, "survey_confidence", "unknown"),
            survey_search_backend=getattr(survey, "search_backend", ""),
            survey_killer_theorem_attempt=getattr(survey, "killer_theorem_attempt", ""),
            survey_direct_corollary_check=getattr(survey, "direct_corollary_check", ""),
            survey_directly_applicable_theorems=getattr(survey, "directly_applicable_theorems", []),
            survey_counterexamples_and_pitfalls=getattr(survey, "counterexamples_and_pitfalls", []),
            survey_evidence_penalty=evidence_penalty,
        )
    except Exception as exc:
        survey_path, critic_path = _write_degraded_review_reports(candidate, paper_entry, batch_id, str(exc))
        degraded_penalty = 35.0
        validation_penalty = _validation_penalty(candidate) + degraded_penalty
        return CandidateHardReviewItem(
            paper_id=paper_id,
            question_id=question_id,
            ok=True,
            survey_path=survey_path,
            critic_path=critic_path,
            duplicate_risk="unknown",
            novelty_verdict="insufficient evidence",
            critic_verdict="conditionally positive",
            recommended_action="revise",
            passed_final_gate=False,
            error_message=f"Hard review degraded because survey/critic failed: {exc}",
            final_score=_candidate_score(candidate),
            validation_quality=_validation_quality(candidate),
            validation_penalty=validation_penalty,
            review_score=max(
                0.0,
                _candidate_score(candidate)
                - validation_penalty
                + _transfer_pattern_bonus(candidate)
                + _general_strategy_bonus(candidate)
                + _novelty_review_bonus(candidate)
                - _novelty_review_penalty(candidate),
            ),
            transfer_pattern_used=_transfer_pattern_used(candidate),
            transfer_pattern_bonus=_transfer_pattern_bonus(candidate),
            general_strategy_used=_general_strategy_used(candidate),
            general_strategy_bonus=_general_strategy_bonus(candidate),
            novelty_review_path=_novelty_review_path(candidate),
            novelty_review_verdict=_novelty_review_verdict(candidate),
            novelty_review_confidence=_novelty_review_confidence(candidate),
            closest_external_result=_closest_external_result(candidate),
            killer_known_theorem_attempt=_killer_known_theorem_attempt(candidate),
            non_cosmetic_difference=_non_cosmetic_difference(candidate),
            why_not_direct_corollary=_why_not_direct_corollary(candidate),
            strict_novelty_pass=_strict_novelty_pass(candidate),
            novelty_review_penalty=_novelty_review_penalty(candidate),
            novelty_review_bonus=_novelty_review_bonus(candidate),
            validation_warnings=_validation_warnings(candidate)
            + [
                {
                    "metric": "hard_review_degraded",
                    "message": f"Survey/critic failed locally: {exc}",
                    "penalty": degraded_penalty,
                }
            ],
            hard_review_degraded=True,
            survey_confidence="unknown",
            survey_search_backend="degraded",
            survey_killer_theorem_attempt="",
            survey_direct_corollary_check="",
            survey_directly_applicable_theorems=[],
            survey_counterexamples_and_pitfalls=[],
            survey_evidence_penalty=degraded_penalty,
        )


def _top_candidates_for_review(candidates: list[Any], limit: int | None) -> list[dict[str, Any]]:
    normalized = [candidate for candidate in candidates if isinstance(candidate, dict)]
    if limit is None or limit <= 0 or len(normalized) <= limit:
        return normalized
    return sorted(normalized, key=_candidate_score, reverse=True)[:limit]


def _not_reviewed_candidate(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str,
) -> CandidateHardReviewItem:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    paper_id = str(paper_entry.get("paper_id", "paper"))
    return CandidateHardReviewItem(
        paper_id=paper_id,
        question_id=question_id,
        ok=True,
        survey_path="",
        critic_path="",
        duplicate_risk="not surveyed",
        novelty_verdict="not reviewed",
        critic_verdict="not reviewed",
        recommended_action="not selected for novelty search",
        passed_final_gate=False,
        error_message="Skipped by fast hard review because this candidate was below the top novelty-search cutoff.",
        final_score=_candidate_score(candidate),
        validation_quality=_validation_quality(candidate),
        validation_penalty=_validation_penalty(candidate),
        review_score=0.0,
        transfer_pattern_used=_transfer_pattern_used(candidate),
        transfer_pattern_bonus=_transfer_pattern_bonus(candidate),
        general_strategy_used=_general_strategy_used(candidate),
        general_strategy_bonus=_general_strategy_bonus(candidate),
        novelty_review_path=_novelty_review_path(candidate),
        novelty_review_verdict=_novelty_review_verdict(candidate),
        novelty_review_confidence=_novelty_review_confidence(candidate),
        closest_external_result=_closest_external_result(candidate),
        killer_known_theorem_attempt=_killer_known_theorem_attempt(candidate),
        non_cosmetic_difference=_non_cosmetic_difference(candidate),
        why_not_direct_corollary=_why_not_direct_corollary(candidate),
        strict_novelty_pass=False,
        novelty_review_penalty=0.0,
        novelty_review_bonus=0.0,
        validation_warnings=_validation_warnings(candidate),
        survey_confidence="not surveyed",
        survey_search_backend="skipped below top cutoff",
        survey_evidence_penalty=0.0,
    )


class _LightweightCriticReport:
    def __init__(self, verdict: str, summary: str) -> None:
        self.verdict = verdict
        self.critic_summary = summary


def _lightweight_critic(
    candidate: dict[str, Any],
    survey_data: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str,
) -> _LightweightCriticReport:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    out_dir = Path("outputs") / batch_id / paper_id / "candidate_critic"
    out_dir.mkdir(parents=True, exist_ok=True)
    duplicate_risk = str(survey_data.get("duplicate_risk", "unknown"))
    novelty_verdict = str(survey_data.get("novelty_verdict", "insufficient evidence"))
    action = str(survey_data.get("recommended_action", "revise"))
    verdict = "conditionally positive" if duplicate_risk.lower() in {"low", "medium"} and action.lower() == "keep" else "negative"
    summary = (
        "Full critic skipped in fast mode. Hard review used candidate self-check fields "
        f"plus novelty-search survey only: duplicate_risk={duplicate_risk}, "
        f"novelty_verdict={novelty_verdict}, recommended_action={action}."
    )
    path = out_dir / f"{question_id}.md"
    path.write_text(
        "\n".join(
            [
                "# Lightweight Candidate Gate",
                "",
                f"Verdict: {verdict}.",
                "",
                summary,
                "",
                "This file is a compatibility trace; direct-corollary/formal checks are expected to happen during candidate generation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return _LightweightCriticReport(verdict, summary)


def _candidate_survey_try_online(candidate: dict[str, Any], try_online: bool) -> bool:
    """Use online survey whenever the user enabled it.

    Earlier versions gated online survey behind strict AI novelty review. That
    created a bad loop: candidates needed survey evidence to pass novelty, but
    did not receive online survey until after passing novelty. The hard-review
    stage should collect duplicate-risk evidence first, then decide whether the
    candidate survives.
    """
    return bool(try_online)


def _passes_final_gate(
    duplicate_risk: str,
    recommended_action: str,
    novelty_verdict: str,
    critic_verdict: str,
    candidate: dict[str, Any],
    survey_result: dict[str, Any] | None = None,
) -> bool:
    if _survey_evidence_kills(survey_result or {}):
        return False
    if _survey_evidence_penalty(survey_result or {}) >= 60.0:
        return False
    base_pass = (
        duplicate_risk.lower() == "low"
        and recommended_action.lower() == "keep"
        and novelty_verdict.lower() == "new enough"
        and critic_verdict.lower() != "negative"
    )
    if not base_pass:
        return False
    if _has_novelty_review(candidate):
        return _strict_novelty_pass(candidate)
    return _candidate_has_self_novelty_evidence(candidate, survey_result or {})


def _passed_count(paper: PaperHardReviewItem) -> int:
    return sum(1 for candidate in paper.candidates if _allowed_for_final(candidate))


def _allowed_for_final(candidate: CandidateHardReviewItem) -> bool:
    return candidate.passed_final_gate or candidate.fallback_selected


def _fill_from_rejected_by_score(paper: PaperHardReviewItem, b: int) -> None:
    missing = b - _passed_count(paper)
    if missing <= 0:
        return
    rejected = [
        candidate
        for candidate in paper.candidates
        if candidate.ok
        and not candidate.passed_final_gate
        and not candidate.fallback_selected
        and _eligible_for_fallback(candidate)
    ]
    rejected.sort(key=lambda candidate: candidate.review_score, reverse=True)
    for candidate in rejected[:missing]:
        candidate.fallback_selected = True


def _eligible_for_fallback(candidate: CandidateHardReviewItem) -> bool:
    """Fallback may fill low-confidence gaps, but must not resurrect killed candidates."""
    if not candidate.ok:
        return False
    if str(candidate.critic_verdict).strip().lower() == "negative" and _candidate_has_hard_kill(candidate):
        return False
    if str(candidate.recommended_action).strip().lower() == "remove":
        return False
    if str(candidate.duplicate_risk).strip().lower() == "high":
        return False
    killed_novelty = {"likely_known", "direct_corollary", "too_close_to_input"}
    if str(candidate.novelty_review_verdict).strip().lower() in killed_novelty:
        return False
    if candidate.novelty_review_penalty >= 60.0:
        return False
    if _candidate_has_hard_kill(candidate):
        return False
    return True


def _candidate_has_hard_kill(candidate: CandidateHardReviewItem) -> bool:
    if str(candidate.recommended_action).strip().lower() == "remove":
        return True
    if str(candidate.duplicate_risk).strip().lower() == "high":
        return True
    if str(candidate.novelty_verdict).strip().lower() in {
        "direct corollary",
        "too close to input theorem",
        "probably already known",
        "likely known",
    }:
        return True
    if str(candidate.novelty_review_verdict).strip().lower() in {"likely_known", "direct_corollary", "too_close_to_input"}:
        return True
    return _directly_applicable_theorem_kills(candidate.survey_directly_applicable_theorems or [])


def _candidate_has_self_novelty_evidence(candidate: dict[str, Any], survey_result: dict[str, Any]) -> bool:
    required_candidate_fields = [
        "closest_input_result",
        "why_not_direct_corollary",
        "why_not_standard_theorem",
        "novelty_axis",
        "new_obstruction",
        "method_delta",
        "fast_sci_route",
    ]
    enough_candidate = all(len(str(candidate.get(field, "") or "").strip()) >= 24 for field in required_candidate_fields)
    comparison = str(survey_result.get("detailed_novelty_comparison", "") or "").strip()
    queries = survey_result.get("search_queries", [])
    enough_survey = len(comparison) >= 40 and isinstance(queries, list) and len(queries) >= 4
    return enough_candidate and enough_survey


def _survey_evidence_penalty(survey_result: dict[str, Any]) -> float:
    if not survey_result:
        return 18.0
    if _survey_evidence_kills(survey_result):
        return 80.0

    penalty = 0.0
    confidence = str(survey_result.get("survey_confidence", "")).strip().lower()
    duplicate_risk = str(survey_result.get("duplicate_risk", "")).strip().lower()
    action = str(survey_result.get("recommended_action", "")).strip().lower()
    novelty = str(survey_result.get("novelty_verdict", "")).strip().lower()
    applicable = survey_result.get("directly_applicable_theorems", [])
    pitfalls = survey_result.get("counterexamples_and_pitfalls", [])

    if confidence in {"low", "unknown", ""}:
        penalty += 24.0
    elif confidence == "medium":
        penalty += 4.0
    if duplicate_risk in {"medium", "unknown"}:
        penalty += 18.0
    if action == "revise":
        penalty += 18.0
    if novelty == "insufficient evidence":
        penalty += 25.0
    elif novelty and novelty != "new enough":
        penalty += 40.0
    if isinstance(applicable, list) and applicable:
        penalty += min(20.0, 5.0 * len(applicable))
    if isinstance(pitfalls, list) and len([item for item in pitfalls if str(item).strip()]) >= 3:
        penalty += 6.0

    return min(round(penalty, 3), 80.0)


def _survey_evidence_kills(survey_result: dict[str, Any]) -> bool:
    duplicate_risk = str(survey_result.get("duplicate_risk", "")).strip().lower()
    recommended_action = str(survey_result.get("recommended_action", "")).strip().lower()
    novelty = str(survey_result.get("novelty_verdict", "")).strip().lower()
    classification = str(survey_result.get("classification", "")).strip().lower()
    if duplicate_risk == "high" or recommended_action == "remove":
        return True
    if novelty in {"direct corollary", "too close to input theorem", "probably already known", "likely known"}:
        return True
    if any(fragment in classification for fragment in ["known theorem", "direct restatement", "module of known theorem"]):
        return True
    return _directly_applicable_theorem_kills(survey_result.get("directly_applicable_theorems", []))


def _directly_applicable_theorem_kills(items: Any) -> bool:
    if not isinstance(items, list):
        return False
    hard_kill_phrases = [
        "directly proves",
        "fully proves",
        "exactly proves",
        "implies the candidate",
        "direct corollary",
        "exact duplicate",
        "same theorem",
        "kills the candidate as stated",
        "kills the proposed theorem",
        "no new analytic mechanism",
    ]
    softening_phrases = [
        "does not literally kill",
        "does not directly",
        "not directly",
        "not a direct",
        "only kills",
        "kills only",
        "does not cover",
        "does not imply",
        "remains different",
        "surviving",
        "novelty can only lie",
    ]
    for item in items:
        if not isinstance(item, dict):
            continue
        killed = str(item.get("candidate_direction_killed", "")).strip().lower()
        if not killed:
            continue
        if any(phrase in killed for phrase in softening_phrases):
            continue
        if any(phrase in killed for phrase in hard_kill_phrases):
            return True
    return False


def _candidate_review_score(candidate: dict[str, Any]) -> float:
    return max(
        0.0,
        _candidate_score(candidate)
        - _validation_penalty(candidate)
        + _transfer_pattern_bonus(candidate)
        + _general_strategy_bonus(candidate)
        + _novelty_review_bonus(candidate)
        - _novelty_review_penalty(candidate),
    )


def _transfer_pattern_used(candidate: dict[str, Any]) -> str:
    return str(candidate.get("transfer_pattern_used", "")).strip()


def _transfer_pattern_bonus(candidate: dict[str, Any]) -> float:
    """Reward concrete transfer-pattern use without making it a hard gate."""
    pattern = _transfer_pattern_used(candidate)
    if not pattern:
        return 0.0

    bonus = 2.0
    if "TP" in pattern.upper():
        bonus += 2.0
    for field in [
        "parent_transfer_pattern",
        "domain_gate",
        "source_theorem_or_method",
        "target_model",
        "new_obstruction",
        "why_old_proof_may_survive",
        "minimal_publishable_version",
        "forbidden_mechanisms_avoided",
    ]:
        if str(candidate.get(field, "")).strip():
            bonus += 1.0

    fit_score = candidate.get("transfer_pattern_fit_score")
    if isinstance(fit_score, (int, float)):
        bonus += max(0.0, min(float(fit_score), 10.0)) * 0.4
    elif isinstance(fit_score, str):
        try:
            bonus += max(0.0, min(float(fit_score.strip()), 10.0)) * 0.4
        except ValueError:
            pass

    return round(min(bonus, 13.0), 3)


def _general_strategy_used(candidate: dict[str, Any]) -> str:
    return str(candidate.get("question_strategy_used", "")).strip()


def _general_strategy_bonus(candidate: dict[str, Any]) -> float:
    strategy = _general_strategy_used(candidate)
    if not strategy:
        return 0.0

    bonus = 2.0
    for field in [
        "why_this_is_good_research_question",
        "one_step_change_from_input",
        "proof_route_shortness",
        "novelty_defense",
    ]:
        value = str(candidate.get(field, "")).strip()
        if len(value) >= 30:
            bonus += 2.0

    fit_score = candidate.get("strategy_fit_score")
    if isinstance(fit_score, (int, float)):
        bonus += max(0.0, min(float(fit_score), 10.0)) * 0.4
    elif isinstance(fit_score, str):
        try:
            bonus += max(0.0, min(float(fit_score.strip()), 10.0)) * 0.4
        except ValueError:
            pass

    return round(min(bonus, 13.0), 3)


def _has_novelty_review(candidate: dict[str, Any]) -> bool:
    return isinstance(candidate.get("novelty_review"), dict)


def _novelty_review(candidate: dict[str, Any]) -> dict[str, Any]:
    review = candidate.get("novelty_review")
    return review if isinstance(review, dict) else {}


def _novelty_review_path(candidate: dict[str, Any]) -> str:
    return str(candidate.get("novelty_review_path", "")).strip()


def _novelty_review_verdict(candidate: dict[str, Any]) -> str:
    return str(_novelty_review(candidate).get("verdict", "")).strip()


def _novelty_review_confidence(candidate: dict[str, Any]) -> str:
    return str(_novelty_review(candidate).get("confidence", "")).strip()


def _closest_external_result(candidate: dict[str, Any]) -> str:
    return str(_novelty_review(candidate).get("closest_external_result", "")).strip()


def _killer_known_theorem_attempt(candidate: dict[str, Any]) -> str:
    return str(_novelty_review(candidate).get("killer_known_theorem_attempt", "")).strip()


def _non_cosmetic_difference(candidate: dict[str, Any]) -> str:
    return str(_novelty_review(candidate).get("non_cosmetic_difference", "")).strip()


def _why_not_direct_corollary(candidate: dict[str, Any]) -> str:
    return str(
        _novelty_review(candidate).get("why_not_direct_corollary")
        or candidate.get("why_not_direct_corollary", "")
    ).strip()


def _strict_novelty_pass(candidate: dict[str, Any]) -> bool:
    review = _novelty_review(candidate)
    if not review:
        return False
    return (
        str(review.get("verdict", "")).strip() == "new_enough"
        and str(review.get("duplicate_risk", "")).strip().lower() == "low"
        and str(review.get("recommended_action", "")).strip().lower() == "keep"
        and str(review.get("confidence", "")).strip().lower() in {"medium", "high"}
        and _specific_review_field(review, "killer_known_theorem_attempt")
        and _specific_review_field(review, "non_cosmetic_difference")
        and _specific_review_field(review, "why_not_direct_corollary")
        and _specific_review_field(review, "why_not_standard_theorem")
    )


def _specific_review_field(review: dict[str, Any], key: str) -> bool:
    value = str(review.get(key, "")).strip().lower()
    if len(value) < 20:
        return False
    vague = {
        "not provided",
        "unknown",
        "none",
        "n/a",
        "not applicable",
        "not established",
        "unclear",
    }
    if value in vague:
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


def _novelty_review_bonus(candidate: dict[str, Any]) -> float:
    if not _has_novelty_review(candidate):
        return 0.0
    return 12.0 if _strict_novelty_pass(candidate) else 0.0


def _novelty_review_penalty(candidate: dict[str, Any]) -> float:
    review = _novelty_review(candidate)
    if not review:
        return 0.0
    verdict = str(review.get("verdict", "")).strip()
    if verdict in {"likely_known", "direct_corollary", "too_close_to_input"}:
        return 60.0
    if verdict == "insufficient_evidence":
        return 22.0
    if str(review.get("duplicate_risk", "")).strip().lower() in {"medium", "high", "unknown"} and not _strict_novelty_pass(candidate):
        return 18.0
    return 0.0


def _write_degraded_review_reports(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str,
    error_message: str,
) -> tuple[str, str]:
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    survey_dir = Path("outputs") / batch_id / paper_id / "candidate_surveys"
    critic_dir = Path("outputs") / batch_id / paper_id / "candidate_critic"
    survey_dir.mkdir(parents=True, exist_ok=True)
    critic_dir.mkdir(parents=True, exist_ok=True)
    survey_path = survey_dir / f"{question_id}.md"
    critic_path = critic_dir / f"{question_id}.md"
    survey_path.write_text(
        "\n".join(
            [
                f"# Candidate Survey: {question_id}",
                "",
                "## Search queries used",
                "",
                "- degraded hard review: survey failed before queries could be trusted",
                "",
                "## Nearby papers found",
                "",
                "- Survey unavailable because hard review degraded this candidate.",
                "",
                "## Classification",
                "",
                "- Candidate looks like: insufficient evidence",
                "- Duplicate risk: unknown",
                "- Recommended action: revise",
                "- Novelty verdict: insufficient evidence",
                "",
                "## Detailed novelty comparison",
                "",
                f"Hard review failed while surveying this candidate: {error_message}",
                "",
                "## Log",
                "",
                "- This degraded report exists so the batch can continue; human review is required before trusting the candidate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    critic_path.write_text(
        "\n".join(
            [
                f"# Candidate Critic Report: {question_id}",
                "",
                "1. Is this theorem-level? unknown",
                "2. Are domain, object class, assumptions, and conclusion explicit? unknown",
                "3. Is it a direct restatement of the input paper? unknown",
                "4. Is it likely already known? insufficient evidence",
                "5. Is it too broad? unknown",
                "6. Is it too trivial? unknown",
                "7. Does it arise from a concrete theorem skeleton, proof pressure point, survey-supported small variation, or justified transfer mechanism? unknown",
                "8. What is the new obstruction? not checked because hard review degraded",
                "9. Can the configured Codex/QED proving agent quickly start proving it? conditional",
                "10. Could it plausibly become a small SCI-level result? conditional",
                "11. Is the proof route short enough for AI-assisted human work? unknown",
                "12. Is the method delta small and explicit? unknown",
                "13. Is it too ambitious for JDE/JMAA/CPAA-level work? unknown",
                "14. Is it too easy/trivial to be publishable? unknown",
                "",
                "## Verdict",
                "",
                "conditionally positive",
                "",
                "## Critic summary",
                "",
                f"Verdict: conditionally positive. Hard review degraded because survey/critic failed: {error_message}. Treat this candidate as low-confidence fallback only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return (
        f"outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md",
        f"outputs/{batch_id}/{paper_id}/candidate_critic/{question_id}.md",
    )


def _write_early_kill_critic_report(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str,
    survey_data: dict[str, Any],
) -> str:
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    critic_dir = Path("outputs") / batch_id / paper_id / "candidate_critic"
    critic_dir.mkdir(parents=True, exist_ok=True)
    path = critic_dir / f"{question_id}.md"
    reason = (
        f"duplicate_risk={survey_data.get('duplicate_risk', 'unknown')}; "
        f"novelty_verdict={survey_data.get('novelty_verdict', 'unknown')}; "
        f"recommended_action={survey_data.get('recommended_action', 'unknown')}"
    )
    path.write_text(
        "\n".join(
            [
                f"# Candidate Critic Report: {question_id}",
                "",
                "## Verdict",
                "",
                "negative",
                "",
                "## Early Kill",
                "",
                "Full critic was skipped because candidate survey already found hard-kill evidence.",
                reason,
                "",
                "## Survey Evidence",
                "",
                f"- Killer theorem attempt: {survey_data.get('killer_theorem_attempt', '') or 'not recorded'}",
                f"- Direct corollary check: {survey_data.get('direct_corollary_check', '') or 'not recorded'}",
                f"- Detailed novelty comparison: {survey_data.get('detailed_novelty_comparison', '') or 'not recorded'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return f"outputs/{batch_id}/{paper_id}/candidate_critic/{question_id}.md"


def _validation_quality(candidate: dict[str, Any]) -> str:
    value = candidate.get("validation_quality")
    return str(value).strip() or "ok"


def _validation_penalty(candidate: dict[str, Any]) -> float:
    value = candidate.get("validation_penalty", 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return 0.0
    return 0.0


def _validation_warnings(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = candidate.get("validation_warnings")
    if isinstance(warnings, list):
        return [item for item in warnings if isinstance(item, dict)]
    return []


def _candidate_score(candidate: dict[str, Any]) -> float:
    for key in ["weighted_score", "final_score", "score"]:
        value = candidate.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                continue
    score_breakdown = candidate.get("score_breakdown")
    if isinstance(score_breakdown, dict):
        value = score_breakdown.get("weighted_score") or score_breakdown.get("final_score")
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _paper_entry_from_profile(paper_dir: Path, paper_id: str) -> dict[str, Any]:
    profile = _read_json(paper_dir / "paper_profile.json")
    if not isinstance(profile, dict):
        profile = {}
    return {
        "paper_id": paper_id,
        "title": profile.get("title") or profile.get("paper_title") or paper_id,
        "authors": profile.get("authors", ""),
        "year": profile.get("year", ""),
        "url": profile.get("source_url", ""),
        "matched_keywords": profile.get("model_class", ""),
        "abstract": profile.get("abstract", ""),
    }


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    if "question_id" not in normalized and "id" in normalized:
        normalized["question_id"] = normalized["id"]
    if "precise_problem_statement" not in normalized:
        normalized["precise_problem_statement"] = (
            normalized.get("problem_statement")
            or normalized.get("problem_statement_tex")
            or normalized.get("question")
            or normalized.get("title")
            or ""
        )
    if "mechanism_labels" not in normalized:
        labels = normalized.get("mechanisms") or normalized.get("mechanism") or []
        normalized["mechanism_labels"] = labels if isinstance(labels, list) else [str(labels)]
    return normalized


def _candidate_quality_flags(paper_dir: Path) -> dict[str, dict[str, Any]]:
    data = _read_json(paper_dir / "candidate_quality_flags.json")
    if not isinstance(data, dict):
        return {}
    flags = data.get("flags")
    if not isinstance(flags, dict):
        return {}
    return {str(key): value for key, value in flags.items() if isinstance(value, dict)}


def _candidate_novelty_reviews(paper_dir: Path) -> dict[str, dict[str, Any]]:
    review_dir = paper_dir / "candidate_novelty_reviews"
    if not review_dir.is_dir():
        return {}
    reviews: dict[str, dict[str, Any]] = {}
    for path in review_dir.glob("*.json"):
        data = _read_json(path)
        if _valid_novelty_review(data, path.stem):
            question_id = str(data.get("question_id") or path.stem).strip()
            reviews[question_id] = data
    return reviews


def _valid_novelty_review(data: Any, fallback_question_id: str) -> bool:
    if not isinstance(data, dict):
        return False
    question_id = str(data.get("question_id") or "").strip()
    if question_id != fallback_question_id:
        return False
    verdict = str(data.get("verdict", "")).strip()
    if verdict not in NOVELTY_VERDICTS:
        return False
    duplicate_risk = str(data.get("duplicate_risk", "")).strip().lower()
    if duplicate_risk not in {"low", "medium", "high", "unknown"}:
        return False
    action = str(data.get("recommended_action", "")).strip().lower()
    if action not in {"keep", "revise", "remove"}:
        return False
    confidence = str(data.get("confidence", "")).strip().lower()
    return confidence in {"high", "medium", "low"}


def _apply_novelty_review(candidate: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> None:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "").strip()
    review = reviews.get(question_id)
    if not review:
        return
    candidate["novelty_review"] = review
    candidate["novelty_review_path"] = f"candidate_novelty_reviews/{question_id}.json"


def _apply_quality_flags(candidate: dict[str, Any], flags: dict[str, dict[str, Any]]) -> None:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "").strip()
    flag = flags.get(question_id)
    if not flag:
        candidate.setdefault("validation_quality", "ok")
        candidate.setdefault("validation_penalty", 0.0)
        candidate.setdefault("validation_warnings", [])
        return
    candidate["validation_quality"] = str(flag.get("validation_quality") or "weak_theorem_form")
    candidate["validation_penalty"] = flag.get("validation_penalty", 0.0)
    warnings = flag.get("quality_warnings")
    candidate["validation_warnings"] = warnings if isinstance(warnings, list) else []


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
