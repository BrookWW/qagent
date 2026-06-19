"""Output writers for QAgent."""

from __future__ import annotations

import json
from pathlib import Path

from .parser import Paper


def write_mock_outputs(batch_output_dir: Path, paper: Paper) -> None:
    paper_dir = batch_output_dir / paper.paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)

    candidate_questions = _candidate_questions(paper)
    ranked_questions = [
        {**question, "rank": index + 1, "score": round(1.0 - index * 0.1, 2)}
        for index, question in enumerate(candidate_questions)
    ]

    _write_json(
        paper_dir / "result.json",
        {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "mode": "mock",
            "selected_question_ids": ["q01", "q02", "q03"],
        },
    )
    _write_json(paper_dir / "candidate_questions.json", candidate_questions)
    _write_json(paper_dir / "ranked_questions.json", ranked_questions)

    for question in ranked_questions[:3]:
        _write_selected_question(paper_dir, paper, question)


def write_batch_report(batch_output_dir: Path, batch_id: str, papers: list[Paper]) -> Path:
    report_path = batch_output_dir / "batch_report.md"
    lines = [
        f"# Batch Report: {batch_id}",
        "",
        f"- Papers processed: {len(papers)}",
        "- Mode: mock",
        "",
        "## Papers",
        "",
    ]

    for paper in papers:
        lines.extend(
            [
                f"### {paper.paper_id}",
                "",
                f"- Title: {paper.title}",
                f"- CVGMT ID: {paper.cvgmt_id or 'not provided'}",
                f"- Year: {paper.year or 'not provided'}",
                "",
            ]
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _candidate_questions(paper: Paper) -> list[dict[str, str]]:
    topic = paper.matched_keywords or "the main analytical method"
    return [
        {
            "question_id": "q01",
            "question": f"What assumptions guarantee regularity for weak solutions in '{paper.title}'?",
            "theme": "regularity",
        },
        {
            "question_id": "q02",
            "question": f"How can convergence to stationary states be verified for the model in '{paper.title}'?",
            "theme": "equilibrium",
        },
        {
            "question_id": "q03",
            "question": f"Which estimates involving {topic} are central to the argument?",
            "theme": "estimates",
        },
    ]


def _write_selected_question(paper_dir: Path, paper: Paper, question: dict[str, object]) -> None:
    question_id = str(question["question_id"])
    question_dir = paper_dir / "selected" / question_id
    question_dir.mkdir(parents=True, exist_ok=True)

    problem_statement = (
        "\\section*{Mock Problem Statement}\n\n"
        f"Paper: {paper.title}\n\n"
        f"Question: {question['question']}\n\n"
        "This is a placeholder problem statement generated in mock mode.\n"
    )
    question_dir.joinpath("problem_statement.tex").write_text(problem_statement, encoding="utf-8")

    question_dir.joinpath("additional_prove_human_help_global.md").write_text(
        "# Human Proof Help\n\n"
        "Mock guidance: identify the main hypotheses, state the target estimate, and outline the proof strategy.\n",
        encoding="utf-8",
    )
    question_dir.joinpath("additional_verify_rule_global.md").write_text(
        "# Verification Rules\n\n"
        "- Check that all assumptions are explicitly stated.\n"
        "- Check that every estimate cites its required hypothesis.\n"
        "- Check that the conclusion matches the selected question.\n",
        encoding="utf-8",
    )
    question_dir.joinpath("survey_queries.md").write_text(
        "# Survey Queries\n\n"
        f"- {paper.title} {question['theme']}\n"
        f"- CVGMT {paper.cvgmt_id or paper.paper_id} {question['theme']}\n",
        encoding="utf-8",
    )
    question_dir.joinpath("feasibility_analysis.md").write_text(
        "# Feasibility verdict\n\n"
        "medium. This mock question is plausible, but the real feasibility depends on the exact hypotheses of the paper.\n\n"
        "# Quick proof attempt\n\n"
        "Start from the model theorem, isolate the main estimate, and test it in the simplest smooth setting.\n\n"
        "# Key estimates or lemmas needed\n\n"
        "- A priori estimate matching the selected theme.\n"
        "- Compactness or approximation lemma.\n"
        "- Verification that assumptions pass to the limit.\n\n"
        "# Simplified model case\n\n"
        "Use smooth data and the strongest natural structural assumptions.\n\n"
        "# Possible failure points\n\n"
        "The estimate may fail at borderline regularity or without the missing structural assumptions.\n\n"
        "# Counterexample mechanisms\n\n"
        "- Scaling failure.\n"
        "- Concentration.\n"
        "- Loss of compactness.\n\n"
        "# Suggested revision\n\n"
        "State a narrower theorem with explicit assumptions before attempting a sharp version.\n\n"
        "# Recommendation\n\n"
        "keep but simplify\n",
        encoding="utf-8",
    )
    _write_json(
        question_dir / "metadata.json",
        {
            "paper_id": paper.paper_id,
            "question_id": question_id,
            "theme": question["theme"],
            "mock": True,
        },
    )


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
