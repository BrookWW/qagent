from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.candidate_exporter import write_ranked_candidate_latex


class CandidateExporterTests(unittest.TestCase):
    def test_writes_ranked_candidate_latex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            _write_json(paper / "paper_profile.json", {"title": "A&B paper"})
            candidates = [
                _candidate("c01", "Lower score", 70),
                _candidate("c02", "Higher score", 95),
            ]
            _write_json(paper / "candidate_questions.json", candidates)
            _write_json(paper / "ranked_questions.json", [candidates[1], candidates[0]])

            path = write_ranked_candidate_latex(root, n=1)
            text = path.read_text(encoding="utf-8")

            self.assertTrue(path.is_file())
            self.assertIn(r"\section{A\&B paper}", text)
            self.assertLess(text.index("c02"), text.index("c01"))
            self.assertIn(r"\textbf{Rank:} 1", text)
            self.assertIn("Prove estimate c02.", text)


def _candidate(question_id: str, title: str, score: int) -> dict[str, object]:
    return {
        "question_id": question_id,
        "title": title,
        "precise_problem_statement": f"Let u solve a model equation. Prove estimate {question_id}.",
        "final_score": score,
    }


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
