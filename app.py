from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import streamlit as st

from src.qagent.backend_diagnostics import (
    collect_backend_diagnostics,
    patch_selected_metadata_backend_info,
    write_backend_info,
    write_backend_info_markdown,
)
from src.qagent.candidate_validator import (
    trim_excess_candidate_outputs,
    validate_candidate_outputs,
    validate_candidate_outputs_with_policy,
    write_candidate_quality_flags,
    write_candidate_repair_prompt,
    write_candidate_validation_markdown,
    write_candidate_validation_result,
)
from src.qagent.candidate_exporter import write_ranked_candidate_latex
from src.qagent.evidence_preflight import (
    evidence_summary_markdown,
    run_evidence_preflight,
    write_evidence_preflight_result,
)
from src.qagent.hard_review import (
    hard_review_summary_markdown,
    run_hard_review,
    write_hard_review_result,
    write_passed_candidates,
)
from src.qagent.gpt_pro_handoff import (
    write_gpt_pro_final_selection_handoff,
    write_gpt_pro_handoff,
)
from src.qagent.input_resolver import resolve_paper_entries
from src.qagent.novelty_review import (
    build_novelty_review_prompt,
    ensure_novelty_review_outputs,
)
from src.qagent.paper_literature_survey import (
    build_paper_literature_survey_prompt,
    ensure_paper_literature_survey_outputs,
    run_local_paper_literature_survey,
)
from src.qagent.quality_audit import audit_outputs, write_audit_result
from src.qagent.quality_audit import write_quality_repair_prompt
from src.qagent.runner import (
    build_candidate_generation_prompt,
    build_candidate_replacement_prompt,
    build_final_selection_prompt,
    check_codex_cli,
    codex_backend_metadata,
    run_codex_cli,
)
from src.qagent.ui_helpers import (
    estimate_output_tokens,
    estimate_tokens,
    paper_dirs,
    read_text,
    zip_directory,
)


DEFAULT_BATCH_ID = "batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")
BATCH_ID = DEFAULT_BATCH_ID
INPUT_PATH = Path("data") / f"{BATCH_ID}.md"
OUTPUT_DIR = Path("outputs") / BATCH_ID
STATUS_PATH = OUTPUT_DIR / "run_status.json"
BACKEND_INFO_PATH = OUTPUT_DIR / "backend_info.json"
BACKEND_INFO_LOG_PATH = OUTPUT_DIR / "backend_info.md"
METADATA_BACKEND_PATCH_PATH = OUTPUT_DIR / "metadata_backend_patch.json"
CANDIDATE_VALIDATION_PATH = OUTPUT_DIR / "candidate_validation.json"
CANDIDATE_VALIDATION_LOG_PATH = OUTPUT_DIR / "candidate_validation.md"
CANDIDATE_REPAIR_PROMPT_PATH = OUTPUT_DIR / "candidate_repair_prompt.md"
CANDIDATE_REPAIR_RUN_LOG_PATH = OUTPUT_DIR / "candidate_repair_run_log.txt"
MAX_CANDIDATE_REPAIR_ATTEMPTS = 3
MAX_CANDIDATE_REPLACEMENT_ATTEMPTS = 3
ENABLE_CODEX_NOVELTY_REVIEW = False
ENABLE_FULL_CANDIDATE_CRITIC = False
RESOLVER_LOG_PATH = OUTPUT_DIR / "resolver_log.md"
RUN_LOG_PATH = OUTPUT_DIR / "run_log.txt"
CANDIDATE_RUN_LOG_PATH = OUTPUT_DIR / "candidate_run_log.txt"
FINAL_RUN_LOG_PATH = OUTPUT_DIR / "final_run_log.txt"
QUALITY_AUDIT_PATH = OUTPUT_DIR / "quality_audit.json"
REPAIR_PROMPT_PATH = OUTPUT_DIR / "repair_prompt.md"
REPAIR_RUN_LOG_PATH = OUTPUT_DIR / "repair_run_log.txt"
EVIDENCE_PREFLIGHT_PATH = OUTPUT_DIR / "evidence_preflight.json"
EVIDENCE_PREFLIGHT_LOG_PATH = OUTPUT_DIR / "evidence_preflight.md"
HARD_REVIEW_PATH = OUTPUT_DIR / "hard_review.json"
HARD_REVIEW_LOG_PATH = OUTPUT_DIR / "hard_review.md"
PASSED_CANDIDATES_PATH = OUTPUT_DIR / "hard_review_passed_candidates.json"
NOVELTY_REVIEW_RUN_LOG_PATH = OUTPUT_DIR / "novelty_review_run_log.txt"
PAPER_LITERATURE_SURVEY_RUN_LOG_PATH = OUTPUT_DIR / "paper_literature_survey_run_log.txt"
GPT_PRO_HANDOFF_PATH = OUTPUT_DIR / "gpt_pro_handoff"
REQUIRED_QED_FILES = [
    "problem_statement.tex",
    "additional_prove_human_help_global.md",
    "additional_verify_rule_global.md",
    "survey_queries.md",
    "feasibility_analysis.md",
    "metadata.json",
]
RUN_STAGES = [
    "resolving papers",
    "evidence preflight",
    "paper literature survey",
    "candidate generation",
    "candidate validation",
    "candidate auto repair",
    "novelty search",
    "hard review",
    "candidate replacement",
    "final selection",
    "quality audit",
    "quality auto repair",
    "completed",
]

EXAMPLE_MARKDOWN = """## Exact paper title
Authors: First Author; Second Author
URL: https://arxiv.org/abs/2501.01234

---

Title: Exact paper title from CVGMT or another open repository
Authors: First Author; Second Author
URL: https://cvgmt.sns.it/paper/1234/
PDF URL: optional direct PDF URL if available
DOI: optional

---

A. Author and B. Author, "Exact paper title", 2026.
URL: https://example.org/open-access-paper-page
PDF Path: optional local PDF path, e.g. C:\\Users\\19891\\Desktop\\papers\\paper.pdf

Strongly recommended: provide arXiv, CVGMT, another openly downloadable paper URL, a direct PDF URL, or a local PDF path.
"""


def safe_batch_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value.strip())
    cleaned = cleaned.strip("_-")
    return cleaned or DEFAULT_BATCH_ID


def configure_batch_paths(batch_id: str) -> None:
    global BATCH_ID
    global INPUT_PATH, OUTPUT_DIR, STATUS_PATH, BACKEND_INFO_PATH, BACKEND_INFO_LOG_PATH
    global METADATA_BACKEND_PATCH_PATH, CANDIDATE_VALIDATION_PATH, CANDIDATE_VALIDATION_LOG_PATH
    global CANDIDATE_REPAIR_PROMPT_PATH, CANDIDATE_REPAIR_RUN_LOG_PATH
    global RESOLVER_LOG_PATH, RUN_LOG_PATH, CANDIDATE_RUN_LOG_PATH, FINAL_RUN_LOG_PATH
    global QUALITY_AUDIT_PATH, REPAIR_PROMPT_PATH, REPAIR_RUN_LOG_PATH
    global EVIDENCE_PREFLIGHT_PATH, EVIDENCE_PREFLIGHT_LOG_PATH
    global HARD_REVIEW_PATH, HARD_REVIEW_LOG_PATH, PASSED_CANDIDATES_PATH, NOVELTY_REVIEW_RUN_LOG_PATH
    global PAPER_LITERATURE_SURVEY_RUN_LOG_PATH
    global GPT_PRO_HANDOFF_PATH

    BATCH_ID = safe_batch_id(batch_id)
    INPUT_PATH = Path("data") / f"{BATCH_ID}.md"
    OUTPUT_DIR = Path("outputs") / BATCH_ID
    STATUS_PATH = OUTPUT_DIR / "run_status.json"
    BACKEND_INFO_PATH = OUTPUT_DIR / "backend_info.json"
    BACKEND_INFO_LOG_PATH = OUTPUT_DIR / "backend_info.md"
    METADATA_BACKEND_PATCH_PATH = OUTPUT_DIR / "metadata_backend_patch.json"
    CANDIDATE_VALIDATION_PATH = OUTPUT_DIR / "candidate_validation.json"
    CANDIDATE_VALIDATION_LOG_PATH = OUTPUT_DIR / "candidate_validation.md"
    CANDIDATE_REPAIR_PROMPT_PATH = OUTPUT_DIR / "candidate_repair_prompt.md"
    CANDIDATE_REPAIR_RUN_LOG_PATH = OUTPUT_DIR / "candidate_repair_run_log.txt"
    RESOLVER_LOG_PATH = OUTPUT_DIR / "resolver_log.md"
    RUN_LOG_PATH = OUTPUT_DIR / "run_log.txt"
    CANDIDATE_RUN_LOG_PATH = OUTPUT_DIR / "candidate_run_log.txt"
    FINAL_RUN_LOG_PATH = OUTPUT_DIR / "final_run_log.txt"
    QUALITY_AUDIT_PATH = OUTPUT_DIR / "quality_audit.json"
    REPAIR_PROMPT_PATH = OUTPUT_DIR / "repair_prompt.md"
    REPAIR_RUN_LOG_PATH = OUTPUT_DIR / "repair_run_log.txt"
    EVIDENCE_PREFLIGHT_PATH = OUTPUT_DIR / "evidence_preflight.json"
    EVIDENCE_PREFLIGHT_LOG_PATH = OUTPUT_DIR / "evidence_preflight.md"
    HARD_REVIEW_PATH = OUTPUT_DIR / "hard_review.json"
    HARD_REVIEW_LOG_PATH = OUTPUT_DIR / "hard_review.md"
    PASSED_CANDIDATES_PATH = OUTPUT_DIR / "hard_review_passed_candidates.json"
    NOVELTY_REVIEW_RUN_LOG_PATH = OUTPUT_DIR / "novelty_review_run_log.txt"
    PAPER_LITERATURE_SURVEY_RUN_LOG_PATH = OUTPUT_DIR / "paper_literature_survey_run_log.txt"
    GPT_PRO_HANDOFF_PATH = OUTPUT_DIR / "gpt_pro_handoff"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def setup_page() -> None:
    st.set_page_config(page_title="QAgent", layout="wide")
    st.markdown(
        """
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #c1121f;
            border-color: #c1121f;
            color: white;
            font-weight: 700;
            min-height: 3rem;
            width: 100%;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #9f0f1a;
            border-color: #9f0f1a;
            color: white;
        }
        .qagent-status {
            padding: 0.9rem 1rem;
            border-radius: 0.4rem;
            font-weight: 700;
            margin: 0.5rem 0 1rem 0;
        }
        .qagent-running { background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd; }
        .qagent-completed { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .qagent-failed { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        .qagent-idle { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
        .qagent-waiting { background: #fef3c7; color: #92400e; border: 1px solid #fbbf24; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "paper_input": "",
        "run_clicked": False,
        "show_outputs": False,
        "current_status": "idle",
        "generated_prompt": "",
        "resolver_summary": None,
        "last_run_result": None,
        "status_snapshot": None,
        "gpt_pro_handoff_manifest": None,
        "gpt_pro_final_selection_manifest": None,
        "batch_id": DEFAULT_BATCH_ID,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def load_status() -> dict:
    if STATUS_PATH.exists():
        try:
            return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "status": "idle",
        "start_time": "",
        "end_time": "",
        "backend": "codex_cli",
        "command": "",
        "return_code": None,
        "error_message": "",
        "estimated_input_tokens": 0,
        "estimated_output_tokens": estimate_output_tokens(OUTPUT_DIR),
        "stdout_summary": "",
        "stderr_summary": "",
        "current_stage": "idle",
        "stages": RUN_STAGES,
        "quality_audit_ok": None,
        "quality_audit_errors": 0,
        "quality_audit_warnings": 0,
        "evidence_preflight_ok": None,
        "hard_review_ok": None,
        "hard_review_candidates": 0,
        "hard_review_passed": 0,
        "candidate_validation_ok": None,
        "candidate_validation_errors": 0,
        "candidate_validation_warnings": 0,
        "model_backend": "codex_cli_logged_in",
        "model_source": "",
        "model": "codex_default",
        "codex_cli_version": "",
        "supports_model_override": None,
    }


def write_status(**updates: object) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    status = st.session_state.status_snapshot or load_status()
    status.update(updates)
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def update_running_stage(placeholder: object, stage: str, **updates: object) -> dict:
    status = write_status(status="running", current_stage=stage, stages=RUN_STAGES, **updates)
    st.session_state.status_snapshot = status
    with placeholder.container():
        status_box(status)
    return status


def failed_run_stage(
    candidate_result: dict,
    candidate_validation: dict,
    candidate_repair_result: dict,
    hard_review: dict,
    final_result: dict,
    audit: dict,
    n: int,
    b: int,
) -> str:
    candidate_attempted = codex_returned_or_timed_out(candidate_result) or candidate_outputs_present(n)
    candidate_ready = candidate_attempted and candidate_validation.get("ok")
    final_ready = final_outputs_complete(n, b) if final_result.get("ok") or final_result.get("timed_out") else False
    if not candidate_attempted:
        return "candidate generation"
    if candidate_repair_result.get("ok") is False:
        return "candidate auto repair"
    if not candidate_ready:
        return "candidate validation"
    if not hard_review.get("ok"):
        return "hard review"
    if not final_ready:
        return "final selection"
    if not audit.get("ok"):
        return "quality audit"
    return "completed"


def codex_returned_or_timed_out(result: dict) -> bool:
    return bool(result.get("ok") or result.get("timed_out"))


def candidate_outputs_present(n: int) -> bool:
    return all((OUTPUT_DIR / f"paper_{index:03d}" / "candidate_questions.json").is_file() for index in range(1, n + 1))


CANDIDATE_STAGE_FILES = [
    "candidate_questions.json",
    "ranked_questions.json",
    "result.json",
    "adjacent_model_pool.json",
    "method_transfer_map.json",
]


def snapshot_candidate_stage_files(n: int) -> dict[Path, bytes | None]:
    snapshot: dict[Path, bytes | None] = {}
    for index in range(1, n + 1):
        paper_dir = OUTPUT_DIR / f"paper_{index:03d}"
        for filename in CANDIDATE_STAGE_FILES:
            path = paper_dir / filename
            snapshot[path] = path.read_bytes() if path.exists() else None
    return snapshot


def restore_candidate_stage_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def gpt_pro_candidate_results_completion(n: int) -> dict:
    results_dir = GPT_PRO_HANDOFF_PATH / "results"
    papers = []
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        path = results_dir / f"{paper_id}.json"
        papers.append({"paper_id": paper_id, "path": path.as_posix(), "present": path.is_file() and path.stat().st_size > 0})
    present = sum(1 for item in papers if item["present"])
    return {"present": present, "required": n, "all_present": present == n, "papers": papers}


def gpt_pro_final_selection_result_present() -> bool:
    path = GPT_PRO_HANDOFF_PATH / "final_selection_result.json"
    return path.is_file() and path.stat().st_size > 0


def final_outputs_completion(n: int, b: int) -> dict:
    papers = []
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        selected_dir = OUTPUT_DIR / f"paper_{index:03d}" / "selected"
        required = expected_selected_for_paper(paper_id, b)
        complete = 0
        if selected_dir.is_dir():
            for qdir in selected_dir.iterdir():
                if qdir.is_dir() and all((qdir / filename).is_file() for filename in REQUIRED_QED_FILES):
                    complete += 1
        papers.append(
            {
                "paper_id": paper_id,
                "complete_selected": complete,
                "required_selected": required,
                "ok": complete >= required,
            }
        )
    all_complete = bool(papers) and all(item["ok"] for item in papers)
    any_complete = any(item["complete_selected"] > 0 for item in papers)
    return {
        "all_complete": all_complete,
        "any_complete": any_complete,
        "papers": papers,
        "failed_papers": [item for item in papers if not item["ok"]],
    }


def final_outputs_complete(n: int, b: int) -> bool:
    return bool(final_outputs_completion(n, b)["all_complete"])


def expected_selected_for_paper(paper_id: str, b: int) -> int:
    data = read_json(PASSED_CANDIDATES_PATH)
    if isinstance(data, dict):
        for paper in data.get("papers", []):
            if isinstance(paper, dict) and paper.get("paper_id") == paper_id:
                ids = paper.get("passed_question_ids", [])
                if isinstance(ids, list):
                    return min(b, len(ids))
    return b


def final_outputs_any_complete(n: int, b: int) -> bool:
    return bool(final_outputs_completion(n, b)["any_complete"])


def final_outputs_failure_message(completion: dict) -> str:
    failed = completion.get("failed_papers", [])
    if not failed:
        return ""
    details = "; ".join(
        f"{item.get('paper_id')}: {item.get('complete_selected', 0)}/{item.get('required_selected', 0)} complete selected questions"
        for item in failed
    )
    return f"Final selection produced partial outputs. Failed/incomplete papers: {details}. Completed papers are still shown below."


def log_snippet(text: str, limit: int = 3000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated; see outputs/{BATCH_ID}/run_log.txt for full log]..."


def write_run_log(result: dict, path: Path = RUN_LOG_PATH, title: str = "QAgent Codex Run Log") -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {title}",
                "",
                f"Command: {result.get('command', '')}",
                f"Backend: {result.get('backend', '')}",
                f"Model: {result.get('model', '')}",
                f"Model source: {result.get('model_source', '')}",
                f"Return code: {result.get('return_code', '')}",
                f"Error message: {result.get('error_message', '')}",
                "",
                "## STDOUT",
                result.get("stdout", ""),
                "",
                "## STDERR",
                result.get("stderr", ""),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_two_phase_run_log(candidate_result: dict, final_result: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_LOG_PATH.write_text(
        "\n".join(
            [
                "# QAgent Two-Phase Codex Run Log",
                "",
                "## Candidate Generation",
                "",
                f"Command: {candidate_result.get('command', '')}",
                f"Backend: {candidate_result.get('backend', '')}",
                f"Model: {candidate_result.get('model', '')}",
                f"Model source: {candidate_result.get('model_source', '')}",
                f"Return code: {candidate_result.get('return_code', '')}",
                f"Error message: {candidate_result.get('error_message', '')}",
                "",
                "### STDOUT",
                candidate_result.get("stdout", ""),
                "",
                "### STDERR",
                candidate_result.get("stderr", ""),
                "",
                "## Final Selection",
                "",
                f"Command: {final_result.get('command', '')}",
                f"Backend: {final_result.get('backend', '')}",
                f"Model: {final_result.get('model', '')}",
                f"Model source: {final_result.get('model_source', '')}",
                f"Return code: {final_result.get('return_code', '')}",
                f"Error message: {final_result.get('error_message', '')}",
                "",
                "### STDOUT",
                final_result.get("stdout", ""),
                "",
                "### STDERR",
                final_result.get("stderr", ""),
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_quality_audit(n: int, a: int, b: int) -> dict:
    result = audit_outputs(OUTPUT_DIR, n=n, a=a, b=b)
    write_audit_result(OUTPUT_DIR, result)
    write_quality_repair_prompt(OUTPUT_DIR, BATCH_ID, result)
    write_quality_audit_guidance(OUTPUT_DIR, result)
    errors = sum(1 for issue in result.issues if issue.severity == "error")
    warnings = sum(1 for issue in result.issues if issue.severity == "warning")
    return {
        "ok": result.ok,
        "errors": errors,
        "warnings": warnings,
        "issues": result.issues,
    }


def write_quality_audit_guidance(output_dir: Path, audit: object) -> None:
    issues = getattr(audit, "issues", [])
    if not issues:
        return
    grouped: dict[Path, list[object]] = {}
    global_issues: list[object] = []
    for issue in issues:
        qdir = selected_question_dir_from_path(output_dir, getattr(issue, "path", ""))
        if qdir is None:
            global_issues.append(issue)
        else:
            grouped.setdefault(qdir, []).append(issue)

    if global_issues:
        for qdir in output_dir.glob("paper_*/selected/*"):
            if qdir.is_dir():
                grouped.setdefault(qdir, []).extend(global_issues)

    for qdir, qissues in grouped.items():
        guidance_path = qdir / "additional_prove_human_help_global.md"
        if not guidance_path.exists():
            continue
        original = guidance_path.read_text(encoding="utf-8")
        guidance_path.write_text(
            replace_quality_guidance_section(original, qissues),
            encoding="utf-8",
        )


def selected_question_dir_from_path(output_dir: Path, issue_path: str) -> Path | None:
    parts = Path(issue_path).parts
    for index, part in enumerate(parts):
        if part == "selected" and index + 1 < len(parts):
            question_id = parts[index + 1]
            paper_id = parts[index - 1] if index > 0 and parts[index - 1].startswith("paper_") else ""
            if paper_id:
                qdir = output_dir / paper_id / "selected" / question_id
                return qdir if qdir.is_dir() else None
    return None


def replace_quality_guidance_section(text: str, issues: list[object]) -> str:
    start = "<!-- QAGENT_QUALITY_AUDIT_GUIDANCE_START -->"
    end = "<!-- QAGENT_QUALITY_AUDIT_GUIDANCE_END -->"
    before = text.split(start, 1)[0].rstrip()
    after = ""
    if end in text:
        after = text.split(end, 1)[1].lstrip()

    lines = [
        start,
        "## Quality Audit Guidance",
        "",
        "The final selected output was generated, but the local audit found items to improve before use.",
        "",
    ]
    for issue in issues:
        lines.append(
            f"- `{getattr(issue, 'severity', 'warning')}` `{getattr(issue, 'path', '')}`: "
            f"{getattr(issue, 'message', '')}"
        )
    lines.extend(["", end])
    section = "\n".join(lines)
    return "\n\n".join(part for part in [before, section, after.rstrip()] if part) + "\n"


def write_source_confidence_guidance(output_dir: Path) -> None:
    for paper_dir in output_dir.glob("paper_*"):
        if not paper_dir.is_dir():
            continue
        profile = read_json(paper_dir / "paper_profile.json")
        if not isinstance(profile, dict):
            continue
        full_text = bool(profile.get("full_text_was_read"))
        confidence = str(profile.get("paper_reading_confidence", "")).lower()
        if full_text and confidence != "low":
            continue
        for qdir in (paper_dir / "selected").glob("*"):
            if not qdir.is_dir():
                continue
            guidance_path = qdir / "additional_prove_human_help_global.md"
            if not guidance_path.exists():
                continue
            text = guidance_path.read_text(encoding="utf-8")
            guidance_path.write_text(
                replace_source_confidence_section(text, confidence or "low"),
                encoding="utf-8",
            )


def replace_source_confidence_section(text: str, confidence: str) -> str:
    start = "<!-- QAGENT_SOURCE_CONFIDENCE_START -->"
    end = "<!-- QAGENT_SOURCE_CONFIDENCE_END -->"
    before = text.split(start, 1)[0].rstrip()
    after = ""
    if end in text:
        after = text.split(end, 1)[1].lstrip()

    section = "\n".join(
        [
            start,
            "## Source Confidence Note",
            "",
            (
                "The full paper text was not completely read or the extraction confidence is low; "
                f"treat this question as low confidence until the PDF/full text is checked by a human. "
                f"Recorded extraction confidence: {confidence}."
            ),
            "",
            end,
        ]
    )
    return "\n\n".join(part for part in [before, section, after.rstrip()] if part) + "\n"


def run_evidence_stage(entries: list[dict], try_online: bool, require_full_text: bool) -> dict:
    result = run_evidence_preflight(
        entries,
        batch_id=BATCH_ID,
        try_online=try_online,
        require_full_text=require_full_text,
    )
    write_evidence_preflight_result(OUTPUT_DIR, result)
    EVIDENCE_PREFLIGHT_LOG_PATH.write_text(evidence_summary_markdown(result), encoding="utf-8")
    failures = [item for item in result.items if not item.ok]
    low_confidence = [
        item
        for item in result.items
        if item.confidence.lower() == "low" or not item.full_text_was_read
    ]
    return {
        "ok": result.ok,
        "failures": failures,
        "low_confidence": low_confidence,
    }


def run_hard_review_stage(n: int, b: int, try_online: bool) -> dict:
    review_limit = max(2 * b, b + 2)
    result = run_hard_review(
        OUTPUT_DIR,
        n=n,
        b=b,
        batch_id=BATCH_ID,
        try_online=try_online,
        review_limit_per_paper=review_limit,
        use_critic=ENABLE_FULL_CANDIDATE_CRITIC,
    )
    write_hard_review_result(OUTPUT_DIR, result)
    write_passed_candidates(OUTPUT_DIR, result)
    HARD_REVIEW_LOG_PATH.write_text(hard_review_summary_markdown(result), encoding="utf-8")
    return {
        "ok": result.ok,
        "candidates_reviewed": result.candidates_reviewed,
        "candidates_passed": result.candidates_passed,
        "papers": result.to_dict().get("papers", []),
    }


def run_candidate_validation_stage(
    n: int,
    a: int,
    b: int,
    allow_quality_warnings: bool = False,
    question_style: str = "specialized",
) -> dict:
    expected_candidates = (a + 1) * b
    normalization = trim_excess_candidate_outputs(OUTPUT_DIR, n=n, expected_candidates=expected_candidates)
    result = validate_candidate_outputs_with_policy(
        OUTPUT_DIR,
        n=n,
        expected_candidates=expected_candidates,
        allow_quality_warnings=allow_quality_warnings,
        question_style=question_style,
    )
    write_candidate_validation_result(OUTPUT_DIR, result)
    write_candidate_validation_markdown(OUTPUT_DIR, result)
    write_candidate_quality_flags(OUTPUT_DIR, n, result)
    candidate_latex_path = write_ranked_candidate_latex(OUTPUT_DIR, n)
    write_candidate_repair_prompt(OUTPUT_DIR, BATCH_ID, result, question_style)
    errors = sum(1 for issue in result.issues if issue.severity == "error")
    warnings = sum(1 for issue in result.issues if issue.severity == "warning")
    return {
        "ok": result.ok,
        "errors": errors,
        "warnings": warnings,
        "normalization": normalization,
        "candidate_latex_path": candidate_latex_path.as_posix(),
    }


def run_candidate_repair_stage(codex_model: str) -> dict:
    if not CANDIDATE_REPAIR_PROMPT_PATH.exists():
        return {
            "ok": None,
            "backend": "codex_cli",
            "command": "codex exec --skip-git-repo-check <candidate repair prompt>",
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "",
        }

    prompt = CANDIDATE_REPAIR_PROMPT_PATH.read_text(encoding="utf-8")
    repair_result = run_codex_cli(prompt, model=codex_model)
    write_run_log(repair_result, CANDIDATE_REPAIR_RUN_LOG_PATH, "QAgent Candidate Repair Run Log")
    return repair_result


def run_paper_literature_survey_stage(codex_model: str, n: int) -> dict:
    local_summary = run_local_paper_literature_survey(OUTPUT_DIR, n=n, try_online=True)
    prompt = build_paper_literature_survey_prompt(OUTPUT_DIR, BATCH_ID, n=n)
    result = run_codex_cli(prompt, model=codex_model)
    write_run_log(result, PAPER_LITERATURE_SURVEY_RUN_LOG_PATH, "QAgent Paper Literature Survey Run Log")
    summary = ensure_paper_literature_survey_outputs(OUTPUT_DIR, n=n, survey_result=result)
    return {
        "ok": True,
        "reviewer_ok": result.get("ok"),
        "local_summary": local_summary,
        "papers_with_valid_survey": summary.get("papers_with_valid_survey", 0),
        "degraded_surveys": summary.get("degraded_surveys", 0),
        "return_code": result.get("return_code"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "error_message": result.get("error_message", ""),
        "backend": result.get("backend", "codex_cli_logged_in"),
    }


def run_novelty_review_stage(codex_model: str, n: int, b: int) -> dict:
    if not ENABLE_CODEX_NOVELTY_REVIEW:
        summary = {
            "ok": True,
            "reviewer_ok": None,
            "strict_novelty_pass": 0,
            "degraded_top_candidates": 0,
            "not_selected_for_ai_review": 0,
            "disabled": True,
            "reason": "Disabled: candidate novelty is checked by candidate-generation self-gates plus hard-review novelty search.",
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "novelty_review_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            **summary,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "",
        }
    prompt = build_novelty_review_prompt(OUTPUT_DIR, BATCH_ID, n=n, b=b)
    result = run_codex_cli(prompt, model=codex_model)
    write_run_log(result, NOVELTY_REVIEW_RUN_LOG_PATH, "QAgent Novelty Review Run Log")
    summary = ensure_novelty_review_outputs(OUTPUT_DIR, n=n, b=b, reviewer_result=result)
    return {
        "ok": True,
        "reviewer_ok": result.get("ok"),
        "strict_novelty_pass": summary.get("strict_novelty_pass", 0),
        "degraded_top_candidates": summary.get("degraded_top_candidates", 0),
        "not_selected_for_ai_review": summary.get("not_selected_for_ai_review", 0),
        "return_code": result.get("return_code"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "error_message": result.get("error_message", ""),
    }


def run_candidate_replacement_stage(
    codex_model: str,
    n: int,
    a: int,
    b: int,
    attempt: int,
    question_style: str,
) -> dict:
    prompt = build_candidate_replacement_prompt(
        OUTPUT_DIR,
        BATCH_ID,
        n=n,
        a=a,
        b=b,
        attempt=attempt,
        question_style=question_style,
    )
    prompt_path = OUTPUT_DIR / f"candidate_replacement_prompt_{attempt}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    result = run_codex_cli(prompt, model=codex_model)
    log_path = OUTPUT_DIR / f"candidate_replacement_run_log_{attempt}.txt"
    write_run_log(result, log_path, f"QAgent Candidate Replacement Run Log Attempt {attempt}")
    result["prompt_path"] = prompt_path.as_posix()
    result["run_log_path"] = log_path.as_posix()
    return result


def hard_review_needs_candidate_replacement(hard_review: dict, b: int, output_dir: Path | None = None) -> bool:
    output_dir = output_dir or OUTPUT_DIR
    for paper in hard_review.get("papers", []) if isinstance(hard_review, dict) else []:
        candidates = paper.get("candidates", []) if isinstance(paper, dict) else []
        paper_id = str(paper.get("paper_id", "")) if isinstance(paper, dict) else ""
        strict_passed = sum(
            1
            for candidate in candidates
            if isinstance(candidate, dict) and bool(candidate.get("passed_final_gate"))
        )
        if any(_replacement_kill_candidate(candidate, output_dir, paper_id) for candidate in candidates if isinstance(candidate, dict)):
            return True
        if strict_passed < b and any(
            _replacement_weak_candidate(candidate, output_dir, paper_id)
            for candidate in candidates
            if isinstance(candidate, dict)
        ):
            return True
    return False


def _replacement_kill_candidate(candidate: dict, output_dir: Path | None = None, paper_id: str = "") -> bool:
    if candidate.get("killed_early"):
        return True
    if str(candidate.get("recommended_action", "")).strip().lower() == "remove":
        return True
    if str(candidate.get("duplicate_risk", "")).strip().lower() == "high":
        return True
    if str(candidate.get("novelty_verdict", "")).strip().lower() in {
        "direct corollary",
        "too close to input theorem",
        "probably already known",
        "likely known",
    }:
        return True
    if str(candidate.get("novelty_review_verdict", "")).strip().lower() in {
        "direct_corollary",
        "too_close_to_input",
        "likely_known",
    }:
        return True
    if output_dir is not None and paper_id:
        question_id = str(candidate.get("question_id", "")).strip()
        if question_id and _candidate_survey_json_kills(output_dir, paper_id, question_id):
            return True
    return False


def _replacement_weak_candidate(candidate: dict, output_dir: Path | None = None, paper_id: str = "") -> bool:
    if candidate.get("passed_final_gate"):
        return False
    if _replacement_kill_candidate(candidate, output_dir, paper_id):
        return True
    if str(candidate.get("critic_verdict", "")).strip().lower() in {"negative", "reject", "remove"}:
        return True
    if str(candidate.get("recommended_action", "")).strip().lower() in {"revise", "remove"}:
        return True
    if str(candidate.get("novelty_verdict", "")).strip().lower() in {"insufficient evidence", "too vague"}:
        return True
    if str(candidate.get("duplicate_risk", "")).strip().lower() in {"medium", "high"}:
        return True
    try:
        return float(candidate.get("review_score", 0) or 0) < 650.0
    except (TypeError, ValueError):
        return True


def _candidate_survey_json_kills(output_dir: Path, paper_id: str, question_id: str) -> bool:
    path = output_dir / paper_id / "candidate_surveys" / f"{question_id}.json"
    if not path.is_file():
        return False
    try:
        survey = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
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
        "too close to input theorem",
        "probably already known",
        "likely known",
        "known theorem",
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


def run_downstream_after_valid_candidates(
    codex_model: str,
    try_online: bool,
    mode: str,
    question_style: str,
    n: int,
    a: int,
    b: int,
) -> dict:
    final_prompt = build_final_selection_prompt(INPUT_PATH, a, b, n, mode, batch_id=BATCH_ID)
    novelty_review = run_novelty_review_stage(codex_model, n=n, b=b)
    hard_review = run_hard_review_stage(n, b=b, try_online=try_online)
    replacement_results: list[dict] = []
    replacement_attempt = 0
    candidate_validation = {"ok": True, "errors": 0, "warnings": 0}
    while (
        hard_review.get("ok")
        and hard_review_needs_candidate_replacement(hard_review, b)
        and replacement_attempt < MAX_CANDIDATE_REPLACEMENT_ATTEMPTS
    ):
        replacement_attempt += 1
        replacement_result = run_candidate_replacement_stage(
            codex_model,
            n=n,
            a=a,
            b=b,
            attempt=replacement_attempt,
            question_style=question_style,
        )
        replacement_results.append(replacement_result)
        if not codex_returned_or_timed_out(replacement_result):
            break
        candidate_validation = run_candidate_validation_stage(
            n,
            a,
            b,
            allow_quality_warnings=False,
            question_style=question_style,
        )
        if not candidate_validation.get("ok"):
            break
        novelty_review = run_novelty_review_stage(codex_model, n=n, b=b)
        hard_review = run_hard_review_stage(n, b=b, try_online=try_online)
    final_result = (
        run_codex_cli(final_prompt, model=codex_model)
        if hard_review["ok"] and candidate_validation.get("ok")
        else {
            "ok": None,
            "backend": "codex_cli",
            "command": "codex exec --skip-git-repo-check <final prompt>",
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "",
        }
    )
    if final_result["ok"] is not None:
        write_run_log(final_result, FINAL_RUN_LOG_PATH, "QAgent Final Selection Run Log")
    final_completion = final_outputs_completion(n, b)
    final_stage_ok = bool(final_completion["all_complete"])
    final_stage_partial = bool(final_completion["any_complete"] and not final_completion["all_complete"])
    if final_stage_ok or final_stage_partial:
        patch_selected_metadata_backend_info(OUTPUT_DIR)
        write_source_confidence_guidance(OUTPUT_DIR)
    audit = run_quality_audit(n, a, b) if (final_stage_ok or final_stage_partial) else {"ok": None, "errors": 0, "warnings": 0}
    return {
        "novelty_review": novelty_review,
        "hard_review": hard_review,
        "candidate_validation": candidate_validation,
        "replacement_results": replacement_results,
        "final_result": final_result,
        "final_stage_ok": final_stage_ok,
        "final_stage_partial": final_stage_partial,
        "final_completion": final_completion,
        "audit": audit,
    }


def run_candidate_repair(
    codex_model: str,
    try_online: bool,
    mode: str,
    question_style: str,
    n: int,
    a: int,
    b: int,
) -> dict:
    if not CANDIDATE_REPAIR_PROMPT_PATH.exists():
        return {"ok": False, "error_message": "No candidate_repair_prompt.md exists for this batch."}

    prompt = CANDIDATE_REPAIR_PROMPT_PATH.read_text(encoding="utf-8")
    repair_result = run_codex_cli(prompt, model=codex_model)
    write_run_log(repair_result, CANDIDATE_REPAIR_RUN_LOG_PATH, "QAgent Candidate Repair Run Log")
    repair_runnable = codex_returned_or_timed_out(repair_result)
    candidate_validation = (
        run_candidate_validation_stage(n, a, b, allow_quality_warnings=True, question_style=question_style)
        if repair_runnable
        else {"ok": None, "errors": 0, "warnings": 0}
    )
    downstream = (
        run_downstream_after_valid_candidates(codex_model, try_online, mode, question_style, n, a, b)
        if repair_runnable and candidate_validation["ok"]
        else {
            "novelty_review": {"ok": None, "strict_novelty_pass": 0, "degraded_top_candidates": 0},
            "hard_review": {"ok": None, "candidates_reviewed": 0, "candidates_passed": 0},
            "final_result": {"ok": None, "stdout": "", "stderr": "", "error_message": ""},
            "final_stage_ok": False,
            "final_stage_partial": False,
            "final_completion": final_outputs_completion(n, b),
            "audit": {"ok": None, "errors": 0, "warnings": 0},
        }
    )
    final_result = downstream["final_result"]
    audit = downstream["audit"]
    final_stage_ok = bool(downstream.get("final_stage_ok"))
    final_stage_partial = bool(downstream.get("final_stage_partial"))
    final_completion = downstream.get("final_completion") or final_outputs_completion(n, b)
    completed = repair_runnable and candidate_validation["ok"] and downstream["hard_review"]["ok"] and final_stage_ok
    current_stage = "completed"
    if not completed:
        if not repair_runnable:
            current_stage = "candidate auto repair"
        elif not candidate_validation["ok"]:
            current_stage = "candidate validation"
        elif not downstream["hard_review"]["ok"]:
            current_stage = "hard review"
        elif final_stage_partial or not final_stage_ok:
            current_stage = "final selection"
        else:
            current_stage = "quality audit"
    status = write_status(
        status="completed" if completed else "failed",
        end_time=now_iso(),
        backend=final_result.get("backend") or repair_result.get("backend", "codex_cli_logged_in"),
        command="codex exec --skip-git-repo-check <candidate repair prompt>",
        return_code=final_result.get("return_code") if final_result.get("return_code") is not None else repair_result.get("return_code"),
        error_message=(repair_result.get("error_message") if not repair_runnable else "")
        or (f"Candidate repair completed but validation still failed; inspect outputs/{BATCH_ID}/candidate_validation.json." if repair_runnable and not candidate_validation["ok"] else "")
        or (f"Hard candidate review failed; inspect outputs/{BATCH_ID}/hard_review.json." if candidate_validation["ok"] and not downstream["hard_review"]["ok"] else "")
        or (final_outputs_failure_message(final_completion) if final_stage_partial else "")
        or (final_outputs_failure_message(final_completion) if final_result.get("ok") and not final_stage_ok else "")
        or (final_result.get("error_message", "") if not final_stage_ok else ""),
        estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
        stdout_summary=log_snippet(repair_result.get("stdout", "")),
        stderr_summary=log_snippet(repair_result.get("stderr", "")),
        current_stage=current_stage,
        stages=RUN_STAGES,
        candidate_validation_ok=candidate_validation["ok"],
        candidate_validation_errors=candidate_validation["errors"],
        candidate_validation_warnings=candidate_validation.get("warnings", 0),
        gpt_pro_mode=expert_backend.startswith("gpt_pro_web_handoff"),
        gpt_pro_policy=(
            "required" if expert_backend == "gpt_pro_web_handoff_required"
            else "optional" if expert_backend == "gpt_pro_web_handoff_optional"
            else "off"
        ),
        gpt_pro_used=(
            expert_backend.startswith("gpt_pro_web_handoff")
            and gpt_pro_candidate_results_completion(n)["present"] > 0
        ),
        gpt_pro_candidate_results_present=(
            gpt_pro_candidate_results_completion(n)["present"] if expert_backend.startswith("gpt_pro_web_handoff") else 0
        ),
        gpt_pro_candidate_results_required=(n if expert_backend.startswith("gpt_pro_web_handoff") else 0),
        gpt_pro_final_selection_result_present=(
            gpt_pro_final_selection_result_present() if expert_backend.startswith("gpt_pro_web_handoff") else False
        ),
        hard_review_ok=downstream["hard_review"]["ok"],
        hard_review_candidates=downstream["hard_review"]["candidates_reviewed"],
        hard_review_passed=downstream["hard_review"]["candidates_passed"],
        quality_audit_ok=audit["ok"],
        quality_audit_errors=audit["errors"],
        quality_audit_warnings=audit["warnings"],
    )
    st.session_state.status_snapshot = status
    st.session_state.current_status = status["status"]
    st.session_state.show_outputs = bool(final_stage_ok or final_stage_partial)
    return {"ok": status["status"] == "completed", "error_message": status.get("error_message", "")}


def run_repair(codex_model: str, n: int, a: int, b: int) -> dict:
    if not REPAIR_PROMPT_PATH.exists():
        return {"ok": False, "error_message": "No repair_prompt.md exists for this batch."}

    prompt = REPAIR_PROMPT_PATH.read_text(encoding="utf-8")
    result = run_codex_cli(prompt, model=codex_model)
    write_run_log(result, REPAIR_RUN_LOG_PATH, "QAgent Repair Run Log")
    if result["ok"]:
        patch_selected_metadata_backend_info(OUTPUT_DIR)
        write_source_confidence_guidance(OUTPUT_DIR)
        audit = run_quality_audit(n, a, b)
    else:
        audit = {"ok": None, "errors": 0, "warnings": 0}
    completed = result["ok"]
    status = write_status(
        status="completed" if completed else "failed",
        end_time=now_iso(),
        backend=result.get("backend", "codex_cli_logged_in"),
        command=result.get("command", "codex exec --skip-git-repo-check <repair prompt>"),
        return_code=result.get("return_code"),
        error_message=result.get("error_message")
        or "",
        estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
        stdout_summary=log_snippet(result.get("stdout", "")),
        stderr_summary=log_snippet(result.get("stderr", "")),
        current_stage="completed" if completed else "quality auto repair",
        stages=RUN_STAGES,
        quality_audit_ok=audit["ok"],
        quality_audit_errors=audit["errors"],
        quality_audit_warnings=audit["warnings"],
    )
    st.session_state.status_snapshot = status
    st.session_state.current_status = status["status"]
    st.session_state.show_outputs = True
    return {"ok": result["ok"] and audit["ok"], "error_message": status.get("error_message", "")}


def status_box(status: dict) -> None:
    value = status.get("status", "idle")
    css = {
        "running": "qagent-running",
        "completed": "qagent-completed",
        "failed": "qagent-failed",
        "waiting_gpt_pro_candidates": "qagent-waiting",
        "waiting_gpt_pro_final_selection": "qagent-waiting",
        "idle": "qagent-idle",
    }.get(value, "qagent-idle")
    st.markdown(f'<div class="qagent-status {css}">{value}</div>', unsafe_allow_html=True)
    if status.get("current_stage"):
        st.caption(f"Current stage: {status.get('current_stage')}")
    if value == "waiting_gpt_pro_candidates":
        st.warning(
            "Waiting for GPT Pro candidate/survey results. Copy the paper prompts into GPT Pro, "
            "save JSON replies under `gpt_pro_handoff/results/paper_###.json`, then click Run Agent again."
        )
    if value == "waiting_gpt_pro_final_selection":
        st.warning(
            "Waiting for GPT Pro final-selection result. Copy the final-selection prompt into GPT Pro, "
            "save the JSON reply as `gpt_pro_handoff/final_selection_result.json`, then click Run Agent again."
        )
    if status.get("gpt_pro_used") is False:
        policy = status.get("gpt_pro_policy", "off")
        if policy == "optional":
            st.info("GPT Pro handoff was enabled but no GPT Pro result files were available; this run continued with Codex.")
        elif policy == "required":
            st.info("GPT Pro has not been used yet; required result files are still missing.")
        else:
            st.info("GPT Pro was not used in this run.")
    if value == "failed" and status.get("error_message"):
        st.error(status["error_message"])
        details = "\n\n".join(
            part
            for part in [
                status.get("stderr_summary", ""),
                status.get("stdout_summary", ""),
            ]
            if part
        )
        if details:
            st.code(details)
    if status.get("model_source"):
        st.caption(
            f"Model backend: {status.get('model_backend', 'unknown')} | "
            f"model: {status.get('model', 'unknown')} | source: {status.get('model_source')}"
        )
        if status.get("codex_cli_version"):
            st.caption(
                f"Codex CLI: {status.get('codex_cli_version')} | "
                f"--model support: {status.get('supports_model_override')}"
            )
    if status.get("quality_audit_ok") is False:
        st.warning(
            f"Outputs generated; quality audit guidance found {status.get('quality_audit_errors', 0)} errors and "
            f"{status.get('quality_audit_warnings', 0)} warnings. See guidance tabs and quality_audit.json."
        )
    elif status.get("quality_audit_ok") is True:
        warning_count = status.get("quality_audit_warnings", 0)
        if warning_count:
            st.info(f"Quality audit passed with {warning_count} warnings.")
        else:
            st.success("Quality audit passed.")
    if status.get("evidence_preflight_ok") is False:
        st.error("Evidence preflight failed before generation.")
    if status.get("candidate_validation_ok") is False:
        st.error(f"Candidate validation failed with {status.get('candidate_validation_errors', 0)} errors.")
    elif status.get("candidate_validation_ok") is True and status.get("candidate_validation_warnings", 0):
        st.info(f"Candidate validation passed with {status.get('candidate_validation_warnings', 0)} quality warnings.")
    if status.get("hard_review_ok") is False:
        st.error("Hard candidate review failed after generation.")
    elif status.get("hard_review_ok") is True:
        st.info(
            f"Hard candidate review completed for {status.get('hard_review_candidates', 0)} candidates; "
            f"{status.get('hard_review_passed', 0)} allowed for final selection."
        )
    if status.get("candidate_replacement_attempts"):
        st.info(
            f"Candidate replacement attempts: {status.get('candidate_replacement_attempts')} / "
            f"{status.get('candidate_replacement_max_attempts', MAX_CANDIDATE_REPLACEMENT_ATTEMPTS)}."
        )


def render_stage_progress(status: dict) -> None:
    current = status.get("current_stage", "idle")
    st.caption("Run stages")
    for stage in RUN_STAGES:
        if status.get("status") == "completed":
            marker = "done"
        elif status.get("status") == "failed" and stage == current:
            marker = "failed"
        elif stage == current:
            marker = "running"
        else:
            marker = "pending"
        st.write(f"- `{marker}` {stage}")


def render_sidebar(markdown: str) -> tuple[str, str, int, int, int, bool, bool, str, str, str]:
    st.sidebar.header("Run Controls")
    batch_id = safe_batch_id(
        st.sidebar.text_input(
            "Batch ID",
            value=st.session_state.batch_id,
            help="Outputs go to outputs/<batch_id> and normalized input goes to data/<batch_id>.md.",
        )
    )
    st.session_state.batch_id = batch_id
    st.sidebar.caption(f"Output directory: outputs/{batch_id}")
    mode_label = st.sidebar.selectbox(
        "Mode",
        ["Deep Mode (recommended for quality)", "Batch Mode (fast screening)"],
        index=0,
    )
    mode = "deep" if mode_label.startswith("Deep") else "batch"
    question_style_label = st.sidebar.selectbox(
        "Question style",
        ["General research style", "Specialized transfer-pattern style"],
        index=0,
        help="Independent from Deep/Batch mode. General is freer; specialized uses transfer-pattern examples.",
    )
    question_style = "general" if question_style_label.startswith("General") else "specialized"
    if mode == "deep":
        n = st.sidebar.number_input("Number of input papers n", min_value=1, max_value=10, value=1, step=1)
    else:
        n = st.sidebar.number_input("Number of input papers n", min_value=11, max_value=60, value=11, step=1)
    a = st.sidebar.slider("Refinement rounds a", 1, 6, 2)
    b = st.sidebar.slider("Final questions per paper b", 1, 10, 3)
    initial_count = (a + 1) * b
    st.sidebar.metric("Initial candidate questions per paper", initial_count)
    st.sidebar.metric("Total initial candidate questions", n * initial_count)
    st.sidebar.metric("Total final selected questions", n * b)
    st.sidebar.caption(
        "Each paper first generates (a+1)*b candidate questions. Each refinement round removes b weaker "
        "questions. After a rounds, b questions remain."
    )
    st.sidebar.warning("For high-quality theorem-level questions, use Deep Mode. Batch Mode is only for rough screening.")
    try_online = st.sidebar.checkbox("Try to identify/enrich papers online", value=True)
    require_full_text = st.sidebar.checkbox(
        "Prefer downloaded PDF full text before generation",
        value=mode == "deep",
        help="Recommended for Deep Mode. QAgent will strongly try PDF/full-text extraction; if unavailable, it continues and marks the paper as low confidence.",
    )

    st.sidebar.header("Model Backend")
    backend_label = st.sidebar.selectbox(
        "Backend",
        ["Codex CLI logged-in account (no API)", "OpenAI API (not enabled yet)"],
        index=0,
    )
    if backend_label.startswith("OpenAI API"):
        st.sidebar.warning("API mode is planned but disabled in this no-API build. Using Codex CLI instead.")
    expert_backend_label = st.sidebar.selectbox(
        "External expert mode",
        [
            "Codex logged-in account only",
            "GPT Pro web handoff optional",
            "GPT Pro web handoff required",
        ],
        index=0,
        help=(
            "Codex uses the logged-in Codex CLI account/config. GPT Pro web handoff creates prompts for manual GPT Pro web use; "
            "QAgent does not automate the GPT Pro web UI."
        ),
    )
    if expert_backend_label == "GPT Pro web handoff optional":
        expert_backend = "gpt_pro_web_handoff_optional"
    elif expert_backend_label == "GPT Pro web handoff required":
        expert_backend = "gpt_pro_web_handoff_required"
    else:
        expert_backend = "codex_only"
    if expert_backend.startswith("gpt_pro_web_handoff"):
        st.sidebar.info("GPT Pro handoff will create prompt files under outputs/<batch_id>/gpt_pro_handoff.")
        if expert_backend.endswith("optional"):
            st.sidebar.caption("Optional mode continues with Codex if GPT Pro JSON results are missing.")
        else:
            st.sidebar.caption("Required mode pauses until GPT Pro JSON results are saved.")
    codex_model = st.sidebar.text_input(
        "Codex CLI model override",
        value="gpt-5.5",
        placeholder="gpt-5.5 or gpt-5.5-pro; leave blank for Codex default",
        help="QED-style default is gpt-5.5 with Codex search and xhigh reasoning. Clear this field to use the logged-in Codex CLI default/config.",
    ).strip()
    meta = codex_backend_metadata(codex_model)
    st.sidebar.caption(f"Model source: {meta['model_source']}")
    st.sidebar.caption(f"Codex search: {meta['search_enabled']} | reasoning: {meta['reasoning_effort']}")
    diagnostics = collect_backend_diagnostics(codex_model)
    if diagnostics.codex_cli_available:
        st.sidebar.success(f"Codex CLI: {diagnostics.codex_cli_version}")
    else:
        st.sidebar.error(f"Codex CLI unavailable: {diagnostics.error_message}")
    if codex_model and not diagnostics.supports_model_override:
        st.sidebar.warning("This Codex CLI help output did not advertise --model support.")

    st.sidebar.header("PDF Reader")
    pypdf_available = importlib.util.find_spec("pypdf") is not None
    pymupdf_available = importlib.util.find_spec("fitz") is not None
    windows_fallback = Path("/mnt/c/tools/Python313/python.exe").exists() or Path("C:/tools/Python313/python.exe").exists()
    if pypdf_available or pymupdf_available:
        available = [
            name
            for name, ok in [("pypdf", pypdf_available), ("PyMuPDF", pymupdf_available)]
            if ok
        ]
        st.sidebar.success("PDF extraction: " + ", ".join(available))
    elif windows_fallback:
        st.sidebar.warning("PDF extraction: using Windows Python fallback. Restart Streamlit after code updates.")
    else:
        st.sidebar.error("PDF extraction unavailable: install pypdf or PyMuPDF in the Python running Streamlit.")

    st.sidebar.header("Token Estimate")
    input_tokens = estimate_tokens(markdown)
    output_tokens = estimate_output_tokens(OUTPUT_DIR) if OUTPUT_DIR.exists() else 0
    st.sidebar.metric("Estimated input tokens", f"{input_tokens:,}")
    st.sidebar.metric("Estimated output tokens", f"{output_tokens:,}")
    st.sidebar.metric("Total estimated tokens", f"{input_tokens + output_tokens:,}")
    st.sidebar.caption("Actual token usage is unavailable in no-API mode. This is only a rough estimate.")

    return mode, question_style, int(n), a, b, try_online, require_full_text, codex_model, batch_id, expert_backend


def resolver_summary(resolved: dict) -> dict:
    entries = resolved["entries"]
    return {
        "detected_entries": len(entries),
        "high": sum(1 for entry in entries if entry["match_confidence"] == "high"),
        "medium": sum(1 for entry in entries if entry["match_confidence"] == "medium"),
        "low": sum(1 for entry in entries if entry["match_confidence"] == "low"),
        "warnings": resolved["warnings"],
    }


def write_resolver_log(resolved: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Resolver Log", ""]
    lines.extend(f"- {line}" for line in resolved["resolver_log"])
    if resolved["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in resolved["warnings"])
    RESOLVER_LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def handle_run(
    markdown: str,
    mode: str,
    question_style: str,
    n: int,
    a: int,
    b: int,
    try_online: bool,
    require_full_text: bool,
    codex_model: str,
    expert_backend: str,
    placeholder: st.delta_generator.DeltaGenerator,
) -> None:
    st.session_state.run_clicked = True
    backend_meta = codex_backend_metadata(codex_model)
    backend_diagnostics = collect_backend_diagnostics(codex_model)
    write_backend_info(OUTPUT_DIR, backend_diagnostics)
    write_backend_info_markdown(OUTPUT_DIR, backend_diagnostics)
    st.session_state.current_status = "running"
    st.session_state.status_snapshot = write_status(
        status="running",
        current_stage="resolving papers",
        stages=RUN_STAGES,
        model_backend=backend_meta["backend"],
        model_source=backend_meta["model_source"],
        model=backend_meta["model"],
        codex_cli_version=backend_diagnostics.codex_cli_version,
        supports_model_override=backend_diagnostics.supports_model_override,
    )
    resolved = resolve_paper_entries(markdown, try_online=try_online)
    summary = resolver_summary(resolved)
    st.session_state.resolver_summary = summary
    st.session_state.generated_prompt = build_candidate_generation_prompt(
        INPUT_PATH,
        a,
        b,
        n,
        mode,
        batch_id=BATCH_ID,
        question_style=question_style,
    )
    st.session_state.show_outputs = False

    write_resolver_log(resolved)
    if summary["detected_entries"] != n:
        st.session_state.status_snapshot = write_status(
            status="failed",
            start_time=now_iso(),
            end_time=now_iso(),
            backend="input_resolver",
            command="resolve_paper_entries",
            return_code=None,
            error_message=f"Detected {summary['detected_entries']} paper entries. Expected exactly {n}.",
            estimated_input_tokens=estimate_tokens(markdown),
            estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
            stdout_summary="",
            stderr_summary="",
            current_stage="resolving papers",
            stages=RUN_STAGES,
            model_backend=backend_meta["backend"],
            model_source=backend_meta["model_source"],
            model=backend_meta["model"],
            codex_cli_version=backend_diagnostics.codex_cli_version,
            supports_model_override=backend_diagnostics.supports_model_override,
        )
        st.session_state.current_status = "failed"
        return

    INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    INPUT_PATH.write_text(resolved["normalized_markdown"], encoding="utf-8")

    st.session_state.status_snapshot = write_status(
        status="running",
        current_stage="evidence preflight",
        evidence_preflight_ok=None,
    )
    with placeholder.container():
        status_box(st.session_state.status_snapshot)

    evidence = run_evidence_stage(
        resolved["entries"],
        try_online=try_online,
        require_full_text=require_full_text,
    )
    if not evidence["ok"]:
        failed = write_status(
            status="failed",
            start_time=now_iso(),
            end_time=now_iso(),
            backend="evidence_preflight",
            command="run_evidence_preflight",
            return_code=None,
            error_message=f"Evidence preflight failed; inspect outputs/{BATCH_ID}/evidence_preflight.json.",
            estimated_input_tokens=estimate_tokens(markdown),
            estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
            stdout_summary="",
            stderr_summary="",
            current_stage="evidence preflight",
            stages=RUN_STAGES,
            evidence_preflight_ok=False,
            model_backend=backend_meta["backend"],
            model_source=backend_meta["model_source"],
            model=backend_meta["model"],
            codex_cli_version=backend_diagnostics.codex_cli_version,
            supports_model_override=backend_diagnostics.supports_model_override,
        )
        st.session_state.status_snapshot = failed
        st.session_state.current_status = "failed"
        with placeholder.container():
            status_box(failed)
        return

    update_running_stage(placeholder, "paper literature survey")
    paper_survey = run_paper_literature_survey_stage(codex_model, n=n)

    if expert_backend.startswith("gpt_pro_web_handoff"):
        handoff_manifest = write_gpt_pro_handoff(OUTPUT_DIR, BATCH_ID, n, a, b)
        st.session_state.gpt_pro_handoff_manifest = handoff_manifest
        candidate_handoff = gpt_pro_candidate_results_completion(n)
        if expert_backend == "gpt_pro_web_handoff_required" and not candidate_handoff["all_present"]:
            waiting = write_status(
                status="waiting_gpt_pro_candidates",
                start_time=now_iso(),
                end_time="",
                backend="gpt_pro_web_handoff",
                command="manual GPT Pro web handoff",
                return_code=None,
                error_message="",
                estimated_input_tokens=estimate_tokens(resolved["normalized_markdown"]),
                estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
                stdout_summary="",
                stderr_summary="",
                current_stage="waiting for GPT Pro candidate results",
                stages=RUN_STAGES,
                evidence_preflight_ok=True,
                gpt_pro_mode=True,
                gpt_pro_used=False,
                gpt_pro_policy="required",
                gpt_pro_candidate_results_present=candidate_handoff["present"],
                gpt_pro_candidate_results_required=candidate_handoff["required"],
                gpt_pro_handoff_dir=GPT_PRO_HANDOFF_PATH.as_posix(),
                model_backend=backend_meta["backend"],
                model_source=backend_meta["model_source"],
                model=backend_meta["model"],
                codex_cli_version=backend_diagnostics.codex_cli_version,
                supports_model_override=backend_diagnostics.supports_model_override,
            )
            st.session_state.status_snapshot = waiting
            st.session_state.current_status = "waiting_gpt_pro_candidates"
            with placeholder.container():
                status_box(waiting)
            return

    candidate_prompt = build_candidate_generation_prompt(
        INPUT_PATH,
        a,
        b,
        n,
        mode,
        batch_id=BATCH_ID,
        question_style=question_style,
    )
    final_prompt = build_final_selection_prompt(INPUT_PATH, a, b, n, mode, batch_id=BATCH_ID)
    paper_survey_prompt = build_paper_literature_survey_prompt(OUTPUT_DIR, BATCH_ID, n=n)
    st.session_state.generated_prompt = (
        "===== PAPER LITERATURE SURVEY PROMPT =====\n\n"
        + paper_survey_prompt
        + "\n\n===== CANDIDATE GENERATION PROMPT =====\n\n"
        + candidate_prompt
        + "\n\n===== FINAL SELECTION PROMPT =====\n\n"
        + final_prompt
    )
    running = write_status(
        status="running",
        start_time=now_iso(),
        end_time="",
        backend="codex_cli",
        command='codex exec --skip-git-repo-check "<paper survey prompt>" then "<candidate prompt>" then "<final prompt>"',
        return_code=None,
        error_message="",
        estimated_input_tokens=estimate_tokens(resolved["normalized_markdown"]),
        estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
        stdout_summary=log_snippet("## Paper literature survey\n" + paper_survey.get("stdout", "")),
        stderr_summary=log_snippet("## Paper literature survey\n" + paper_survey.get("stderr", "")),
        current_stage="candidate generation",
        stages=RUN_STAGES,
        evidence_preflight_ok=True,
        model_backend=backend_meta["backend"],
        model_source=backend_meta["model_source"],
        model=backend_meta["model"],
        codex_cli_version=backend_diagnostics.codex_cli_version,
        supports_model_override=backend_diagnostics.supports_model_override,
    )
    st.session_state.status_snapshot = running
    with placeholder.container():
        status_box(running)

    candidate_result = run_codex_cli(candidate_prompt, model=codex_model)
    write_run_log(candidate_result, CANDIDATE_RUN_LOG_PATH, "QAgent Candidate Generation Run Log")
    candidate_runnable = codex_returned_or_timed_out(candidate_result) or candidate_outputs_present(n)
    if candidate_runnable:
        update_running_stage(placeholder, "candidate validation")
    candidate_validation = (
        run_candidate_validation_stage(n, a, b, question_style=question_style)
        if candidate_runnable
        else {"ok": None, "errors": 0, "warnings": 0}
    )
    candidate_repair_result = {
        "ok": None,
        "backend": "codex_cli",
        "command": "codex exec --skip-git-repo-check <candidate repair prompt>",
        "return_code": None,
        "stdout": "",
        "stderr": "",
        "error_message": "",
    }
    repair_attempt = 0
    while candidate_runnable and not candidate_validation["ok"] and repair_attempt < MAX_CANDIDATE_REPAIR_ATTEMPTS:
        repair_attempt += 1
        update_running_stage(
            placeholder,
            "candidate auto repair",
            candidate_repair_attempt=repair_attempt,
            candidate_repair_max_attempts=MAX_CANDIDATE_REPAIR_ATTEMPTS,
        )
        candidate_repair_result = run_candidate_repair_stage(codex_model)
        candidate_repair_runnable = codex_returned_or_timed_out(candidate_repair_result)
        if not candidate_repair_runnable:
            break
        update_running_stage(placeholder, "candidate validation")
        candidate_validation = run_candidate_validation_stage(
            n,
            a,
            b,
            allow_quality_warnings=False,
            question_style=question_style,
        )

    candidate_stage_ok = bool(candidate_runnable and candidate_validation["ok"])
    if candidate_stage_ok:
        update_running_stage(placeholder, "novelty search")
    novelty_review = (
        run_novelty_review_stage(codex_model, n=n, b=b)
        if candidate_stage_ok
        else {"ok": None, "strict_novelty_pass": 0, "degraded_top_candidates": 0}
    )
    if candidate_stage_ok:
        update_running_stage(placeholder, "hard review")
    hard_review = (
        run_hard_review_stage(n, b=b, try_online=try_online)
        if candidate_stage_ok
        else {"ok": None, "candidates_reviewed": 0, "candidates_passed": 0}
    )
    replacement_attempt = 0
    replacement_results: list[dict] = []
    while (
        candidate_stage_ok
        and hard_review.get("ok")
        and hard_review_needs_candidate_replacement(hard_review, b)
        and replacement_attempt < MAX_CANDIDATE_REPLACEMENT_ATTEMPTS
    ):
        replacement_attempt += 1
        candidate_snapshot = snapshot_candidate_stage_files(n)
        update_running_stage(
            placeholder,
            "candidate replacement",
            candidate_replacement_attempt=replacement_attempt,
            candidate_replacement_max_attempts=MAX_CANDIDATE_REPLACEMENT_ATTEMPTS,
        )
        replacement_result = run_candidate_replacement_stage(
            codex_model,
            n=n,
            a=a,
            b=b,
            attempt=replacement_attempt,
            question_style=question_style,
        )
        replacement_results.append(replacement_result)
        if not codex_returned_or_timed_out(replacement_result):
            break

        update_running_stage(placeholder, "candidate validation")
        candidate_validation = run_candidate_validation_stage(
            n,
            a,
            b,
            allow_quality_warnings=False,
            question_style=question_style,
        )
        candidate_stage_ok = bool(candidate_validation["ok"])
        if not candidate_stage_ok:
            restore_candidate_stage_files(candidate_snapshot)
            candidate_validation = run_candidate_validation_stage(
                n,
                a,
                b,
                allow_quality_warnings=False,
                question_style=question_style,
            )
            candidate_stage_ok = bool(candidate_validation["ok"])
            break

        update_running_stage(placeholder, "novelty search")
        novelty_review = run_novelty_review_stage(codex_model, n=n, b=b)
        update_running_stage(placeholder, "hard review")
        hard_review = run_hard_review_stage(n, b=b, try_online=try_online)

    if candidate_stage_ok and hard_review["ok"]:
        if expert_backend.startswith("gpt_pro_web_handoff"):
            final_handoff = write_gpt_pro_final_selection_handoff(OUTPUT_DIR, BATCH_ID, n, b)
            st.session_state.gpt_pro_final_selection_manifest = final_handoff
            if expert_backend == "gpt_pro_web_handoff_required" and not gpt_pro_final_selection_result_present():
                waiting = write_status(
                    status="waiting_gpt_pro_final_selection",
                    end_time="",
                    backend="gpt_pro_web_handoff",
                    command="manual GPT Pro web handoff final selection",
                    return_code=None,
                    error_message="",
                    estimated_input_tokens=estimate_tokens(resolved["normalized_markdown"]),
                    estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
                    stdout_summary="",
                    stderr_summary="",
                    current_stage="waiting for GPT Pro final-selection result",
                    stages=RUN_STAGES,
                    evidence_preflight_ok=True,
                    hard_review_ok=hard_review["ok"],
                    hard_review_candidates=hard_review["candidates_reviewed"],
                    hard_review_passed=hard_review["candidates_passed"],
                    candidate_validation_ok=candidate_validation["ok"],
                    candidate_validation_errors=candidate_validation["errors"],
                    candidate_validation_warnings=candidate_validation.get("warnings", 0),
                    gpt_pro_mode=True,
                    gpt_pro_used=True,
                    gpt_pro_policy="required",
                    gpt_pro_final_selection_result_present=False,
                    gpt_pro_handoff_dir=GPT_PRO_HANDOFF_PATH.as_posix(),
                    model_backend=backend_meta["backend"],
                    model_source=backend_meta["model_source"],
                    model=backend_meta["model"],
                    codex_cli_version=backend_diagnostics.codex_cli_version,
                    supports_model_override=backend_diagnostics.supports_model_override,
                )
                st.session_state.status_snapshot = waiting
                st.session_state.current_status = "waiting_gpt_pro_final_selection"
                with placeholder.container():
                    status_box(waiting)
                return
        update_running_stage(placeholder, "final selection")
    final_result = (
        run_codex_cli(final_prompt, model=codex_model)
        if candidate_stage_ok and hard_review["ok"]
        else {
            "ok": None,
            "backend": "codex_cli",
            "command": "codex exec --skip-git-repo-check <final prompt>",
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "",
        }
    )
    final_completion = final_outputs_completion(n, b)
    final_stage_ok = bool(final_completion["all_complete"])
    final_stage_partial = bool(final_completion["any_complete"] and not final_completion["all_complete"])
    if final_result["ok"] is not None:
        write_run_log(final_result, FINAL_RUN_LOG_PATH, "QAgent Final Selection Run Log")
    write_two_phase_run_log(candidate_result, final_result)
    if final_stage_ok or final_stage_partial:
        patch_selected_metadata_backend_info(OUTPUT_DIR)
        write_source_confidence_guidance(OUTPUT_DIR)
        if final_stage_ok:
            update_running_stage(placeholder, "quality audit")
    audit = run_quality_audit(n, a, b) if (final_stage_ok or final_stage_partial) else {"ok": None, "errors": 0, "warnings": 0}
    completed_status = (
        "completed"
        if candidate_stage_ok and hard_review["ok"] and final_stage_ok
        else "failed"
    )
    return_code = (
        final_result.get("return_code")
        if final_result.get("return_code") is not None
        else candidate_repair_result.get("return_code")
        if candidate_repair_result.get("return_code") is not None
        else candidate_result.get("return_code")
    )
    status = write_status(
        status=completed_status,
        end_time=now_iso(),
        backend=final_result.get("backend") or candidate_result.get("backend"),
        command='codex exec --skip-git-repo-check "<paper survey prompt>"; codex exec --skip-git-repo-check "<candidate prompt>"; codex exec --skip-git-repo-check "<final prompt>"',
        return_code=return_code,
        error_message=(
            candidate_result["error_message"] if not candidate_stage_ok and not candidate_outputs_present(n) else ""
        )
        or (candidate_repair_result.get("error_message", "") if candidate_runnable and not candidate_stage_ok else "")
        or (f"Candidate validation failed after automatic repair; inspect outputs/{BATCH_ID}/candidate_validation.json." if candidate_runnable and not candidate_validation["ok"] else "")
        or (f"Hard candidate review failed; inspect outputs/{BATCH_ID}/hard_review.json." if candidate_stage_ok and not hard_review["ok"] else "")
        or (final_outputs_failure_message(final_completion) if final_stage_partial else "")
        or (final_outputs_failure_message(final_completion) if final_result.get("ok") and not final_stage_ok else "")
        or (final_result.get("error_message", "") if hard_review["ok"] and not final_stage_ok else ""),
        estimated_output_tokens=estimate_output_tokens(OUTPUT_DIR),
        stdout_summary=log_snippet(
            "## Paper literature survey\n"
            + paper_survey.get("stdout", "")
            + "\n\n## Candidate generation\n"
            + candidate_result.get("stdout", "")
            + "\n\n## Candidate repair\n"
            + candidate_repair_result.get("stdout", "")
            + "\n\n## Novelty search\n"
            + novelty_review.get("stdout", "")
            + "\n\n## Final selection\n"
            + final_result.get("stdout", "")
        ),
        stderr_summary=log_snippet(
            "## Paper literature survey\n"
            + paper_survey.get("stderr", "")
            + "\n\n## Candidate generation\n"
            + candidate_result.get("stderr", "")
            + "\n\n## Candidate repair\n"
            + candidate_repair_result.get("stderr", "")
            + "\n\n## Novelty search\n"
            + novelty_review.get("stderr", "")
            + "\n\n## Final selection\n"
            + final_result.get("stderr", "")
        ),
        current_stage="completed" if completed_status == "completed" else failed_run_stage(
            candidate_result,
            candidate_validation,
            candidate_repair_result,
            hard_review,
            final_result,
            audit,
            n,
            b,
        ),
        stages=RUN_STAGES,
        quality_audit_ok=audit["ok"],
        quality_audit_errors=audit["errors"],
        quality_audit_warnings=audit["warnings"],
        hard_review_ok=hard_review["ok"],
        hard_review_candidates=hard_review["candidates_reviewed"],
        hard_review_passed=hard_review["candidates_passed"],
        candidate_replacement_attempts=len(replacement_results),
        candidate_replacement_max_attempts=MAX_CANDIDATE_REPLACEMENT_ATTEMPTS,
        candidate_validation_ok=candidate_validation["ok"],
        candidate_validation_errors=candidate_validation["errors"],
        candidate_validation_warnings=candidate_validation.get("warnings", 0),
        model_backend=backend_meta["backend"],
        model_source=backend_meta["model_source"],
        model=backend_meta["model"],
        codex_cli_version=backend_diagnostics.codex_cli_version,
        supports_model_override=backend_diagnostics.supports_model_override,
    )
    st.session_state.status_snapshot = status
    st.session_state.current_status = completed_status
    st.session_state.last_run_result = final_result
    st.session_state.show_outputs = bool(final_stage_ok or final_stage_partial)
    with placeholder.container():
        status_box(status)


def render_resolver_summary() -> None:
    summary = st.session_state.resolver_summary
    if not summary:
        return
    st.subheader("Resolver summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Detected entries", summary["detected_entries"])
    c2.metric("High confidence", summary["high"])
    c3.metric("Medium confidence", summary["medium"])
    c4.metric("Low confidence", summary["low"])
    if summary["warnings"]:
        st.warning("\n".join(f"- {warning}" for warning in summary["warnings"]))


def render_input(
    mode: str,
    question_style: str,
    n: int,
    a: int,
    b: int,
    try_online: bool,
    require_full_text: bool,
    codex_model: str,
    expert_backend: str,
) -> None:
    st.write(
        f"Paste {n} paper entries. Use English field names. Title, authors, and URL are strongly recommended. "
        "Prefer arXiv, CVGMT, another openly downloadable paper URL, a direct PDF URL, or a local PDF path."
    )
    if mode == "batch":
        st.warning("Batch Mode is for fast screening only. Outputs should be treated as lower-confidence.")
    st.caption(f"Question style: {'General research style' if question_style == 'general' else 'Specialized transfer-pattern style'}")
    with st.expander("Flexible input example", expanded=False):
        st.code(EXAMPLE_MARKDOWN, language="markdown")

    markdown = st.text_area(
        "Paper input",
        key="paper_input",
        height=420,
        placeholder=EXAMPLE_MARKDOWN,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Load previous batch input"):
            st.session_state.paper_input = read_text(INPUT_PATH)
            st.rerun()
    with col2:
        if st.button("Clear input"):
            st.session_state.paper_input = ""
            st.session_state.run_clicked = False
            st.session_state.show_outputs = False
            st.session_state.current_status = "idle"
            st.session_state.status_snapshot = None
            st.session_state.resolver_summary = None
            st.session_state.generated_prompt = ""
            st.session_state.gpt_pro_handoff_manifest = None
            st.session_state.gpt_pro_final_selection_manifest = None
            st.rerun()

    status_placeholder = st.empty()
    if st.button("Run Agent", type="primary"):
        handle_run(
            markdown,
            mode,
            question_style,
            n,
            a,
            b,
            try_online,
            require_full_text,
            codex_model,
            expert_backend,
            status_placeholder,
        )

    if st.session_state.run_clicked:
        render_resolver_summary()
        visible_status = st.session_state.status_snapshot or {"status": st.session_state.current_status}
        status_box(visible_status)
        render_stage_progress(visible_status)


def render_file_tab(path: Path, kind: str) -> None:
    text = read_text(path)
    if not text:
        st.warning(f"Missing {path.name}")
        return
    if kind == "code":
        st.code(text, language="tex")
    elif path.suffix == ".json":
        try:
            st.json(json.loads(text))
        except json.JSONDecodeError:
            st.code(text, language="json")
    else:
        st.markdown(text)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def input_titles_by_id() -> dict[str, str]:
    text = read_text(INPUT_PATH)
    blocks = [block.strip() for block in text.split("---") if block.strip()]
    titles: dict[str, str] = {}
    for block in blocks:
        title_match = None
        for line in block.splitlines():
            if line.startswith("## "):
                title_match = line[3:].strip()
                break
        cvgmt_match = None
        for line in block.splitlines():
            if "CVGMT ID" in line:
                cvgmt_match = line.split(":", 1)[-1].strip().strip("* ")
                break
        if title_match and cvgmt_match and cvgmt_match != "not provided":
            titles[f"cvgmt_{cvgmt_match}"] = title_match
    return titles


def paper_title(paper_dir: Path, input_titles: dict[str, str]) -> str:
    result = read_json(paper_dir / "result.json")
    profile = result.get("paper_profile", {}) if isinstance(result, dict) else {}
    for value in [
        profile.get("paper_title"),
        profile.get("title"),
        result.get("title") if isinstance(result, dict) else None,
    ]:
        if value:
            return str(value)

    for name in ["candidate_questions.json", "ranked_questions.json"]:
        data = read_json(paper_dir / name)
        if isinstance(data, dict):
            candidate = data.get("paper_title") or data.get("title")
            if candidate:
                return str(candidate)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    candidate = item.get("paper_title") or item.get("paper", {}).get("title")
                    if candidate:
                        return str(candidate)

    for qdir in detect_question_folders(paper_dir):
        metadata = read_json(qdir / "metadata.json")
        for key in ["paper_title", "source_paper_title"]:
            if metadata.get(key):
                return str(metadata[key])

    return input_titles.get(paper_dir.name, paper_dir.name)


def has_required_files(path: Path) -> bool:
    return path.is_dir() and all((path / filename).is_file() for filename in REQUIRED_QED_FILES)


def detect_question_folders(paper_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for base in [paper_dir / "selected", paper_dir, paper_dir / "selected_questions"]:
        if base.exists():
            candidates.extend(sorted(path for path in base.iterdir() if path.is_dir() and has_required_files(path)))

    for path in sorted(paper_dir.rglob("*")):
        if path.is_dir() and has_required_files(path):
            candidates.append(path)

    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve())] = path
    return list(unique.values())


def question_title(question_dir: Path) -> str:
    metadata = read_json(question_dir / "metadata.json")
    return str(metadata.get("title") or question_dir.name)


def validation_summary(papers: list[Path]) -> tuple[bool, list[str], int]:
    details = []
    total_questions = 0
    ok = bool(papers)
    for paper_dir in papers:
        questions = detect_question_folders(paper_dir)
        total_questions += len(questions)
        if not questions:
            ok = False
            details.append(f"{paper_dir.name}: no complete final question folders detected")
            continue
        details.append(f"{paper_dir.name}: {len(questions)} complete final question folders detected")
        for question_dir in questions:
            missing = [filename for filename in REQUIRED_QED_FILES if not (question_dir / filename).is_file()]
            if missing:
                ok = False
                details.append(f"{paper_dir.name}/{question_dir.name}: missing {', '.join(missing)}")
    return ok, details, total_questions


def render_validation_status(papers: list[Path]) -> None:
    ok, details, total_questions = validation_summary(papers)
    if ok:
        st.success(f"Validation passed: {len(papers)} papers, {total_questions} final questions.")
    else:
        st.warning("Validation warnings found.")
    with st.expander("Advanced validation details", expanded=False):
        for detail in details:
            st.write(f"- {detail}")


def render_quality_audit() -> None:
    if not QUALITY_AUDIT_PATH.exists():
        return
    data = read_json(QUALITY_AUDIT_PATH)
    if not data:
        with st.expander("Advanced: quality audit", expanded=False):
            st.code(read_text(QUALITY_AUDIT_PATH), language="json")
        return

    issues = data.get("issues", [])
    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    if error_count:
        st.warning(f"Outputs generated; quality audit guidance: {error_count} errors, {warning_count} warnings.")
    elif warning_count:
        st.warning(f"Quality audit passed with warnings: {warning_count} warnings.")
    else:
        st.success("Quality audit passed.")

    with st.expander("Advanced: quality audit details", expanded=bool(error_count)):
        st.write(
            f"Expected: {data.get('expected_papers')} papers, "
            f"{data.get('expected_candidates_per_paper')} candidates per paper, "
            f"{data.get('expected_selected_per_paper')} selected questions per paper."
        )
        st.write(
            f"Found: {data.get('papers_found')} papers and "
            f"{data.get('selected_questions_found')} selected questions."
        )
        for issue in issues:
            st.write(f"- `{issue.get('severity')}` `{issue.get('path')}`: {issue.get('message')}")


def render_evidence_preflight() -> None:
    if not EVIDENCE_PREFLIGHT_PATH.exists():
        return
    data = read_json(EVIDENCE_PREFLIGHT_PATH)
    if not data:
        return

    items = data.get("items", [])
    failed = [item for item in items if not item.get("ok")]
    low_confidence = [
        item
        for item in items
        if str(item.get("confidence", "")).lower() == "low" or not item.get("full_text_was_read")
    ]
    if failed:
        st.error(f"Evidence preflight failed for {len(failed)} paper(s).")
    elif low_confidence:
        st.warning(f"Evidence preflight completed, but {len(low_confidence)} paper(s) have partial/low-confidence text.")
    else:
        st.success("Evidence preflight passed with full-text evidence.")

    with st.expander("Advanced: evidence preflight details", expanded=bool(failed)):
        for item in items:
            st.write(
                f"- `{item.get('paper_id')}` {item.get('title')}: "
                f"confidence `{item.get('confidence')}`, "
                f"full text read `{item.get('full_text_was_read')}`, "
                f"status `{'passed' if item.get('ok') else 'failed'}`"
            )
            if item.get("missing_files"):
                st.write(f"  Missing: {', '.join(item.get('missing_files', []))}")
            if item.get("error_message"):
                st.write(f"  Error: {item.get('error_message')}")


def render_hard_review() -> None:
    if not HARD_REVIEW_PATH.exists():
        return
    data = read_json(HARD_REVIEW_PATH)
    if not data:
        return

    papers = data.get("papers", [])
    failed = [paper for paper in papers if not paper.get("ok")]
    if failed:
        st.error(f"Hard candidate review failed for {len(failed)} paper(s).")
    else:
        st.success(f"Hard candidate review completed for {data.get('candidates_reviewed', 0)} candidates.")

    with st.expander("Advanced: hard candidate review details", expanded=bool(failed)):
        for paper in papers:
            st.write(
                f"- `{paper.get('paper_id')}`: reviewed "
                f"{paper.get('reviewed_count')}/{paper.get('candidate_count')} candidates, "
                f"status `{'passed' if paper.get('ok') else 'failed'}`"
            )
            if paper.get("error_message"):
                st.write(f"  Error: {paper.get('error_message')}")
            for candidate in paper.get("candidates", [])[:20]:
                st.write(
                    f"  - `{candidate.get('question_id')}`: duplicate `{candidate.get('duplicate_risk')}`, "
                    f"critic `{candidate.get('critic_verdict')}`, action `{candidate.get('recommended_action')}`, "
                    f"strict_passed `{candidate.get('passed_final_gate')}`, "
                    f"fallback_selected `{candidate.get('fallback_selected')}`"
                )
                if candidate.get("error_message"):
                    st.write(f"    Error: {candidate.get('error_message')}")


def render_detected_tree(paper_dir: Path, question_dirs: list[Path]) -> None:
    with st.expander("Advanced: detected output tree", expanded=False):
        st.write(f"Paper directory: `{paper_dir.as_posix()}`")
        for qdir in question_dirs:
            st.write(f"Question folder: `{qdir.as_posix()}`")
            found = [filename for filename in REQUIRED_QED_FILES if (qdir / filename).is_file()]
            missing = [filename for filename in REQUIRED_QED_FILES if not (qdir / filename).is_file()]
            st.write(f"- found: {', '.join(found) if found else 'none'}")
            st.write(f"- missing: {', '.join(missing) if missing else 'none'}")


def render_question(question_dir: Path) -> None:
    problem, guidance, verification, survey, feasibility = st.tabs(
        ["Problem", "Guidance", "Verification", "Survey", "Feasibility and scores"]
    )
    with problem:
        render_file_tab(question_dir / "problem_statement.tex", "code")
    with guidance:
        render_file_tab(question_dir / "additional_prove_human_help_global.md", "markdown")
    with verification:
        render_file_tab(question_dir / "additional_verify_rule_global.md", "markdown")
    with survey:
        render_file_tab(question_dir / "survey_queries.md", "markdown")
    with feasibility:
        render_file_tab(question_dir / "feasibility_analysis.md", "markdown")
        st.divider()
        render_file_tab(question_dir / "metadata.json", "json")


def render_json_artifact(path: Path, title: str) -> None:
    st.subheader(title)
    if not path.exists():
        st.info(f"{path.name} has not been generated for this paper yet.")
        return
    data = read_json(path)
    if data:
        st.json(data)
    else:
        st.code(read_text(path), language="json")


def render_final_problem_browser(question_dirs: list[Path]) -> None:
    question_labels = {f"{question_title(path)}  ({path.name})": path for path in question_dirs}
    selected_question_label = st.selectbox("Question", list(question_labels))
    render_question(question_labels[selected_question_label])


def render_results(b: int) -> None:
    if not st.session_state.show_outputs:
        return
    st.header("QAgent Results")
    if not OUTPUT_DIR.exists():
        st.info("No outputs found yet.")
        return

    papers = paper_dirs(OUTPUT_DIR)
    if not papers:
        st.info("No paper output folders found.")
        return

    render_evidence_preflight()
    render_hard_review()
    render_quality_audit()
    render_validation_status(papers)
    title_map = input_titles_by_id()
    paper_labels = {f"{paper_title(path, title_map)}  ({path.name})": path for path in papers}
    selected_paper_label = st.selectbox("Paper", list(paper_labels))
    paper_dir = paper_labels[selected_paper_label]
    question_dirs = detect_question_folders(paper_dir)
    if not question_dirs:
        st.warning("No final question folders found for this paper.")
        render_detected_tree(paper_dir, question_dirs)
        return
    profile_tab, theorem_tab, gap_tab, final_tab = st.tabs(["Paper profile", "Theorem cards", "Gap cards", "Final problems"])
    with profile_tab:
        render_json_artifact(paper_dir / "paper_profile.json", "Paper profile")
    with theorem_tab:
        render_json_artifact(paper_dir / "theorem_cards.json", "Theorem cards")
    with gap_tab:
        render_json_artifact(paper_dir / "gap_cards.json", "Gap cards")
    with final_tab:
        render_final_problem_browser(question_dirs)
    render_detected_tree(paper_dir, question_dirs)


def render_actions(codex_model: str, try_online: bool, mode: str, question_style: str, n: int, a: int, b: int) -> None:
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col1:
        if st.button("Refresh results"):
            st.session_state.show_outputs = True
            st.session_state.status_snapshot = load_status()
            st.rerun()
    with col2:
        if st.button("Load existing outputs"):
            st.session_state.show_outputs = True
            st.session_state.status_snapshot = load_status()
    with col3:
        st.download_button(
            "Download outputs as zip",
            data=zip_directory(OUTPUT_DIR),
            file_name=f"{BATCH_ID}.zip",
            mime="application/zip",
            disabled=not OUTPUT_DIR.exists(),
        )
    with col4:
        if st.button("Run Repair", disabled=not REPAIR_PROMPT_PATH.exists()):
            result = run_repair(codex_model, n, a, b)
            if result["ok"]:
                st.success("Repair completed; quality guidance was written.")
            else:
                st.error(result["error_message"] or "Repair failed.")
    with col5:
        if st.button("Run Candidate Repair", disabled=not CANDIDATE_REPAIR_PROMPT_PATH.exists()):
            result = run_candidate_repair(codex_model, try_online, mode, question_style, n, a, b)
            if result["ok"]:
                st.success("Candidate repair completed; final quality guidance was written.")
            else:
                st.error(result["error_message"] or "Candidate repair failed.")


def render_advanced() -> None:
    with st.expander("Advanced: run log", expanded=False):
        status = st.session_state.status_snapshot or load_status()
        st.write(f"Command attempted: `{status.get('command', '')}`")
        st.write(f"Start time: `{status.get('start_time', '')}`")
        st.write(f"End time: `{status.get('end_time', '')}`")
        st.write(f"Return code: `{status.get('return_code', '')}`")
        if status.get("stdout_summary"):
            st.caption("stdout summary")
            st.code(status["stdout_summary"])
        if status.get("stderr_summary"):
            st.caption("stderr summary")
            st.code(status["stderr_summary"])
        if RUN_LOG_PATH.exists():
            st.caption("Full run_log.txt")
            st.code(read_text(RUN_LOG_PATH))
        if CANDIDATE_RUN_LOG_PATH.exists():
            st.caption("Candidate generation run log")
            st.code(read_text(CANDIDATE_RUN_LOG_PATH))
        if FINAL_RUN_LOG_PATH.exists():
            st.caption("Final selection run log")
            st.code(read_text(FINAL_RUN_LOG_PATH))

    if RESOLVER_LOG_PATH.exists():
        with st.expander("Advanced: resolver log", expanded=False):
            st.markdown(read_text(RESOLVER_LOG_PATH))

    if BACKEND_INFO_LOG_PATH.exists():
        with st.expander("Advanced: backend info", expanded=False):
            st.markdown(read_text(BACKEND_INFO_LOG_PATH))

    if BACKEND_INFO_PATH.exists():
        with st.expander("Advanced: backend_info.json", expanded=False):
            st.json(read_json(BACKEND_INFO_PATH))

    if METADATA_BACKEND_PATCH_PATH.exists():
        with st.expander("Advanced: metadata_backend_patch.json", expanded=False):
            st.json(read_json(METADATA_BACKEND_PATCH_PATH))

    if CANDIDATE_VALIDATION_LOG_PATH.exists():
        with st.expander("Advanced: candidate validation", expanded=False):
            st.markdown(read_text(CANDIDATE_VALIDATION_LOG_PATH))

    if CANDIDATE_VALIDATION_PATH.exists():
        with st.expander("Advanced: candidate_validation.json", expanded=False):
            st.json(read_json(CANDIDATE_VALIDATION_PATH))

    if CANDIDATE_REPAIR_PROMPT_PATH.exists():
        with st.expander("Advanced: candidate repair prompt", expanded=False):
            st.markdown(read_text(CANDIDATE_REPAIR_PROMPT_PATH))

    if CANDIDATE_REPAIR_RUN_LOG_PATH.exists():
        with st.expander("Advanced: candidate repair run log", expanded=False):
            st.code(read_text(CANDIDATE_REPAIR_RUN_LOG_PATH))

    if EVIDENCE_PREFLIGHT_LOG_PATH.exists():
        with st.expander("Advanced: evidence preflight log", expanded=False):
            st.markdown(read_text(EVIDENCE_PREFLIGHT_LOG_PATH))

    if EVIDENCE_PREFLIGHT_PATH.exists():
        with st.expander("Advanced: evidence_preflight.json", expanded=False):
            st.json(read_json(EVIDENCE_PREFLIGHT_PATH))

    if HARD_REVIEW_LOG_PATH.exists():
        with st.expander("Advanced: hard review log", expanded=False):
            st.markdown(read_text(HARD_REVIEW_LOG_PATH))

    if HARD_REVIEW_PATH.exists():
        with st.expander("Advanced: hard_review.json", expanded=False):
            st.json(read_json(HARD_REVIEW_PATH))

    if PASSED_CANDIDATES_PATH.exists():
        with st.expander("Advanced: hard_review_passed_candidates.json", expanded=False):
            st.json(read_json(PASSED_CANDIDATES_PATH))

    if QUALITY_AUDIT_PATH.exists():
        with st.expander("Advanced: quality_audit.json", expanded=False):
            st.json(read_json(QUALITY_AUDIT_PATH))

    if REPAIR_PROMPT_PATH.exists():
        with st.expander("Advanced: repair prompt", expanded=False):
            st.markdown(read_text(REPAIR_PROMPT_PATH))

    if REPAIR_RUN_LOG_PATH.exists():
        with st.expander("Advanced: repair run log", expanded=False):
            st.code(read_text(REPAIR_RUN_LOG_PATH))

    if GPT_PRO_HANDOFF_PATH.exists():
        with st.expander("Advanced: GPT Pro web handoff", expanded=False):
            manifest_path = GPT_PRO_HANDOFF_PATH / "manifest.json"
            final_manifest_path = GPT_PRO_HANDOFF_PATH / "final_selection_manifest.json"
            if manifest_path.exists():
                st.subheader("Candidate-generation handoff")
                st.json(read_json(manifest_path))
                status = load_status()
                required = int(status.get("gpt_pro_candidate_results_required") or 0)
                if required:
                    completion = gpt_pro_candidate_results_completion(required)
                    st.caption(
                        f"GPT Pro candidate results: {completion['present']}/{completion['required']} present"
                    )
                    missing = [item["paper_id"] for item in completion["papers"] if not item["present"]]
                    if missing:
                        st.warning("Missing GPT Pro result files for: " + ", ".join(missing))
            prompts_dir = GPT_PRO_HANDOFF_PATH / "prompts"
            prompt_files = sorted(prompts_dir.glob("*_gpt_pro_prompt.md")) if prompts_dir.exists() else []
            if prompt_files:
                selected_prompt = st.selectbox(
                    "Paper GPT Pro prompt",
                    prompt_files,
                    format_func=lambda p: p.name,
                    key="gpt_pro_prompt_selector",
                )
                st.text_area("Copy into GPT Pro", value=read_text(selected_prompt), height=360)
            if final_manifest_path.exists():
                st.subheader("Final-selection handoff")
                st.json(read_json(final_manifest_path))
                if gpt_pro_final_selection_result_present():
                    st.success("GPT Pro final-selection result is present.")
                else:
                    st.warning("GPT Pro final-selection result is missing.")
            final_prompt_path = GPT_PRO_HANDOFF_PATH / "final_selection_prompt.md"
            if final_prompt_path.exists():
                st.text_area("Copy final-selection prompt into GPT Pro", value=read_text(final_prompt_path), height=360)

    report_path = OUTPUT_DIR / "batch_report.md"
    if report_path.exists():
        with st.expander("Advanced: batch report", expanded=False):
            st.markdown(read_text(report_path))

    if st.session_state.generated_prompt:
        with st.expander("Advanced: manual prompt fallback", expanded=False):
            st.text_area("Generated Codex prompt", value=st.session_state.generated_prompt, height=360)


def main() -> None:
    setup_page()
    init_state()
    configure_batch_paths(st.session_state.batch_id)
    mode, question_style, n, a, b, try_online, require_full_text, codex_model, batch_id, expert_backend = render_sidebar(
        st.session_state.paper_input
    )
    configure_batch_paths(batch_id)

    st.title("QAgent: Question-Generating Agent")
    st.caption(f"Current batch: `{BATCH_ID}`")
    st.subheader("Input papers, refine candidate questions, and export QED-ready research problems.")

    render_input(mode, question_style, n, a, b, try_online, require_full_text, codex_model, expert_backend)
    st.divider()
    render_actions(codex_model, try_online, mode, question_style, n, a, b)
    render_results(b)
    render_advanced()


if __name__ == "__main__":
    main()
