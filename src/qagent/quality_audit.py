from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .validators import REQUIRED_SELECTED_FILES, theorem_level_validation_errors


LOW_SOURCE_PHRASES = [
    "full pdf text was not extracted",
    "only title/abstract",
    "metadata/abstract only",
    "full text was unavailable",
    "local batch metadata used",
]


@dataclass
class AuditIssue:
    severity: str
    path: str
    message: str


@dataclass
class AuditResult:
    ok: bool
    expected_papers: int
    expected_candidates_per_paper: int
    expected_selected_per_paper: int
    papers_found: int
    selected_questions_found: int
    issues: list[AuditIssue]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = [asdict(issue) for issue in self.issues]
        return data


def audit_outputs(output_dir: Path, n: int, a: int, b: int) -> AuditResult:
    expected_candidates = (a + 1) * b
    issues: list[AuditIssue] = []
    all_paper_dirs = _paper_dirs(output_dir)
    expected_names = {f"paper_{index:03d}" for index in range(1, n + 1)}
    paper_dirs = [path for path in all_paper_dirs if path.name in expected_names]
    extra_dirs = [path.name for path in all_paper_dirs if path.name not in expected_names]
    selected_total = 0

    if len(paper_dirs) != n:
        issues.append(
            AuditIssue(
                "error",
                output_dir.as_posix(),
                f"Expected {n} paper directories, found {len(paper_dirs)}.",
            )
        )
    if extra_dirs:
        issues.append(
            AuditIssue(
                "warning",
                output_dir.as_posix(),
                f"Ignoring stale or out-of-scope paper directories: {', '.join(extra_dirs[:10])}.",
            )
        )

    for paper_dir in paper_dirs:
        selected_dirs = _selected_question_dirs(paper_dir)
        selected_total += len(selected_dirs)
        expected_selected = _expected_selected_for_paper(output_dir, paper_dir.name, b)
        _audit_paper_counts(paper_dir, expected_candidates, expected_selected, selected_dirs, issues)
        _audit_paper_evidence(paper_dir, issues)
        _audit_selected_questions(paper_dir, selected_dirs, _passed_question_ids(output_dir, paper_dir.name), issues)

    _audit_repeated_scores(paper_dirs, issues)
    ok = not any(issue.severity == "error" for issue in issues)
    return AuditResult(ok, n, expected_candidates, b, len(paper_dirs), selected_total, issues)


def write_audit_result(output_dir: Path, result: AuditResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "quality_audit.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_quality_repair_prompt(output_dir: Path, batch_id: str, audit: AuditResult) -> str:
    errors = [issue for issue in audit.issues if issue.severity == "error"]
    error_lines = "\n".join(f"- `{issue.path}`: {issue.message}" for issue in errors) or "- No error issues."
    return f"""Please repair the QAgent final outputs for batch `{batch_id}`.

Scope:
- Work only under `outputs/{batch_id}`.
- Do not regenerate the whole batch.
- Do not modify candidate_questions.json, ranked_questions.json, hard_review.json, or hard_review_passed_candidates.json unless an audit error explicitly names one of those files.
- Do not create selected questions whose question_id is absent from `outputs/{batch_id}/hard_review_passed_candidates.json`.
- Do not select any high duplicate-risk, survey action remove, or negative-critic candidate.
- Preserve existing valid files whenever possible.

Quality audit errors to repair:
{error_lines}

Required references:
- `outputs/{batch_id}/quality_audit.json`
- `outputs/{batch_id}/hard_review_passed_candidates.json`
- `outputs/{batch_id}/hard_review.json`
- `outputs/{batch_id}/backend_info.json`
- paper evidence files under `outputs/{batch_id}/paper_###/`

Repair rules:
1. For missing selected files, create only the missing required file(s) in the existing selected question folder.
2. For invalid `problem_statement.tex`, rewrite only that file as a clean theorem-style `\\begin{{q}}...\\end{{q}}` statement.
3. For metadata errors, patch only `metadata.json` and keep the selected question_id unchanged.
4. For selected question IDs outside the hard-review allowlist, remove that selected folder and replace it only with an allowed passed candidate if the paper has fewer than the required selected count.
5. For missing candidate-level novelty/duplicate evidence or critic reports, do not invent reports. Instead choose a different passed candidate that already has matching hard-review evidence, if needed.
6. After repair, ensure every selected folder has:
   - problem_statement.tex
   - additional_prove_human_help_global.md
   - additional_verify_rule_global.md
   - survey_queries.md
   - feasibility_analysis.md
   - metadata.json
7. Ensure metadata includes generation_backend, generation_api_mode, generation_model, generation_model_source, and codex_cli_version from backend_info.json.

When finished, summarize only the files changed and why."""


def write_quality_repair_prompt(output_dir: Path, batch_id: str, audit: AuditResult) -> Path | None:
    path = output_dir / "repair_prompt.md"
    if audit.ok:
        if path.exists():
            path.unlink()
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(build_quality_repair_prompt(output_dir, batch_id, audit), encoding="utf-8")
    return path


def _paper_dirs(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    return sorted(path for path in output_dir.iterdir() if path.is_dir())


def _selected_question_dirs(paper_dir: Path) -> list[Path]:
    selected_root = paper_dir / "selected"
    if not selected_root.exists():
        return []
    return sorted(path for path in selected_root.iterdir() if path.is_dir())


def _expected_selected_for_paper(output_dir: Path, paper_id: str, requested: int) -> int:
    passed = _passed_question_ids(output_dir, paper_id)
    if passed:
        return min(requested, len(passed))
    allowlist = _read_json(output_dir / "hard_review_passed_candidates.json")
    if isinstance(allowlist, dict):
        for paper in allowlist.get("papers", []):
            if isinstance(paper, dict) and paper.get("paper_id") == paper_id:
                ids = paper.get("passed_question_ids", [])
                return min(requested, len(ids)) if isinstance(ids, list) else requested
    return requested


def _audit_paper_counts(
    paper_dir: Path,
    expected_candidates: int,
    expected_selected: int,
    selected_dirs: list[Path],
    issues: list[AuditIssue],
) -> None:
    for name in ["candidate_questions.json", "ranked_questions.json"]:
        path = paper_dir / name
        data = _read_json(path)
        count = len(data) if isinstance(data, list) else None
        if count != expected_candidates:
            issues.append(
                AuditIssue(
                    "error",
                    path.as_posix(),
                    f"Expected {expected_candidates} items, found {count if count is not None else 'invalid JSON/list'}.",
                )
            )

    if len(selected_dirs) != expected_selected:
        if len(selected_dirs) < expected_selected:
            allowed_shortfall = _allowed_quality_shortfall(paper_dir, expected_selected, selected_dirs)
            if allowed_shortfall:
                issues.append(
                    AuditIssue(
                        "warning",
                        (paper_dir / "selected").as_posix(),
                        allowed_shortfall,
                    )
                )
                return
        issues.append(
            AuditIssue(
                "error",
                (paper_dir / "selected").as_posix(),
                f"Expected {expected_selected} selected question folders, found {len(selected_dirs)}.",
            )
        )


def _allowed_quality_shortfall(
    paper_dir: Path,
    expected_selected: int,
    selected_dirs: list[Path],
) -> str:
    passed_ids = _passed_question_ids(paper_dir.parent, paper_dir.name)
    if not passed_ids:
        return ""
    selected_ids = {path.name for path in selected_dirs}
    missing_ids = sorted(passed_ids - selected_ids)
    deficit = expected_selected - len(selected_dirs)
    if deficit <= 0 or len(missing_ids) < deficit:
        return ""

    disqualified = [question_id for question_id in missing_ids if _final_exclusion_is_quality_based(paper_dir, question_id)]
    if len(disqualified) < deficit:
        return ""

    shown = ", ".join(disqualified[:deficit])
    return (
        f"Expected {expected_selected} selected question folders, found {len(selected_dirs)}. "
        f"Accepted as completed with warnings because the missing allowlisted candidate(s) "
        f"{shown} were excluded by final novelty/quality evidence "
        "(high duplicate risk, remove action, direct corollary, or known-result verdict)."
    )


def _final_exclusion_is_quality_based(paper_dir: Path, question_id: str) -> bool:
    survey = _read_json(paper_dir / "candidate_surveys" / f"{question_id}.json")
    if not isinstance(survey, dict):
        return False

    duplicate_risk = str(survey.get("duplicate_risk", "")).strip().lower()
    recommended_action = str(survey.get("recommended_action", "")).strip().lower()
    novelty_verdict = str(survey.get("novelty_verdict", "")).strip().lower()
    classification = str(survey.get("classification", "")).strip().lower()
    direct_check = str(survey.get("direct_corollary_check", "")).strip().lower()

    if duplicate_risk == "high":
        return True
    if recommended_action == "remove":
        return True
    if novelty_verdict in {
        "direct corollary",
        "known theorem",
        "likely known",
        "probably already known",
        "too close to input theorem",
    }:
        return True
    if classification in {
        "direct restatement of input paper",
        "direct corollary",
        "known theorem",
        "likely known",
    }:
        return True
    if "direct corollary" in direct_check and survey.get("directly_applicable_theorems"):
        return True
    return False


def _audit_paper_evidence(paper_dir: Path, issues: list[AuditIssue]) -> None:
    required = [
        "paper_profile.json",
        "theorem_cards.json",
        "proof_cards.json",
        "limitation_cards.json",
        "gap_cards.json",
    ]
    for name in required:
        path = paper_dir / name
        if not path.is_file():
            issues.append(AuditIssue("error", path.as_posix(), "Required evidence artifact is missing."))

    profile = _read_json(paper_dir / "paper_profile.json")
    full_text_read = profile.get("full_text_was_read") if isinstance(profile, dict) else None
    confidence = str(profile.get("paper_reading_confidence", "") if isinstance(profile, dict) else "").lower()
    if full_text_read is False or confidence == "low":
        issues.append(
            AuditIssue(
                "warning",
                (paper_dir / "paper_profile.json").as_posix(),
                "Paper appears to be based on partial text or low-confidence extraction; final questions need explicit caution.",
            )
        )


def _audit_selected_questions(
    paper_dir: Path,
    selected_dirs: list[Path],
    passed_question_ids: set[str] | None,
    issues: list[AuditIssue],
) -> None:
    for qdir in selected_dirs:
        for filename in REQUIRED_SELECTED_FILES:
            path = qdir / filename
            if not path.is_file():
                issues.append(AuditIssue("error", path.as_posix(), "Required selected-question file is missing."))

        tex_path = qdir / "problem_statement.tex"
        if tex_path.is_file():
            tex = tex_path.read_text(encoding="utf-8", errors="ignore")
            for error in theorem_level_validation_errors(tex):
                issues.append(AuditIssue("error", tex_path.as_posix(), error))

        metadata = _read_json(qdir / "metadata.json")
        question_id = qdir.name
        if isinstance(metadata, dict):
            question_id = str(metadata.get("question_id") or question_id)
        if passed_question_ids is not None and question_id not in passed_question_ids:
            issues.append(
                AuditIssue(
                    "error",
                    qdir.as_posix(),
                    f"Selected question {question_id} is not present in hard_review_passed_candidates.json.",
                )
            )
        _audit_metadata(qdir / "metadata.json", metadata, issues)
        _audit_hard_review_trace(paper_dir, qdir, metadata, issues)
        _audit_source_caution(qdir, metadata, issues)


def _audit_metadata(path: Path, metadata: Any, issues: list[AuditIssue]) -> None:
    if not isinstance(metadata, dict):
        issues.append(AuditIssue("error", path.as_posix(), "metadata.json is not a JSON object."))
        return

    duplicate_risk = str(metadata.get("survey_duplicate_risk", metadata.get("duplicate_risk", ""))).lower()
    if duplicate_risk == "high":
        issues.append(AuditIssue("error", path.as_posix(), "High duplicate-risk candidate was selected."))

    critic = str(metadata.get("critic_summary", "")).lower()
    if not critic:
        issues.append(AuditIssue("warning", path.as_posix(), "Missing critic_summary."))
    elif "negative" in critic:
        issues.append(AuditIssue("error", path.as_posix(), "Negative critic candidate was selected."))

    for key in ["theorem_cards_used", "gap_cards_used"]:
        if key in metadata and not metadata.get(key):
            issues.append(AuditIssue("warning", path.as_posix(), f"{key} is empty."))

    for key in ["generation_backend", "generation_api_mode", "generation_model", "generation_model_source"]:
        if not metadata.get(key):
            issues.append(AuditIssue("warning", path.as_posix(), f"Missing backend metadata field: {key}."))


def _audit_hard_review_trace(paper_dir: Path, qdir: Path, metadata: Any, issues: list[AuditIssue]) -> None:
    question_id = qdir.name
    if isinstance(metadata, dict):
        question_id = str(metadata.get("question_id") or question_id)

    survey_path = paper_dir / "candidate_surveys" / f"{question_id}.md"
    critic_path = paper_dir / "candidate_critic" / f"{question_id}.md"
    if not survey_path.is_file():
        issues.append(
            AuditIssue(
                "error",
                survey_path.as_posix(),
                f"Selected question {question_id} has no matching candidate-level novelty/duplicate evidence.",
            )
        )
    if not critic_path.is_file():
        issues.append(
            AuditIssue(
                "error",
                critic_path.as_posix(),
                f"Selected question {question_id} has no matching hard critic report.",
            )
        )
        return

    verdict = _critic_verdict(critic_path)
    if verdict == "negative":
        issues.append(
            AuditIssue(
                "error",
                critic_path.as_posix(),
                f"Selected question {question_id} has a negative hard critic verdict.",
            )
        )


def _audit_source_caution(qdir: Path, metadata: Any, issues: list[AuditIssue]) -> None:
    metadata_text = json.dumps(metadata, ensure_ascii=False).lower() if isinstance(metadata, dict) else ""
    feasibility_path = qdir / "feasibility_analysis.md"
    feasibility = feasibility_path.read_text(encoding="utf-8", errors="ignore").lower() if feasibility_path.exists() else ""
    low_source = any(phrase in metadata_text or phrase in feasibility for phrase in LOW_SOURCE_PHRASES)
    confidence = str(metadata.get("paper_reading_confidence", "") if isinstance(metadata, dict) else "").lower()
    if confidence == "low" and not low_source:
        issues.append(
            AuditIssue(
                "warning",
                qdir.as_posix(),
                "metadata says paper_reading_confidence is low, but selected output lacks a clear lower-confidence source note.",
            )
        )


def _audit_repeated_scores(paper_dirs: list[Path], issues: list[AuditIssue]) -> None:
    score_sequences: dict[tuple[Any, ...], list[str]] = {}
    for paper_dir in paper_dirs:
        scores = []
        for qdir in _selected_question_dirs(paper_dir):
            metadata = _read_json(qdir / "metadata.json")
            if isinstance(metadata, dict):
                scores.append(metadata.get("final_score", metadata.get("weighted_score")))
        if scores:
            score_sequences.setdefault(tuple(scores), []).append(paper_dir.name)

    for scores, names in score_sequences.items():
        if len(names) >= 3:
            issues.append(
                AuditIssue(
                    "warning",
                    paper_dirs[0].parent.as_posix() if paper_dirs else "outputs",
                    f"{len(names)} papers share the same selected score pattern {list(scores)}; scoring may be templated.",
                )
            )


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _critic_verdict(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"(?ims)^##\s*Verdict\s*$\s*(positive|conditionally positive|negative)\b", text)
    if match:
        return match.group(1).lower()
    summary = re.search(r"(?i)\bVerdict:\s*(positive|conditionally positive|negative)\b", text)
    return summary.group(1).lower() if summary else ""


def _passed_question_ids(output_dir: Path, paper_id: str) -> set[str] | None:
    data = _read_json(output_dir / "hard_review_passed_candidates.json")
    if not isinstance(data, dict):
        return None
    papers = data.get("papers")
    if not isinstance(papers, list):
        return None
    for paper in papers:
        if isinstance(paper, dict) and paper.get("paper_id") == paper_id:
            ids = paper.get("passed_question_ids")
            if isinstance(ids, list):
                return {str(item) for item in ids}
            return set()
    return set()
