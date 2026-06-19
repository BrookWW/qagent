from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_ranked_candidate_latex(output_dir: Path, n: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "candidate_questions_ranked.tex"
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{amsmath,amssymb,amsthm}",
        r"\newtheorem{candidateproblem}{Candidate Problem}[section]",
        r"\begin{document}",
        r"\title{QAgent Ranked Candidate Problems}",
        r"\maketitle",
        "",
    ]
    for index in range(1, n + 1):
        paper_id = f"paper_{index:03d}"
        paper_dir = output_dir / paper_id
        profile = _read_json(paper_dir / "paper_profile.json")
        title = _paper_title(profile, paper_id)
        lines.extend(
            [
                rf"\section{{{_latex_escape(title)}}}",
                "",
            ]
        )
        candidates = _ranked_candidates(paper_dir)
        if not candidates:
            lines.extend([r"No candidate questions found.", ""])
            continue
        for rank, candidate in enumerate(candidates, 1):
            question_id = str(candidate.get("question_id") or candidate.get("id") or f"candidate_{rank:02d}")
            candidate_title = str(candidate.get("title") or question_id)
            score = _candidate_score(candidate)
            statement = str(
                candidate.get("precise_problem_statement")
                or candidate.get("problem_statement")
                or candidate.get("question")
                or ""
            ).strip()
            lines.extend(
                [
                    rf"\begin{{candidateproblem}}[{_latex_escape(question_id)}: {_latex_escape(candidate_title)}]",
                    rf"\textbf{{Rank:}} {rank}. \quad \textbf{{Score:}} {_format_score(score)}.",
                    "",
                    statement or r"No precise problem statement was provided.",
                    r"\end{candidateproblem}",
                    "",
                ]
            )
    lines.extend([r"\end{document}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _ranked_candidates(paper_dir: Path) -> list[dict[str, Any]]:
    candidates = _read_json(paper_dir / "candidate_questions.json")
    if not isinstance(candidates, list):
        return []
    items = [item for item in candidates if isinstance(item, dict)]
    ranked = _read_json(paper_dir / "ranked_questions.json")
    if isinstance(ranked, list):
        order = [str(item.get("question_id", "")).strip() for item in ranked if isinstance(item, dict)]
        order_index = {question_id: index for index, question_id in enumerate(order) if question_id}
        if order_index:
            return sorted(
                items,
                key=lambda item: (
                    order_index.get(str(item.get("question_id", "")).strip(), len(order_index)),
                    -_candidate_score(item),
                ),
            )
    return sorted(items, key=_candidate_score, reverse=True)


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
        for key in ["weighted_score", "final_score", "score"]:
            value = score_breakdown.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return 0.0


def _format_score(score: float) -> str:
    return str(int(score)) if float(score).is_integer() else f"{score:.2f}"


def _paper_title(profile: Any, fallback: str) -> str:
    if isinstance(profile, dict):
        return str(profile.get("title") or profile.get("paper_title") or fallback)
    return fallback


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
