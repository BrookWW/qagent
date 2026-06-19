from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re


@dataclass
class CriticReport:
    question_id: str
    theorem_level: str
    explicit_structure: str
    direct_restatement: str
    likely_known: str
    too_broad: str
    too_trivial: str
    transfer_pattern: str
    new_obstruction: str
    qed_gpt_startability: str
    sci_potential: str
    fast_sci_route: str
    small_method_delta: str
    too_ambitious: str
    too_easy_to_publish: str
    survey_evidence_kills_candidate: str
    survey_confidence: str
    survey_killer_theorem: str
    survey_direct_corollary_check: str
    survey_pitfalls: str
    verdict: str
    critic_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def review_candidate(candidate: dict[str, Any], survey_result: dict[str, Any] | None, paper_entry: dict[str, Any], batch_id: str = "batch_001") -> CriticReport:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    title = str(candidate.get("title", ""))
    statement = str(candidate.get("precise_problem_statement", ""))
    survey_class = (survey_result or {}).get("classification", "")
    duplicate_risk = (survey_result or {}).get("duplicate_risk", "")
    novelty_verdict = (survey_result or {}).get("novelty_verdict", "")
    recommended_action = (survey_result or {}).get("recommended_action", "")
    survey_confidence = str((survey_result or {}).get("survey_confidence", "unknown") or "unknown").lower()
    killer_theorem = str((survey_result or {}).get("killer_theorem_attempt", "") or "").strip()
    corollary_check = str((survey_result or {}).get("direct_corollary_check", "") or "").strip()
    pitfalls = (survey_result or {}).get("counterexamples_and_pitfalls", [])
    if not isinstance(pitfalls, list):
        pitfalls = []
    survey_kills = _survey_evidence_kills(survey_result or {})

    theorem_level = "yes" if _has_theorem_shape(statement) else "no"
    explicit_structure = "yes" if _has_explicit_structure(statement) else "partly"
    direct_restatement = "yes" if survey_class == "direct restatement of input paper" else "no"
    likely_known = "yes" if survey_class == "known theorem" or duplicate_risk == "high" or survey_kills else "uncertain"
    too_broad = "yes" if _too_broad(statement) else "no"
    too_trivial = "yes" if _too_trivial(title, statement) else "no"
    transfer_pattern = "yes" if _generation_rationale_fit(candidate) else "no"
    new_obstruction = _new_obstruction(candidate, statement)
    fast_sci = "yes" if _fast_sci_fit(candidate) else "no"
    small_delta = "yes" if _small_method_delta(candidate) else "no"
    too_ambitious = "yes" if _too_ambitious(candidate, statement) else "no"
    too_easy_publish = "yes" if _too_easy_to_publish(candidate, statement) else "no"
    qed_start = "yes" if theorem_level == "yes" and too_broad == "no" and direct_restatement == "no" else "conditional"
    sci = "yes" if transfer_pattern == "yes" and likely_known != "yes" and too_trivial == "no" and fast_sci == "yes" else "conditional"
    verdict = _verdict(
        theorem_level,
        direct_restatement,
        likely_known,
        too_broad,
        too_trivial,
        qed_start,
        sci,
        novelty_verdict,
        fast_sci,
        small_delta,
        too_ambitious,
        too_easy_publish,
        survey_kills,
        recommended_action,
        survey_confidence,
    )
    survey_evidence = _survey_evidence_summary(survey_result or {})
    summary = (
        f"Verdict: {verdict}. The candidate is theorem-level: {theorem_level}; explicit structure: "
        f"{explicit_structure}; generation rationale: {transfer_pattern}; duplicate risk: {duplicate_risk or 'unknown'}; "
        f"novelty verdict: {novelty_verdict or 'unknown'}; survey confidence: {survey_confidence}; "
        f"survey evidence kill: {'yes' if survey_kills else 'no'}; fast SCI route: {fast_sci}; "
        f"small method delta: {small_delta}. {survey_evidence}"
    )
    report = CriticReport(
        question_id,
        theorem_level,
        explicit_structure,
        direct_restatement,
        likely_known,
        too_broad,
        too_trivial,
        transfer_pattern,
        new_obstruction,
        qed_start,
        sci,
        fast_sci,
        small_delta,
        too_ambitious,
        too_easy_publish,
        "yes" if survey_kills else "no",
        survey_confidence,
        killer_theorem[:800] or "not recorded",
        corollary_check[:800] or "not recorded",
        "; ".join(str(item).strip() for item in pitfalls if str(item).strip())[:800] or "not recorded",
        verdict,
        summary,
    )
    write_critic_report(report, paper_entry, batch_id)
    return report


def write_critic_report(report: CriticReport, paper_entry: dict[str, Any], batch_id: str) -> Path:
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    out_dir = Path("outputs") / batch_id / paper_id / "candidate_critic"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report.question_id}.md"
    path.write_text(
        "\n".join(
            [
                f"# Candidate Critic Report: {report.question_id}",
                "",
                f"1. Is this theorem-level? {report.theorem_level}",
                f"2. Are domain, object class, assumptions, and conclusion explicit? {report.explicit_structure}",
                f"3. Is it a direct restatement of the input paper? {report.direct_restatement}",
                f"4. Is it likely already known? {report.likely_known}",
                f"5. Is it too broad? {report.too_broad}",
                f"6. Is it too trivial? {report.too_trivial}",
                f"7. Does it arise from a concrete theorem skeleton, proof pressure point, survey-supported small variation, or justified transfer mechanism? {report.transfer_pattern}",
                f"8. What is the new obstruction? {report.new_obstruction}",
                f"9. Can the configured Codex/QED proving agent quickly start proving it? {report.qed_gpt_startability}",
                f"10. Could it plausibly become a small SCI-level result? {report.sci_potential}",
                f"11. Is the proof route short enough for AI-assisted human work? {report.fast_sci_route}",
                f"12. Is the method delta small and explicit? {report.small_method_delta}",
                f"13. Is it too ambitious for JDE/JMAA/CPAA-level work? {report.too_ambitious}",
                f"14. Is it too easy/trivial to be publishable? {report.too_easy_to_publish}",
                f"15. Does QED-style survey evidence kill this candidate? {report.survey_evidence_kills_candidate}",
                f"16. Survey confidence: {report.survey_confidence}",
                "",
                "## Survey Evidence Used",
                "",
                f"- Killer theorem attempt: {report.survey_killer_theorem}",
                f"- Direct corollary check: {report.survey_direct_corollary_check}",
                f"- Counterexamples/pitfalls: {report.survey_pitfalls}",
                "",
                f"## Verdict\n\n{report.verdict}",
                "",
                f"## Critic summary\n\n{report.critic_summary}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _has_theorem_shape(statement: str) -> bool:
    lower = statement.lower()
    return any(word in lower for word in ["prove", "show", "establish", "derive"]) and any(word in lower for word in ["assume", "let", "if", "under"])


def _has_explicit_structure(statement: str) -> bool:
    lower = statement.lower()
    return any(word in lower for word in ["let", "domain", "manifold", "space", "equation", "energy"]) and any(word in lower for word in ["prove", "then", "conclusion", "estimate"])


def _too_broad(statement: str) -> bool:
    lower = statement.lower()
    return any(phrase in lower for phrase in ["all equations", "general theory", "fully classify", "arbitrary", "all nonlinear"])


def _too_trivial(title: str, statement: str) -> bool:
    lower = f"{title} {statement}".lower()
    return any(phrase in lower for phrase in ["direct corollary", "apply the theorem", "restate", "same theorem"])


def _generation_rationale_fit(candidate: dict[str, Any]) -> bool:
    general_fields = [
        "pressure_point_id",
        "question_strategy_used",
        "input_anchor",
        "one_step_change_from_input",
        "minimal_proof_route",
        "why_generation_survives_direct_corollary_filter",
    ]
    if any(_field_has_content(candidate.get(field)) for field in general_fields):
        return True
    return _transfer_fit(candidate)


def _transfer_fit(candidate: dict[str, Any]) -> bool:
    labels = " ".join(candidate.get("mechanism_labels", [])) if isinstance(candidate.get("mechanism_labels"), list) else ""
    text = f"{labels} {candidate.get('title', '')} {candidate.get('why_natural', '')}".lower()
    return any(word in text for word in ["transfer", "analogy", "generalization", "boundary", "parabolic", "anisotropic", "finite-index", "inhomogeneous"])


def _field_has_content(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_field_has_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_field_has_content(item) for item in value)
    return len(str(value or "").strip()) >= 8


def _new_obstruction(candidate: dict[str, Any], statement: str) -> str:
    text = f"{candidate.get('possible_obstacles', '')} {statement}".strip()
    if text:
        return re.sub(r"\s+", " ", text)[:600]
    return "not clearly identified"


def _fast_sci_fit(candidate: dict[str, Any]) -> bool:
    text = str(candidate.get("fast_sci_route", "") or candidate.get("expected_tools", "")).lower()
    return bool(text.strip()) and not any(phrase in text for phrase in ["major new theory", "multi-year", "too hard"])


def _small_method_delta(candidate: dict[str, Any]) -> bool:
    text = str(candidate.get("method_delta", "") or candidate.get("why_natural", "")).lower()
    return bool(text.strip()) and any(word in text for word in ["small", "adapt", "modify", "perturb", "boundary", "coefficient", "compactness", "estimate"])


def _too_ambitious(candidate: dict[str, Any], statement: str) -> bool:
    lower = f"{candidate.get('fast_sci_route', '')} {statement}".lower()
    return any(phrase in lower for phrase in ["major new theory", "fully classify", "complete classification", "all dimensions", "arbitrary nonlinear"])


def _too_easy_to_publish(candidate: dict[str, Any], statement: str) -> bool:
    lower = f"{candidate.get('method_delta', '')} {statement}".lower()
    return any(phrase in lower for phrase in ["direct corollary", "apply known theorem", "immediate consequence", "notation change"])


def _verdict(
    theorem_level: str,
    direct: str,
    known: str,
    broad: str,
    trivial: str,
    qed: str,
    sci: str,
    novelty: str,
    fast_sci: str,
    small_delta: str,
    ambitious: str,
    easy: str,
    survey_kills: bool,
    recommended_action: str,
    survey_confidence: str,
) -> str:
    if survey_kills:
        return "negative"
    if direct == "yes" or known == "yes" or broad == "yes" or trivial == "yes" or ambitious == "yes" or easy == "yes":
        return "negative"
    if str(recommended_action).strip().lower() == "remove":
        return "negative"
    if novelty and novelty not in {"new enough", "insufficient evidence"}:
        return "negative"
    if str(recommended_action).strip().lower() == "revise" or novelty == "insufficient evidence":
        return "conditionally positive"
    if survey_confidence in {"low", "unknown"}:
        return "conditionally positive"
    if theorem_level == "yes" and qed == "yes" and sci in {"yes", "conditional"} and fast_sci == "yes" and small_delta == "yes":
        return "positive"
    return "conditionally positive"


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


def _survey_evidence_summary(survey_result: dict[str, Any]) -> str:
    theorem_count = len(survey_result.get("directly_applicable_theorems", []) or [])
    killer = str(survey_result.get("killer_theorem_attempt", "") or "").strip()
    corollary = str(survey_result.get("direct_corollary_check", "") or "").strip()
    pieces = [f"QED-style survey evidence: {theorem_count} directly applicable theorem(s) recorded."]
    if killer:
        pieces.append(f"Killer theorem attempt: {killer[:240]}.")
    if corollary:
        pieces.append(f"Direct corollary check: {corollary[:240]}.")
    return " ".join(pieces)


def _paper_id(entry: dict[str, Any]) -> str:
    cvgmt = str(entry.get("cvgmt_id", "")).strip()
    if cvgmt and cvgmt != "not provided":
        return f"cvgmt_{cvgmt}"
    title = str(entry.get("title", "paper"))
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:80] or "paper"
