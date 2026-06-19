# QAgent Workflow

## Purpose

QAgent takes `n` mathematical paper entries in `data/{batch_id}.md`, where `n` is chosen in the UI and `1 <= n <= 60`, and generates QED-ready research-question folders under `outputs/{batch_id}`.

The output is designed for downstream proving or verification agents. Each selected question should become a paper-specific theorem-like task with a narrowed problem statement, proof guidance, verification rules, survey queries, feasibility analysis, and metadata.

## Input Format

Each paper starts with a Markdown heading beginning with:

```markdown
## 
```

Each paper entry may contain:

- CVGMT ID
- authors
- year
- DOI
- URL
- matched keywords
- abstract

DOI, CVGMT ID, URL, matched keywords, and abstract are optional. Title is strongly recommended. If the user gives a loose citation, QAgent should try to normalize it before running.

## Refinement Parameters

The runner supplies a mode and three parameters:

- mode: `Deep Mode` or `Batch Mode`.
- `n`: number of input papers, chosen in the UI with `1 <= n <= 60`.
- `a`: refinement rounds.
- `b`: final questions per paper, chosen in the UI with `1 <= b <= 10`.

## Two Modes

### Deep Mode

Deep Mode is for 1--10 papers and is the high-quality mode. Final SCI-level QED-ready problems should normally be generated in Deep Mode.

Deep Mode must perform:

- paper resolving;
- metadata/full-text/PDF fetching when possible;
- theorem card extraction;
- proof mechanism extraction;
- limitation/gap extraction;
- candidate generation;
- actual survey/duplicate-risk checks;
- lightweight hard-review trace, with full critic only when explicitly enabled;
- quick proof sprint;
- final selection.

In Deep Mode, quality matters more than speed or token cost. The agent may spend more reasoning and search time per paper and should not lower question quality to save time.

### Batch Mode

Batch Mode is for 11--60 papers. It is a rough screening mode only.

Batch Mode should:

- perform lightweight paper screening;
- clearly mark outputs as lower-confidence;
- avoid claiming final SCI-level QED-ready status;
- recommend which papers deserve a future Deep Mode run.

For high-quality theorem-level questions, use Deep Mode. Batch Mode is only for rough screening.

### GPT Pro web handoff

QAgent may create a GPT Pro web handoff package for candidate generation and final selection:

- `outputs/{batch_id}/gpt_pro_handoff/prompts/paper_###_gpt_pro_prompt.md`
- `outputs/{batch_id}/gpt_pro_handoff/results/paper_###.json`
- `outputs/{batch_id}/gpt_pro_handoff/final_selection_prompt.md`
- `outputs/{batch_id}/gpt_pro_handoff/final_selection_result.json`

This is a manual parallel-web workflow. QAgent does not automate the GPT Pro web UI, does not scrape ChatGPT pages, and does not use an OpenAI API key. If GPT Pro handoff result files are present, Codex should use them as external expert evidence while still enforcing local hard-review, survey, and theorem-level validators.

GPT Pro web handoff has two policies:

- optional: write GPT Pro prompts and continue with Codex if GPT Pro result files are missing;
- required: pause until GPT Pro result files are saved.

When required GPT Pro web handoff is selected, the workflow is intentionally staged:

1. Stop after evidence preflight and write candidate/survey prompts.
2. Wait until `gpt_pro_handoff/results/paper_###.json` exists for every paper.
3. Continue candidate validation, novelty review, and hard review.
4. Stop after hard review and write `gpt_pro_handoff/final_selection_prompt.md`.
5. Wait until `gpt_pro_handoff/final_selection_result.json` exists.
6. Continue final Codex export.

If the GPT Pro result files are missing, do not claim that GPT Pro was used. In optional mode, continue with Codex and record that GPT Pro evidence was absent.

For each paper:

- initial candidates = `(a+1)*b`;
- each refinement round runs a quick proof sprint for every remaining candidate;
- each refinement round removes `b` weaker candidates;
- after `a` rounds, exactly `b` final questions remain.

Example: if `a=2` and `b=3`, QAgent generates 9 initial candidates, removes 3 in round 1, removes 3 in round 2, and keeps 3 final questions.

## Core Workflow

For each paper:

1. Resolve and normalize metadata.
2. Fetch the richest available source: PDF, HTML full text, abstract/metadata, or user information.
3. Extract text and build deep reading cards.
4. Build a compact paper profile.
5. Generate exactly `(a+1)*b` candidate mathematical research questions from theorem/proof/method/limitation/gap cards whenever possible.
6. For each candidate in Deep Mode, run a real survey/duplicate-risk check.
7. Label every candidate with question-generation mechanisms.
8. Score and rank all candidates using `prompts/scoring_policy.md`.
9. In hard review, run novelty/duplicate search only for the top ranked candidates needed for selection.
10. Run exactly `a` refinement rounds.
11. In each round, every remaining question receives a quick proof sprint.
12. At each round, remove exactly `b` weaker candidates and record why.
13. Select exactly `b` final questions.
14. Generate QED-ready files for each final question.

Mechanism labels include direct extraction, analogy between models, operator generalization, object generalization, setting generalization, parameter and regularity variation, strengthening and quantification, and counterexample or sharpness problems.

## Scoring Priorities

Selection must prioritize:

- configured-model / QED quick attackability;
- nontrivial but not overly ambitious problems;
- SCI-level publishable potential and small but real publishable mathematical results;
- plausible novelty;
- feasibility by adapting known methods;
- QED decomposability.

The target is not necessarily a top-tier breakthrough. It is acceptable to sacrifice ambition if the problem is more likely to become a publishable SCI-level result.

Avoid huge open problems, problems requiring a completely new theory, trivial variations, vague survey tasks, statements with too many unspecified assumptions, and questions that are likely already known.

## Selected Metadata

Metadata for every selected question should include:

- `qed_gpt_attackability`
- `nontriviality`
- `sci_publishable_potential`
- `novelty_potential`
- `feasibility`
- `qed_suitability`
- `duplicate_risk`
- `counterexample_risk`
- `too_broad_penalty`
- `too_trivial_penalty`
- `final_score`
- `recommendation`
- `survey_duplicate_risk`
- `survey_report_path`
- `critic_summary`

## Survey / Duplicate-Risk Stage

In Deep Mode, every final-selected candidate must receive a candidate-level
survey report before final selection. The default fast workflow surveys only
the top `max(2b, b+2)` ranked candidates per paper, not every generated
candidate:

```text
outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md
```

For each surveyed candidate:

1. Generate at least 8 search queries:
   - exact title-style query;
   - model + theorem type;
   - model + conclusion;
   - input paper title + proposed extension;
   - key tool + target model;
   - author names + related theorem;
   - arXiv/CVGMT-style keyword query;
   - broad semantic query.
2. Search available public metadata sources:
   - local resolved paper metadata;
   - Crossref;
   - OpenAlex;
   - arXiv;
   - Semantic Scholar if available.
3. Do not scrape Google Scholar.
4. List nearby known results from the input paper itself, known classical theorems, and likely arXiv/CVGMT/OpenAlex/Crossref/Semantic Scholar hits.
5. Classify whether the candidate looks like:
   - reproduction of input theorem;
   - proof module of input theorem;
   - known theorem or likely known theorem;
   - plausible transfer question;
   - plausible new theorem-level question;
   - too vague / insufficient evidence.
6. Assign duplicate risk: low / medium / high.
7. Assign recommended action: keep / revise / remove.

High duplicate risk candidates cannot be final selected questions. Reproduction of the input theorem cannot be final selected unless the user explicitly asks for reproduction. Known theorem or likely known theorem cannot be final selected. Too vague candidates cannot be final selected. Insufficient-evidence candidates should be repaired or replaced before final selection when possible; if hard review still allowlists one as fallback, final selection may export it only with low-confidence metadata and explicit risk disclosure. Proof module questions may survive only if useful and explicitly labeled as module questions. Precise and feasible transfer questions or plausible new theorem-level questions should be preferred.

For final selected questions, `survey_queries.md` must include search queries, nearby results, duplicate risk, and the final reason why the question survived the hard survey gate.

## Hard Review Trace

In the default fast workflow, full critic review is disabled. The hard-review
stage writes a short compatibility trace after survey and before final
selection:

```text
outputs/{batch_id}/{paper_id}/candidate_critic/{question_id}.md
```

This trace records the novelty-search duplicate risk and whether the candidate
remains eligible. Direct-corollary, theorem-form, method-transfer, and
short-proof-route checks must happen during candidate generation and local
validation. If full critic mode is explicitly enabled, the critic should answer:

1. Is this theorem-level?
2. Are domain, object class, assumptions, and conclusion explicit?
3. Is it a direct restatement of the input paper?
4. Is it likely already known?
5. Is it too broad?
6. Is it too trivial?
7. Does it arise from a concrete theorem skeleton, proof pressure point, survey-supported small variation, or justified transfer mechanism?
8. What is the new obstruction?
9. Can the configured Codex/QED proving agent quickly start proving it?
10. Could it plausibly become a small SCI-level result?

A candidate cannot be selected unless hard review gives a positive or
conditionally positive trace verdict. Final `metadata.json` must include
`critic_summary`.

## Refinement Proof Sprints

Refinement is internal and should not appear in the main UI. It is not a superficial score update.

For every remaining candidate in every refinement round, produce:

1. `theorem_level_check`
   Does the question have explicit assumptions, domain/object class, and conclusion?

2. `generation_rationale_check`
   Does the question arise from a concrete theorem skeleton, proof pressure point, survey-supported small variation, or justified transfer mechanism? In general style, cite the pressure point and one-step change. In specialized transfer-pattern style, cite the pattern only when it genuinely fits the paper domain. The sprint must also state the domain gate: why the mechanism belongs to this paper's mathematical domain and which tempting but irrelevant mechanisms were avoided.

3. `quick_proof_sprint`
   A concrete proof sprint before the keep/remove decision. It must include:
   - exact theorem-level restatement;
   - main estimate or lemma needed;
   - 5--10 step proof attempt;
   - where the input paper's method would be used;
   - where the method may fail in the new setting;
   - whether failure suggests a counterexample/sharpness formulation;
   - configured-model / QED attackability score;
   - SCI-publishable potential score;
   - nontriviality score;
   - final keep/remove reason.

4. `key_estimate_to_prove`
   The single most important estimate, compactness lemma, or regularity criterion.

5. `failure_mode`
   Where the proof is likely to break.

6. `duplicate_risk_check`
   Whether the question looks known or directly restates the input paper.

7. `qed_gpt_attackability_score`
   Integer from 1 to 5.

8. `sci_publishable_potential_score`
   Integer from 1 to 5.

9. `nontriviality_score`
   Integer from 1 to 5.

10. `remove_or_keep_decision`
   Exactly `keep` or `remove`, with reason.

Save the per-paper internal report as:

```text
outputs/{batch_id}/{paper_id}/refinement_rounds.md
```

This file is an internal artifact. The main Streamlit UI should show only final selected question outputs.

Hard proof-sprint rules:

- If no plausible proof route exists, remove.
- If the proof route is just `apply known theorem directly`, remove as too trivial.
- If it requires a major new theory, remove as too ambitious.
- If it is a direct restatement of an existing theorem, remove.
- Prefer problems where the proof route adapts a known tool to a genuinely new obstruction.
- Final `feasibility_analysis.md` should summarize only the surviving question's final proof sprint.

## Required Output Files

For each final selected question, create:

```text
outputs/{batch_id}/{paper_id}/selected/{question_id}/problem_statement.tex
outputs/{batch_id}/{paper_id}/selected/{question_id}/feasibility_analysis.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/additional_prove_human_help_global.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/additional_verify_rule_global.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/survey_queries.md
outputs/{batch_id}/{paper_id}/selected/{question_id}/metadata.json
```

Each paper directory should also include:

```text
paper_profile.json
theorem_cards.json
proof_cards.json
method_cards.json
limitation_cards.json
gap_cards.json
paper_reading_quality.json
paper_reader_report.md
refinement_rounds.md
result.json
method_transfer_map.json
candidate_questions.json
ranked_questions.json
```

The batch directory should include:

```text
outputs/{batch_id}/batch_report.md
```

## Quality Rules

`prompts/theorem_level_problem_rules.md` is a hard specification for final problem quality. QAgent must obey it before selecting a final question.

- `feasibility_analysis.md` must be domain-specific.
- Do not include irrelevant proof mechanisms from other fields.
- The recommendation must be exactly one of: `keep`, `keep but simplify`, `revise`, `discard`.
- `problem_statement.tex` must be theorem-like and paper-specific.
- A candidate cannot be selected unless `problem_statement.tex` satisfies the theorem-level schema:
  - specific title;
  - concrete model;
  - concrete domain/setting;
  - concrete object class;
  - explicit assumptions;
  - concrete conclusion;
  - novelty explanation outside the `q` environment;
  - QED decomposability note outside the `q` environment.
- If `problem_statement.tex` does not contain explicit `Assumptions` and `Conclusion`, remove the candidate during refinement.
- The validator should reject only meta/template contamination inside `\begin{q}...\end{q}`. It must not reject ordinary mathematical language such as `Assume:`, `Suppose:`, `Define:`, `Prove:`, `More precisely:`, `Conclusion:`, compactness, regularity, convergence, or no-neck when used in a real theorem statement.
- Forbidden template/meta headings inside `q` include `\textbf{Model.}`, `\textbf{Objects.}`, `\textbf{Novelty condition.}`, `\textbf{QED suitability.}`, `\textbf{User rating.}`, `\textbf{Why this is good.}`, and `\textbf{Feasibility.}`.
- The generator must not assemble `q` environments from generic metadata sections. It must produce a clean theorem-level `q` statement or write `No suitable new theorem-level problem found.`
- Avoid vague language such as `under suitable assumptions`, `main regularity mechanism`, `natural setting of the paper`, or `study whether`, unless explicit assumptions are listed immediately afterwards.
- If an assumption is unknown because the paper text was unavailable, write: `The exact structural hypothesis [X] must be recovered from the input paper before attempting the proof.`
- Selected questions must be based on a specific theorem card or gap card whenever possible.
- If full text was unavailable, record a lower-confidence source note in `metadata.json` and `feasibility_analysis.md`, not inside `problem_statement.tex`.
- Proof guidance and verification rules must be concrete.
- Selected question titles must be paper-specific, not generic templates.
- Scores should reflect the actual question and should not be identical templates across papers.

## Validation Checklist

Validate that the output has:

- `n` paper directories.
- `(a+1)*b` candidate questions per paper.
- `(a+1)*b` ranked questions per paper.
- `b` selected folders per paper.
- Every selected folder has all 6 required files.

The 6 required selected-question files are:

- `problem_statement.tex`
- `feasibility_analysis.md`
- `additional_prove_human_help_global.md`
- `additional_verify_rule_global.md`
- `survey_queries.md`
- `metadata.json`

## No API Key Mode

This version uses the configured Codex CLI backend to generate outputs. It does not require `OPENAI_API_KEY` and should not ask the user for an API key.

When operating in this mode, use `prompts/question_agent_v0.md` and `prompts/scoring_policy.md` as the governing instructions and write generated artifacts directly under `outputs/{batch_id}/`.

## Future Extensions

Possible future extensions include:

- optional literature survey integration;
- crawler integration for CVGMT or arXiv metadata;
- a direct Codex CLI runner when `codex` is executable;
- a future API-backed runner mode;
- Streamlit review and export tools.
