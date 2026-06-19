from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.novelty_review import build_novelty_review_prompt, ensure_novelty_review_outputs


class NoveltyReviewTests(unittest.TestCase):
    def test_prompt_mentions_structured_novelty_review_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")

            prompt = build_novelty_review_prompt(root, "batch_test", n=1, b=1)

            self.assertIn("strict mathematical novelty referee", prompt)
            self.assertIn("strict_novelty_pass", prompt)
            self.assertIn("candidate_novelty_reviews", prompt)
            self.assertIn("direct_corollary", prompt)
            self.assertIn("killer known theorem", prompt)
            self.assertIn("non_cosmetic_difference", prompt)
            self.assertIn("search_attempted", prompt)
            self.assertIn("Codex CLI web/search", prompt)

    def test_missing_reviewer_outputs_are_degraded_not_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")

            summary = ensure_novelty_review_outputs(
                root,
                n=1,
                b=1,
                reviewer_result={"ok": False, "error_message": "codex boom"},
            )
            review_path = root / "paper_001" / "candidate_novelty_reviews" / "c01.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))

            self.assertTrue(summary["ok"])
            self.assertEqual(review["verdict"], "insufficient_evidence")
            self.assertFalse(review["strict_novelty_pass"])
            self.assertTrue(review["review_degraded"])
            self.assertIn("killer_known_theorem_attempt", review)
            self.assertIn("non_cosmetic_difference", review)
            self.assertFalse(review["search_attempted"])
            self.assertIn("search_limitations", review)

    def test_summary_recomputes_strict_pass_instead_of_trusting_json_bool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")
            review_dir = root / "paper_001" / "candidate_novelty_reviews"
            review_dir.mkdir(parents=True)
            _write_json(
                review_dir / "c01.json",
                {
                    "question_id": "c01",
                    "verdict": "new_enough",
                    "duplicate_risk": "low",
                    "recommended_action": "keep",
                    "confidence": "high",
                    "killer_known_theorem_attempt": "not established by Codex novelty reviewer",
                    "non_cosmetic_difference": "unclear",
                    "why_not_direct_corollary": "trace term",
                    "why_not_standard_theorem": "paper-specific weak class",
                    "strict_novelty_pass": True,
                },
            )

            summary = ensure_novelty_review_outputs(root, n=1, b=1, reviewer_result={"ok": True})

            self.assertEqual(summary["reviewed_or_existing_top_candidates"], 1)
            self.assertEqual(summary["strict_novelty_pass"], 0)


def _write_paper(paper_dir: Path) -> None:
    paper_dir.mkdir(parents=True)
    _write_json(paper_dir / "paper_profile.json", {"title": "A test theorem"})
    _write_json(paper_dir / "theorem_cards.json", [{"theorem_label": "T1"}])
    _write_json(paper_dir / "gap_cards.json", [{"gap_title": "G1"}])
    _write_json(
        paper_dir / "candidate_questions.json",
        [
            {
                "question_id": "c01",
                "title": "Boundary transfer",
                "precise_problem_statement": "Let u solve an elliptic equation. Prove a boundary estimate.",
                "novelty_axis": "boundary",
                "closest_input_result": "interior estimate",
                "why_not_direct_corollary": "trace term",
                "why_not_standard_theorem": "paper-specific weak class",
                "final_score": 90,
            }
        ],
    )


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
