from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.qagent.evidence_preflight import REQUIRED_EVIDENCE_FILES, run_evidence_preflight


class EvidencePreflightTests(unittest.TestCase):
    def test_metadata_only_entry_creates_required_evidence_files(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                result = run_evidence_preflight(
                    [
                        {
                            "title": "A test theorem on elliptic regularity",
                            "authors": "A. Author",
                            "year": "2026",
                            "abstract": (
                                "We prove a theorem for weak solutions of an elliptic equation "
                                "on a bounded domain under a stability assumption."
                            ),
                        }
                    ],
                    batch_id="batch_test",
                    try_online=False,
                )
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result.ok)
            self.assertEqual(result.papers_processed, 1)
            self.assertEqual(result.items[0].paper_id, "paper_001")
            self.assertEqual(result.items[0].confidence, "low")
            self.assertFalse(result.items[0].full_text_was_read)

            paper_dir = Path(tmp) / "outputs" / "batch_test" / "paper_001"
            for name in REQUIRED_EVIDENCE_FILES:
                self.assertTrue((paper_dir / name).is_file(), name)

    def test_require_full_text_marks_metadata_only_entry_low_confidence(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                result = run_evidence_preflight(
                    [
                        {
                            "title": "A test theorem on elliptic regularity",
                            "authors": "A. Author",
                            "year": "2026",
                            "abstract": "We prove a theorem from metadata only.",
                        }
                    ],
                    batch_id="batch_test",
                    try_online=False,
                    require_full_text=True,
                )
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result.ok)
            self.assertTrue(result.items[0].ok)
            self.assertFalse(result.items[0].full_text_was_read)
            self.assertEqual(result.items[0].confidence, "low")
            self.assertEqual(result.items[0].error_message, "")
            self.assertIn("continuing with low confidence", "\n".join(result.items[0].extraction_log))

    def test_single_paper_evidence_failure_gets_low_confidence_fallback(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("src.qagent.evidence_preflight.read_paper_deeply", side_effect=RuntimeError("boom")):
                    result = run_evidence_preflight(
                        [
                            {
                                "title": "A failed paper",
                                "authors": "A. Author",
                                "abstract": "We study an elliptic theorem.",
                            }
                        ],
                        batch_id="batch_test",
                        try_online=False,
                    )
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result.ok)
            self.assertTrue(result.items[0].ok)
            self.assertEqual(result.items[0].confidence, "low")
            self.assertFalse(result.items[0].full_text_was_read)
            self.assertIn("boom", result.items[0].error_message)

            paper_dir = Path(tmp) / "outputs" / "batch_test" / "paper_001"
            for name in REQUIRED_EVIDENCE_FILES:
                self.assertTrue((paper_dir / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
