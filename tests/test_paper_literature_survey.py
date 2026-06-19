from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.paper_literature_survey import (
    build_paper_literature_survey_prompt,
    ensure_paper_literature_survey_outputs,
    run_local_paper_literature_survey,
)


class PaperLiteratureSurveyTests(unittest.TestCase):
    def test_prompt_requires_pre_generation_adversarial_survey(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")

            prompt = build_paper_literature_survey_prompt(root, "batch_test", n=1)

            self.assertIn("paper-level literature survey only", prompt)
            self.assertIn("ProofQED-style adversarial survey workflow", prompt)
            self.assertIn("do_not_generate", prompt)
            self.assertIn("recommended_candidate_angles", prompt)
            self.assertIn("arXiv, CVGMT, OpenAlex, Semantic Scholar, Crossref", prompt)

    def test_missing_survey_outputs_are_degraded_not_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")

            summary = ensure_paper_literature_survey_outputs(
                root,
                n=1,
                survey_result={"ok": False, "error_message": "codex survey failed"},
            )
            survey_path = root / "paper_001" / "paper_literature_survey.json"
            md_path = root / "paper_001" / "paper_literature_survey.md"
            survey = json.loads(survey_path.read_text(encoding="utf-8"))

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["degraded_surveys"], 1)
            self.assertEqual(survey["survey_confidence"], "low")
            self.assertTrue(survey["do_not_generate"])
            self.assertTrue(md_path.is_file())

    def test_local_survey_is_kept_when_codex_survey_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_paper(root / "paper_001")

            local = run_local_paper_literature_survey(root, n=1, try_online=False)
            summary = ensure_paper_literature_survey_outputs(
                root,
                n=1,
                survey_result={"ok": False, "error_message": "codex argument too long"},
            )
            survey = json.loads((root / "paper_001" / "paper_literature_survey.json").read_text(encoding="utf-8"))

            self.assertTrue(local["ok"])
            self.assertEqual(summary["papers_with_valid_survey"], 1)
            self.assertEqual(summary["degraded_surveys"], 0)
            self.assertFalse(survey["survey_degraded"])
            self.assertTrue(survey["related_papers"])


def _write_paper(paper_dir: Path) -> None:
    paper_dir.mkdir(parents=True)
    _write_json(
        paper_dir / "paper_profile.json",
        {
            "title": "Boundary estimates for a model equation",
            "authors": "A. Author",
            "year": "2026",
            "url": "https://arxiv.org/abs/2601.00001",
        },
    )
    _write_json(paper_dir / "theorem_cards.json", [{"theorem_label": "T1"}])
    _write_json(paper_dir / "proof_cards.json", [{"proof_label": "P1"}])
    _write_json(paper_dir / "method_cards.json", [{"method_label": "M1"}])
    _write_json(paper_dir / "limitation_cards.json", [{"limitation": "L1"}])
    _write_json(paper_dir / "gap_cards.json", [{"gap_title": "G1"}])


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
