from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.qagent.survey import survey_candidate


class CandidateQEDSurveyTests(unittest.TestCase):
    def test_qed_style_codex_survey_is_used_when_available(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                paper_dir = Path("outputs") / "batch_test" / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(paper_dir / "paper_profile.json", {"title": "Input theorem", "authors": "A"})
                _write_json(paper_dir / "paper_literature_survey.json", {"do_not_generate": ["input theorem"]})
                _write_json(paper_dir / "theorem_cards.json", [{"theorem_label": "T1"}])
                codex_json = {
                    "question_id": "c01",
                    "search_queries": ["candidate exact theorem"],
                    "related_papers": [
                        {
                            "title": "A nearby theorem",
                            "authors": "B",
                            "year": "2025",
                            "source": "arXiv",
                            "url": "https://arxiv.org/abs/2501.00001",
                            "relationship": "related extension",
                        }
                    ],
                    "directly_applicable_theorems": [],
                    "killer_theorem_attempt": "No direct killer survived.",
                    "direct_corollary_check": "Not a direct corollary because a new error term is present.",
                    "counterexamples_and_pitfalls": ["Do not drop the energy bound."],
                    "duplicate_risk": "low",
                    "novelty_verdict": "new enough",
                    "recommended_action": "keep",
                    "classification": "plausible new transfer problem",
                    "detailed_novelty_comparison": "QED-style survey found no direct duplicate and identified a non-cosmetic obstruction.",
                    "self_verification": {"entries_checked": 1, "confidence_in_remaining_entries": "medium"},
                }
                with patch(
                    "src.qagent.survey.run_codex_cli",
                    return_value={
                        "ok": True,
                        "command": "codex --search -m gpt-5.5 exec --json",
                        "return_code": 0,
                        "stdout": json.dumps(codex_json),
                        "stderr": "",
                        "error_message": "",
                    },
                ) as mocked:
                    result = survey_candidate(
                        {
                            "question_id": "c01",
                            "title": "Candidate theorem",
                            "precise_problem_statement": "Let u solve an equation. Prove a new estimate.",
                        },
                        {"paper_id": "paper_001", "title": "Input theorem"},
                        batch_id="batch_test",
                        try_online=True,
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(result.duplicate_risk, "low")
            self.assertEqual(result.recommended_action, "keep")
            self.assertEqual(result.novelty_verdict, "new enough")
            mocked.assert_called_once()
            survey_json = Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_surveys" / "c01.json"
            self.assertTrue(survey_json.is_file())


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
