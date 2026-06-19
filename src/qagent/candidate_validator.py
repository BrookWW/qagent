from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .validators import theorem_body_validation_errors


REQUIRED_CANDIDATE_FIELDS = [
    "question_id",
    "title",
    "precise_problem_statement",
    "mechanism_labels",
    "novelty_assessment",
    "method_delta",
    "fast_sci_route",
    "journal_fit",
    "final_score",
]

TRANSFER_PATTERN_FIELDS = [
    "transfer_pattern_used",
    "parent_transfer_pattern",
    "domain_gate",
    "source_theorem_or_method",
    "target_model",
    "new_obstruction",
    "why_old_proof_may_survive",
    "minimal_publishable_version",
    "forbidden_mechanisms_avoided",
]

GENERAL_CORE_FIELDS = [
    "input_anchor",
    "one_step_change_from_input",
    "new_obstruction",
    "direct_corollary_attack",
    "minimal_proof_route",
    "research_level_gate",
    "abstraction_lift",
    "research_direction_gate",
]

GENERAL_RANKING_FIELDS = [
    "pressure_point_id",
    "question_strategy_used",
    "strategy_fit_score",
    "why_this_is_good_research_question",
    "proof_route_shortness",
    "novelty_defense",
    "direct_corollary_precheck",
    "why_generation_survives_direct_corollary_filter",
    "candidate_origin_type",
    "adjacent_model_transfer",
]

INPUT_ANCHOR_FIELDS = [
    "closest_result",
    "exact_assumption_changed",
    "proof_step_where_used",
    "why_this_step_is_fragile",
]

DIRECT_COROLLARY_ATTACK_FIELDS = [
    "attack_from_input_theorem",
    "attack_from_standard_theorem",
    "attack_from_routine_approximation",
    "why_all_fail",
]

DIRECT_COROLLARY_ATTEMPT_FIELDS = [
    "attack_from_input_theorem",
    "attack_from_standard_theorem",
    "attack_from_routine_approximation",
]

MINIMAL_PROOF_ROUTE_FIELDS = [
    "known_modules_reused",
    "one_new_lemma_needed",
    "main_estimate_or_construction",
]

GENERAL_TRANSFER_FIELDS = [
    "target_adjacent_model",
    "shared_method_structure",
    "new_obstruction_after_transfer",
    "why_transfer_is_not_random",
]

METHOD_TRANSFER_CANDIDATE_FIELDS = [
    "source_method_module_id",
    "target_model_from_transfer_map",
    "shared_invariant",
    "structural_match_score",
    "new_failure_term",
    "failure_type",
    "one_new_lemma_needed",
    "why_not_random_transfer",
]

METHOD_TRANSFER_REQUIRED_FOR_TRANSFER = [
    "source_method_module_id",
    "target_model_from_transfer_map",
    "shared_invariant",
    "new_failure_term",
    "failure_type",
    "one_new_lemma_needed",
    "why_not_random_transfer",
]

METHOD_MODULE_REQUIRED_FIELDS = [
    "method_module_id",
    "source_theorem_or_proof_step",
    "method_module",
    "load_bearing_structure",
    "nearby_models",
]

RESEARCH_LEVEL_GATE_FIELDS = [
    "is_independent_research_problem",
    "not_merely_input_lemma",
    "why_publishable_if_solved",
    "what_new_object_or_model_is_added",
    "why_not_just_technical_cleanup",
]

ABSTRACTION_LIFT_FIELDS = [
    "raw_proof_detail_used",
    "is_raw_detail_suppressed",
    "abstract_mechanism",
    "main_research_object",
    "why_mechanism_is_research_level",
    "candidate_not_about_raw_detail",
]

RESEARCH_DIRECTION_GATE_FIELDS = [
    "main_object_shift",
    "not_input_family_variant",
    "interesting_model_or_object",
    "new_obstruction_not_in_input",
    "why_direction_is_not_routine",
]

ADJACENT_MODEL_POOL_REQUIRED_FIELDS = [
    "source_method",
    "adjacent_model_pool",
]

ADJACENT_MODEL_ENTRY_REQUIRED_FIELDS = [
    "target_model",
    "shared_structure",
    "new_obstruction",
    "transfer_plausibility",
]

NEARBY_MODEL_REQUIRED_FIELDS = [
    "target_model",
    "shared_invariant",
    "structural_match_score",
    "new_failure_term",
    "failure_type",
    "one_new_lemma_needed",
    "why_not_random_transfer",
]

NOVELTY_TUPLE_FIELDS = [
    "novelty_axis",
    "closest_input_result",
    "why_not_direct_corollary",
    "why_not_standard_theorem",
]

PAPER_SURVEY_FIELDS = [
    "paper_survey_used",
    "related_work_checked",
    "known_result_to_avoid",
]

TEMPLATE_PHRASES = [
    "under suitable assumptions",
    "natural setting of the paper",
    "natural generalization",
    "appropriate structural conditions",
    "chosen to match the input paper",
    "extend the main theorem to a broader class",
    "develop a theory of",
    "general framework",
    "main regularity mechanism",
    "principal conclusion",
    "paper-specific smooth model",
    "choose assumptions to match",
    "the stated estimate",
    "the indicated narrowed model",
    "generated from metadata",
]

BOILERPLATE_SECTION_PHRASES = [
    "conclusion:",
    "conclusions:",
    "in conclusion",
    "to conclude",
    "summary:",
    "summarizing,",
    "we conclude that",
]

DIRECT_COROLLARY_RISK_PHRASES = [
    "direct corollary",
    "immediate consequence",
    "follows immediately",
    "follows directly",
    "routine bookkeeping",
    "only tracks constants",
    "same proof",
    "standard theorem applies",
    "apply the standard theorem",
    "no new obstruction",
]

PROOF_DETAIL_CATEGORY_PHRASES = [
    "annular region",
    "annulus",
    "annuli",
    "dyadic shell",
    "cutoff",
    "cut-off",
    "covering argument",
    "partition of unity",
    "coordinate chart",
    "flattening map",
    "regularization parameter",
    "mollifier",
    "epsilon bookkeeping",
]

RAW_DETAIL_STOPWORDS = {
    "and",
    "the",
    "with",
    "from",
    "into",
    "over",
    "under",
    "local",
    "global",
    "proof",
    "device",
    "step",
    "construction",
    "argument",
    "estimate",
    "identity",
    "input",
    "theorem",
    "statement",
    "candidate",
    "problem",
    "packing",
    "stationarity",
    "stationary",
    "tangent",
    "tangent-pair",
    "pair",
    "pairs",
    "compactness",
    "quantitative",
    "stratum",
    "strata",
    "measure",
    "measures",
    "energy",
    "method",
    "maps",
    "map",
    "target",
    "source",
}

MIN_STATEMENT_CHARS = 120


@dataclass
class CandidateValidationIssue:
    severity: str
    path: str
    message: str
    question_id: str = ""
    quality_metric: str = ""
    penalty: float = 0.0


@dataclass
class CandidateValidationResult:
    ok: bool
    expected_papers: int
    expected_candidates_per_paper: int
    papers_checked: int
    issues: list[CandidateValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [asdict(issue) for issue in self.issues]
        return data


def trim_excess_candidate_outputs(output_dir: Path, n: int, expected_candidates: int) -> dict[str, Any]:
    """Deterministically trim oversized candidate files before validation.

    Shortage is intentionally not repaired here: it needs a Codex repair call to
    generate real additional candidates. Oversized files are safe to trim by
    output order because the user explicitly wants extra candidates removed from
    the tail rather than blocking the run.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    actions: list[dict[str, Any]] = []
    for index in range(1, n + 1):
        paper_dir = output_dir / f"paper_{index:03d}"
        candidate_path = paper_dir / "candidate_questions.json"
        ranked_path = paper_dir / "ranked_questions.json"
        candidates = _read_json(candidate_path)
        ranked = _read_json(ranked_path)

        if isinstance(candidates, list) and len(candidates) > expected_candidates:
            original_count = len(candidates)
            candidates = candidates[:expected_candidates]
            _write_json(candidate_path, candidates)
            actions.append(
                {
                    "path": candidate_path.as_posix(),
                    "action": "trimmed_tail",
                    "from": original_count,
                    "to": expected_candidates,
                }
            )

        if isinstance(ranked, list):
            candidate_ids = set(_ids_from_list(candidates)) if isinstance(candidates, list) else set()
            original_count = len(ranked)
            if candidate_ids:
                ranked = [item for item in ranked if isinstance(item, dict) and str(item.get("question_id", "")).strip() in candidate_ids]
            if len(ranked) > expected_candidates:
                ranked = ranked[:expected_candidates]
            if len(ranked) != original_count:
                _write_json(ranked_path, ranked)
                actions.append(
                    {
                        "path": ranked_path.as_posix(),
                        "action": "trimmed_or_filtered_tail",
                        "from": original_count,
                        "to": len(ranked),
                    }
                )

    report = {"ok": True, "expected_candidates_per_paper": expected_candidates, "actions": actions}
    (output_dir / "candidate_count_normalization.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def validate_candidate_outputs(
    output_dir: Path,
    n: int,
    expected_candidates: int,
    question_style: str = "specialized",
) -> CandidateValidationResult:
    return validate_candidate_outputs_with_policy(
        output_dir,
        n=n,
        expected_candidates=expected_candidates,
        allow_quality_warnings=False,
        question_style=question_style,
    )


def validate_candidate_outputs_with_policy(
    output_dir: Path,
    n: int,
    expected_candidates: int,
    allow_quality_warnings: bool = False,
    question_style: str = "specialized",
) -> CandidateValidationResult:
    issues: list[CandidateValidationIssue] = []
    papers_checked = 0
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        papers_checked += 1
        _validate_paper_candidates(paper_dir, expected_candidates, issues, allow_quality_warnings, question_style)

    ok = not any(issue.severity == "error" for issue in issues)
    return CandidateValidationResult(ok, n, expected_candidates, papers_checked, issues)


def write_candidate_validation_result(output_dir: Path, result: CandidateValidationResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "candidate_validation.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def candidate_validation_markdown(result: CandidateValidationResult) -> str:
    lines = [
        "# Candidate Validation",
        "",
        f"- Status: {'passed' if result.ok else 'failed'}",
        f"- Expected papers: {result.expected_papers}",
        f"- Expected candidates per paper: {result.expected_candidates_per_paper}",
        f"- Papers checked: {result.papers_checked}",
        "",
    ]
    if not result.issues:
        lines.append("- No issues found.")
    else:
        for issue in result.issues:
            lines.append(f"- `{issue.severity}` `{issue.path}`: {issue.message}")
    lines.append("")
    return "\n".join(lines)


def write_candidate_validation_markdown(output_dir: Path, result: CandidateValidationResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "candidate_validation.md"
    path.write_text(candidate_validation_markdown(result), encoding="utf-8")
    return path


def write_candidate_quality_flags(output_dir: Path, n: int, result: CandidateValidationResult) -> Path:
    flags_by_paper: dict[str, dict[str, dict[str, Any]]] = {}
    for issue in result.issues:
        if not issue.quality_metric or not issue.question_id:
            continue
        paper_id = _paper_id_from_issue_path(issue.path)
        if not paper_id:
            continue
        paper_flags = flags_by_paper.setdefault(paper_id, {})
        item = paper_flags.setdefault(
            issue.question_id,
            {
                "question_id": issue.question_id,
                "validation_quality": "ok",
                "validation_penalty": 0.0,
                "quality_warnings": [],
            },
        )
        item["validation_quality"] = _combine_validation_quality(item["validation_quality"], _quality_label(issue.quality_metric))
        item["validation_penalty"] = round(float(item["validation_penalty"]) + issue.penalty, 3)
        item["quality_warnings"].append(
            {
                "metric": issue.quality_metric,
                "message": issue.message,
                "penalty": issue.penalty,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)
        flags = flags_by_paper.get(paper_id, {})
        (paper_dir / "candidate_quality_flags.json").write_text(
            json.dumps(
                {
                    "paper_id": paper_id,
                    "flags": flags,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    path = output_dir / "candidate_quality_flags_summary.json"
    path.write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": f"paper_{index:03d}",
                        "flagged_candidates": list(flags_by_paper.get(f"paper_{index:03d}", {}).values()),
                    }
                    for index in range(1, n + 1)
                ]
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_candidate_repair_prompt(
    output_dir: Path,
    batch_id: str,
    result: CandidateValidationResult,
    question_style: str = "specialized",
) -> str:
    errors = [issue for issue in result.issues if issue.severity == "error"]
    error_lines = "\n".join(f"- `{issue.path}`: {issue.message}" for issue in errors) or "- No error issues."
    style = _normalize_question_style(question_style)
    strategy_fields = (
        """General research strategy fields are not hard-fail fields, but they must be repaired whenever possible:
- question_strategy_used
- strategy_fit_score
- why_this_is_good_research_question
- one_step_change_from_input
- proof_route_shortness
- novelty_defense
- abstraction_lift"""
        if style == "general"
        else """Transfer-pattern fields are not hard-fail fields, but they must be repaired whenever possible:
- transfer_pattern_used
- parent_transfer_pattern
- domain_gate
- source_theorem_or_method
- target_model
- new_obstruction
- why_old_proof_may_survive
- minimal_publishable_version
- forbidden_mechanisms_avoided
- transfer_pattern_fit_score"""
    )
    strategy_rule = (
        "13. question_strategy_used should cite a general strategy from examples/general_research_question_principles.md. "
        "It should also include one_step_change_from_input, proof_route_shortness, novelty_defense, and a numeric strategy_fit_score. "
        "Do not force a TP## transfer pattern in general style."
        if style == "general"
        else "13. transfer_pattern_used should cite one item from examples/transfer_patterns_active.md only when a genuine pattern fits. "
        "It should also include parent_transfer_pattern, domain_gate, source theorem/method, target model, new obstruction, "
        "old proof survival reason, minimal publishable version, and forbidden_mechanisms_avoided. Do not invent a fake "
        "transfer match merely to satisfy a template."
    )
    return f"""Please repair the QAgent candidate-generation outputs for batch `{batch_id}`.

Scope:
- Work only under `outputs/{batch_id}`.
- Repair only candidate-stage artifacts:
  - `outputs/{batch_id}/paper_###/candidate_questions.json`
  - `outputs/{batch_id}/paper_###/ranked_questions.json`
  - `outputs/{batch_id}/paper_###/result.json`, if needed.
- Do not create or modify any `selected/` folders.
- Do not run final selection.
- Do not modify hard_review, hard_review_passed_candidates, quality_audit, backend_info, or final selected files.
- Preserve evidence files: paper_profile.json, theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, paper_reader_report.md.

Candidate validation errors to repair:
{error_lines}

Required schema for every candidate:
- question_id
- title
- precise_problem_statement
- mechanism_labels
- novelty_assessment
- method_delta
- fast_sci_route
- journal_fit
- final_score

{strategy_fields}

Novelty tuple fields are also warning-only, but they are important for Codex novelty review:
- novelty_axis
- closest_input_result
- why_not_direct_corollary
- why_not_standard_theorem

Paper-level survey fields are warning-only, but they directly affect ranking and hard review:
- paper_survey_used
- related_work_checked
- known_result_to_avoid

Hard requirements:
1. Each paper should have exactly {result.expected_candidates_per_paper} candidates, but do not invent weak
   high-quality-looking candidates merely to satisfy the count. If a paper has too few candidates, add only
   honest theorem-level candidates that pass the gates below. If a paper has too many candidates, preserve the first
   {result.expected_candidates_per_paper} and remove only the tail extras. The app will run at most three candidate
   repair attempts; after that, an unresolved shortage should remain visible rather than being hidden by fake candidates.
2. question_id values must be unique within each paper.
3. ranked_questions.json and candidate_questions.json must contain the same question_id set.
4. precise_problem_statement must be theorem-like, concrete, and at least {MIN_STATEMENT_CHARS} characters.
   It must pass the same theorem-body audit used for final problem statements:
   explicit domain/setting, unknown object class, equation/energy/model, assumptions, and conclusion.
   It must be one paragraph of theorem-style mathematics only. It must not use section labels,
   explanatory prose, conclusion labels, markdown headings, or report-style language.
5. precise_problem_statement must not contain template phrases such as:
   - under suitable assumptions
   - natural setting of the paper
   - main regularity mechanism
   - principal conclusion
   - paper-specific smooth model
   - choose assumptions to match
   - the stated estimate
   - generated from metadata
6. precise_problem_statement must not contain prose section labels or conclusion filler such as:
   - Conclusion:
   - In conclusion
   - Summary:
   These are hard errors even during automatic repair; replace the candidate with a clean theorem-level statement.
7. final_score must be numeric.
8. mechanism_labels must be a non-empty list.
9. novelty_assessment must explain why this is not already the input theorem or a likely known theorem.
10. method_delta must state that the proof uses nearby methods with a small but real change, not a major new theory.
11. fast_sci_route must give a short proof/development route suitable for AI-assisted human work.
12. journal_fit must name a plausible JDE/JMAA/CPAA-level fit or say why the result is too weak/too strong.
{strategy_rule}
14. novelty_axis, closest_input_result, why_not_direct_corollary, and why_not_standard_theorem should be concrete
    enough for an adversarial novelty reviewer to decide whether the candidate is already known.
15. paper_survey_used, related_work_checked, and known_result_to_avoid should name the pre-generation
    survey evidence used to avoid already-known or too-close questions.
16. In general style, every candidate must include abstraction_lift. Raw proof details may be used only
    as evidence for a broader mechanism; the title, novelty axis, and theorem statement must target the
    main equation, variational object, flow, solution class, geometric object, operator, or adjacent model.
    Do not repair a failed candidate by turning a local proof device into the research object.
17. In general style, every candidate must include research_direction_gate. It must name the main
    object/model/flow/operator/solution-class shift, certify not_input_family_variant=true, name a
    new obstruction absent from the input paper, and explain why the direction is not routine.

When finished, summarize only the candidate files changed and why."""


def write_candidate_repair_prompt(
    output_dir: Path,
    batch_id: str,
    result: CandidateValidationResult,
    question_style: str = "specialized",
) -> Path | None:
    if result.ok:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "candidate_repair_prompt.md"
    path.write_text(build_candidate_repair_prompt(output_dir, batch_id, result, question_style), encoding="utf-8")
    return path


def _validate_paper_candidates(
    paper_dir: Path,
    expected_candidates: int,
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
    question_style: str,
) -> None:
    candidate_path = paper_dir / "candidate_questions.json"
    ranked_path = paper_dir / "ranked_questions.json"
    candidates = _read_json(candidate_path)
    ranked = _read_json(ranked_path)
    theorem_anchor_labels = _card_anchor_labels(paper_dir / "theorem_cards.json")
    adjacent_model_pool = _adjacent_model_pool_index(paper_dir / "adjacent_model_pool.json", issues, allow_quality_warnings, question_style)
    method_transfer_index = _method_transfer_index(paper_dir / "method_transfer_map.json", issues, allow_quality_warnings)

    if not isinstance(candidates, list):
        issues.append(CandidateValidationIssue("error", candidate_path.as_posix(), "candidate_questions.json is missing or not a list."))
        return
    if not isinstance(ranked, list):
        issues.append(CandidateValidationIssue("error", ranked_path.as_posix(), "ranked_questions.json is missing or not a list."))
        return

    if len(candidates) != expected_candidates:
        issues.append(
            CandidateValidationIssue(
                "error",
                candidate_path.as_posix(),
                f"Expected {expected_candidates} candidates, found {len(candidates)}.",
            )
        )
    if len(ranked) != expected_candidates:
        issues.append(
            CandidateValidationIssue(
                "error",
                ranked_path.as_posix(),
                f"Expected {expected_candidates} ranked candidates, found {len(ranked)}.",
            )
        )

    pressure_point_ids = _pressure_point_ids(paper_dir / "result.json")
    candidate_ids = _validate_candidate_list(
        candidate_path,
        candidates,
        issues,
        allow_quality_warnings,
        question_style,
        pressure_point_ids,
        theorem_anchor_labels,
        method_transfer_index,
        adjacent_model_pool,
    )
    ranked_ids = _ids_from_list(ranked)
    if len(ranked_ids) != len(set(ranked_ids)):
        issues.append(CandidateValidationIssue("error", ranked_path.as_posix(), "ranked_questions.json has duplicate question_id values."))
    if set(candidate_ids) != set(ranked_ids):
        issues.append(
            CandidateValidationIssue(
                "error",
                ranked_path.as_posix(),
                "ranked_questions.json question IDs do not match candidate_questions.json.",
            )
        )


def _validate_candidate_list(
    path: Path,
    candidates: list[Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
    question_style: str,
    pressure_point_ids: set[str],
    theorem_anchor_labels: set[str],
    method_transfer_index: dict[str, Any],
    adjacent_model_pool: dict[str, Any],
) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            issues.append(CandidateValidationIssue("error", path.as_posix(), f"Candidate {index} is not a JSON object."))
            continue

        question_id = str(candidate.get("question_id", "")).strip()
        if question_id:
            ids.append(question_id)
            if question_id in seen:
                issues.append(CandidateValidationIssue("error", path.as_posix(), f"Duplicate question_id: {question_id}."))
            seen.add(question_id)

        for field in REQUIRED_CANDIDATE_FIELDS:
            if not _field_present(candidate, field):
                label = question_id or f"candidate {index}"
                issues.append(CandidateValidationIssue("error", path.as_posix(), f"{label} is missing required field: {field}."))

        _validate_statement(path, question_id or f"candidate {index}", candidate, issues, allow_quality_warnings)
        _validate_mechanism_labels(path, question_id or f"candidate {index}", candidate, issues)
        _validate_score(path, question_id or f"candidate {index}", candidate, issues)
        if _normalize_question_style(question_style) == "general":
            _validate_general_strategy(path, question_id or f"candidate {index}", candidate, issues, allow_quality_warnings)
            _validate_pressure_point_reference(
                path,
                question_id or f"candidate {index}",
                candidate,
                pressure_point_ids,
                issues,
                allow_quality_warnings,
            )
            _validate_card_anchor_reference(
                path,
                question_id or f"candidate {index}",
                candidate,
                theorem_anchor_labels,
                issues,
                allow_quality_warnings,
            )
            _validate_method_transfer_reference(
                path,
                question_id or f"candidate {index}",
                candidate,
                method_transfer_index,
                adjacent_model_pool,
                issues,
                allow_quality_warnings,
            )
        else:
            _validate_transfer_pattern(path, question_id or f"candidate {index}", candidate, issues)
        _validate_novelty_tuple(path, question_id or f"candidate {index}", candidate, issues)
        _validate_paper_survey_use(path, question_id or f"candidate {index}", candidate, issues)

    if _normalize_question_style(question_style) == "general":
        _validate_general_candidate_mix(path, candidates, issues, allow_quality_warnings)

    return ids


def _pressure_point_ids(result_path: Path) -> set[str]:
    result = _read_json(result_path)
    if not isinstance(result, dict):
        return set()
    points = result.get("pressure_points")
    if not isinstance(points, list):
        return set()
    ids: set[str] = set()
    for point in points:
        if isinstance(point, dict):
            value = str(point.get("pressure_point_id", "")).strip()
            if value:
                ids.add(value)
    return ids


def _method_transfer_index(
    path: Path,
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> dict[str, Any]:
    data = _read_json(path)
    if data is None:
        return {"exists": False, "module_ids": set(), "targets_by_module": {}, "path": path}
    if not isinstance(data, dict):
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                "method_transfer_map.json is present but is not a JSON object.",
                quality_metric="weak_method_transfer_map",
                penalty=24.0,
            )
        )
        return {"exists": True, "module_ids": set(), "targets_by_module": {}, "path": path}
    modules = data.get("method_modules")
    if not isinstance(modules, list) or not modules:
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                "method_transfer_map.json must contain a non-empty method_modules list.",
                quality_metric="weak_method_transfer_map",
                penalty=24.0,
            )
        )
        return {"exists": True, "module_ids": set(), "targets_by_module": {}, "path": path}

    module_ids: set[str] = set()
    targets_by_module: dict[str, set[str]] = {}
    for index, module in enumerate(modules, 1):
        if not isinstance(module, dict):
            issues.append(
                CandidateValidationIssue(
                    "warning",
                    path.as_posix(),
                    f"method_transfer_map.json method_modules[{index}] is not an object.",
                    quality_metric="weak_method_transfer_map",
                    penalty=12.0,
                )
            )
            continue
        module_id = str(module.get("method_module_id", "")).strip()
        if module_id:
            module_ids.add(module_id)
        missing = [field for field in METHOD_MODULE_REQUIRED_FIELDS if not _field_present(module, field)]
        if missing:
            issues.append(
                CandidateValidationIssue(
                    "warning",
                    path.as_posix(),
                    f"method_transfer_map.json module {module_id or index} has missing fields: {missing}.",
                    quality_metric="weak_method_transfer_map",
                    penalty=10.0 + 3.0 * len(missing),
                )
            )
        nearby = module.get("nearby_models")
        targets: set[str] = set()
        if isinstance(nearby, list):
            for nearby_index, item in enumerate(nearby, 1):
                if not isinstance(item, dict):
                    continue
                target = str(item.get("target_model", "")).strip()
                if target:
                    targets.add(_normalize_model_text(target))
                missing_nearby = [field for field in NEARBY_MODEL_REQUIRED_FIELDS if not _field_present(item, field)]
                if missing_nearby:
                    issues.append(
                        CandidateValidationIssue(
                            "warning",
                            path.as_posix(),
                            f"method_transfer_map.json module {module_id or index} nearby_models[{nearby_index}] has missing fields: {missing_nearby}.",
                            quality_metric="weak_method_transfer_map",
                            penalty=8.0 + 2.0 * len(missing_nearby),
                        )
                    )
        if module_id:
            targets_by_module[module_id] = targets
    return {"exists": True, "module_ids": module_ids, "targets_by_module": targets_by_module, "path": path}


def _adjacent_model_pool_index(
    path: Path,
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
    question_style: str,
) -> dict[str, Any]:
    if _normalize_question_style(question_style) != "general":
        return {"exists": False, "targets": set(), "path": path}
    data = _read_json(path)
    if data is None:
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                "General style must write adjacent_model_pool.json before method_transfer_map.json.",
                quality_metric="weak_adjacent_model_pool",
                penalty=30.0,
            )
        )
        return {"exists": False, "targets": set(), "path": path}
    if not isinstance(data, dict):
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                "adjacent_model_pool.json is present but is not a JSON object.",
                quality_metric="weak_adjacent_model_pool",
                penalty=24.0,
            )
        )
        return {"exists": True, "targets": set(), "path": path}
    missing = [field for field in ADJACENT_MODEL_POOL_REQUIRED_FIELDS if not _field_present(data, field)]
    pool = data.get("adjacent_model_pool")
    if missing or not isinstance(pool, list) or not pool:
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"adjacent_model_pool.json must contain source_method and a non-empty adjacent_model_pool list; missing={missing}.",
                quality_metric="weak_adjacent_model_pool",
                penalty=28.0,
            )
        )
        return {"exists": True, "targets": set(), "path": path}
    targets: set[str] = set()
    for index, item in enumerate(pool, 1):
        if not isinstance(item, dict):
            continue
        target = str(item.get("target_model", "")).strip()
        if target:
            targets.add(_normalize_model_text(target))
        missing_entry = [field for field in ADJACENT_MODEL_ENTRY_REQUIRED_FIELDS if not _field_present(item, field)]
        if missing_entry:
            issues.append(
                CandidateValidationIssue(
                    "warning" if allow_quality_warnings else "error",
                    path.as_posix(),
                    f"adjacent_model_pool[{index}] has missing fields: {missing_entry}.",
                    quality_metric="weak_adjacent_model_pool",
                    penalty=12.0 + 3.0 * len(missing_entry),
                )
            )
    return {"exists": True, "targets": targets, "path": path}


def _card_anchor_labels(path: Path) -> set[str]:
    cards = _read_json(path)
    if not isinstance(cards, list):
        return set()
    labels: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        for key in ["theorem_label", "label", "id", "name"]:
            value = str(card.get(key, "")).strip()
            if value:
                labels.add(_normalize_anchor_text(value))
                labels.add(_normalize_anchor_text(value.rstrip(".")))
    return {label for label in labels if len(label) >= 3}


def _validate_card_anchor_reference(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    theorem_anchor_labels: set[str],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    anchor_texts = _candidate_anchor_texts(candidate)
    if not anchor_texts:
        return
    if not theorem_anchor_labels:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} cites input theorem/proof anchors, but theorem_cards.json has no verifiable theorem labels.",
                question_id=label,
                quality_metric="weak_input_anchor",
                penalty=8.0,
            )
        )
        return
    haystack = _normalize_anchor_text(" ".join(anchor_texts))
    if any(anchor and anchor in haystack for anchor in theorem_anchor_labels):
        return
    severity = "warning" if allow_quality_warnings else "error"
    examples = ", ".join(sorted(theorem_anchor_labels)[:8])
    issues.append(
        CandidateValidationIssue(
            severity,
            path.as_posix(),
            f"{label} input theorem anchor does not cite a theorem label from theorem_cards.json; expected one of: {examples}.",
            question_id=label,
            quality_metric="weak_input_anchor",
            penalty=26.0,
        )
    )


def _candidate_anchor_texts(candidate: dict[str, Any]) -> list[str]:
    texts = [
        str(candidate.get("closest_input_result", "") or ""),
        str(candidate.get("why_not_direct_corollary", "") or ""),
    ]
    based = candidate.get("based_on_theorem_cards")
    if isinstance(based, list):
        texts.extend(str(item) for item in based)
    elif based is not None:
        texts.append(str(based))
    input_anchor = candidate.get("input_anchor")
    if isinstance(input_anchor, dict):
        texts.append(str(input_anchor.get("closest_result", "") or ""))
    attack = candidate.get("direct_corollary_attack")
    if isinstance(attack, dict):
        texts.append(str(attack.get("attack_from_input_theorem", "") or ""))
    return [text for text in texts if text.strip()]


def _normalize_anchor_text(value: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", value.lower()).strip()


def _validate_pressure_point_reference(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    pressure_point_ids: set[str],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    pressure_point_id = str(candidate.get("pressure_point_id", "")).strip()
    if not pressure_point_id:
        return
    if not pressure_point_ids:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} cites pressure_point_id={pressure_point_id!r}, but result.json has no pressure_points list to verify against.",
                question_id=label,
                quality_metric="weak_general_strategy",
                penalty=8.0,
            )
        )
        return
    if pressure_point_id not in pressure_point_ids:
        referenced = _known_ids_in_text(pressure_point_id, pressure_point_ids)
        if referenced:
            issues.append(
                CandidateValidationIssue(
                    "warning",
                    path.as_posix(),
                    f"{label} cites multiple/non-canonical pressure_point_id={pressure_point_id!r}; recognized {referenced}. Use one exact id in future runs.",
                    question_id=label,
                    quality_metric="weak_general_strategy",
                    penalty=8.0,
                )
            )
            return
        severity = "warning" if allow_quality_warnings else "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} cites unknown pressure_point_id={pressure_point_id!r}; expected one of {sorted(pressure_point_ids)} from result.json.",
                question_id=label,
                quality_metric="weak_general_strategy",
                penalty=22.0,
            )
        )


def _known_ids_in_text(value: str, known_ids: set[str]) -> list[str]:
    text = str(value or "")
    return sorted(known_id for known_id in known_ids if known_id and known_id in text)


def _validate_statement(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    statement = str(candidate.get("precise_problem_statement", "")).strip()
    severity = "warning" if allow_quality_warnings else "error"
    if statement and len(statement) < MIN_STATEMENT_CHARS:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} precise_problem_statement is too short ({len(statement)} chars).",
                question_id=label,
                quality_metric="statement_too_short",
                penalty=18.0,
            )
        )
    lower = re.sub(r"\s+", " ", statement.lower())
    matched = [phrase for phrase in TEMPLATE_PHRASES if phrase in lower]
    if matched:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} precise_problem_statement contains template/vague phrase(s): {matched}.",
                question_id=label,
                quality_metric="template_or_vague_statement",
                penalty=25.0,
            )
        )
    boilerplate = [phrase for phrase in BOILERPLATE_SECTION_PHRASES if phrase in lower]
    if boilerplate:
        issues.append(
            CandidateValidationIssue(
                "error",
                path.as_posix(),
                f"{label} precise_problem_statement contains conclusion/summary boilerplate phrase(s): {boilerplate}.",
                question_id=label,
                quality_metric="conclusion_boilerplate_statement",
                penalty=50.0,
            )
        )
    theorem_errors = theorem_body_validation_errors(statement)
    if theorem_errors:
        theorem_severity = severity
        if set(theorem_errors) <= {"no explicit domain or geometric setting"}:
            theorem_severity = "warning"
        issues.append(
            CandidateValidationIssue(
                theorem_severity,
                path.as_posix(),
                f"{label} precise_problem_statement failed theorem-form audit: {theorem_errors}.",
                question_id=label,
                quality_metric="weak_theorem_form",
                penalty=min(45.0, 12.0 * len(theorem_errors)),
            )
        )


def _validate_mechanism_labels(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
) -> None:
    labels = candidate.get("mechanism_labels")
    if labels is not None and not (isinstance(labels, list) and all(str(item).strip() for item in labels)):
        issues.append(CandidateValidationIssue("error", path.as_posix(), f"{label} mechanism_labels must be a non-empty list of labels."))


def _validate_score(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
) -> None:
    score = candidate.get("final_score")
    if score is None:
        return
    if not isinstance(score, (int, float)):
        issues.append(CandidateValidationIssue("error", path.as_posix(), f"{label} final_score must be numeric."))


def _validate_transfer_pattern(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
) -> None:
    missing = [field for field in TRANSFER_PATTERN_FIELDS if not _field_present(candidate, field)]
    if missing:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has weak/missing transfer pattern fields: {missing}.",
                question_id=label,
                quality_metric="weak_transfer_pattern",
                penalty=12.0 + min(18.0, 3.0 * len(missing)),
            )
        )

    pattern = str(candidate.get("transfer_pattern_used", "")).strip()
    if pattern and not re.search(r"\bTP\d{2}\b", pattern):
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} transfer_pattern_used should cite a TP## pattern id from examples/transfer_patterns_active.md.",
                question_id=label,
                quality_metric="unclear_transfer_pattern_id",
                penalty=8.0,
            )
        )

    fit_score = candidate.get("transfer_pattern_fit_score")
    if fit_score is not None and not isinstance(fit_score, (int, float)):
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} transfer_pattern_fit_score should be numeric 0-10.",
                question_id=label,
                quality_metric="invalid_transfer_pattern_fit_score",
                penalty=6.0,
            )
        )

def _validate_general_strategy(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool = True,
) -> None:
    missing = [field for field in GENERAL_CORE_FIELDS if not _field_present(candidate, field)]
    if missing:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has weak/missing core generation evidence fields: {missing}.",
                question_id=label,
                quality_metric="weak_general_strategy",
                penalty=16.0 + min(24.0, 5.0 * len(missing)),
            )
        )

    missing_ranking = [field for field in GENERAL_RANKING_FIELDS if not _field_present(candidate, field)]
    if missing_ranking:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has missing ranking metadata fields to fill after core candidate generation: {missing_ranking}.",
                question_id=label,
                quality_metric="weak_general_ranking_metadata",
                penalty=4.0 + min(8.0, 1.0 * len(missing_ranking)),
            )
        )

    strategy = str(candidate.get("question_strategy_used", "")).strip()
    if strategy and len(strategy) < 8:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} question_strategy_used is too vague.",
                question_id=label,
                quality_metric="weak_general_strategy",
                penalty=6.0,
            )
        )

    fit_score = candidate.get("strategy_fit_score")
    if fit_score is not None and not isinstance(fit_score, (int, float)):
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} strategy_fit_score should be numeric 0-10.",
                question_id=label,
                quality_metric="invalid_general_strategy_fit_score",
                penalty=6.0,
            )
        )

    _validate_structured_field(
        path,
        label,
        candidate,
        "input_anchor",
        INPUT_ANCHOR_FIELDS,
        "weak_input_anchor",
        24.0,
        issues,
    )
    _validate_direct_corollary_attack_attempt(path, label, candidate, issues, allow_quality_warnings)
    _validate_structured_field(
        path,
        label,
        candidate,
        "direct_corollary_attack",
        DIRECT_COROLLARY_ATTACK_FIELDS,
        "weak_direct_corollary_attack",
        24.0,
        issues,
    )
    _validate_direct_corollary_attack_hard_completeness(path, label, candidate, issues, allow_quality_warnings)
    _validate_structured_field(
        path,
        label,
        candidate,
        "minimal_proof_route",
        MINIMAL_PROOF_ROUTE_FIELDS,
        "weak_minimal_proof_route",
        18.0,
        issues,
    )
    _validate_structured_field(
        path,
        label,
        candidate,
        "research_level_gate",
        RESEARCH_LEVEL_GATE_FIELDS,
        "weak_research_level_gate",
        26.0,
        issues,
    )
    _validate_research_level_gate(path, label, candidate, issues, allow_quality_warnings)
    _validate_structured_field(
        path,
        label,
        candidate,
        "abstraction_lift",
        ABSTRACTION_LIFT_FIELDS,
        "weak_abstraction_lift",
        28.0,
        issues,
    )
    _validate_abstraction_lift(path, label, candidate, issues, allow_quality_warnings)
    _validate_structured_field(
        path,
        label,
        candidate,
        "research_direction_gate",
        RESEARCH_DIRECTION_GATE_FIELDS,
        "weak_research_direction_gate",
        32.0,
        issues,
    )
    _validate_research_direction_gate(path, label, candidate, issues, allow_quality_warnings)

    precheck_text = " ".join(
        str(candidate.get(field, "") or "")
        for field in [
            "title",
            "novelty_assessment",
            "method_delta",
            "direct_corollary_precheck",
            "why_generation_survives_direct_corollary_filter",
        ]
    ).lower()
    survival = str(candidate.get("why_generation_survives_direct_corollary_filter", "") or "").strip().lower()
    risky = any(phrase in precheck_text for phrase in DIRECT_COROLLARY_RISK_PHRASES)
    weak_survival = len(survival) < 30 or any(
        phrase in survival
        for phrase in [
            "does not survive",
            "it is a direct corollary",
            "no new obstruction",
            "routine",
            "same proof",
        ]
    )
    if risky and weak_survival:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has direct-corollary risk without a concrete survival reason.",
                question_id=label,
                quality_metric="direct_corollary_candidate_risk",
                penalty=35.0,
            )
        )

    _validate_forbidden_proof_module_candidate(path, label, candidate, issues, allow_quality_warnings)

    if _truthy(candidate.get("adjacent_model_transfer")):
        missing_transfer = [field for field in GENERAL_TRANSFER_FIELDS if not _field_present(candidate, field)]
        if missing_transfer:
            issues.append(
                CandidateValidationIssue(
                    "warning",
                    path.as_posix(),
                    f"{label} marks adjacent_model_transfer but lacks transfer evidence fields: {missing_transfer}.",
                    question_id=label,
                    quality_metric="weak_adjacent_model_transfer",
                    penalty=10.0 + min(16.0, 4.0 * len(missing_transfer)),
                )
            )


def _validate_abstraction_lift(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    lift = candidate.get("abstraction_lift")
    severity = "warning" if allow_quality_warnings else "error"
    if not isinstance(lift, dict):
        if not allow_quality_warnings:
            issues.append(
                CandidateValidationIssue(
                    "error",
                    path.as_posix(),
                    f"{label} is missing abstraction_lift; general style must lift proof details to a main research object.",
                    question_id=label,
                    quality_metric="weak_abstraction_lift",
                    penalty=40.0,
                )
            )
        return

    visible_text = _normalized_join(
        candidate.get(field, "")
        for field in [
            "title",
            "precise_problem_statement",
            "novelty_axis",
            "method_delta",
            "question_strategy_used",
            "candidate_origin_type",
        ]
    )
    headline_text = _normalized_join(
        candidate.get(field, "")
        for field in [
            "title",
            "novelty_axis",
            "candidate_origin_type",
            "question_strategy_used",
        ]
    )
    raw_detail = _normalized_join(
        [
            lift.get("raw_proof_detail_used", ""),
            lift.get("abstract_mechanism", ""),
            lift.get("main_research_object", ""),
            lift.get("candidate_not_about_raw_detail", ""),
        ]
    )
    visible_hits = _proof_detail_hits(visible_text)
    raw_leaks = _raw_detail_leaks(str(lift.get("raw_proof_detail_used", "") or ""), visible_text)
    lift_hits = _proof_detail_hits(raw_detail)
    suppressed = _truthy(lift.get("is_raw_detail_suppressed"))
    not_about_raw = str(lift.get("candidate_not_about_raw_detail", "") or "").strip().lower()
    main_object = str(lift.get("main_research_object", "") or "").strip().lower()
    abstract_mechanism = str(lift.get("abstract_mechanism", "") or "").strip().lower()

    if lift_hits and not suppressed:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} abstraction_lift names proof-detail material but does not suppress it: {lift_hits}.",
                question_id=label,
                quality_metric="weak_abstraction_lift",
                penalty=38.0,
            )
        )

    if visible_hits:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} appears centered on proof-detail categories rather than the main research object: {visible_hits}.",
                question_id=label,
                quality_metric="proof_detail_candidate_forbidden",
                penalty=48.0,
            )
        )

    if raw_leaks:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} abstraction_lift claims suppression, but raw proof-detail terms leak into visible candidate text: {raw_leaks}.",
                question_id=label,
                quality_metric="proof_detail_candidate_forbidden",
                penalty=48.0,
            )
        )

    if len(main_object) < 24 or _proof_detail_hits(main_object):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} abstraction_lift.main_research_object is missing, vague, or still a proof detail.",
                question_id=label,
                quality_metric="weak_abstraction_lift",
                penalty=30.0,
            )
        )

    if len(abstract_mechanism) < 24:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} abstraction_lift.abstract_mechanism is too vague to drive a general-mode research question.",
                question_id=label,
                quality_metric="weak_abstraction_lift",
                penalty=24.0,
            )
        )

    if not_about_raw and any(phrase in not_about_raw for phrase in ["about the raw detail", "about raw detail", "not suppressed"]):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} abstraction_lift.candidate_not_about_raw_detail admits the candidate still targets raw proof detail.",
                question_id=label,
                quality_metric="weak_abstraction_lift",
                penalty=34.0,
            )
        )


def _validate_research_direction_gate(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    gate = candidate.get("research_direction_gate")
    severity = "warning" if allow_quality_warnings else "error"
    if not isinstance(gate, dict):
        if not allow_quality_warnings:
            issues.append(
                CandidateValidationIssue(
                    "error",
                    path.as_posix(),
                    f"{label} is missing research_direction_gate; general style must reject input-family variants before hard review.",
                    question_id=label,
                    quality_metric="weak_research_direction_gate",
                    penalty=42.0,
                )
            )
        return

    not_variant = gate.get("not_input_family_variant")
    if not_variant is not True and str(not_variant).strip().lower() not in {"true", "yes", "1"}:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} research_direction_gate does not certify that the candidate escaped the input theorem family.",
                question_id=label,
                quality_metric="weak_research_direction_gate",
                penalty=48.0,
            )
        )

    text = _normalized_join(
        gate.get(field, "")
        for field in [
            "main_object_shift",
            "interesting_model_or_object",
            "new_obstruction_not_in_input",
            "why_direction_is_not_routine",
        ]
    )
    weak_phrases = [
        "same theorem",
        "same result",
        "input lemma",
        "technical cleanup",
        "bookkeeping",
        "routine bookkeeping",
        "routine cleanup",
        "minor variant",
        "small variant",
        "local lemma",
        "proof detail",
        "auxiliary lemma",
        "no new obstruction",
        "not applicable",
        "n/a",
    ]
    if len(text) < 120 or any(phrase in text for phrase in weak_phrases):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} research_direction_gate is too weak; it must name a main-object shift and a non-routine obstruction.",
                question_id=label,
                quality_metric="weak_research_direction_gate",
                penalty=38.0,
            )
        )

    obstruction = str(gate.get("new_obstruction_not_in_input", "") or "").strip().lower()
    if len(obstruction) < 24 or any(
        phrase in obstruction
        for phrase in ["no new obstruction", "routine", "standard argument", "none", "not applicable"]
    ):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} research_direction_gate.new_obstruction_not_in_input is missing or routine.",
                question_id=label,
                quality_metric="weak_research_direction_gate",
                penalty=36.0,
            )
        )


def _validate_forbidden_proof_module_candidate(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    text = " ".join(
        str(candidate.get(field, "") or "")
        for field in [
            "candidate_origin_type",
            "question_strategy_used",
            "title",
            "precise_problem_statement",
            "why_this_is_good_research_question",
            "method_delta",
        ]
    ).lower()
    if any(
        phrase in text
        for phrase in [
            "proof module",
            "module question",
            "input lemma",
            "lemma extraction",
            "prove the lemma",
            "technical lemma",
            "constant tracking",
        ]
    ):
        issues.append(
            CandidateValidationIssue(
                "warning" if allow_quality_warnings else "error",
                path.as_posix(),
                f"{label} is a proof-module/input-lemma candidate, which is forbidden in general style.",
                question_id=label,
                quality_metric="proof_module_candidate_forbidden",
                penalty=50.0,
            )
        )


def _validate_research_level_gate(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    gate = candidate.get("research_level_gate")
    severity = "warning" if allow_quality_warnings else "error"
    if not isinstance(gate, dict):
        return
    independent = gate.get("is_independent_research_problem")
    if independent is not True and str(independent).strip().lower() not in {"true", "yes", "1"}:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} research_level_gate does not certify an independent research problem.",
                question_id=label,
                quality_metric="weak_research_level_gate",
                penalty=45.0,
            )
        )
    text = " ".join(
        str(gate.get(field, "") or "")
        for field in [
            "not_merely_input_lemma",
            "why_publishable_if_solved",
            "what_new_object_or_model_is_added",
            "why_not_just_technical_cleanup",
        ]
    ).lower()
    bad = [
        "merely a lemma",
        "input lemma",
        "proof module only",
        "technical cleanup",
        "constant tracking",
        "same proof",
        "routine",
        "not independent",
    ]
    if any(phrase in text for phrase in bad):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} research_level_gate admits lemma/proof-module/cleanup risk.",
                question_id=label,
                quality_metric="weak_research_level_gate",
                penalty=42.0,
            )
        )


def _validate_method_transfer_reference(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    method_transfer_index: dict[str, Any],
    adjacent_model_pool: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    is_transfer = _candidate_is_method_transfer(candidate)
    cited_module = str(candidate.get("source_method_module_id", "") or "").strip()
    if not _meaningful_transfer_value(cited_module):
        cited_module = ""
    target_model = str(
        candidate.get("target_model_from_transfer_map", "")
        or (candidate.get("target_adjacent_model", "") if is_transfer else "")
        or ""
    ).strip()
    if not _meaningful_transfer_value(target_model):
        target_model = ""

    if not is_transfer and not cited_module and not target_model:
        return

    severity = "warning" if allow_quality_warnings else "error"
    if not method_transfer_index.get("exists"):
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} uses adjacent/model-transfer evidence but method_transfer_map.json is missing.",
                question_id=label,
                quality_metric="weak_method_transfer_map",
                penalty=28.0,
            )
        )
        return

    required = [field for field in METHOD_TRANSFER_REQUIRED_FOR_TRANSFER if not _field_present(candidate, field)]
    if required:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} marks method transfer but lacks required transfer-generation fields: {required}.",
                question_id=label,
                quality_metric="weak_method_transfer_reference",
                penalty=18.0 + min(24.0, 4.0 * len(required)),
            )
        )

    if cited_module:
        module_ids = method_transfer_index.get("module_ids", set())
        if cited_module not in module_ids:
            issues.append(
                CandidateValidationIssue(
                    severity,
                    path.as_posix(),
                    f"{label} cites source_method_module_id={cited_module!r}, but it is absent from method_transfer_map.json.",
                    question_id=label,
                    quality_metric="unknown_method_module_id",
                    penalty=36.0,
                )
            )
            return

    if cited_module and target_model:
        normalized_target = _normalize_model_text(target_model)
        targets = method_transfer_index.get("targets_by_module", {}).get(cited_module, set())
        if targets and not any(_model_text_matches(normalized_target, target) for target in targets):
            issues.append(
                CandidateValidationIssue(
                    severity,
                    path.as_posix(),
                    f"{label} target_model_from_transfer_map={target_model!r} is not listed under {cited_module} in method_transfer_map.json.",
                    question_id=label,
                    quality_metric="unknown_transfer_target_model",
                    penalty=30.0,
                )
            )

    if is_transfer and target_model:
        pool_targets = adjacent_model_pool.get("targets", set())
        if adjacent_model_pool.get("exists") and pool_targets:
            normalized_target = _normalize_model_text(target_model)
            if not any(_model_text_matches(normalized_target, target) for target in pool_targets):
                issues.append(
                    CandidateValidationIssue(
                        severity,
                        path.as_posix(),
                        f"{label} transfer target {target_model!r} is absent from adjacent_model_pool.json.",
                        question_id=label,
                        quality_metric="unknown_adjacent_model_pool_target",
                        penalty=32.0,
                    )
                )

    if is_transfer:
        weak_text_fields = [
            field
            for field in [
                "shared_invariant",
                "new_failure_term",
                "one_new_lemma_needed",
                "why_not_random_transfer",
            ]
            if _field_present(candidate, field) and _vague_short_value(candidate.get(field))
        ]
        if weak_text_fields:
            issues.append(
                CandidateValidationIssue(
                    "warning" if allow_quality_warnings else "error",
                    path.as_posix(),
                    f"{label} has vague method-transfer mechanism fields: {weak_text_fields}.",
                    question_id=label,
                    quality_metric="weak_method_transfer_reference",
                    penalty=18.0 + 3.0 * len(weak_text_fields),
                )
            )

        score = candidate.get("structural_match_score")
        if score is not None and not isinstance(score, (int, float)):
            issues.append(
                CandidateValidationIssue(
                    severity,
                    path.as_posix(),
                    f"{label} structural_match_score must be numeric 0-10.",
                    question_id=label,
                    quality_metric="weak_method_transfer_reference",
                    penalty=10.0,
                )
            )


def _validate_paper_survey_use(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
) -> None:
    missing = [field for field in PAPER_SURVEY_FIELDS if not _field_present(candidate, field)]
    if missing:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has weak paper-level survey use; missing field(s): {missing}.",
                question_id=label,
                quality_metric="weak_paper_survey_use",
                penalty=8.0 + 4.0 * len(missing),
            )
        )


def _validate_novelty_tuple(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
) -> None:
    missing = [field for field in NOVELTY_TUPLE_FIELDS if not _field_present(candidate, field)]
    if missing:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has weak/missing novelty tuple fields: {missing}.",
                question_id=label,
                quality_metric="weak_novelty_tuple",
                penalty=10.0 + min(16.0, 4.0 * len(missing)),
            )
    )


def _validate_structured_field(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    field: str,
    required_keys: list[str],
    quality_metric: str,
    base_penalty: float,
    issues: list[CandidateValidationIssue],
) -> None:
    value = candidate.get(field)
    if not isinstance(value, dict):
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has missing or invalid {field}; expected object with keys {required_keys}.",
                question_id=label,
                quality_metric=quality_metric,
                penalty=base_penalty,
            )
        )
        return
    missing = [key for key in required_keys if not _field_present(value, key)]
    vague = [
        key
        for key in required_keys
        if key not in missing and _vague_short_value(value.get(key))
    ]
    if missing or vague:
        issues.append(
            CandidateValidationIssue(
                "warning",
                path.as_posix(),
                f"{label} has weak {field}; missing={missing}, vague={vague}.",
                question_id=label,
                quality_metric=quality_metric,
                penalty=base_penalty + min(18.0, 4.0 * (len(missing) + len(vague))),
            )
        )


def _validate_direct_corollary_attack_hard_completeness(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    if allow_quality_warnings:
        return
    attack = candidate.get("direct_corollary_attack")
    if not isinstance(attack, dict):
        return
    missing = [key for key in DIRECT_COROLLARY_ATTACK_FIELDS if not _field_present(attack, key)]
    attack_missing = [key for key in DIRECT_COROLLARY_ATTEMPT_FIELDS if key in missing]
    if "why_all_fail" in missing or len(attack_missing) >= 2:
        issues.append(
            CandidateValidationIssue(
                "error",
                path.as_posix(),
                f"{label} direct_corollary_attack is incomplete enough to require repair; missing={missing}.",
                question_id=label,
                quality_metric="weak_direct_corollary_attack",
                penalty=42.0,
            )
        )


def _validate_direct_corollary_attack_attempt(
    path: Path,
    label: str,
    candidate: dict[str, Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool = True,
) -> None:
    attack = candidate.get("direct_corollary_attack")
    if not isinstance(attack, dict):
        return
    weak = []
    for field in DIRECT_COROLLARY_ATTEMPT_FIELDS:
        text = str(attack.get(field, "") or "")
        if not _looks_like_attempted_proof(text):
            weak.append(field)
    if weak:
        severity = "warning"
        if not allow_quality_warnings and len(weak) >= 3:
            severity = "error"
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"{label} direct_corollary_attack should be written as attempted proof steps; weak fields: {weak}.",
                question_id=label,
                quality_metric="weak_attempted_direct_proof",
                penalty=14.0 + 4.0 * len(weak),
            )
        )


def _quality_label(metric: str) -> str:
    if metric in {"weak_transfer_pattern", "unclear_transfer_pattern_id", "invalid_transfer_pattern_fit_score"}:
        return "weak_transfer_pattern"
    if metric in {"weak_general_strategy", "invalid_general_strategy_fit_score"}:
        return "weak_general_strategy"
    if metric == "direct_corollary_candidate_risk":
        return "direct_corollary_candidate_risk"
    if metric == "weak_adjacent_model_transfer":
        return "weak_adjacent_model_transfer"
    if metric in {
        "weak_method_transfer_map",
        "weak_method_transfer_reference",
        "unknown_method_module_id",
        "unknown_transfer_target_model",
        "weak_adjacent_model_pool",
        "unknown_adjacent_model_pool_target",
    }:
        return metric
    if metric in {
        "weak_input_anchor",
        "weak_direct_corollary_attack",
        "weak_minimal_proof_route",
        "weak_research_level_gate",
        "weak_abstraction_lift",
        "proof_detail_candidate_forbidden",
    }:
        return metric
    if metric in {"weak_general_ranking_metadata", "weak_attempted_direct_proof"}:
        return metric
    if metric == "weak_novelty_tuple":
        return "weak_novelty_tuple"
    if metric == "weak_paper_survey_use":
        return "weak_paper_survey_use"
    return "weak_theorem_form"


def _normalize_question_style(question_style: str) -> str:
    style = str(question_style or "specialized").strip().lower()
    return "general" if style.startswith("general") else "specialized"


def _validate_general_candidate_mix(
    path: Path,
    candidates: list[Any],
    issues: list[CandidateValidationIssue],
    allow_quality_warnings: bool,
) -> None:
    objects = [candidate for candidate in candidates if isinstance(candidate, dict)]
    if len(objects) < 2:
        return
    proof_module_count = 0
    for candidate in objects:
        origin = str(candidate.get("candidate_origin_type", "")).strip().lower()
        strategy = str(candidate.get("question_strategy_used", "")).strip().lower()
        statement = str(candidate.get("precise_problem_statement", "")).strip().lower()
        title = str(candidate.get("title", "")).strip().lower()
        if any(
            phrase in " ".join([origin, strategy, statement, title])
            for phrase in [
                "proof module",
                "proof module of",
                "module question",
                "input lemma",
                "lemma extraction",
                "prove the lemma",
                "technical lemma",
                "constant tracking",
            ]
        ):
            proof_module_count += 1
    severity = "warning" if allow_quality_warnings else "error"
    if proof_module_count:
        issues.append(
            CandidateValidationIssue(
                severity,
                path.as_posix(),
                f"General style produced {proof_module_count} proof-module/lemma-extraction candidate(s); pure proof-module candidates are not allowed in general mode.",
                quality_metric="proof_module_candidate_forbidden",
                penalty=50.0,
            )
        )


def _proof_detail_hits(text: str) -> list[str]:
    lower = str(text or "").lower()
    return [phrase for phrase in PROOF_DETAIL_CATEGORY_PHRASES if phrase in lower]


def _raw_detail_leaks(raw_detail: str, visible_text: str) -> list[str]:
    raw = str(raw_detail or "").lower()
    visible = str(visible_text or "").lower()
    if not raw or raw.strip() in {"none", "n/a", "not applicable"}:
        return []
    phrase_hits = []
    for phrase in re.findall(r"[a-z][a-z0-9-]*(?:\s+[a-z][a-z0-9-]*)+", raw):
        words = [word for word in re.findall(r"[a-z][a-z0-9-]*", phrase) if word not in RAW_DETAIL_STOPWORDS]
        if len(words) >= 2:
            compact = " ".join(words[:4])
            if compact and compact in visible:
                phrase_hits.append(compact)
    tokens = [
        token
        for token in re.findall(r"[a-z][a-z0-9-]{4,}", raw)
        if token not in RAW_DETAIL_STOPWORDS
    ]
    token_hits = sorted({token for token in tokens if token in visible})
    if len(token_hits) >= 2:
        phrase_hits.extend(token_hits[:5])
    return sorted(set(phrase_hits))


def _normalized_join(values: Any) -> str:
    if isinstance(values, (str, bytes)):
        return str(values)
    return re.sub(r"\s+", " ", " ".join(str(value or "") for value in values)).strip().lower()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def _candidate_is_method_transfer(candidate: dict[str, Any]) -> bool:
    origin = str(candidate.get("candidate_origin_type", "") or "").lower()
    strategy = str(candidate.get("question_strategy_used", "") or "").lower()
    source_module = str(candidate.get("source_method_module_id", "") or "").strip().lower()
    target_model = str(candidate.get("target_model_from_transfer_map", "") or "").strip().lower()
    return (
        _truthy(candidate.get("adjacent_model_transfer"))
        or _contains_transfer_intent(origin)
        or _contains_transfer_intent(strategy)
        or _meaningful_transfer_value(source_module)
        or _meaningful_transfer_value(target_model)
    )


def _contains_transfer_intent(text: str) -> bool:
    clean = str(text or "").lower()
    if any(phrase in clean for phrase in ["non-transfer", "non transfer", "not a transfer", "not transfer"]):
        return False
    return "transfer" in clean or "adjacent" in clean


def _meaningful_transfer_value(value: str) -> bool:
    clean = str(value or "").strip().lower()
    if not clean:
        return False
    sentinels = {
        "none",
        "n/a",
        "na",
        "not applicable",
        "not_applicable",
        "not-applicable",
        "not_applicable_non_transfer",
        "non_transfer",
        "non-transfer",
        "local",
        "local_candidate",
    }
    return clean not in sentinels


def _normalize_model_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+\-_. ]+", " ", value.lower())).strip()


def _model_text_matches(candidate_target: str, map_target: str) -> bool:
    if not candidate_target or not map_target:
        return False
    return candidate_target == map_target or candidate_target in map_target or map_target in candidate_target


def _vague_short_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, list):
        return not value or any(_vague_short_value(item) for item in value[:1])
    text = str(value or "").strip().lower()
    if len(text) < 24:
        return True
    vague = [
        "standard arguments",
        "routine",
        "same proof",
        "as in the paper",
        "not specified",
        "unknown",
        "n/a",
        "suitable assumptions",
        "appropriate conditions",
    ]
    return any(phrase in text for phrase in vague)


def _looks_like_attempted_proof(text: str) -> bool:
    clean = str(text or "").strip().lower()
    if len(clean) < 60:
        return False
    step_markers = ["1.", "2.", "3.", "step 1", "step 2", "apply", "then", "fails", "breaks", "cannot"]
    if sum(1 for marker in step_markers if marker in clean) >= 2:
        return True
    return bool(re.search(r"\b(first|second|third)\b", clean)) and any(
        word in clean for word in ["fails", "breaks", "cannot", "does not"]
    )


def _combine_validation_quality(current: str, label: str) -> str:
    labels = [item.strip() for item in str(current or "ok").split(";") if item.strip() and item.strip() != "ok"]
    if label not in labels:
        labels.append(label)
    return "; ".join(labels) if labels else "ok"


def _field_present(candidate: dict[str, Any], field: str) -> bool:
    value = candidate.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _ids_from_list(items: list[Any]) -> list[str]:
    ids = []
    for item in items:
        if isinstance(item, dict):
            question_id = str(item.get("question_id", "")).strip()
            if question_id:
                ids.append(question_id)
    return ids


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _paper_id_from_issue_path(path: str) -> str:
    for part in Path(path).parts:
        if part.startswith("paper_"):
            return part
    return ""


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
