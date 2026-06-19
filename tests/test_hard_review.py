from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.qagent.hard_review import _passes_final_gate, run_hard_review


class HardReviewTests(unittest.TestCase):
    def test_strict_gate_rejects_medium_survey_risk_even_with_strict_novelty_pass(self) -> None:
        candidate = {
            "novelty_review": {
                "verdict": "new_enough",
                "duplicate_risk": "low",
                "recommended_action": "keep",
                "confidence": "medium",
                "killer_known_theorem_attempt": "The closest possible theorem handles only the unperturbed model and fails at the boundary term.",
                "non_cosmetic_difference": "The candidate adds a coefficient perturbation that changes the load-bearing estimate.",
                "why_not_direct_corollary": "The input theorem cannot absorb the perturbation in the main estimate.",
                "why_not_standard_theorem": "The standard theorem assumes the missing cancellation.",
            }
        }
        survey = {
            "duplicate_risk": "medium",
            "novelty_verdict": "new enough",
            "recommended_action": "keep",
            "classification": "plausible new theorem-level question",
        }

        self.assertFalse(
            _passes_final_gate(
                "medium",
                "keep",
                "new enough",
                "positive",
                candidate,
                survey,
            )
        )

    def test_hard_review_writes_candidate_survey_and_critic(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(
                    paper_dir / "candidate_questions.json",
                    [_candidate("c01", 90)],
                )

                result = run_hard_review(root, n=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result.ok)
            self.assertEqual(result.candidates_reviewed, 1)
            self.assertTrue((Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_surveys" / "c01.md").is_file())
            self.assertTrue((Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_critic" / "c01.md").is_file())
            self.assertFalse(result.papers[0].candidates[0].passed_final_gate)

    def test_hard_review_falls_back_to_highest_score_when_strict_passes_are_short(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(
                    paper_dir / "candidate_questions.json",
                    [_candidate("c01", 90)],
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result.ok)
            self.assertEqual(result.candidates_passed, 1)
            self.assertEqual(result.papers[0].candidates[0].novelty_verdict, "new enough")
            self.assertFalse(result.papers[0].candidates[0].passed_final_gate)
            self.assertTrue(result.papers[0].candidates[0].fallback_selected)

    def test_hard_review_uses_validation_quality_penalty_for_fallback_order(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(
                    paper_dir / "candidate_questions.json",
                    [
                        _candidate("c01", 100),
                        _candidate("c02", 90),
                    ],
                )
                _write_json(
                    paper_dir / "candidate_quality_flags.json",
                    {
                        "paper_id": "paper_001",
                        "flags": {
                            "c01": {
                                "question_id": "c01",
                                "validation_quality": "weak_theorem_form",
                                "validation_penalty": 40,
                                "quality_warnings": [
                                    {"metric": "weak_theorem_form", "message": "missing concrete conclusion", "penalty": 40}
                                ],
                            }
                        },
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            candidates = {item.question_id: item for item in result.papers[0].candidates}
            self.assertEqual(candidates["c01"].review_score, 56)
            self.assertEqual(candidates["c02"].review_score, 86)
            self.assertFalse(candidates["c01"].fallback_selected)
            self.assertTrue(candidates["c02"].fallback_selected)

    def test_hard_review_degrades_candidate_when_survey_fails(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 100)])

                with patch("src.qagent.hard_review.survey_candidate", side_effect=RuntimeError("survey boom")):
                    result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertTrue(result.ok)
            self.assertTrue(item.ok)
            self.assertTrue(item.hard_review_degraded)
            self.assertTrue(item.fallback_selected)
            self.assertEqual(item.duplicate_risk, "unknown")
            self.assertIn("survey boom", item.error_message)
            self.assertTrue((Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_surveys" / "c01.md").is_file())
            self.assertTrue((Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_critic" / "c01.md").is_file())

    def test_hard_review_adds_transfer_pattern_bonus_to_review_score(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                with_pattern = _candidate("c01", 80)
                with_pattern.update(
                    {
                        "transfer_pattern_used": "TP03 Boundary Transfer",
                        "source_theorem_or_method": "Interior Caccioppoli estimate",
                        "target_model": "Boundary Dirichlet elliptic problem",
                        "new_obstruction": "Boundary flattening and trace terms",
                        "why_old_proof_may_survive": "The energy and compactness steps survive after boundary cutoff.",
                        "minimal_publishable_version": "Boundary Caccioppoli estimate in a C^2 model domain.",
                        "transfer_pattern_fit_score": 8,
                    }
                )
                _write_json(paper_dir / "candidate_questions.json", [with_pattern, _candidate("c02", 80)])

                result = run_hard_review(root, n=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            candidates = {item.question_id: item for item in result.papers[0].candidates}
            self.assertEqual(candidates["c01"].transfer_pattern_used, "TP03 Boundary Transfer")
            self.assertGreater(candidates["c01"].transfer_pattern_bonus, 0)
            self.assertGreater(candidates["c01"].review_score, candidates["c02"].review_score)

    def test_hard_review_uses_codex_novelty_review_for_strict_pass(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 80), _candidate("c02", 90)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "c01",
                        "verdict": "new_enough",
                        "duplicate_risk": "low",
                        "recommended_action": "keep",
                        "confidence": "medium",
                        "closest_external_result": "No close external result found in the reviewer pass.",
                        "killer_known_theorem_attempt": (
                            "The closest possible killer theorem is standard boundary regularity for uniformly "
                            "elliptic operators with smooth coefficients."
                        ),
                        "non_cosmetic_difference": (
                            "The candidate changes the proof module by adding a weak boundary trace term that is "
                            "not present in the input theorem."
                        ),
                        "why_not_direct_corollary": "Boundary trace terms require a new estimate beyond the input argument.",
                        "why_not_standard_theorem": (
                            "The standard theorem assumes smooth boundary data, while the candidate uses weak trace data."
                        ),
                        "strict_novelty_pass": True,
                    },
                )
                _write_json(
                    review_dir / "c02.json",
                    {
                        "question_id": "c02",
                        "verdict": "likely_known",
                        "duplicate_risk": "high",
                        "recommended_action": "remove",
                        "confidence": "medium",
                        "closest_external_result": "Standard boundary regularity theorem.",
                        "why_not_direct_corollary": "",
                        "strict_novelty_pass": False,
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            candidates = {item.question_id: item for item in result.papers[0].candidates}
            self.assertTrue(candidates["c01"].strict_novelty_pass)
            self.assertEqual(candidates["c01"].novelty_review_verdict, "new_enough")
            self.assertGreater(candidates["c01"].review_score, candidates["c02"].review_score)
            self.assertTrue(candidates["c01"].fallback_selected or candidates["c01"].passed_final_gate)
            self.assertFalse(candidates["c02"].fallback_selected)

    def test_hard_review_requires_adversarial_novelty_evidence_for_strict_pass(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 80)])
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
                        "why_not_direct_corollary": "Boundary trace terms require a new estimate.",
                        "why_not_standard_theorem": "The standard theorem has stronger smoothness assumptions.",
                        "strict_novelty_pass": True,
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertFalse(item.strict_novelty_pass)
            self.assertFalse(item.passed_final_gate)
            self.assertTrue(item.fallback_selected)

    def test_hard_review_recomputes_strict_novelty_pass_instead_of_trusting_json_bool(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 80)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "c01",
                        "verdict": "likely_known",
                        "duplicate_risk": "high",
                        "recommended_action": "remove",
                        "confidence": "high",
                        "strict_novelty_pass": True,
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertFalse(item.strict_novelty_pass)
            self.assertFalse(item.passed_final_gate)
            self.assertFalse(item.fallback_selected)
            self.assertTrue(result.ok)
            self.assertIn("Proceeding with the available allowlist", result.papers[0].error_message)

    def test_direct_corollary_remove_candidate_is_never_fallback_selected(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 99)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "c01",
                        "verdict": "direct_corollary",
                        "duplicate_risk": "high",
                        "recommended_action": "remove",
                        "confidence": "medium",
                        "killer_known_theorem_attempt": "Odd reflection kills the proposed boundary variant.",
                        "non_cosmetic_difference": "No non-cosmetic difference survives the reflection attack.",
                        "why_not_direct_corollary": "It is a direct corollary of the input theorem.",
                        "why_not_standard_theorem": "A separate theorem is unnecessary.",
                        "strict_novelty_pass": False,
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertFalse(item.fallback_selected)
            self.assertTrue(result.ok)
            self.assertIn("Proceeding with the available allowlist", result.papers[0].error_message)

    def test_qed_survey_killer_theorem_prevents_fallback_selection(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 99)])

                def fake_survey(candidate, paper_entry, batch_id="batch_test", try_online=True):
                    return SimpleNamespace(
                        question_id="c01",
                        duplicate_risk="low",
                        novelty_verdict="new enough",
                        recommended_action="keep",
                        survey_confidence="high",
                        search_backend="qed-style codex --search",
                        killer_theorem_attempt="The boundary Caccioppoli estimate follows from Theorem 2.1.",
                        direct_corollary_check="The candidate is a direct corollary after boundary flattening.",
                        directly_applicable_theorems=[
                            {
                                "theorem_name": "Boundary Caccioppoli theorem",
                                "candidate_direction_killed": "Directly proves the proposed estimate.",
                            }
                        ],
                        counterexamples_and_pitfalls=[],
                        to_dict=lambda: {
                            "question_id": "c01",
                            "classification": "plausible new theorem-level question",
                            "duplicate_risk": "low",
                            "novelty_verdict": "new enough",
                            "recommended_action": "keep",
                            "survey_confidence": "high",
                            "search_backend": "qed-style codex --search",
                            "killer_theorem_attempt": "The boundary Caccioppoli estimate follows from Theorem 2.1.",
                            "direct_corollary_check": "The candidate is a direct corollary after boundary flattening.",
                            "directly_applicable_theorems": [
                                {
                                    "theorem_name": "Boundary Caccioppoli theorem",
                                    "candidate_direction_killed": "Directly proves the proposed estimate.",
                                }
                            ],
                            "counterexamples_and_pitfalls": [],
                        },
                    )

                with patch("src.qagent.hard_review.survey_candidate", side_effect=fake_survey):
                    result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=True)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertEqual(item.critic_verdict, "negative")
            self.assertEqual(item.survey_evidence_penalty, 80.0)
            self.assertFalse(item.passed_final_gate)
            self.assertFalse(item.fallback_selected)
            self.assertTrue(result.ok)
            self.assertIn("Proceeding with the available allowlist", result.papers[0].error_message)

    def test_hard_kill_survey_skips_full_critic(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                paper_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 99)])

                def fake_survey(candidate, paper_entry, batch_id="batch_test", try_online=True):
                    return SimpleNamespace(
                        question_id="c01",
                        duplicate_risk="high",
                        novelty_verdict="too close to input theorem",
                        recommended_action="remove",
                        survey_confidence="high",
                        search_backend="qed-style codex --search",
                        killer_theorem_attempt="The input theorem directly proves it.",
                        direct_corollary_check="Direct corollary.",
                        directly_applicable_theorems=[],
                        counterexamples_and_pitfalls=[],
                        to_dict=lambda: {
                            "question_id": "c01",
                            "classification": "module of known theorem",
                            "duplicate_risk": "high",
                            "novelty_verdict": "too close to input theorem",
                            "recommended_action": "remove",
                            "survey_confidence": "high",
                            "search_backend": "qed-style codex --search",
                            "killer_theorem_attempt": "The input theorem directly proves it.",
                            "direct_corollary_check": "Direct corollary.",
                            "directly_applicable_theorems": [],
                            "counterexamples_and_pitfalls": [],
                        },
                    )

                with patch("src.qagent.hard_review.survey_candidate", side_effect=fake_survey):
                    with patch("src.qagent.hard_review.review_candidate", side_effect=AssertionError("critic should be skipped")):
                        result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=True)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertTrue(item.killed_early)
            self.assertEqual(item.critic_verdict, "negative")
            self.assertFalse(item.fallback_selected)
            critic_path = Path(tmp) / "outputs" / "batch_test" / "paper_001" / "candidate_critic" / "c01.md"
            self.assertIn("Full critic was skipped", critic_path.read_text(encoding="utf-8"))

    def test_insufficient_evidence_candidate_can_fill_fallback_with_low_confidence(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 99)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "c01",
                        "verdict": "insufficient_evidence",
                        "duplicate_risk": "unknown",
                        "recommended_action": "revise",
                        "confidence": "medium",
                        "killer_known_theorem_attempt": "The closest theorem handles only the smoother boundary case.",
                        "non_cosmetic_difference": "The proposed problem changes the boundary regularity regime.",
                        "why_not_direct_corollary": "The cited theorem does not cover the stated hypotheses.",
                        "why_not_standard_theorem": "Uniform constants require a separate boundary argument.",
                    },
                )

                def fake_survey(candidate, paper_entry, batch_id="batch_test", try_online=True):
                    return SimpleNamespace(
                        question_id="c01",
                        duplicate_risk="medium",
                        novelty_verdict="insufficient evidence",
                        recommended_action="revise",
                        survey_confidence="medium",
                        search_backend="qed-style codex --search",
                        killer_theorem_attempt="No exact killer survived; related theorems cover only smoother domains.",
                        direct_corollary_check="Not a direct corollary because constants must be reproved.",
                        directly_applicable_theorems=[
                            {
                                "theorem_name": "Smoother boundary theorem",
                                "candidate_direction_killed": (
                                    "Kills only the C2 case. It does not literally kill the C11 version."
                                ),
                            }
                        ],
                        counterexamples_and_pitfalls=["Could be a technical cleanup."],
                        to_dict=lambda: {
                            "question_id": "c01",
                            "classification": "insufficient novelty evidence",
                            "duplicate_risk": "medium",
                            "novelty_verdict": "insufficient evidence",
                            "recommended_action": "revise",
                            "survey_confidence": "medium",
                            "search_backend": "qed-style codex --search",
                            "killer_theorem_attempt": "No exact killer survived; related theorems cover only smoother domains.",
                            "direct_corollary_check": "Not a direct corollary because constants must be reproved.",
                            "directly_applicable_theorems": [
                                {
                                    "theorem_name": "Smoother boundary theorem",
                                    "candidate_direction_killed": (
                                        "Kills only the C2 case. It does not literally kill the C11 version."
                                    ),
                                }
                            ],
                            "counterexamples_and_pitfalls": ["Could be a technical cleanup."],
                        },
                    )

                with patch("src.qagent.hard_review.survey_candidate", side_effect=fake_survey):
                    result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=True)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertEqual(item.critic_verdict, "conditionally positive")
            self.assertFalse(item.passed_final_gate)
            self.assertTrue(item.fallback_selected)
            self.assertTrue(result.ok)
            self.assertGreater(item.survey_evidence_penalty, 0)
            self.assertLess(item.survey_evidence_penalty, 80)

    def test_hard_review_ignores_invalid_novelty_review_json(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 80)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "wrong_id",
                        "verdict": "new_enough",
                        "duplicate_risk": "low",
                        "recommended_action": "keep",
                        "confidence": "high",
                    },
                )

                result = run_hard_review(root, n=1, b=1, batch_id="batch_test", try_online=False)
            finally:
                os.chdir(old_cwd)

            item = result.papers[0].candidates[0]
            self.assertEqual(item.novelty_review_verdict, "")
            self.assertFalse(item.strict_novelty_pass)
            self.assertFalse(item.passed_final_gate)
            self.assertTrue(item.fallback_selected)

    def test_online_survey_runs_only_for_strict_novelty_pass_candidates(self) -> None:
        old_cwd = Path.cwd()
        calls: list[bool] = []
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                root = Path("outputs") / "batch_test"
                paper_dir = root / "paper_001"
                review_dir = paper_dir / "candidate_novelty_reviews"
                review_dir.mkdir(parents=True)
                _write_json(
                    paper_dir / "paper_profile.json",
                    {
                        "title": "A test elliptic theorem",
                        "authors": "A. Author",
                        "year": "2026",
                        "abstract": "We prove regularity for weak solutions of an elliptic equation.",
                    },
                )
                _write_json(paper_dir / "candidate_questions.json", [_candidate("c01", 90), _candidate("c02", 80)])
                _write_json(
                    review_dir / "c01.json",
                    {
                        "question_id": "c01",
                        "verdict": "new_enough",
                        "duplicate_risk": "low",
                        "recommended_action": "keep",
                        "confidence": "medium",
                        "killer_known_theorem_attempt": (
                            "The closest possible killer theorem is standard boundary regularity for uniformly "
                            "elliptic operators with smooth coefficients."
                        ),
                        "non_cosmetic_difference": (
                            "The candidate adds a weak trace obstruction that changes the boundary estimate proof."
                        ),
                        "why_not_direct_corollary": "The input proof lacks the required trace compactness estimate.",
                        "why_not_standard_theorem": "The standard theorem assumes smoother coefficients and boundary data.",
                    },
                )
                _write_json(
                    review_dir / "c02.json",
                    {
                        "question_id": "c02",
                        "verdict": "insufficient_evidence",
                        "duplicate_risk": "unknown",
                        "recommended_action": "revise",
                        "confidence": "low",
                    },
                )

                def fake_survey(candidate, paper_entry, batch_id="batch_test", try_online=True):
                    calls.append(bool(try_online))
                    qid = str(candidate["question_id"])
                    return SimpleNamespace(
                        question_id=qid,
                        duplicate_risk="low",
                        novelty_verdict="new enough",
                        recommended_action="keep",
                        to_dict=lambda: {
                            "question_id": qid,
                            "classification": "plausible new theorem-level question",
                            "duplicate_risk": "low",
                            "novelty_verdict": "new enough",
                            "recommended_action": "keep",
                        },
                    )

                with patch("src.qagent.hard_review.survey_candidate", side_effect=fake_survey):
                    run_hard_review(root, n=1, batch_id="batch_test", try_online=True)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(calls, [True, True])


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _candidate(question_id: str, score: int) -> dict[str, object]:
    return {
        "question_id": question_id,
        "title": f"Boundary Caccioppoli transfer {question_id}",
        "mechanism_labels": ["E. Setting generalization"],
        "precise_problem_statement": (
            "Let u be a weak solution of a uniformly elliptic divergence-form equation on a bounded "
            "C^2 domain Omega with homogeneous Dirichlet boundary data and coefficients satisfying a "
            "Dini-continuity bound. Assume an energy bound and prove a boundary Caccioppoli estimate "
            "with constants depending only on the ellipticity, the Dini modulus, and the domain."
        ),
        "novelty_assessment": "The candidate changes an interior estimate into a boundary estimate with trace errors not present in the input theorem.",
        "method_delta": "Small method delta: adapt the input Caccioppoli and compactness argument after boundary flattening.",
        "fast_sci_route": "A short proof route should isolate the boundary trace estimate before extending to regularity.",
        "journal_fit": "JMAA/CPAA-level if the boundary trace obstruction is genuinely new.",
        "final_score": score,
    }


if __name__ == "__main__":
    unittest.main()
