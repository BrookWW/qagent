from __future__ import annotations

import unittest
from unittest.mock import patch
import subprocess

from src.qagent.runner import (
    build_candidate_generation_prompt,
    build_candidate_replacement_prompt,
    build_final_selection_prompt,
    codex_backend_metadata,
    run_codex_cli,
    )


class RunnerPromptTests(unittest.TestCase):
    def test_candidate_prompt_forbids_final_selected_outputs(self) -> None:
        prompt = build_candidate_generation_prompt("data/batch_test.md", a=2, b=3, n=4, mode="deep", batch_id="batch_test")

        self.assertIn("candidate generation only", prompt)
        self.assertIn("Do not write any outputs/batch_test/{paper_id}/selected", prompt)
        self.assertIn("initial candidate questions per paper = (a+1)*b = 9", prompt)
        self.assertIn("novelty_assessment", prompt)
        self.assertIn("fast_sci_route", prompt)
        self.assertIn("JDE/JMAA/CPAA", prompt)
        self.assertIn("examples/transfer_patterns_active.md", prompt)
        self.assertIn("examples/successful_transfer_patterns.md", prompt)
        self.assertIn("transfer_pattern_used", prompt)
        self.assertIn("source_theorem_or_method", prompt)
        self.assertIn("target_model", prompt)
        self.assertIn("new_obstruction", prompt)
        self.assertIn("minimal_publishable_version", prompt)
        self.assertIn("novelty_axis", prompt)
        self.assertIn("why_not_direct_corollary", prompt)
        self.assertIn("why_not_standard_theorem", prompt)
        self.assertIn("successful_transfer_pattern_fit", prompt)
        self.assertIn("candidate-level novelty/duplicate evidence", prompt)
        self.assertIn("Do not create per-paper survey_report.md", prompt)
        self.assertIn("paper_literature_survey.json", prompt)
        self.assertIn("do_not_generate", prompt)
        self.assertIn("paper_survey_used", prompt)
        self.assertIn("known_result_to_avoid", prompt)

    def test_general_candidate_prompt_uses_general_principles_not_transfer_templates(self) -> None:
        prompt = build_candidate_generation_prompt(
            "data/batch_test.md",
            a=2,
            b=3,
            n=4,
            mode="deep",
            batch_id="batch_test",
            question_style="general",
        )

        self.assertIn("question style = General Research Style", prompt)
        self.assertIn("examples/general_research_question_principles.md", prompt)
        self.assertNotIn("examples/transfer_patterns_active.md", prompt)
        self.assertNotIn("examples/successful_transfer_patterns.md", prompt)
        self.assertIn("question_strategy_used", prompt)
        self.assertIn("input_anchor", prompt)
        self.assertIn("pressure_point_id", prompt)
        self.assertIn("theorem skeletons", prompt)
        self.assertIn("proof-level", prompt)
        self.assertIn("Attack A", prompt)
        self.assertIn("Attack B", prompt)
        self.assertIn("Attack C", prompt)
        self.assertIn("fewer than five", prompt)
        self.assertIn("one_step_change_from_input", prompt)
        self.assertIn("novelty_defense", prompt)
        self.assertIn("direct_corollary_attack", prompt)
        self.assertIn("minimal_proof_route", prompt)
        self.assertIn("do not invent", prompt)
        self.assertIn("evidence insufficient", prompt)
        self.assertIn("attempted proof", prompt)
        self.assertIn("Formal statement gate", prompt)
        self.assertIn("Do not force a TP## transfer pattern", prompt)
        self.assertIn("method_transfer_map.json", prompt)
        self.assertIn("adjacent_model_pool.json", prompt)
        self.assertIn("research_level_gate", prompt)
        self.assertIn("source_method_module_id", prompt)
        self.assertIn("new_failure_term", prompt)
        self.assertIn("why_not_random_transfer", prompt)
        self.assertIn("abstract role of the method", prompt)
        self.assertIn("Pure proof-module", prompt)
        self.assertIn("research_direction_gate", prompt)
        self.assertIn("direction-level self-check", prompt)
        self.assertIn("stays inside small variants", prompt)

    def test_final_prompt_requires_hard_review_allowlist(self) -> None:
        prompt = build_final_selection_prompt("data/batch_test.md", a=2, b=3, n=4, mode="deep", batch_id="batch_test")

        self.assertIn("final selection only", prompt)
        self.assertIn("hard_review_passed_candidates.json", prompt)
        self.assertIn("outputs/batch_test/hard_review_passed_candidates.json", prompt)
        self.assertIn("select final questions only from", prompt)
        self.assertIn("Do not invent new question IDs", prompt)
        self.assertIn("not a second hard-kill stage", prompt)
        self.assertIn("low_confidence_final", prompt)
        self.assertIn("final_risk_disclosures", prompt)
        self.assertIn("method_delta", prompt)
        self.assertIn("fallback_selected", prompt)
        self.assertIn("candidate_quality_flags.json", prompt)
        self.assertIn("validation_quality", prompt)
        self.assertIn("review_score", prompt)
        self.assertIn("candidate_novelty_reviews", prompt)
        self.assertIn("strict_novelty_pass", prompt)
        self.assertIn("hard review underfill", prompt)

    def test_candidate_replacement_prompt_replaces_hard_killed_candidates(self) -> None:
        prompt = build_candidate_replacement_prompt(
            output_dir="outputs/batch_test",
            batch_id="batch_test",
            n=1,
            a=2,
            b=3,
            attempt=2,
            question_style="general",
        )

        self.assertIn("candidate replacement only", prompt)
        self.assertIn("replacement attempt = 2", prompt)
        self.assertIn("maximum attempts = 3", prompt)
        self.assertIn("candidates per paper must remain exactly 9", prompt)
        self.assertIn("killed_early = true", prompt)
        self.assertIn("not only for underfilled papers", prompt)
        self.assertIn("even if the current hard-review allowlist already has b items", prompt)
        self.assertIn("candidate_surveys/*.json", prompt)
        self.assertIn("must be replaced", prompt)
        self.assertIn("Use fresh question_id values", prompt)
        self.assertIn("direct_corollary_precheck", prompt)
        self.assertIn("why_transfer_is_not_random", prompt)
        self.assertIn("does not mean random model hopping", prompt)
        self.assertIn("method_transfer_map.json", prompt)
        self.assertIn("adjacent_model_pool.json", prompt)
        self.assertIn("target_model_from_transfer_map", prompt)

    def test_codex_backend_metadata_is_explicit_about_source(self) -> None:
        default_meta = codex_backend_metadata("")
        explicit_meta = codex_backend_metadata("o3")

        self.assertEqual(default_meta["backend"], "codex_cli_logged_in")
        self.assertEqual(default_meta["api_mode"], "no_api")
        self.assertIn("logged-in account/config", default_meta["model_source"])
        self.assertEqual(default_meta["search_enabled"], "true")
        self.assertEqual(default_meta["reasoning_effort"], "xhigh")
        self.assertEqual(explicit_meta["model"], "o3")
        self.assertEqual(explicit_meta["model_source"], "explicit codex exec --model o3")

    def test_codex_timeout_is_marked_for_partial_file_recovery(self) -> None:
        with patch("src.qagent.runner.shutil.which", return_value="C:/bin/codex.exe"):
            with patch("src.qagent.runner.subprocess.run", side_effect=subprocess.TimeoutExpired(["codex"], 1, output="partial")):
                result = run_codex_cli("prompt", timeout_seconds=1)

        self.assertFalse(result["ok"])
        self.assertTrue(result["timed_out"])
        self.assertIn("partial files may have been written", result["error_message"])

    def test_long_codex_prompt_is_passed_by_prompt_file(self) -> None:
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch("src.qagent.runner.shutil.which", return_value="C:/bin/codex.exe"):
            with patch("src.qagent.runner.subprocess.run", side_effect=fake_run):
                result = run_codex_cli("x" * 30000)

        self.assertTrue(result["ok"])
        self.assertIn("--search", captured["command"])
        self.assertIn("--json", captured["command"])
        self.assertIn('-C', captured["command"])
        self.assertLess(len(captured["command"][-1]), 1000)
        self.assertIn("Read the full QAgent prompt", captured["command"][-1])
        self.assertIn("prompt_file=", result["command"])

    def test_codex_jsonl_response_is_extracted(self) -> None:
        payload = '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n'
        with patch("src.qagent.runner.shutil.which", return_value="C:/bin/codex.exe"):
            with patch("src.qagent.runner.subprocess.run", return_value=subprocess.CompletedProcess(["codex"], 0, stdout=payload, stderr="")):
                result = run_codex_cli("prompt")

        self.assertTrue(result["ok"])
        self.assertEqual(result["stdout"], "done")


if __name__ == "__main__":
    unittest.main()
