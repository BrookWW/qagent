from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.quality_audit import audit_outputs, write_quality_repair_prompt


GOOD_THEOREM_Q = r"""
\begin{q}[Quantitative no-neck criterion for one-bubble Sacks--Uhlenbeck sequences]
Let \(N\subset\mathbb R^L\) be a closed smooth Riemannian submanifold. Let
\(\alpha_j\downarrow1\), and let \(u_j:S^2\to N\) be smooth critical points of
the Sacks--Uhlenbeck energy
\[
E_{\alpha_j}(u)
=
\frac12\int_{S^2}(1+|\nabla u|^2)^{\alpha_j}\,dV .
\]
Assume
\[
\sup_j E_{\alpha_j}(u_j)<\infty.
\]
Prove the no-neck estimate
\[
\lim_{R\to\infty}\lim_{\delta\downarrow0}\limsup_{j\to\infty}
\operatorname{osc}_{B_\delta(p)\setminus B_{Rr_j}(p)} u_j=0.
\]
\end{q}
"""


class QualityAuditTests(unittest.TestCase):
    def test_complete_output_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001", candidate_count=4, selected_count=2)

            result = audit_outputs(root, n=1, a=1, b=2)

            self.assertTrue(result.ok)
            self.assertEqual(result.papers_found, 1)
            self.assertEqual(result.selected_questions_found, 2)
            self.assertFalse([issue for issue in result.issues if issue.severity == "error"])

    def test_per_paper_survey_report_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001", candidate_count=4, selected_count=2)

            result = audit_outputs(root, n=1, a=1, b=2)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertTrue(result.ok)
            self.assertNotIn("survey_report.md", messages)

    def test_missing_counts_and_bad_problem_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            _write_paper(paper, candidate_count=3, selected_count=1)
            (paper / "selected" / "c01" / "problem_statement.tex").write_text(
                r"\begin{q}[Bad]Generated from metadata/abstract only.\end{q}",
                encoding="utf-8",
            )

            result = audit_outputs(root, n=1, a=1, b=2)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("Expected 4 items", messages)
            self.assertNotIn("Expected 2 selected question folders", messages)
            self.assertIn("forbidden meta/template text", messages)

    def test_repair_prompt_is_written_for_failed_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            _write_paper(paper, candidate_count=3, selected_count=1)

            result = audit_outputs(root, n=1, a=1, b=2)
            path = write_quality_repair_prompt(root, "batch_test", result)

            self.assertIsNotNone(path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("Please repair the QAgent final outputs", text)
            self.assertIn("outputs/batch_test/hard_review_passed_candidates.json", text)
            self.assertIn("Expected 4 items", text)

    def test_allowlist_shortfall_due_to_final_quality_exclusion_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            _write_paper(paper, candidate_count=6, selected_count=2)
            _write_json(
                root / "hard_review_passed_candidates.json",
                {
                    "batch_id": "batch_test",
                    "papers": [
                        {
                            "paper_id": "paper_001",
                            "passed_question_ids": ["c01", "c02", "c03"],
                            "passed_candidates": [],
                        }
                    ],
                },
            )
            survey_dir = paper / "candidate_surveys"
            survey_dir.mkdir(exist_ok=True)
            _write_json(
                survey_dir / "c03.json",
                {
                    "question_id": "c03",
                    "duplicate_risk": "high",
                    "novelty_verdict": "direct corollary",
                    "recommended_action": "remove",
                    "classification": "direct restatement of input paper",
                },
            )

            result = audit_outputs(root, n=1, a=1, b=3)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertTrue(result.ok)
            self.assertIn("completed with warnings", messages)
            self.assertFalse([issue for issue in result.issues if issue.severity == "error"])


def _write_paper(paper_dir: Path, candidate_count: int, selected_count: int) -> None:
    paper_dir.mkdir(parents=True)
    _write_json(
        paper_dir / "paper_profile.json",
        {
            "full_text_was_read": True,
            "paper_reading_confidence": "high",
        },
    )
    _write_json(paper_dir / "theorem_cards.json", [{"theorem_label": "T1"}])
    _write_json(paper_dir / "proof_cards.json", [{"theorem_label": "T1"}])
    _write_json(paper_dir / "limitation_cards.json", [{"limitation_id": "L1"}])
    _write_json(paper_dir / "gap_cards.json", [{"gap_id": "G1"}])
    candidates = [{"question_id": f"c{index:02d}"} for index in range(1, candidate_count + 1)]
    _write_json(paper_dir / "candidate_questions.json", candidates)
    _write_json(paper_dir / "ranked_questions.json", candidates)
    _write_json(
        paper_dir.parent / "hard_review_passed_candidates.json",
        {
            "batch_id": "batch_test",
            "papers": [
                {
                    "paper_id": paper_dir.name,
                    "passed_question_ids": [f"c{index:02d}" for index in range(1, selected_count + 1)],
                    "passed_candidates": [],
                }
            ],
        },
    )

    for index in range(1, selected_count + 1):
        qdir = paper_dir / "selected" / f"c{index:02d}"
        qdir.mkdir(parents=True)
        (qdir / "problem_statement.tex").write_text(GOOD_THEOREM_Q, encoding="utf-8")
        (qdir / "additional_prove_human_help_global.md").write_text("# Goal\n", encoding="utf-8")
        (qdir / "additional_verify_rule_global.md").write_text("# Verification checklist\n", encoding="utf-8")
        (qdir / "survey_queries.md").write_text("# Survey Queries\n", encoding="utf-8")
        (qdir / "feasibility_analysis.md").write_text("# Feasibility verdict\nhigh\n", encoding="utf-8")
        survey_dir = paper_dir / "candidate_surveys"
        critic_dir = paper_dir / "candidate_critic"
        survey_dir.mkdir(exist_ok=True)
        critic_dir.mkdir(exist_ok=True)
        (survey_dir / f"c{index:02d}.md").write_text("# Candidate Survey\n\nDuplicate risk: low\n", encoding="utf-8")
        (critic_dir / f"c{index:02d}.md").write_text("## Verdict\n\npositive\n", encoding="utf-8")
        _write_json(
            qdir / "metadata.json",
            {
                "question_id": f"c{index:02d}",
                "survey_duplicate_risk": "low",
                "critic_summary": "positive verdict",
                "theorem_cards_used": ["T1"],
                "gap_cards_used": ["G1"],
                "final_score": 100 - index,
                "generation_backend": "codex_cli_logged_in",
                "generation_api_mode": "no_api",
                "generation_model": "codex_default",
                "generation_model_source": "Codex CLI default from logged-in account/config",
            },
        )


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
