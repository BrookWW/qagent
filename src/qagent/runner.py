from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


CODEX_COMMAND_TEMPLATE = ["codex", "--search", "-c", 'model_reasoning_effort="xhigh"', "exec", "--json", "--skip-git-repo-check", "{prompt}"]
CODEX_DEFAULT_MODEL_SOURCE = "Codex CLI default from logged-in account/config"
CODEX_DEFAULT_REASONING_EFFORT = "xhigh"
MAX_INLINE_CODEX_PROMPT_CHARS = 24000
ACCESS_DENIED_MESSAGE = (
    "Codex CLI exists but cannot be executed. Start the app from WSL/Ubuntu or fix Windows Codex CLI permissions."
)


def _summarize(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def _materialize_command(
    prompt: str,
    model: str = "",
    *,
    use_search: bool = True,
    reasoning_effort: str = CODEX_DEFAULT_REASONING_EFFORT,
    json_output: bool = True,
    working_dir: str | Path | None = None,
) -> list[str]:
    command = ["codex"]
    if use_search:
        command.append("--search")
    if model.strip():
        command.extend(["-m", model.strip()])
    if reasoning_effort.strip():
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort.strip()}"'])
    command.append("exec")
    if json_output:
        command.append("--json")
    command.append("--skip-git-repo-check")
    if working_dir is not None:
        command.extend(["-C", Path(working_dir).as_posix()])
    command.append(prompt)
    return command


def _prompt_for_codex_arg(prompt: str) -> tuple[str, Path | None]:
    if len(prompt) <= MAX_INLINE_CODEX_PROMPT_CHARS:
        return prompt, None
    path = Path(tempfile.gettempdir()) / "qagent_codex_prompt.md"
    path.write_text(prompt, encoding="utf-8")
    return (
        f"Read the full QAgent prompt from `{path.as_posix()}` and execute it exactly. "
        "Do not summarize the prompt; follow the file instructions and write the requested outputs.",
        path,
    )


def codex_backend_metadata(
    model: str = "",
    *,
    use_search: bool = True,
    reasoning_effort: str = CODEX_DEFAULT_REASONING_EFFORT,
) -> dict[str, str]:
    model = model.strip()
    return {
        "backend": "codex_cli_logged_in",
        "api_mode": "no_api",
        "model": model or "codex_default",
        "model_source": f"explicit codex exec --model {model}" if model else CODEX_DEFAULT_MODEL_SOURCE,
        "search_enabled": "true" if use_search else "false",
        "reasoning_effort": reasoning_effort.strip() or "default",
    }


def check_codex_cli(timeout_seconds: int = 10) -> dict[str, Any]:
    codex_path = shutil.which("codex")
    if not codex_path:
        return {
            "available": False,
            "version": "",
            "error_message": "Codex CLI was not found on PATH.",
            "command": "codex --version",
            "return_code": None,
        }

    try:
        completed = subprocess.run(
            [codex_path, "--version"],
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except PermissionError:
        return {
            "available": False,
            "version": "",
            "error_message": ACCESS_DENIED_MESSAGE,
            "command": f"{codex_path} --version",
            "return_code": None,
        }
    except OSError as exc:
        message = ACCESS_DENIED_MESSAGE if "access is denied" in str(exc).lower() else str(exc)
        return {
            "available": False,
            "version": "",
            "error_message": message,
            "command": f"{codex_path} --version",
            "return_code": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "version": "",
            "error_message": "Timed out while checking Codex CLI.",
            "command": f"{codex_path} --version",
            "return_code": None,
        }

    combined = completed.stdout + completed.stderr
    if completed.returncode != 0:
        denied = "access is denied" in combined.lower()
        return {
            "available": False,
            "version": "",
            "error_message": ACCESS_DENIED_MESSAGE if denied else _summarize(combined.strip()),
            "command": f"{codex_path} --version",
            "return_code": completed.returncode,
        }

    return {
        "available": True,
        "version": completed.stdout.strip() or completed.stderr.strip(),
        "error_message": "",
        "command": f"{codex_path} --version",
        "return_code": completed.returncode,
    }


def build_codex_prompt(
    batch_path: str | Path,
    a: int,
    b: int,
    n: int = 10,
    mode: str = "deep",
    batch_id: str = "batch_001",
) -> str:
    batch_path = Path(batch_path).as_posix()
    initial_candidates = (a + 1) * b
    mode_title = "Deep Mode" if mode == "deep" else "Batch Mode"
    mode_instructions = (
        "Deep Mode is selected. Prioritize quality over speed and token cost. You may spend more reasoning and search time during candidate generation, and you must not lower question quality to save time. The highest priority is novelty/not-already-done: candidate generation must avoid direct corollaries and known-looking variants before writing candidate_questions.json. The second priority is short SCI route: prefer JDE/JMAA/CPAA-level problems that an AI-assisted human can attack quickly. The third priority is small method delta: reuse the paper's method or a nearby standard method with exactly one real new obstruction. For every paper perform paper resolving, metadata/full-text/PDF fetching when possible, theorem card extraction, proof mechanism extraction, limitation/gap extraction, candidate generation with self-gates, top-candidate novelty/duplicate search, lightweight hard-review trace, compact proof-route sanity check, and final selection. Always create the evidence files before generating questions. Do not allow final selection unless paper_profile.json, theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, and paper_reading_quality.json exist. Read paper_reading_quality.json before candidate generation; if high_confidence_final_questions_allowed is false, generate conservatively and mark lower confidence, and if must_prefer_needs_deeper_reading is true, prefer needs deeper reading rather than forcing weak problems. Hard novelty gate: no candidate can become final selected unless it has outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md. Survey only the top candidates needed for final selection by default, normally max(2b,b+2) per paper. Search local metadata, Crossref, OpenAlex, arXiv, and Semantic Scholar if available. Classify surveyed candidates as reproduction of input theorem, proof module of input theorem, known theorem or likely known theorem, plausible transfer question, plausible new theorem-level question, or too vague / insufficient evidence. High duplicate risk, reproduction, known/likely known, direct corollary, and too vague candidates cannot be selected. Medium or insufficient-evidence risk should be repaired earlier when possible; if still allowlisted as fallback, final selection should export it with low-confidence disclosure rather than failing the run. Full critic is optional; default hard review writes a lightweight candidate_critic trace."
        if mode == "deep"
        else "Batch Mode is selected. Perform lightweight screening only, clearly mark outputs as lower-confidence, and recommend which papers deserve a future Deep Mode run. Do not overclaim SCI-level readiness from Batch Mode."
    )

    return f"""Please run the QAgent workflow.

Follow:
- skills/qagent/SKILL.md
- prompts/question_agent_v0.md
- prompts/scoring_policy.md
- prompts/theorem_level_problem_rules.md
- prompts/deep_paper_reader.md
- prompts/theorem_extractor.md
- prompts/proof_mechanism_extractor.md
- prompts/gap_extractor.md
- examples/transfer_patterns_active.md

Input:
- {batch_path}

Do not use an API key.
Do not call the OpenAI API.
Use the Codex CLI execution context and the current workspace files.
Before this prompt is executed, the Streamlit app may already have run a local evidence preflight.
If outputs/{batch_id}/paper_001, paper_002, ... contain paper_profile.json, theorem_cards.json,
proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, paper_reading_quality.json, and paper_reader_report.md,
reuse those files as the authoritative reading artifacts. Preserve the paper_### directory names.
Do not replace concrete preflight evidence with generic abstract-level guesses.

Run parameters:
- candidate width parameter a = {a}
- final questions per paper b = {b}
- number of input papers n = {n}
- mode = {mode_title}
- initial candidate questions per paper = (a+1)*b = {initial_candidates}
- total initial candidate questions = n*(a+1)*b = {n * initial_candidates}
- total final selected questions = n*b = {n * b}

Task:
0. {mode_instructions}
1. Process exactly {n} normalized paper entries from {batch_path}.
2. For each paper, try to fetch the richest available source: PDF, HTML full text, abstract/metadata, or user information.
3. Extract paper text and create deep reading artifacts:
   - paper_profile.json
   - theorem_cards.json
   - proof_cards.json
   - method_cards.json
   - limitation_cards.json
   - gap_cards.json
   - paper_reading_quality.json
   - paper_reader_report.md
4. Do not create or require a per-paper survey_report.md. Use candidate-level novelty/duplicate evidence instead.
5. Evidence gate: do not generate final selected questions unless paper_profile.json, theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, and paper_reading_quality.json exist for the paper.
6. Use theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, and paper_reading_quality.json for question generation. Do not generate directly from title/abstract alone unless full text was unavailable.
7. If full text was unavailable and only title/abstract/metadata was read, set paper_reading_confidence = low and put the lower-confidence source note in metadata.json and feasibility_analysis.md, not in problem_statement.tex.
8. If theorem_cards are weak, missing, empty, only abstract-level, or paper_reading_quality.json says must_prefer_needs_deeper_reading, refuse to produce high-confidence theorem-level problems and output needs deeper reading.
9. For each paper, generate exactly {initial_candidates} initial candidate research questions.
10. Label every candidate with question-generation mechanism labels.
11. Score every candidate using prompts/scoring_policy.md, including all required score components.
12. For the top candidate questions needed for selection in Deep Mode, normally max(2b,b+2) per paper:
   - generate at least 8 search queries: exact title-style query, model + theorem type, model + conclusion, input paper title + proposed extension, key tool + target model, author names + related theorem, arXiv/CVGMT-style keyword query, and broad semantic query;
   - search local resolved paper metadata, Crossref, OpenAlex, arXiv, and Semantic Scholar if available;
   - do not scrape Google Scholar;
   - save the candidate-level novelty/duplicate evidence to outputs/{batch_id}/{{paper_id}}/candidate_surveys/{{question_id}}.md;
   - list nearby known results from the input paper itself, known classical theorems, and likely arXiv/CVGMT/OpenAlex/Crossref/Semantic Scholar hits;
   - classify it as reproduction of input theorem, proof module of input theorem, known theorem or likely known theorem, plausible transfer question, plausible new theorem-level question, or too vague / insufficient evidence;
   - assign duplicate risk low/medium/high and recommended action keep/revise/remove.
13. By default, write a lightweight hard-review trace instead of a full critic review. If full critic mode is explicitly enabled, run a critic review answering:
   - Is this theorem-level?
   - Are domain, object class, assumptions, and conclusion explicit?
   - Is it a direct restatement of the input paper?
   - Is it likely already known?
   - Is it too broad?
   - Is it too trivial?
   - Does it arise from a concrete theorem skeleton, proof pressure point, survey-supported small variation, or justified transfer mechanism?
   - What is the new obstruction?
   - Can the configured Codex/QED proving agent quickly start proving it?
   - Could it plausibly become a small SCI-level result?
   Save the critic or lightweight trace to outputs/{batch_id}/{{paper_id}}/candidate_critic/{{question_id}}.md.
14. Do not run legacy broad refinement rounds after candidate generation. The local app handles
   candidate survey, hard review, and replacement. Use those artifacts as the refinement evidence.
15. Write only a compact selection trace: for every final keep/remove decision, record the novelty
   evidence, direct-corollary evidence, one proof-route sanity check, and the final reason.
16. Select up to {b} final questions per paper from the hard-review allowlist.
18. Optimize selection for:
   - configured Codex/QED proving-agent quick attackability;
   - nontrivial but not too hard;
   - plausible novelty;
   - SCI-level publishable potential;
   - not necessarily a top-tier breakthrough;
   - avoiding trivial exercises;
   - avoiding huge open problems requiring new theory.
19. Each final selected question folder must contain:
   - problem_statement.tex
   - additional_prove_human_help_global.md
   - additional_verify_rule_global.md
   - survey_queries.md
   - feasibility_analysis.md
   - metadata.json
20. problem_statement.tex must contain a narrowed, paper-specific LaTeX theorem-style problem.
   - It must obey prompts/theorem_level_problem_rules.md.
   - It must contain only the clean mathematical problem inside \\begin{{q}}...\\end{{q}}.
   - Do not assemble q environments from generic metadata sections.
   - Do not put source-confidence notes, novelty disclaimers, placeholder instructions, or proof-agent suitability text inside problem_statement.tex.
   - If no candidate can be written as a clean theorem-level q statement, write exactly: No suitable new theorem-level problem found.
21. additional_prove_human_help_global.md must contain concrete proof guidance.
22. additional_verify_rule_global.md must contain concrete verification points.
23. survey_queries.md must contain survey/literature-check queries.
24. feasibility_analysis.md must contain a domain-specific value judgment, quick proof attempt, obstacles, counterexample mechanisms, suggested revision, and recommendation, summarizing only the surviving question's final proof sprint.
25. metadata.json must contain the core selection fields only: question_id, title, final_score,
   selected rank, recommendation, selection rationale, survey evidence path, survey duplicate
   risk, critic/trace summary, validation quality, fallback status, and backend fields.
26. High duplicate risk candidates cannot be final selected questions.
27. Reproduction of input theorem cannot be final selected unless the user explicitly asks for reproduction.
28. Known theorem or likely known theorem cannot be final selected.
29. Too vague candidates cannot be final selected; insufficient-evidence candidates should be repaired earlier when possible and otherwise exported only as low-confidence allowlisted fallback.
30. Proof module questions may survive only if useful and explicitly labeled as module questions.
31. Plausible transfer questions and plausible new theorem-level questions should be preferred if precise and feasible.
32. A candidate cannot be selected unless hard review allowlists it; weak critic verdicts become low-confidence final disclosures rather than a final-stage hard failure when no better allowlisted candidate exists.
33. If no plausible proof route exists, remove.
34. If the proof route is just apply known theorem directly, remove as too trivial.
35. If it requires a major new theory, remove as too ambitious.
36. If it is a direct restatement of an existing theorem, remove.
37. Prefer problems where the proof route adapts a known tool to a genuinely new obstruction.
38. Final selected question survey_queries.md must include search queries, nearby results, duplicate risk, and final reason why it survived the hard novelty gate.
39. If full text was unavailable, record the lower-confidence source note in metadata.json and feasibility_analysis.md, not in problem_statement.tex.
40. Save the compact per-paper selection trace to outputs/{batch_id}/{{paper_id}}/refinement_rounds.md for compatibility.
41. Update outputs/{batch_id}/batch_report.md from the actual selected metadata.

Quality requirements:
- Selected question titles must be paper-specific and not generic templates.
- Scores must reflect the actual candidate and must not be generic templates.
- problem_statement.tex must use narrowed model theorems, not generic natural-setting language.
- problem_statement.tex must contain an explicit domain/setting, object class, assumptions, equation/functional/geometric object, and concrete conclusion.
- feasibility_analysis.md must be domain-specific and must not import irrelevant proof mechanisms from other fields.

Validation:
After writing outputs, validate:
- {n} paper directories;
- {initial_candidates} candidate questions per paper;
- {initial_candidates} ranked questions per paper;
- {b} final selected question folders per paper;
- every selected question folder has all 6 required files.

Report the validation result when finished."""


def build_candidate_generation_prompt(
    batch_path: str | Path,
    a: int,
    b: int,
    n: int = 10,
    mode: str = "deep",
    batch_id: str = "batch_001",
    question_style: str = "specialized",
) -> str:
    batch_path = Path(batch_path).as_posix()
    initial_candidates = (a + 1) * b
    mode_title = "Deep Mode" if mode == "deep" else "Batch Mode"
    style = normalize_question_style(question_style)
    style_title = "General Research Style" if style == "general" else "Specialized Transfer-Pattern Style"
    style_follow = (
        "- examples/general_research_question_principles.md"
        if style == "general"
        else "- examples/transfer_patterns_active.md\n- examples/successful_transfer_patterns.md"
    )
    style_schema = (
        """     input_anchor, pressure_point_id,
     one_step_change_from_input, new_obstruction,
     direct_corollary_precheck, why_generation_survives_direct_corollary_filter,
     direct_corollary_attack, minimal_proof_route, research_level_gate, abstraction_lift,
     research_direction_gate,
     question_strategy_used, strategy_fit_score, why_this_is_good_research_question,
     proof_route_shortness, novelty_defense,
     candidate_origin_type, adjacent_model_transfer, target_adjacent_model,
     shared_method_structure, new_obstruction_after_transfer, why_transfer_is_not_random,
     source_method_module_id, target_model_from_transfer_map, shared_invariant,
     structural_match_score, new_failure_term, failure_type, one_new_lemma_needed,
     why_not_random_transfer,"""
        if style == "general"
        else """     transfer_pattern_used, source_theorem_or_method, target_model,
     new_obstruction, why_old_proof_may_survive, minimal_publishable_version,
     parent_transfer_pattern, domain_gate, forbidden_mechanisms_avoided,
     transfer_pattern_fit_score, domain_gate_fit, wrong_domain_mechanism_penalty,
     successful_transfer_fit,"""
    )
    style_instructions = (
        """   General question style is selected. Use examples/general_research_question_principles.md
   as research taste guidance, not as a rigid template. Do not force a TP## transfer pattern.
   Before generating candidates, internally extract theorem skeletons and 5-8 proof-level
   pressure points from the input paper. A pressure point is an exact theorem/proof
   step where a hypothesis, estimate, compactness argument, endpoint, boundary term,
   topology, coefficient condition, or stability assumption is fragile. Generate candidates
  only by either transferring a load-bearing method module to a structurally adjacent target
  or modifying exactly one pressure point into an independent research problem about the main
  equation, flow, variational object, solution class, operator, or geometric object. Initial generation should focus on the
  mathematical bones, not filling a report. First decide whether the candidate has:
  precise_problem_statement/candidate_statement, input_anchor, one_step_change_from_input,
  new_obstruction, minimal_proof_route, research_level_gate, abstraction_lift,
  research_direction_gate, and direct_corollary_attack. Only after it survives
   these core checks should you add ranking metadata such as strategy_fit_score,
   why_this_is_good_research_question, candidate_origin_type, and adjacent-model transfer fields.
   Prefer freedom and mathematical naturalness over matching a specialized pattern.
   Before writing method_transfer_map.json, create outputs/{batch_id}/{paper_id}/adjacent_model_pool.json.
   The pool must list structurally adjacent targets discovered from the input method modules, not from
   fashionable topic names. Each target must name shared_structure, new_obstruction, and
   transfer_plausibility. Then create outputs/{batch_id}/{paper_id}/method_transfer_map.json.
   This is a generation artifact, not a report. It must convert the input paper's proof modules
   into possible adjacent-model transfers. The map must contain method_modules, each with
   method_module_id, source_theorem_or_proof_step, method_module, load_bearing_structure,
   and nearby_models. Each nearby model must name target_model, shared_invariant,
   structural_match_score, new_failure_term, failure_type, one_new_lemma_needed,
   and why_not_random_transfer.
   Do not use a numeric transfer quota. Generate method-transfer candidates when the evidence supports
   credible nearby models in adjacent_model_pool.json / method_transfer_map.json. A method-transfer candidate
   must cite source_method_module_id from the map and copy/adapt a target_model_from_transfer_map,
   shared_invariant, new_failure_term, failure_type, one_new_lemma_needed, and
   why_not_random_transfer. Local endpoint/robustness/quantitative/counterexample candidates are acceptable
   only when they are independent research problems about the main mathematical object, not local cleanups.
  Pure proof-module, input-lemma, or technical-cleanup candidates are forbidden in general style.
   Proof details are evidence, not research objects. If the paper uses a localized region, cutoff,
   covering, coordinate device, approximation step, or parameter bookkeeping, abstract it into the
   mechanism it serves (scale separation, concentration control, localization, compactness, coercivity,
   cancellation, boundary error control, or stability), then formulate the question about the main
   research object or target model. The candidate title, novelty axis, and theorem statement must not
   be about the raw proof device itself.
  Do not make random model hops. Use adjacent-model transfer only when paper_literature_survey.json
   or the extracted theorem/proof/method cards reveal a shared load-bearing structure: method module
   similarity, invariant/energy/compactness similarity, and one named new failure term in the target.
   General transfer principle: extract the abstract role of the method, not the topic name. Ask
   what mathematical structure the proof uses (scaling, variational identity, monotonicity,
   compactness object, coercive estimate, cancellation, conservation law, entropy, defect measure,
   comparison principle, or topological invariant), then search for a different but nearby model
   where the same structure is present and exactly one new obstruction appears. The target must be
  close enough that the old method gives a credible first proof route, and different enough that
  solving it would be an independent research problem.
  Before accepting the candidate pool, run a direction-level self-check: if the pool mostly
  stays inside small variants of the input theorem family, regenerate the weakest candidates.
  Strong general-mode candidates should usually change the main research object, target model,
  solution class, operator, or obstruction; merely changing an auxiliary lemma, local region,
  cutoff, constant, endpoint wording, or proof bookkeeping is not enough."""
        if style == "general"
        else """   Specialized transfer-pattern style is selected. Transfer patterns are idea sources, not
   mandatory templates. First identify the paper domain, theorem type, proof mechanism, and
   actual gap. Then choose a pattern only if it creates a concrete new obstruction. A strong
   match names the parent pattern, TP id, source theorem or method, target model, new
   obstruction, why the old proof may survive, and the smallest publishable version.
   If no strong pattern fits, write the weakest honest fit and give a low transfer_pattern_fit_score;
   do not invent a fake match."""
    )
    style_score_fields = (
        "general_strategy_fit, strategy_fit_score, proof_route_shortness_score,"
        if style == "general"
        else "successful_transfer_pattern_fit, transfer_pattern_fit_score, domain_gate_fit, wrong_domain_mechanism_penalty,"
    )
    return f"""Please run QAgent candidate generation only.

Follow:
- skills/qagent/SKILL.md
- prompts/question_agent_v0.md
- prompts/scoring_policy.md
- prompts/theorem_level_problem_rules.md
- prompts/deep_paper_reader.md
- prompts/theorem_extractor.md
- prompts/proof_mechanism_extractor.md
- prompts/gap_extractor.md
{style_follow}

Input:
- {batch_path}

Use the existing local evidence preflight artifacts under outputs/{batch_id}/paper_001, paper_002, ...
Treat paper_profile.json, theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json,
gap_cards.json, paper_reading_quality.json, paper_reader_report.md, and paper_literature_survey.json
as authoritative pre-generation artifacts. Preserve paper_### directory names.
If outputs/{batch_id}/gpt_pro_handoff/results/paper_###.json exists, treat it as external GPT Pro expert evidence
for candidate generation and survey. Use it critically; do not copy weak or template candidates.

Run parameters:
- candidate width parameter a = {a}
- final questions per paper b = {b}
- number of input papers n = {n}
- mode = {mode_title}
- question style = {style_title}
- initial candidate questions per paper = (a+1)*b = {initial_candidates}

Task:
1. Process exactly {n} paper directories named paper_001 through paper_{n:03d}.
2. Do not write any outputs/{batch_id}/{{paper_id}}/selected directory or final selected-question files in this phase.
3. For each paper, read the preflight evidence files, including paper_reading_quality.json and paper_literature_survey.json. Do not create per-paper survey_report.md; the local hard_review stage will create candidate-level novelty/duplicate evidence.
   If paper_reading_quality.json says high_confidence_final_questions_allowed is false, generate conservatively and record lower confidence in result.json.
   If paper_reading_quality.json says must_prefer_needs_deeper_reading is true, do not force weak theorem-level candidates; write needs deeper reading or a clearly labeled low-confidence theorem-level candidate only if the evidence supports it. In general style, do not output proof-module/input-lemma candidates.
4. Before generating candidates for a paper, use paper_literature_survey.json as a hard negative map:
   - do not generate ideas listed under do_not_generate;
   - treat likely_known_directions as strong duplicate-risk warnings;
   - prefer recommended_candidate_angles and safe_novelty_gaps only when the theorem/proof/gap cards support them;
   - if survey_confidence is low, keep novelty claims cautious and require a clearer new obstruction.
   If the available evidence does not identify where an assumption is used in a proof, do not invent
   the proof step. Mark input_anchor.proof_step_where_used as "evidence insufficient" and either
   generate a lower-confidence theorem-level candidate anchored only in the theorem statement, or
   use full-paper/survey evidence before making proof-level claims.
5. If question style is General Research Style, write outputs/{batch_id}/{{paper_id}}/adjacent_model_pool.json before method_transfer_map.json.
   The pool must have this shape:
   {{
     "source_method": "load-bearing method role extracted from method/proof cards",
     "adjacent_model_pool": [
       {{
         "target_model": "...",
         "shared_structure": "energy / scale / compactness / cancellation / monotonicity / entropy / comparison / topology / other",
         "new_obstruction": "...",
         "transfer_plausibility": 0,
         "why_this_is_not_a_topic_keyword_match": "..."
       }}
     ]
   }}
   Then write outputs/{batch_id}/{{paper_id}}/method_transfer_map.json before candidate_questions.json.
   The map must have this shape:
   {{
     "method_modules": [
       {{
         "method_module_id": "MM01",
         "source_theorem_or_proof_step": "Theorem/Lemma/proof step label from theorem/proof/method cards",
         "method_module": "monotonicity | blow-up | Caccioppoli iteration | compactness | entropy | Carleman | maximum principle | stress-energy | calibration | epiperimetric inequality | other",
         "load_bearing_structure": {{
           "scaling": "...",
           "energy_or_norm": "...",
           "compactness_object": "...",
           "cancellation_or_sign": "...",
           "boundary_or_topology_condition": "..."
         }},
         "nearby_models": [
           {{
             "target_model": "...",
             "shared_invariant": "...",
             "structural_match_score": 0,
             "new_failure_term": "...",
             "failure_type": "boundary | curvature | commutator | nonlocal_tail | coupling | topology | anisotropy | lack_of_sign | pressure | forcing | other",
             "one_new_lemma_needed": "...",
             "why_not_random_transfer": "..."
           }}
         ]
       }}
     ]
   }}
   If evidence is too weak for proof-level transfer, write a low-confidence map with
   "evidence insufficient" entries and do not invent proof steps.
6. Generate exactly {initial_candidates} initial candidate research questions per paper.
   Candidate generation is the main quality gate. Do not output weak candidates and expect hard review
   or replacement to repair them later. Before a candidate is written to candidate_questions.json,
   internally reject and regenerate it if it is a direct corollary, too close to the input theorem,
   not theorem-form, missing a concrete new obstruction, missing a short proof route, too ambitious,
   too trivial, centered on a raw proof detail, or an unsupported adjacent-model jump. Try at most
   three internal regeneration passes for a paper. Do not hard-stitch weak candidates or invent
   high-quality-looking evidence just to satisfy the count. If after three passes you cannot honestly
   write exactly {initial_candidates} candidates that pass these self-gates, leave the shortage or
   validation problem visible in result.json so the local validator can trigger repair/failure.
7. Every candidate must be theorem-level enough for hard review:
   - question_id, title, mechanism_labels, precise_problem_statement, why_natural,
     expected_tools, possible_obstacles, minimal_version, ambitious_version,
     first_sanity_checks, based_on_theorem_cards, based_on_gap_cards,
     based_on_method_cards, based_on_limitation_cards, score_breakdown,
     novelty_assessment, method_delta, fast_sci_route, journal_fit,
     novelty_axis, closest_input_result, why_not_direct_corollary,
     why_not_standard_theorem,
{style_schema}
     paper_survey_used, related_work_checked, known_result_to_avoid,
     final_score, weighted_score.
   The candidate must explicitly explain:
   - why it is not already the input theorem or likely known;
   - which paper_literature_survey related papers/directions were checked;
   - which known result or direction it is explicitly avoiding;
   - the closest known/input result it differs from;
   - the small method delta and single new obstruction;
   - why it is neither too ambitious nor too easy;
   - why it could plausibly become a short JDE/JMAA/CPAA-level result.
   Every general-style candidate must include research_level_gate:
   {{
     "is_independent_research_problem": true,
     "not_merely_input_lemma": "...",
     "why_publishable_if_solved": "...",
     "what_new_object_or_model_is_added": "...",
     "why_not_just_technical_cleanup": "..."
   }}
  Every general-style candidate must include abstraction_lift:
   {{
     "raw_proof_detail_used": "raw proof device noticed, or 'none'",
     "is_raw_detail_suppressed": true,
     "abstract_mechanism": "the general mechanism served by the raw device",
     "main_research_object": "the equation, variational object, flow, solution class, geometric object, operator, or target model the question is really about",
     "why_mechanism_is_research_level": "why this mechanism can support an independent theorem",
     "candidate_not_about_raw_detail": "explicitly state why the title/statement are not about the raw device"
  }}
  Every general-style candidate must include research_direction_gate:
  {{
    "main_object_shift": "what main equation / model / flow / variational object / solution class / operator / geometric object changes, or why the same object still yields a standalone theorem",
    "not_input_family_variant": true,
    "interesting_model_or_object": "why the target object is mathematically worth studying, not just a relabeling of the input theorem",
    "new_obstruction_not_in_input": "the named obstruction absent from the input paper",
    "why_direction_is_not_routine": "why this is not a local lemma, constant-tracking exercise, endpoint cleanup, or direct corollary"
  }}
  If not_input_family_variant is false, do not output the candidate; replace it before
  candidate_questions.json is written.
  Pure proof-module, input-lemma, constant-tracking, or technical-cleanup candidates are forbidden.
   Before writing any candidate, perform a direct-corollary precheck with three attacks:
   Attack A: can the input theorem imply it after simple substitution or localization?
   Attack B: can a standard theorem imply it after applying the input estimate?
   Attack C: can routine approximation, density, regularity cleanup, constant tracking, or
   compactness yield it after the input result? If any attack succeeds in fewer than five
   mathematical steps, do not output that candidate. The direct_corollary_attack must be
   written as an attempted proof with numbered or explicit steps, not a verbal judgment.
   It must include all four fields attack_from_input_theorem,
   attack_from_standard_theorem, attack_from_routine_approximation, and why_all_fail.
   The why_all_fail field must summarize the exact failed step in each attack.
   Missing why_all_fail, or missing two or more attack fields, will trigger automatic
   candidate repair before novelty/hard review.
   Replace bad candidates with a candidate whose direct_corollary_attack explains why all attacks fail and whose
   why_generation_survives_direct_corollary_filter names a real non-cosmetic obstruction.
   Do not fill the list with routine constant tracking, smoothness cleanup, notation changes,
   direct applications of known theorems, or candidates whose proof route starts only with
   "by standard arguments".
   Formal statement gate: before accepting a candidate, check that all objects, domains,
   dimensions, regularity assumptions, boundary conditions, parameter ranges, and conclusions
   are specified. Reject or repair candidates containing "suitable assumptions", "natural
   conditions", "appropriate hypotheses", or any informal theorem placeholder.
{style_instructions}
   Do not use specialized mechanisms such as no-neck, bubble tree,
   energy identity, varifold compactness, De Giorgi iteration, Yamabe Green-function blow-up,
   free-boundary stratification, or dispersive estimates unless the input paper or target model
   genuinely belongs to that domain.
   It must also include a novelty tuple suitable for adversarial review:
   novelty_axis, closest_input_result, why_not_direct_corollary, and
   why_not_standard_theorem. These fields should make it possible to argue
   against the candidate as already known before it is allowed into final selection.
   The precise_problem_statement itself is audited locally before hard review.
   It must already contain explicit theorem-form content: domain/setting, unknown object class,
   equation/energy/model, assumptions, and a concrete conclusion. If it would not be valid as
   the body of a final \\begin{{q}}...\\end{{q}} theorem statement, do not include it as a candidate.
   precise_problem_statement must be one paragraph of theorem-style mathematics only.
   It must not use section labels, explanatory prose, conclusion labels, markdown headings, or report-style language.
   Do not include prose section labels or filler such as `Conclusion:`, `Conclusions:`,
   `In conclusion`, `Summary:`, or `We conclude that`. Any candidate containing this
   boilerplate will be rejected and must be replaced before hard review.
   Score breakdown should be compact. Include only novelty_confidence, already_done_risk,
   fast_sci_route, small_method_delta, {style_score_fields}
   too_ambitious_penalty, too_easy_to_publish_penalty, final_score, and weighted_score.
   Do not add a long report-style score table during initial generation.
8. Write:
   - outputs/{batch_id}/{{paper_id}}/adjacent_model_pool.json when question style is General Research Style
   - outputs/{batch_id}/{{paper_id}}/method_transfer_map.json when question style is General Research Style
   - outputs/{batch_id}/{{paper_id}}/candidate_questions.json
   - outputs/{batch_id}/{{paper_id}}/ranked_questions.json
   - outputs/{batch_id}/{{paper_id}}/result.json with phase = candidate_generation
9. ranked_questions.json must contain exactly {initial_candidates} items sorted by score.
10. Do not claim final selection has happened. The local hard_review stage will run after this phase.
    Hard review is now a lightweight novelty-search gate: it checks whether top candidates have
    already been done. It is not responsible for fixing direct corollaries or vague theorem forms.
11. If GPT Pro handoff results were present, record the source in result.json and explain how the external suggestions were used or rejected.

Validation:
- {n} paper directories exist;
- each general-style paper has adjacent_model_pool.json with adjacent_model_pool;
- each general-style paper has method_transfer_map.json with method_modules;
- each has {initial_candidates} candidate_questions;
- each has {initial_candidates} ranked_questions;
- no selected final folders are created by this phase.

Report the validation result when finished."""


def normalize_question_style(question_style: str) -> str:
    style = str(question_style or "specialized").strip().lower()
    if style.startswith("general"):
        return "general"
    return "specialized"


def build_final_selection_prompt(
    batch_path: str | Path,
    a: int,
    b: int,
    n: int = 10,
    mode: str = "deep",
    batch_id: str = "batch_001",
) -> str:
    batch_path = Path(batch_path).as_posix()
    initial_candidates = (a + 1) * b
    return f"""Please run QAgent final selection only.

Follow:
- skills/qagent/SKILL.md
- prompts/question_agent_v0.md
- prompts/scoring_policy.md
- prompts/theorem_level_problem_rules.md

Input:
- {batch_path}

Required local artifacts:
- outputs/{batch_id}/hard_review.json
- outputs/{batch_id}/hard_review_passed_candidates.json
- outputs/{batch_id}/backend_info.json
- outputs/{batch_id}/paper_###/candidate_questions.json
- outputs/{batch_id}/paper_###/candidate_quality_flags.json
- outputs/{batch_id}/paper_###/ranked_questions.json
- outputs/{batch_id}/paper_###/candidate_surveys/{{question_id}}.md
- outputs/{batch_id}/paper_###/candidate_critic/{{question_id}}.md
- outputs/{batch_id}/paper_###/paper_profile.json
- outputs/{batch_id}/paper_###/paper_literature_survey.json
- outputs/{batch_id}/paper_###/theorem_cards.json
- outputs/{batch_id}/paper_###/proof_cards.json
- outputs/{batch_id}/paper_###/gap_cards.json

Optional external expert artifact:
- outputs/{batch_id}/gpt_pro_handoff/final_selection_result.json

Optional legacy artifact:
- outputs/{batch_id}/paper_###/candidate_novelty_reviews/{{question_id}}.json

Run parameters:
- candidate width parameter a = {a}
- final questions per paper b = {b}
- number of input papers n = {n}
- initial candidate questions per paper = {initial_candidates}
- mode = {mode}

Hard rule:
For each paper, select final questions only from the paper's passed_question_ids in
outputs/{batch_id}/hard_review_passed_candidates.json. Do not create a selected question for any
candidate that is absent from that allowlist. Do not invent new question IDs.
Final selection is a reporting/export stage, not a second hard-kill stage. Prefer strict
passed_final_gate candidates first, but if the allowlist contains only imperfect candidates,
still export the best allowlisted candidates with clear low-confidence warnings instead of
returning zero final questions. High duplicate risk, survey action remove, direct restatement,
known/likely known theorem, or direct-corollary verdicts remain blocked. Medium duplicate risk,
insufficient evidence, weak critic/revise verdicts, weak theorem form, or underfilled hard-review
fallback are selection penalties, not fatal final errors, when the candidate is explicitly
allowlisted by hard review.
Exception: if hard_review_passed_candidates.json marks a candidate with fallback_selected = true,
it was admitted only because fewer than b candidates passed strict hard review for that paper.
Such fallback candidates are allowed to fill the requested count. Prefer strict
passed_final_gate candidates first, then use fallback_selected or conditional/medium-risk candidates
in descending review_score order.
If the hard-review allowlist for a paper contains fewer than {b} candidates, select all available
allowlisted candidates and mark the paper as underfilled in batch_report.md; do not invent or
resurrect non-allowlisted candidates just to reach {b}.
If hard_review_passed_candidates.json or candidate_quality_flags.json marks validation_quality
as weak_theorem_form, treat that as a serious quality penalty: select it only when better strict
or fallback candidates are unavailable, and repair the final theorem statement as much as possible.
For every non-strict final question, metadata.json and feasibility_analysis.md must clearly
record that it was selected with low confidence after hard review underfill or conditional evidence,
and must include its duplicate risk / novelty / critic / validation-quality limitations.

Task:
1. For each paper_001 through paper_{n:03d}, read candidate_questions.json, ranked_questions.json,
   hard_review.json, hard_review_passed_candidates.json, paper_literature_survey.json,
   candidate_surveys, and candidate_critic.
   Also read candidate_novelty_reviews JSON files whenever present as optional legacy evidence, but do not
   require them. The binding novelty evidence is the candidate survey / hard-review allowlist.
   If outputs/{batch_id}/gpt_pro_handoff/final_selection_result.json exists, use it as external GPT Pro
   selection evidence, but still enforce the local hard-review allowlist and theorem-level validator.
2. Do not run a separate legacy refinement loop. Use the paper-level literature survey,
   candidate-level novelty/duplicate search evidence, hard-review allowlist, and validation flags
   as the binding selection evidence. Strict passed_final_gate candidates outrank
   fallback_selected candidates unless the strict pool is smaller than {b}.
3. Block only candidates with high duplicate risk, survey action remove, direct restatement,
   direct-corollary verdict, known/likely known verdict, or no theorem-level statement. Treat
   critic verdict negative/revise, medium duplicate risk, insufficient evidence, weak fast-SCI route,
   or weak theorem-form flags as low-confidence penalties if the candidate is allowlisted. In that
   case still export the best available allowlisted candidates and keep the low-confidence warning
   in metadata.json and feasibility_analysis.md.
4. Select up to {b} final questions per paper from the passed candidates. If fewer than {b} candidates
   are allowlisted for a paper, select every allowlisted candidate and clearly report the underfill.
5. For every final selected question, write exactly these files under
   outputs/{batch_id}/{{paper_id}}/selected/{{question_id}}/:
   - problem_statement.tex
   - additional_prove_human_help_global.md
   - additional_verify_rule_global.md
   - survey_queries.md
   - feasibility_analysis.md
   - metadata.json
6. metadata.json must include question_id matching the selected folder name, survey_report_path,
   survey_duplicate_risk, critic_report_path, critic_summary, final_score, weighted_score,
   selected_rank, recommendation, one_sentence_reason_for_selection, validation_quality,
   fallback_selected, low_confidence_final, final_risk_disclosures, hard_review_selection_reason,
   generation_backend, generation_api_mode,
   generation_model, generation_model_source, and codex_cli_version.
   Read those backend fields from outputs/{batch_id}/backend_info.json.
   It should also include novelty_assessment, method_delta, fast_sci_route, journal_fit,
   already_done_risk, validation_penalty, review_score, strict_novelty_pass,
   closest_external_result, why_not_direct_corollary, why_not_standard_theorem,
   paper_survey_used, related_work_checked, and known_result_to_avoid when those fields exist
   in the candidate or hard-review artifacts. Do not invent missing report fields.
7. problem_statement.tex must contain a clean narrowed theorem-style \\begin{{q}}...\\end{{q}} statement.
   Use an explicit mathematical conclusion introduced by Prove, Show, Establish, or Then.
   Do not include prose section labels or filler such as `Conclusion:`, `Conclusions:`,
   `In conclusion`, `Summary:`, or `We conclude that`.
   Do not include source-confidence notes, novelty disclaimers, or QED suitability prose inside the q environment.
8. feasibility_analysis.md must summarize only the surviving question's proof sprint and must include
   the lower-confidence source note if full text was not read.
   additional_prove_human_help_global.md should also include one short source-confidence sentence when
   full text was not read: "The full paper text was not completely read, so this question is low confidence
   until the PDF/full text is checked by a human."
9. Write outputs/{batch_id}/{{paper_id}}/refinement_rounds.md as a compact selection trace,
   and write outputs/{batch_id}/batch_report.md from the actual final selected metadata.

Validation:
- selected question IDs are all present in hard_review_passed_candidates.json;
- up to {b} selected folders per paper, exactly the number of allowlisted candidates when the allowlist is smaller than {b};
- every selected folder has all 6 required files;
- no high duplicate-risk, remove-action, direct-corollary, direct-restatement, known, or likely-known candidate is selected.
- no selected candidate has missing novelty assessment, high duplicate risk, remove action,
  or major-new-theory requirement. Medium duplicate risk, insufficient-evidence risk, weak critic/revise
  verdict, vague method delta, or weak fast-SCI route is allowed only when the candidate is allowlisted,
  better candidates are unavailable, and metadata.json sets low_confidence_final=true with concrete
  final_risk_disclosures.

Report the validation result when finished."""


def build_candidate_replacement_prompt(
    output_dir: Path,
    batch_id: str,
    n: int,
    a: int,
    b: int,
    attempt: int,
    question_style: str = "general",
) -> str:
    expected_candidates = (a + 1) * b
    style = normalize_question_style(question_style)
    style_fields = (
        """- question_strategy_used, strategy_fit_score, why_this_is_good_research_question
- one_step_change_from_input, proof_route_shortness, novelty_defense
- research_direction_gate
- direct_corollary_precheck, why_generation_survives_direct_corollary_filter
- candidate_origin_type, adjacent_model_transfer, target_adjacent_model
- shared_method_structure, new_obstruction_after_transfer, why_transfer_is_not_random
- source_method_module_id, target_model_from_transfer_map, shared_invariant
- structural_match_score, new_failure_term, failure_type, one_new_lemma_needed
- why_not_random_transfer
- research_level_gate
- abstraction_lift"""
        if style == "general"
        else """- transfer_pattern_used, parent_transfer_pattern, transfer_pattern_fit_score
- source_theorem_or_method, target_model, new_obstruction
- why_old_proof_may_survive, minimal_publishable_version, forbidden_mechanisms_avoided
- direct_corollary_precheck, why_generation_survives_direct_corollary_filter"""
    )
    return f"""Please run QAgent candidate replacement only.

Scope:
- Work only under `outputs/{batch_id}/paper_###/candidate_questions.json`,
  `outputs/{batch_id}/paper_###/ranked_questions.json`,
  `outputs/{batch_id}/paper_###/method_transfer_map.json`, and
  `outputs/{batch_id}/paper_###/result.json`.
- Do not modify selected outputs, hard_review.json, hard_review_passed_candidates.json,
  candidate_surveys, candidate_critic, candidate_novelty_reviews, evidence files, or backend files.
- Do not run final selection.

Reason:
Hard review found too many candidates that were direct corollaries, too close to the
input theorem, likely known, or survey action `remove`. Replace those killed candidates
before the next novelty/hard-review pass instead of wasting review time.
If fewer than b candidates passed the strict final gate, also replace weak non-strict
candidates instead of preserving fallback-selected or revise-only candidates as if they
were successful. Fallback is only a disclosure mechanism for final selection; it is not
evidence that candidate generation was good enough.

Attempt:
- replacement attempt = {attempt}
- maximum attempts = 3
- papers = paper_001 through paper_{n:03d}
- candidates per paper must remain exactly {expected_candidates}
- requested final questions per paper b = {b}
- question style = {style}

Inputs to read:
- outputs/{batch_id}/hard_review.json
- outputs/{batch_id}/paper_###/candidate_questions.json
- outputs/{batch_id}/paper_###/ranked_questions.json
- outputs/{batch_id}/paper_###/paper_literature_survey.json
- outputs/{batch_id}/paper_###/paper_profile.json
- outputs/{batch_id}/paper_###/theorem_cards.json
- outputs/{batch_id}/paper_###/proof_cards.json
- outputs/{batch_id}/paper_###/method_cards.json
- outputs/{batch_id}/paper_###/gap_cards.json
- outputs/{batch_id}/paper_###/adjacent_model_pool.json when present
- outputs/{batch_id}/paper_###/method_transfer_map.json when present
- outputs/{batch_id}/paper_###/candidate_surveys/*.json and *.md when present
- outputs/{batch_id}/paper_###/candidate_novelty_reviews/*.json when present

Replacement rules:
1. Replacement is not only for underfilled papers. For every paper, replace candidates
   whenever hard_review.json, candidate_surveys/*.json, or candidate_novelty_reviews/*.json
   shows hard-kill evidence, even if the current hard-review allowlist already has b items.
   If the number of `passed_final_gate=true` candidates is smaller than b, also replace
   weak non-strict candidates with critic_verdict negative, recommended_action revise/remove,
   novelty_verdict insufficient evidence, duplicate_risk medium/high, or low review_score.
   The goal is to create strict pass candidates before final selection, not merely to keep
   enough fallback candidates.
2. Identify killed candidates from hard_review.json, candidate_surveys/*.json, and
   candidate_novelty_reviews/*.json:
   - killed_early = true
   - recommended_action = remove
   - duplicate_risk = high
   - novelty_verdict is direct corollary, too close to input theorem, probably already known, or likely known
   - classification is direct restatement of input paper, direct corollary, known theorem, or likely known
   - novelty_review_verdict is direct_corollary, too_close_to_input, or likely_known
3. Remove killed or weak non-strict candidates, preferring the clearest direct-corollary,
   high-duplicate, remove-action, known-theorem, critic-negative, revise-only, and
   insufficient-evidence failures first. A passed_final_gate candidate is normally protected.
   A fallback_selected candidate is not protected when the strict-pass count is below b.
   It must be replaced unless it is the best remaining candidate and no honest replacement exists.
4. Insert the same number of new replacement candidates. Use fresh question_id values that do not
   appear in any current candidate, such as `paper_001_r{attempt:02d}_01`.
5. Keep candidate_questions.json and ranked_questions.json at exactly {expected_candidates} items.
   The two files must contain exactly the same question_id set. ranked_questions.json must be sorted
   by final_score descending.
6. Do not repeat a killed direction. Every replacement must explicitly cite at least one killed
   direction or survey item it avoids.
7. Every replacement must be a new research direction, not a small patch of the killed statement.
   When multiple candidates were killed by the survey, use paper_literature_survey.json,
   safe_novelty_gaps, recommended_candidate_angles, and method_transfer_map.json to move to a
   different main object, adjacent model, hypothesis class, obstruction, or conclusion.
   Avoid "same theorem but with corrected wording" unless the survey explicitly says the old
   direction is new enough and only needs formal repair.
8. Every replacement must pass direct-corollary precheck before being written. If it is just the
   input theorem plus standard theory, discard it before writing.
9. Prefer survey-supported small transfer and adjacent-model transfer when mathematically justified.
   This does not mean random model hopping. The target model must share a proof mechanism, energy,
   entropy, compactness, maximum-principle, bootstrap, regularity, or variational structure with the
   input paper and must be supported by paper_literature_survey.json or theorem/proof/method cards.
   In general style, read adjacent_model_pool.json and method_transfer_map.json first. Replacement transfer candidates must cite
   an existing source_method_module_id from that map and use a target_model_from_transfer_map listed
   under that module and in the adjacent model pool. If the pool/map is missing or too weak, first repair/write them in result.json
   context and then create replacements from its credible method modules; do not invent untracked
   transfer candidates.
   Do not create pure proof-module, input-lemma, constant-tracking, or technical-cleanup replacements.
   Do not create replacements centered on raw proof details. A proof device may be used only after
   abstraction_lift converts it into a research-level mechanism and the candidate statement targets
   the main object/model, not the device.
10. If no honest replacement can be found, leave the candidate files unchanged and record this in
   result.json under replacement_attempts. Do not invent weak candidates.

Required fields for every replacement:
- question_id, title, mechanism_labels, precise_problem_statement
- novelty_assessment, method_delta, fast_sci_route, journal_fit
- novelty_axis, closest_input_result, why_not_direct_corollary, why_not_standard_theorem
- paper_survey_used, related_work_checked, known_result_to_avoid
- final_score, weighted_score, score_breakdown
{style_fields}

Direct-corollary and transfer requirements:
- In general style, pressure_point_id must be either empty or one exact id copied from
  result.json pressure_points. Do not write combined values such as "PP01 / PP02" or
  "as applicable"; choose the primary pressure point.
- direct_corollary_precheck must name the closest input theorem or standard theorem that could kill it.
- why_generation_survives_direct_corollary_filter must name a concrete non-cosmetic obstruction.
- direct_corollary_attack must be a complete object with attack_from_input_theorem,
  attack_from_standard_theorem, attack_from_routine_approximation, and why_all_fail.
  Each attack field must be written as an attempted proof with explicit numbered or
  stepwise reasoning, ending at the exact failed step. Do not write only a verbal
  judgment such as "the assumptions are different" or "not a direct corollary".
  If why_all_fail is missing, or if two attack fields are missing, the local validator
  will require another repair/replacement pass.
- adjacent_model_transfer=true candidates must include target_adjacent_model, shared_method_structure,
  new_obstruction_after_transfer, and why_transfer_is_not_random.
- In general style, adjacent_model_transfer=true candidates must also include source_method_module_id,
  target_model_from_transfer_map, shared_invariant, structural_match_score, new_failure_term,
  failure_type, one_new_lemma_needed, and why_not_random_transfer. These fields must trace back to
  method_transfer_map.json and name the new term where the transfer fails.
- In general style, adjacent_model_transfer=false candidates must not fill transfer-map fields with
  fake values such as not_applicable_non_transfer. Omit source_method_module_id,
  target_model_from_transfer_map, shared_invariant, structural_match_score, new_failure_term,
  failure_type, one_new_lemma_needed, and why_not_random_transfer unless the candidate is a real
  method-transfer candidate.
- In general style, do not use a numeric transfer quota for replacements. Prefer adjacent-model
  transfer only when the pool/map gives real structural support; otherwise prefer an honest
  research-level local candidate over a fake transfer, and prefer leaving a failed replacement
  recorded over inventing a weak one.
- In general style, every replacement must pass research_direction_gate before it is written:
  not_input_family_variant=true, one named main-object/model/solution-class/operator shift or
  genuinely independent same-object theorem, one new obstruction absent from the input paper,
  and a reason the direction is not a local lemma, endpoint cleanup, or constant-tracking exercise.

When finished:
- write updated candidate_questions.json, ranked_questions.json, and result.json for each changed paper;
- summarize which killed question_ids were replaced and why each replacement should survive direct-corollary review."""


def run_codex_cli(
    prompt: str,
    timeout_seconds: int = 60 * 60,
    model: str = "",
    *,
    use_search: bool = True,
    reasoning_effort: str = CODEX_DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    backend_meta = codex_backend_metadata(model, use_search=use_search, reasoning_effort=reasoning_effort)
    codex_path = shutil.which("codex")
    if not codex_path:
        return {
            "ok": False,
            **backend_meta,
            "command": " ".join(CODEX_COMMAND_TEMPLATE),
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "Codex CLI was not found on PATH.",
        }

    prompt_arg, prompt_file = _prompt_for_codex_arg(prompt)
    command = _materialize_command(
        prompt_arg,
        model=model,
        use_search=use_search,
        reasoning_effort=reasoning_effort,
        json_output=True,
        working_dir=Path.cwd(),
    )
    command[0] = codex_path
    display_parts = ["codex"]
    if use_search:
        display_parts.append("--search")
    if model.strip():
        display_parts.extend(["-m", model.strip()])
    if reasoning_effort.strip():
        display_parts.extend(["-c", f'model_reasoning_effort="{reasoning_effort.strip()}"'])
    display_parts.extend(["exec", "--json", "--skip-git-repo-check", "-C", Path.cwd().as_posix(), "<prompt>"])
    display_command = " ".join(display_parts)
    if prompt_file is not None:
        display_command += f" [prompt_file={prompt_file.as_posix()}]"

    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            **backend_meta,
            "command": display_command,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": "Codex CLI was not found on PATH.",
        }
    except PermissionError:
        return {
            "ok": False,
            **backend_meta,
            "command": display_command,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": ACCESS_DENIED_MESSAGE,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "timed_out": True,
            **backend_meta,
            "command": display_command,
            "return_code": None,
            "stdout": _summarize(exc.stdout or ""),
            "stderr": _summarize(exc.stderr or ""),
            "error_message": "Codex CLI timed out before returning; partial files may have been written and will be checked locally.",
        }
    except OSError as exc:
        denied = "access is denied" in str(exc).lower()
        return {
            "ok": False,
            **backend_meta,
            "command": display_command,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": ACCESS_DENIED_MESSAGE if denied else f"Codex CLI launch failed: {exc}",
        }

    raw_stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    stdout = _extract_codex_json_response(raw_stdout) or raw_stdout
    combined = raw_stdout + stderr
    if completed.returncode != 0:
        denied = "access is denied" in combined.lower()
        if stdout.strip():
            return {
                "ok": True,
                "timed_out": False,
                **backend_meta,
                "command": display_command,
                "return_code": completed.returncode,
                "stdout": stdout,
                "raw_stdout": raw_stdout,
                "stderr": stderr,
                "error_message": "",
                "warning_message": f"Codex CLI exited with code {completed.returncode}, but produced a usable response.",
            }
        return {
            "ok": False,
            **backend_meta,
            "command": display_command,
            "return_code": completed.returncode,
            "stdout": stdout,
            "raw_stdout": raw_stdout,
            "stderr": stderr,
            "error_message": ACCESS_DENIED_MESSAGE if denied else f"Codex CLI failed with exit code {completed.returncode}.",
        }

    return {
        "ok": True,
        "timed_out": False,
        **backend_meta,
        "command": display_command,
        "return_code": completed.returncode,
        "stdout": stdout,
        "raw_stdout": raw_stdout,
        "stderr": stderr,
        "error_message": "",
    }


def _extract_codex_json_response(stdout: str) -> str:
    response = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = __import__("json").loads(line)
        except Exception:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if isinstance(item, dict) and item.get("type") == "agent_message":
                response = str(item.get("text", ""))
    return response
