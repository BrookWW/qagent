from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.candidate_validator import (
    trim_excess_candidate_outputs,
    validate_candidate_outputs,
    validate_candidate_outputs_with_policy,
    write_candidate_quality_flags,
    write_candidate_repair_prompt,
)


GOOD_STATEMENT = (
    "Let u be a weak solution of a uniformly elliptic divergence-form equation on a bounded "
    "C^2 domain Omega with homogeneous Dirichlet boundary data and coefficients satisfying a "
    "Dini-continuity bound. Assume an energy bound and prove a boundary Caccioppoli estimate "
    "with constants depending only on the ellipticity, the Dini modulus, and the domain."
)


class CandidateValidatorTests(unittest.TestCase):
    def test_valid_candidates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidates = [_candidate("c01"), _candidate("c02")]
            _write_json(paper / "candidate_questions.json", candidates)
            _write_json(paper / "ranked_questions.json", list(reversed(candidates)))

            result = validate_candidate_outputs(root, n=1, expected_candidates=2)

            self.assertTrue(result.ok)
            self.assertEqual(result.issues, [])

    def test_missing_duplicate_mismatch_and_template_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            bad = _candidate("c01")
            bad.pop("title")
            bad["precise_problem_statement"] = "Study the natural setting of the paper."
            candidates = [bad, _candidate("c01")]
            ranked = [_candidate("c01"), _candidate("c03")]
            _write_json(paper / "candidate_questions.json", candidates)
            _write_json(paper / "ranked_questions.json", ranked)

            result = validate_candidate_outputs(root, n=1, expected_candidates=2)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("missing required field: title", messages)
            self.assertIn("Duplicate question_id: c01", messages)
            self.assertIn("do not match", messages)
            self.assertIn("too short", messages)
            self.assertIn("template/vague phrase", messages)

    def test_candidate_statement_must_pass_theorem_form_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            bad = _candidate("c01")
            bad["precise_problem_statement"] = (
                "Let u be a weak solution on a bounded domain and assume the usual estimates. "
                "Discuss why a boundary version should be natural and useful for future work."
            )
            _write_json(paper / "candidate_questions.json", [bad])
            _write_json(paper / "ranked_questions.json", [bad])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("failed theorem-form audit", messages)
            self.assertIn("no explicit equation", messages)
            self.assertIn("no concrete conclusion", messages)

    def test_conclusion_boilerplate_is_hard_error_even_after_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            bad = _candidate("c01")
            bad["precise_problem_statement"] = (
                GOOD_STATEMENT
                + " Conclusion: this gives the desired regularity statement and completes the formulation."
            )
            _write_json(paper / "candidate_questions.json", [bad])
            _write_json(paper / "ranked_questions.json", [bad])

            result = validate_candidate_outputs_with_policy(root, n=1, expected_candidates=1, allow_quality_warnings=True)
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("conclusion/summary boilerplate", messages)
            self.assertTrue(any(issue.severity == "error" for issue in result.issues))

    def test_theorem_form_can_be_carried_as_quality_warning_after_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            bad = _candidate("c01")
            bad["precise_problem_statement"] = (
                "Let u be a weak solution on a bounded domain and assume the usual estimates. "
                "Discuss why a boundary version should be natural and useful for future work."
            )
            _write_json(paper / "candidate_questions.json", [bad])
            _write_json(paper / "ranked_questions.json", [bad])

            result = validate_candidate_outputs_with_policy(root, n=1, expected_candidates=1, allow_quality_warnings=True)
            write_candidate_quality_flags(root, 1, result)
            flags = json.loads((paper / "candidate_quality_flags.json").read_text(encoding="utf-8"))

            self.assertTrue(result.ok)
            self.assertEqual(result.issues[0].severity, "warning")
            self.assertIn("weak_theorem_form", flags["flags"]["c01"]["validation_quality"])
            self.assertGreater(flags["flags"]["c01"]["validation_penalty"], 0)

    def test_weak_transfer_pattern_is_warning_not_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.pop("transfer_pattern_used")
            candidate.pop("new_obstruction")
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1)
            write_candidate_quality_flags(root, 1, result)
            flags = json.loads((paper / "candidate_quality_flags.json").read_text(encoding="utf-8"))

            self.assertTrue(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_transfer_pattern" for issue in result.issues))
            self.assertEqual(result.issues[0].severity, "warning")
            self.assertEqual(flags["flags"]["c01"]["validation_quality"], "weak_transfer_pattern")
            self.assertGreater(flags["flags"]["c01"]["validation_penalty"], 0)

    def test_general_style_does_not_require_transfer_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.pop("transfer_pattern_used")
            candidate.pop("new_obstruction")
            candidate.update(
                {
                    "question_strategy_used": "quantitative refinement",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It turns a qualitative estimate into a rate with a short proof route.",
                    "one_step_change_from_input": "Replace qualitative convergence by a quantitative boundary estimate.",
                    "proof_route_shortness": "The input compactness proof can be reused after one new boundary lemma.",
                    "novelty_defense": "The input theorem does not provide a rate and standard estimates do not cover the singular term.",
                    **_strong_general_fields(),
                    **_research_level_fields(),
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertTrue(result.ok)
            self.assertFalse(any(issue.quality_metric == "weak_transfer_pattern" for issue in result.issues))

    def test_specialized_style_is_not_forced_to_write_adjacent_model_pool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="specialized")

            self.assertTrue(result.ok)
            self.assertFalse(any(issue.quality_metric == "weak_adjacent_model_pool" for issue in result.issues))

    def test_general_style_rejects_missing_general_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            write_candidate_quality_flags(root, 1, result)
            flags = json.loads((paper / "candidate_quality_flags.json").read_text(encoding="utf-8"))

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_general_strategy" for issue in result.issues))
            quality = flags["flags"]["c01"]["validation_quality"]
            self.assertIn("weak_general_strategy", quality)
            self.assertIn("weak_input_anchor", quality)
            self.assertIn("weak_direct_corollary_attack", quality)
            self.assertIn("weak_minimal_proof_route", quality)
            self.assertIn("weak_abstraction_lift", quality)

    def test_general_style_warns_on_direct_corollary_candidate_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "quantitative refinement",
                    "strategy_fit_score": 5,
                    "why_this_is_good_research_question": "It tries to quantify the input theorem.",
                    "one_step_change_from_input": "Track constants in the same proof.",
                    "proof_route_shortness": "The same proof should work.",
                    "novelty_defense": "This is close to the input theorem.",
                    **_strong_general_fields(),
                    "direct_corollary_precheck": "This is a direct corollary by routine bookkeeping.",
                    "direct_corollary_attack": {
                        "attack_from_input_theorem": "The input theorem gives the same conclusion after tracking constants.",
                        "attack_from_standard_theorem": "No separate standard theorem is needed for the same proof.",
                        "attack_from_routine_approximation": "Routine approximation appears sufficient.",
                        "why_all_fail": "same proof",
                    },
                    "why_generation_survives_direct_corollary_filter": "same proof",
                    "candidate_origin_type": "input-local refinement",
                    "adjacent_model_transfer": False,
                }
            )
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "direct_corollary_candidate_risk" for issue in result.issues))

    def test_general_style_requires_direct_attack_as_attempted_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "quantitative refinement",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It turns qualitative compactness into a rate.",
                    "one_step_change_from_input": "Add a quantitative rate to the convergence conclusion.",
                    "new_obstruction": "The input proof loses the modulus in the compactness step.",
                    "proof_route_shortness": "One new compactness-rate lemma should start the proof.",
                    "novelty_defense": "The input theorem is qualitative and does not imply a rate.",
                    "direct_corollary_precheck": "Checked input theorem, standard compactness, and approximation.",
                    "why_generation_survives_direct_corollary_filter": "The standard compactness theorem has no quantitative modulus.",
                    "candidate_origin_type": "quantitative refinement",
                    "adjacent_model_transfer": False,
                    **_strong_general_fields(),
                    "direct_corollary_attack": {
                        "attack_from_input_theorem": "The assumptions are different, so it is not a direct corollary.",
                        "attack_from_standard_theorem": "The standard theorem does not apply.",
                        "attack_from_routine_approximation": "Approximation is not enough.",
                        "why_all_fail": "They do not give the desired rate.",
                    },
                }
            )
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_attempted_direct_proof" for issue in result.issues))

    def test_general_style_allows_research_level_candidates_without_transfer_quota(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidates = []
            for index in range(1, 5):
                candidate = _candidate(f"c{index:02d}")
                candidate.update(
                    {
                        "question_strategy_used": "model-case theorem",
                        "strategy_fit_score": 7,
                        "why_this_is_good_research_question": "It narrows the input model to a publishable theorem.",
                        "one_step_change_from_input": "Use the same model with a localized estimate.",
                        "proof_route_shortness": "The proof starts from the input estimate plus one lemma.",
                        "novelty_defense": "The input theorem does not state this local model version.",
                        **_strong_general_fields(),
                        "direct_corollary_precheck": "The local estimate is checked against the input theorem.",
                        "why_generation_survives_direct_corollary_filter": "The conclusion has a new local error term.",
                        "candidate_origin_type": "input-local refinement",
                        "adjacent_model_transfer": False,
                    }
                )
                candidates.append(candidate)
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", candidates)
            _write_json(paper / "ranked_questions.json", candidates)

            result = validate_candidate_outputs(root, n=1, expected_candidates=4, question_style="general")

            self.assertTrue(result.ok)
            self.assertFalse(any(issue.quality_metric == "weak_general_candidate_mix" for issue in result.issues))

    def test_general_style_rejects_raw_proof_detail_as_research_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["title"] = "Annular region estimate for boundary Caccioppoli localization"
            candidate["novelty_axis"] = "annular region refinement of the cutoff argument"
            candidate["abstraction_lift"] = {
                "raw_proof_detail_used": "annular region in the localization proof",
                "is_raw_detail_suppressed": False,
                "abstract_mechanism": "localization",
                "main_research_object": "annular region",
                "why_mechanism_is_research_level": "It appears in the proof.",
                "candidate_not_about_raw_detail": "The candidate is about the raw detail.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "proof_detail_candidate_forbidden" for issue in result.issues))
            self.assertTrue(any(issue.quality_metric == "weak_abstraction_lift" for issue in result.issues))

    def test_general_style_accepts_abstraction_lift_to_main_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["abstraction_lift"] = {
                "raw_proof_detail_used": "annular region in the localization proof",
                "is_raw_detail_suppressed": True,
                "abstract_mechanism": "Scale separation controls boundary concentration while preserving the energy-pressure compactness route.",
                "main_research_object": "MHD boundary weak-solution model with localized pressure and magnetic energy coupling.",
                "why_mechanism_is_research_level": "The mechanism creates a standalone boundary regularity theorem for the coupled model.",
                "candidate_not_about_raw_detail": "The statement is about weak solutions and pressure coupling, not the annular region itself.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertTrue(result.ok, messages)
            self.assertFalse(any(issue.quality_metric == "proof_detail_candidate_forbidden" for issue in result.issues))

    def test_general_style_rejects_input_family_variant_direction_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["research_direction_gate"] = {
                "main_object_shift": "This stays in the same theorem family with a minor variant.",
                "not_input_family_variant": False,
                "interesting_model_or_object": "The input theorem is adjusted by routine bookkeeping.",
                "new_obstruction_not_in_input": "No new obstruction beyond the same proof.",
                "why_direction_is_not_routine": "It is a small variant of the input theorem.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_research_direction_gate" for issue in result.issues))

    def test_general_style_rejects_raw_detail_leaking_after_claimed_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["title"] = "No-neck heat-density decay for a local neck set"
            candidate["novelty_axis"] = "heat-density neck set localization"
            candidate["precise_problem_statement"] = (
                GOOD_STATEMENT
                + " Prove that the heat-density drop on each neck set controls the localized defect measure."
            )
            candidate["abstraction_lift"] = {
                "raw_proof_detail_used": "heat-density drops and neck set localization",
                "is_raw_detail_suppressed": True,
                "abstract_mechanism": "Scale separation and concentration control for the main solution class.",
                "main_research_object": "Boundary weak solutions of the elliptic equation with Dini coefficients.",
                "why_mechanism_is_research_level": "The mechanism could support a standalone theorem for the main PDE object.",
                "candidate_not_about_raw_detail": "The candidate claims not to be about the raw proof detail.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "proof_detail_candidate_forbidden" for issue in result.issues))

    def test_general_style_allows_high_level_object_terms_in_abstraction_lift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["title"] = "Tangent-pair compactness for boundary weak solutions"
            candidate["novelty_axis"] = "tangent-pair compactness and packing for a boundary model"
            candidate["abstraction_lift"] = {
                "raw_proof_detail_used": "input theorem tangent-pair compactness and packing stationarity",
                "is_raw_detail_suppressed": True,
                "abstract_mechanism": "Compactness and packing for the main boundary weak-solution object.",
                "main_research_object": "Boundary weak solutions with tangent-pair compactness and packing estimates.",
                "why_mechanism_is_research_level": "The mechanism supports a standalone theorem for the main PDE object.",
                "candidate_not_about_raw_detail": "The statement is about weak solutions and tangent-pair compactness, not a local proof device.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertTrue(result.ok)
            self.assertFalse(any(issue.quality_metric == "proof_detail_candidate_forbidden" for issue in result.issues))

    def test_general_style_rejects_unknown_pressure_point_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "boundary pressure point",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It changes one proof pressure point into a publishable boundary estimate.",
                    "one_step_change_from_input": "Move the estimate to a boundary half-ball.",
                    "proof_route_shortness": "One boundary trace lemma should start the proof.",
                    "novelty_defense": "The input theorem is interior and does not control boundary trace errors.",
                    "candidate_origin_type": "model-case theorem",
                    "adjacent_model_transfer": False,
                    **_strong_general_fields(),
                    **_research_level_fields(),
                    "pressure_point_id": "PP-fake",
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(
                paper / "result.json",
                {
                    "pressure_points": [
                        {
                            "pressure_point_id": "PP-good",
                            "source": "Theorem 2.1",
                        }
                    ]
                },
            )
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("unknown pressure_point_id", messages)

    def test_general_style_warns_on_composite_pressure_point_id_with_known_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "boundary pressure point",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It changes one proof pressure point into a publishable boundary estimate.",
                    "one_step_change_from_input": "Move the estimate to a boundary half-ball.",
                    "proof_route_shortness": "One boundary trace lemma should start the proof.",
                    "novelty_defense": "The input theorem is interior and does not control boundary trace errors.",
                    "candidate_origin_type": "model-case theorem",
                    "adjacent_model_transfer": False,
                    **_strong_general_fields(),
                    "pressure_point_id": "PP-good / PP-other as applicable",
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(
                paper / "result.json",
                {"pressure_points": [{"pressure_point_id": "PP-good", "source": "Theorem 2.1"}]},
            )
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertTrue(result.ok)
            self.assertTrue(any("multiple/non-canonical pressure_point_id" in issue.message for issue in result.issues))

    def test_general_style_rejects_unknown_theorem_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "boundary pressure point",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It changes one proof pressure point into a publishable estimate.",
                    "one_step_change_from_input": "Move the estimate to a boundary half-ball.",
                    "proof_route_shortness": "One boundary trace lemma should start the proof.",
                    "novelty_defense": "The input theorem is interior and does not control boundary trace errors.",
                    "candidate_origin_type": "model-case theorem",
                    "adjacent_model_transfer": False,
                    **_strong_general_fields(),
                    **_research_level_fields(),
                    "closest_input_result": "Theorem 9.9 gives the interior estimate.",
                    "based_on_theorem_cards": ["Theorem 9.9"],
                    "input_anchor": {
                        **_strong_general_fields()["input_anchor"],
                        "closest_result": "Theorem 9.9",
                    },
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "theorem_cards.json", [{"theorem_label": "Theorem 2.1."}])
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("input theorem anchor does not cite", messages)

    def test_general_style_accepts_known_theorem_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "boundary pressure point",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It changes one proof pressure point into a publishable estimate.",
                    "one_step_change_from_input": "Move the estimate to a boundary half-ball.",
                    "proof_route_shortness": "One boundary trace lemma should start the proof.",
                    "novelty_defense": "The input theorem is interior and does not control boundary trace errors.",
                    "candidate_origin_type": "model-case theorem",
                    "adjacent_model_transfer": False,
                    **_strong_general_fields(),
                    **_research_level_fields(),
                    "closest_input_result": "Theorem 2.1 gives the interior estimate.",
                    "based_on_theorem_cards": ["Theorem 2.1."],
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "theorem_cards.json", [{"theorem_label": "Theorem 2.1."}])
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertTrue(result.ok)
            self.assertNotIn("input theorem anchor does not cite", messages)

    def test_general_style_rejects_unknown_method_transfer_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["source_method_module_id"] = "MM99"
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("source_method_module_id='MM99'", messages)
            self.assertIn("absent from method_transfer_map.json", messages)

    def test_general_style_accepts_method_transfer_candidate_from_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertTrue(result.ok, messages)
            self.assertFalse(any(issue.quality_metric == "unknown_method_module_id" for issue in result.issues))

    def test_general_style_rejects_transfer_candidate_missing_failure_term(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate.pop("new_failure_term")
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")
            messages = "\n".join(issue.message for issue in result.issues)

            self.assertFalse(result.ok)
            self.assertIn("lacks required transfer-generation fields", messages)
            self.assertIn("new_failure_term", messages)

    def test_general_style_requires_adjacent_model_pool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_adjacent_model_pool" for issue in result.issues))

    def test_general_style_rejects_transfer_target_absent_from_pool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            pool = _adjacent_model_pool()
            pool["adjacent_model_pool"][0]["target_model"] = "Different adjacent model"
            _write_json(paper / "adjacent_model_pool.json", pool)
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "unknown_adjacent_model_pool_target" for issue in result.issues))

    def test_general_style_ignores_non_transfer_sentinel_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.update(
                {
                    "question_strategy_used": "boundary pressure point",
                    "strategy_fit_score": 8,
                    "why_this_is_good_research_question": "It changes one proof pressure point into a publishable boundary estimate.",
                    "one_step_change_from_input": "Move the estimate to a boundary half-ball.",
                    "proof_route_shortness": "One boundary trace lemma should start the proof.",
                    "novelty_defense": "The input theorem is interior and does not control boundary trace errors.",
                    "candidate_origin_type": "non-transfer boundary theorem",
                    "adjacent_model_transfer": False,
                    "source_method_module_id": "not_applicable_non_transfer",
                    **_strong_general_fields(),
                }
            )
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertTrue(result.ok)
            self.assertFalse(any(issue.quality_metric == "unknown_method_module_id" for issue in result.issues))

    def test_general_style_rejects_proof_module_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _method_transfer_candidate("c01")
            candidate["candidate_origin_type"] = "proof module of input theorem"
            candidate["research_level_gate"] = {
                "is_independent_research_problem": False,
                "not_merely_input_lemma": "This is merely a lemma from the input proof.",
                "why_publishable_if_solved": "Not independent.",
                "what_new_object_or_model_is_added": "No new object.",
                "why_not_just_technical_cleanup": "It is technical cleanup.",
            }
            _write_json(paper / "adjacent_model_pool.json", _adjacent_model_pool())
            _write_json(paper / "method_transfer_map.json", _method_transfer_map())
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1, question_style="general")

            self.assertFalse(result.ok)
            self.assertTrue(any(issue.quality_metric == "proof_module_candidate_forbidden" for issue in result.issues))
            self.assertTrue(any(issue.quality_metric == "weak_research_level_gate" for issue in result.issues))

    def test_weak_paper_survey_use_is_warning_not_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidate = _candidate("c01")
            candidate.pop("paper_survey_used")
            candidate.pop("known_result_to_avoid")
            _write_json(paper / "candidate_questions.json", [candidate])
            _write_json(paper / "ranked_questions.json", [candidate])

            result = validate_candidate_outputs(root, n=1, expected_candidates=1)
            write_candidate_quality_flags(root, 1, result)
            flags = json.loads((paper / "candidate_quality_flags.json").read_text(encoding="utf-8"))

            self.assertTrue(result.ok)
            self.assertTrue(any(issue.quality_metric == "weak_paper_survey_use" for issue in result.issues))
            self.assertEqual(flags["flags"]["c01"]["validation_quality"], "weak_paper_survey_use")
            self.assertGreater(flags["flags"]["c01"]["validation_penalty"], 0)

    def test_candidate_repair_prompt_is_written_for_failed_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            _write_json(paper / "candidate_questions.json", [_candidate("c01")])
            _write_json(paper / "ranked_questions.json", [_candidate("c02")])

            result = validate_candidate_outputs(root, n=1, expected_candidates=2)
            path = write_candidate_repair_prompt(root, "batch_test", result)

            self.assertIsNotNone(path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("Please repair the QAgent candidate-generation outputs", text)
            self.assertIn("outputs/batch_test/paper_###/candidate_questions.json", text)
            self.assertIn("Do not create or modify any `selected/` folders", text)
            self.assertIn("Expected 2 candidates", text)

    def test_excess_candidates_are_trimmed_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper_001"
            paper.mkdir()
            candidates = [_candidate("c01"), _candidate("c02"), _candidate("c03")]
            _write_json(paper / "candidate_questions.json", candidates)
            _write_json(paper / "ranked_questions.json", list(reversed(candidates)))

            report = trim_excess_candidate_outputs(root, n=1, expected_candidates=2)
            result = validate_candidate_outputs(root, n=1, expected_candidates=2)
            trimmed_candidates = json.loads((paper / "candidate_questions.json").read_text(encoding="utf-8"))
            trimmed_ranked = json.loads((paper / "ranked_questions.json").read_text(encoding="utf-8"))

            self.assertTrue(result.ok)
            self.assertEqual([item["question_id"] for item in trimmed_candidates], ["c01", "c02"])
            self.assertEqual({item["question_id"] for item in trimmed_ranked}, {"c01", "c02"})
            self.assertTrue(report["actions"])


def _candidate(question_id: str) -> dict[str, object]:
    return {
        "question_id": question_id,
        "title": f"Boundary estimate candidate {question_id}",
        "precise_problem_statement": GOOD_STATEMENT,
        "mechanism_labels": ["E. Setting generalization"],
        "novelty_assessment": "The statement is not the input theorem; it changes the boundary setting and targets a narrower estimate not listed as known.",
        "method_delta": "Small method delta: adapt the paper's Caccioppoli and compactness argument to a boundary flattening step.",
        "fast_sci_route": "A 5-8 lemma route should prove the model estimate before extending to the full coefficient class.",
        "journal_fit": "JMAA/CPAA-level if the boundary estimate is new but uses standard elliptic tools.",
        "novelty_axis": "boundary version of an interior elliptic estimate",
        "closest_input_result": "The input theorem proves an interior Caccioppoli estimate away from the boundary.",
        "why_not_direct_corollary": "The boundary flattening and trace terms are not handled by the interior theorem.",
        "why_not_standard_theorem": "The Dini coefficient boundary estimate is formulated for the paper-specific weak solution class.",
        "paper_survey_used": "paper_literature_survey.json checked the input paper and nearby boundary regularity results.",
        "related_work_checked": "Standard boundary regularity theorem and the input interior Caccioppoli theorem.",
        "known_result_to_avoid": "Avoid direct restatement of the input interior estimate and routine smooth-boundary corollaries.",
        "transfer_pattern_used": "TP03 Boundary Transfer",
        "parent_transfer_pattern": "Setting Transfer",
        "domain_gate": "The paper is an elliptic regularity paper, so boundary transfer is domain-appropriate; no concentration, varifold, Yamabe, or dispersive mechanism is used.",
        "source_theorem_or_method": "Interior Caccioppoli and compactness estimate from the input elliptic theorem.",
        "target_model": "Boundary Dirichlet problem on a C^2 domain with Dini coefficients.",
        "new_obstruction": "Boundary flattening creates coefficient and trace errors in the energy estimate.",
        "why_old_proof_may_survive": "The Caccioppoli, compactness, and coefficient-freezing modules survive after a boundary cutoff.",
        "minimal_publishable_version": "Prove a boundary Caccioppoli estimate for a model Dirichlet problem before treating full regularity.",
        "forbidden_mechanisms_avoided": "No no-neck, varifold, Yamabe, free-boundary, or dispersive language is used because those domains are irrelevant.",
        "transfer_pattern_fit_score": 9,
        "final_score": 100,
    }


def _strong_general_fields() -> dict[str, object]:
    return {
        "input_anchor": {
            "closest_result": "Input Theorem 2.1 gives the interior Caccioppoli estimate.",
            "exact_assumption_changed": "The candidate moves the estimate to a boundary half-ball.",
            "proof_step_where_used": "The cutoff argument uses interior balls before the compactness step.",
            "why_this_step_is_fragile": "Boundary flattening creates trace and coefficient errors not present inside.",
        },
        "pressure_point_id": "PP-boundary-caccioppoli-cutoff",
        "direct_corollary_attack": {
            "attack_from_input_theorem": "1. Apply the input interior theorem to a ball near the boundary. 2. The ball crosses the boundary. 3. The proof fails because trace terms are not controlled.",
            "attack_from_standard_theorem": "1. Apply standard boundary regularity after flattening. 2. Use the input Dini estimate. 3. This fails because the standard theorem does not preserve the paper's weak solution class.",
            "attack_from_routine_approximation": "1. Approximate the boundary by smooth domains. 2. Pass constants to the limit. 3. This fails because the trace error is not uniformly controlled.",
            "why_all_fail": "Each attack misses the new boundary flattening error term.",
        },
        "minimal_proof_route": {
            "known_modules_reused": ["interior Caccioppoli", "coefficient freezing"],
            "one_new_lemma_needed": "A boundary trace Caccioppoli lemma with Dini modulus.",
            "main_estimate_or_construction": "Flatten the boundary and close the trace error by Dini summability.",
        },
        **_research_level_fields(),
        **_abstraction_lift_fields(),
        **_research_direction_gate_fields(),
    }


def _research_level_fields() -> dict[str, object]:
    return {
        "research_level_gate": {
            "is_independent_research_problem": True,
            "not_merely_input_lemma": "The candidate is a standalone theorem in a transferred or changed model, not a lemma from the input proof.",
            "why_publishable_if_solved": "It gives a paper-level estimate with a named new obstruction and a short proof route.",
            "what_new_object_or_model_is_added": "It adds a boundary or adjacent-model object not present in the input theorem.",
            "why_not_just_technical_cleanup": "The new obstruction changes the proof rather than merely tracking constants or cleaning regularity.",
        }
    }


def _abstraction_lift_fields() -> dict[str, object]:
    return {
        "abstraction_lift": {
            "raw_proof_detail_used": "boundary cutoff in the localization proof",
            "is_raw_detail_suppressed": True,
            "abstract_mechanism": "Boundary error control for the main weak-solution estimate.",
            "main_research_object": "Boundary weak solutions of the elliptic equation with Dini coefficients.",
            "why_mechanism_is_research_level": "The mechanism supports a standalone boundary estimate for the main PDE object.",
            "candidate_not_about_raw_detail": "The candidate statement targets weak solutions and estimates, not the cutoff device.",
        }
    }


def _research_direction_gate_fields() -> dict[str, object]:
    return {
        "research_direction_gate": {
            "main_object_shift": "The question moves from an interior estimate to a boundary weak-solution theorem for the main PDE object.",
            "not_input_family_variant": True,
            "interesting_model_or_object": "Boundary weak solutions form an independent object because trace errors and boundary geometry are part of the theorem statement.",
            "new_obstruction_not_in_input": "Boundary flattening creates a trace-error term absent from the input interior theorem.",
            "why_direction_is_not_routine": "The proof needs a new boundary trace Caccioppoli lemma rather than constant tracking or a local proof-device cleanup.",
        }
    }


def _method_transfer_candidate(question_id: str) -> dict[str, object]:
    candidate = _candidate(question_id)
    candidate.update(
        {
            "question_strategy_used": "method-module adjacent-model transfer",
            "strategy_fit_score": 9,
            "why_this_is_good_research_question": "It transfers an energy-pressure module to the smallest coupled system where a new term appears.",
            "one_step_change_from_input": "Add a magnetic coupling to the energy-pressure estimate while keeping the same bounded domain and weak class.",
            "proof_route_shortness": "The proof reuses energy inequality and pressure decomposition plus one commutator lemma.",
            "novelty_defense": "The input theorem has no magnetic coupling and the standard MHD estimate does not cover this boundary pressure class.",
            "candidate_origin_type": "survey-supported adjacent-model transfer",
            "adjacent_model_transfer": True,
            "target_adjacent_model": "MHD boundary weak-solution model",
            "shared_method_structure": "Energy inequality plus pressure decomposition and compactness bootstrap.",
            "new_obstruction_after_transfer": "The Lorentz-force coupling creates a commutator in the pressure decomposition.",
            "why_transfer_is_not_random": "The transfer map identifies the same energy dissipation and compactness object in the MHD target.",
            "source_method_module_id": "MM01",
            "target_model_from_transfer_map": "MHD boundary weak-solution model",
            "shared_invariant": "Energy dissipation controls velocity and magnetic gradients in the same scaling class.",
            "structural_match_score": 8,
            "new_failure_term": "Lorentz-force commutator in the localized pressure equation.",
            "failure_type": "coupling",
            "one_new_lemma_needed": "A localized pressure-commutator estimate controlled by the magnetic energy.",
            "why_not_random_transfer": "The target shares the energy-pressure-compactness module and differs by one named coupling term.",
            **_strong_general_fields(),
        }
    )
    return candidate


def _method_transfer_map() -> dict[str, object]:
    return {
        "method_modules": [
            {
                "method_module_id": "MM01",
                "source_theorem_or_proof_step": "Theorem 2.1 pressure-energy bootstrap step",
                "method_module": "energy inequality plus pressure decomposition",
                "load_bearing_structure": {
                    "scaling": "Navier-Stokes parabolic scaling",
                    "energy_or_norm": "local energy norm for velocity gradients",
                    "compactness_object": "weak compactness of finite-energy solutions",
                    "cancellation_or_sign": "viscous dissipation has a sign",
                    "boundary_or_topology_condition": "boundary cutoff controls pressure terms",
                },
                "nearby_models": [
                    {
                        "target_model": "MHD boundary weak-solution model",
                        "shared_invariant": "Energy dissipation controls velocity and magnetic gradients in the same scaling class.",
                        "structural_match_score": 8,
                        "new_failure_term": "Lorentz-force commutator in the localized pressure equation.",
                        "failure_type": "coupling",
                        "one_new_lemma_needed": "A localized pressure-commutator estimate controlled by the magnetic energy.",
                        "why_not_random_transfer": "The target shares the energy-pressure-compactness module and differs by one named coupling term.",
                    }
                ],
            }
        ]
    }


def _adjacent_model_pool() -> dict[str, object]:
    return {
        "source_method": "energy-pressure compactness module",
        "adjacent_model_pool": [
            {
                "target_model": "MHD boundary weak-solution model",
                "shared_structure": "Energy dissipation and pressure compactness have the same load-bearing role.",
                "new_obstruction": "Lorentz-force commutator in the localized pressure equation.",
                "transfer_plausibility": 8,
                "why_this_is_not_a_topic_keyword_match": "The target is selected because the energy-pressure module survives with one coupling obstruction.",
            }
        ],
    }


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
