# QAgent Scoring Policy

QAgent selects final research questions for a QED-like proving workflow. The goal is not to chase the largest possible open problem. The goal is to find theorem-like mathematical tasks that are plausible, nontrivial, and likely to become small publishable results after careful proof development.

QAgent should explicitly prefer questions with a concrete generation rationale.
In general research style, this means a theorem skeleton, proof pressure point,
one-step variation, direct-corollary survival reason, or survey-supported small
gap. It also means a method-module transfer chain when a candidate moves the
input paper's method to an adjacent model: source method module, shared
invariant, target model, named failure term, and one new lemma. In specialized
transfer-pattern style, this may mean a successful transfer
pattern from `examples/successful_transfer_patterns.md` or the compact active
catalog in `examples/transfer_patterns_active.md`.

For specialized transfer-pattern candidate generation, `examples/transfer_patterns_active.md` is an active idea source, not a mandatory template. Candidates should name `transfer_pattern_used`, `parent_transfer_pattern`, `domain_gate`, `source_theorem_or_method`, `target_model`, `new_obstruction`, `why_old_proof_may_survive`, `minimal_publishable_version`, `forbidden_mechanisms_avoided`, and `transfer_pattern_fit_score` whenever a genuine pattern fits. Weak or missing pattern evidence should lower ranking, but it should not by itself fail the run. For general research style, use the pressure-point, one-step-change, and method-transfer-map fields instead.

Pattern fit is a weak positive signal. It must never rescue a candidate that is vague, likely known, a direct restatement, not theorem-level, or unsupported by a compact proof-route sanity check. Candidate generation and hard review must be strict. Final selection must be driven primarily by theorem-level clarity, survey/duplicate-risk evidence, proof-route viability, one concrete new obstruction, and plausible short-SCI value, but it should export allowlisted weaker candidates with low-confidence warnings rather than failing the run after selection is already complete.

QAgent must also use `examples/qagent_feedback_examples.md` and `examples/question_quality_examples.md` if present. These files are active quality signals, not passive documentation.

Scores must be supported by candidate self-gates and hard-review evidence. A candidate should not survive merely because it sounds interesting; it should survive because it has a plausible route, one key estimate or lemma, a named failure mode, and novelty evidence from candidate survey.

`prompts/theorem_level_problem_rules.md` is a hard scoring and selection gate. A candidate that cannot be written as a clean theorem-level `q` statement must receive a failing score and must not be selected.

Hard theorem-level gate:

A candidate cannot be final selected unless `problem_statement.tex` contains:

- a specific title;
- a concrete model;
- a concrete domain/setting;
- a concrete object class;
- explicit assumptions;
- a concrete conclusion;
- external metadata explaining why this is not just the input paper's main theorem;
- external metadata explaining the expected proof mechanism and QED decomposability.

The metadata above must not be inserted inside `\begin{q}...\end{q}`; the `q` environment must contain only the mathematical problem. Ordinary mathematical labels such as `Assume:`, `Suppose:`, `Define:`, `Prove:`, `More precisely:`, and `Conclusion:` are allowed when they introduce real theorem content. Template/meta headings such as `\textbf{Model.}`, `\textbf{Objects.}`, `\textbf{Novelty condition.}`, `\textbf{QED suitability.}`, `\textbf{User rating.}`, `\textbf{Why this is good.}`, and `\textbf{Feasibility.}` are not allowed inside the `q` environment.

If `problem_statement.tex` lacks explicit assumptions and a concrete conclusion, the candidate must not be selected.

If no candidate passes this gate, prefer `No suitable new theorem-level problem found.` over a vague or template-like problem.

## Selection Priorities

1. **Novelty / not already done**
   The candidate must survive a serious comparison against the input theorem, nearby results, arXiv/CVGMT/OpenAlex/Crossref/Semantic Scholar hits, and common classical theorems. This is the highest priority. A candidate that looks already done, likely known, or too close to the input paper must be removed even if it is elegant or easy.

2. **Short SCI route / AI-assisted human attackability**
   Prefer questions that a strong AI agent plus a human mathematician could attack quickly: a few definitions, a small number of estimates, a known compactness/regularity/blow-up scheme, and a clear model case. The target level is a small but real JDE/JMAA/CPAA/CPDE-style paper, not a top-tier breakthrough.

3. **Small method delta**
   Prefer nearby generalizations where the proof flow changes little: same main estimate with one primary new perturbation, boundary term, parameter regime, coefficient class, stability class, or compactness issue. The candidate should name the exact method being reused and the main new obstruction. Secondary technical issues are allowed only if the proof sprint can keep them under control.

4. **Configured-model / QED quick attackability**
   The problem should be quickly approachable by the configured Codex/model backend or a QED-like proving agent using known tools, precise assumptions, and lemma-level decomposition.

5. **Nontriviality**
   The problem should not be a trivial exercise, direct restatement of the abstract, or cosmetic parameter variation.

6. **SCI-level publishable potential**
   Prefer small but real mathematical results with plausible journal-level value. The target is JDE, JMAA, CPAA, CPDE, DCDS, or similar analysis journals, not necessarily a top-tier breakthrough.

7. **Feasibility**
   Prefer problems that can plausibly be solved by adapting known methods from the paper domain.

8. **QED decomposability**
   Prefer theorem-like statements that can be decomposed into definitions, assumptions, lemmas, estimates, compactness steps, and verification checks.

9. **Generation-rationale fit**
   Prefer questions that identify a source theorem or proof method, a proof pressure point, a nearby target setting when relevant, a new obstruction, and a precise theorem-level conclusion. In general style, reward pressure-point anchoring only after `abstraction_lift` converts raw proof detail into a research-level mechanism and the candidate targets the main mathematical object. Also require `research_direction_gate` to show a main-object/model/flow/operator/solution-class shift or a genuinely independent theorem on the same object, plus a new obstruction absent from the input paper. Reward method-module transfer only when the candidate cites `method_transfer_map.json` through `source_method_module_id`, `target_model_from_transfer_map`, `shared_invariant`, `new_failure_term`, `failure_type`, `one_new_lemma_needed`, and `why_not_random_transfer`. In specialized style, reward a transfer pattern only after the domain gate is satisfied.

`final_score` or `weighted_score` may include a positive `successful_transfer_pattern_fit` component when the pattern match is concrete. Award this component only when the candidate names a pattern from `examples/transfer_patterns_active.md`, passes the domain gate, avoids irrelevant specialized mechanisms, and gives a real source theorem/method, target model, obstruction, survival reason for the old proof, and minimal publishable theorem. Do not award it for a generic "this is a transfer" sentence.

For general style, `final_score` or `weighted_score` may include a positive
`method_module_transfer_fit` or `general_strategy_fit` component. Award it only
when the candidate satisfies all three structural checks:

- method module similarity: the source method from the input paper is named and
  reused in the target;
- invariant similarity: the target has a comparable energy, scale, entropy,
  compactness object, monotonicity, conserved quantity, or defect measure;
- failure term: the target creates one named new term or obstruction that needs
  exactly one new lemma.

Do not award this component for a fashionable adjacent equation, broad analogy,
or a sentence saying that the models are related.

For general style, give a strong penalty to candidates whose title, novelty axis,
or theorem statement is centered on a raw proof device rather than the main
research object. A proof device can support a high score only when
`abstraction_lift` clearly identifies the raw detail, suppresses it, names the
abstract mechanism, and formulates the theorem about the equation, variational
object, flow, solution class, geometric object, operator, or adjacent model.

## Priority Rule

It is acceptable to sacrifice ambition if the problem is more likely to be solved into a publishable SCI-level result.

During hard-review selection and replacement, prioritize candidates whose compact trace shows:

- a detailed novelty comparison against the input theorem and nearby public metadata;
- a low likelihood of being already done;
- a short AI-assisted proof route with a concrete model case;
- a small method delta from the input paper or a nearby standard theorem;
- plausible JDE/JMAA/CPAA-level publishability if solved;
- explicit theorem-level assumptions, object class, and conclusion;
- a concrete proof pressure point, one-step change, transfer pattern, or card-based gap;
- an abstraction lift from any raw proof device to a research-level mechanism
  and main mathematical object;
- a research-direction gate showing this is not an input-family local variant;
- a cited pressure-point rationale or, in specialized style, a successful transfer pattern;
- in general-style transfer candidates, a cited `source_method_module_id` from
  `method_transfer_map.json` and a named target failure term;
- avoidance of known bad direct-corollary or bad-transfer patterns;
- one identifiable key estimate or compactness lemma;
- a failure mode that can plausibly be controlled;
- low duplicate/direct-restatement risk.

## Novelty/Duplicate-Risk Gate

In Deep Mode, every final-selected candidate must receive candidate-level
novelty/duplicate search evidence before final selection. For speed, the app
normally surveys only the top `max(2b, b+2)` ranked candidates per paper after
candidate generation; lower-ranked candidates are not surveyed unless needed
for fallback or replacement.

```text
outputs/{batch_id}/{paper_id}/candidate_surveys/{question_id}.md
```

Each candidate-level novelty/duplicate evidence file should contain sharp
search queries, normally including:

- exact title-style query;
- model + theorem type;
- model + conclusion;
- input paper title + proposed extension;
- key tool + target model;
- author names + related theorem;
- arXiv/CVGMT-style keyword query;
- broad semantic query.

For novelty-sensitive selection, each candidate-level novelty/duplicate evidence file must also contain a **Detailed novelty comparison** section with:

- closest input-paper theorem/result and why the candidate is not just that theorem;
- closest external result found and title-similarity / theorem-similarity assessment;
- exact new parameter, object class, boundary/geometry, stability/index class, coefficient class, or compactness obstruction;
- verdict: `new enough`, `probably already known`, `too close to input theorem`, or `insufficient evidence`.

Each candidate-level novelty/duplicate evidence file must list nearby known results from the input paper itself, known classical theorems, likely arXiv/CVGMT/OpenAlex/Crossref/Semantic Scholar hits, and prior theorem patterns in `examples/qagent_feedback_examples.md`.

Each candidate-level novelty/duplicate evidence file must classify the candidate as one of:

- reproduction of input theorem
- forbidden proof-module / input-lemma extraction in general style
- known theorem or likely known theorem
- plausible transfer question
- plausible new theorem-level question
- too vague / insufficient evidence

Rules:

- High duplicate risk candidates cannot be final selected questions.
- Medium duplicate risk candidates should be repaired or replaced before final selection when possible. If hard review still allowlists them as fallback or conditional candidates, final selection may export them with `low_confidence_final=true` and explicit risk disclosure.
- Reproduction of input theorem cannot be final selected unless the user explicitly asks for reproduction.
- Known theorem or likely known theorem cannot be final selected.
- Too vague candidates cannot be final selected. Insufficient-evidence candidates should be repaired or replaced before final selection when possible; if still allowlisted as fallback, export them only with low-confidence disclosure.
- In general style, proof-module / input-lemma extraction candidates cannot survive; they must be regenerated before candidate files are accepted.
- Plausible transfer questions and plausible new theorem-level questions should be preferred if precise, feasible, and supported by theorem/gap cards.
- If the survey is unavailable or too weak, lower confidence and prefer `revise` unless the candidate is clearly a useful module.

## Avoid

- Huge open problems.
- Problems requiring a completely new theory.
- Problems whose proof needs a major new method rather than a small method delta.
- Problems that are probably already present in the input paper, its arXiv neighborhood, or standard literature.
- Questions too ambitious for a short AI-assisted human proof sprint.
- Questions too easy to be publishable, such as direct corollaries, notation changes, or applying a known theorem verbatim.
- Trivial variations.
- Vague survey questions.
- Statements with too many unspecified assumptions.
- Problems that are likely already known.
- Questions whose proof mechanisms do not match the paper domain.
- Questions whose main novelty is a local proof device, coordinate trick,
  approximation step, or parameter bookkeeping detail rather than a theorem
  about the main research object.
- Transfers that name a famous method but do not specify the target theorem, assumptions, conclusion, or new obstruction.
- Over-specialized transfer language imported from the wrong domain. Do not mention no-neck, bubble tree, energy identity, varifold compactness, De Giorgi iteration, Yamabe Green-function blow-up, free-boundary stratification, or dispersive estimates unless the input paper or target model genuinely belongs to that domain.
- Pattern matching from keywords alone. Read theorem/proof/gap cards first, then choose a pattern.
- Final problem statements using vague phrases such as `under suitable assumptions`, `main regularity mechanism`, `natural setting of the paper`, or `study whether` without immediately listing explicit assumptions and conclusions.
- Direct restatement of the input paper's theorem.
- Abstract keyword splicing.
- Generic title/template problem.
- Confusion between minimizer, stationary, stable, and bounded-index hypotheses.
- Confusion between phase-field level and varifold limit level.
- Boundary transfer where the boundary does not change the key mechanism.

## Score Components

Score each candidate from 1 to 5 for each positive component:

- `novelty_confidence`
- `fast_sci_route`
- `small_method_delta`
- `qed_gpt_attackability`
- `sci_publishable_potential`
- `nontriviality`
- `novelty_potential`
- `feasibility`
- `clarity`
- `qed_suitability`
- `successful_transfer_fit`
- `domain_gate_fit`
- `feedback_alignment`

Score each risk or penalty from 1 to 5, where 5 is worse:

- `duplicate_risk`
- `already_done_risk`
- `too_ambitious_penalty`
- `too_easy_to_publish_penalty`
- `counterexample_risk`
- `too_broad_penalty`
- `too_trivial_penalty`
- `survey_duplicate_risk`
- `wrong_domain_mechanism_penalty`

Compute:

```text
final_score =
45*novelty_confidence
+35*fast_sci_route
+30*small_method_delta
+25*qed_gpt_attackability
+25*sci_publishable_potential
+20*feasibility
+15*qed_suitability
+15*nontriviality
+8*successful_transfer_fit
+12*domain_gate_fit
+15*feedback_alignment
+10*novelty_potential
+10*clarity
-45*already_done_risk
-35*survey_duplicate_risk
-30*too_ambitious_penalty
-25*duplicate_risk
-20*counterexample_risk
-20*too_broad_penalty
-20*too_trivial_penalty
-20*too_easy_to_publish_penalty
-30*wrong_domain_mechanism_penalty
```

`weighted_score` may be included as a compatibility alias, but `final_score` is the preferred field.

## Selected Metadata

Metadata for every selected question must include:

- `novelty_confidence`
- `already_done_risk`
- `fast_sci_route`
- `small_method_delta`
- `method_delta`
- `journal_fit`
- `too_ambitious_penalty`
- `too_easy_to_publish_penalty`
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
- `survey_duplicate_risk`
- `final_score`
- `recommendation`
- `successful_transfer_fit`
- `domain_gate_fit`
- `wrong_domain_mechanism_penalty`
- `feedback_alignment`

The selected final questions should prioritize `qed_gpt_attackability` and `sci_publishable_potential`, while still passing the nontriviality, novelty, feasibility, and QED-suitability checks.

Strict selected-question preference: prefer candidates with `already_done_risk <= 2`, `survey_duplicate_risk <= 2`, `fast_sci_route >= 4`, `small_method_delta >= 4`, and neither `too_ambitious_penalty` nor `too_easy_to_publish_penalty` above 2. If no allowlisted candidate meets these strict preferences, export the best hard-review-allowlisted non-blocked candidates with `low_confidence_final=true`, concrete risk disclosures, and a note that no strict short-SCI candidate survived. Do not fail the whole run solely because final preferences are imperfect.

## Compact Selection Trace Fields

For every selected or removed candidate considered during final selection, produce only compact trace fields:

- `detailed_novelty_comparison`
- `already_done_risk`
- `method_delta`
- `fast_sci_route`
- `journal_fit`
- `too_ambitious_check`
- `too_easy_to_publish_check`
- `theorem_level_check`
- `generation_rationale_check`
- `proof_route_sanity_check`
- `key_estimate_to_prove`
- `failure_mode`
- `duplicate_risk_check`
- `remove_or_keep_decision`

These trace fields are internal artifacts. They should be saved in `outputs/{batch_id}/{paper_id}/refinement_rounds.md`, not displayed as final selected-question content.

The proof-route sanity check should be short. It must name the main estimate or
lemma needed, where the input method may enter, and the one failure mode. Do not
write a long 5--10 step proof attempt unless it is necessary to decide between
two otherwise comparable candidates.

Hard proof-sprint selection rules:

- If no plausible proof route exists, remove.
- If the proof route is just `apply known theorem directly`, remove as too trivial.
- If it requires a major new theory, remove as too ambitious.
- If it is a direct restatement of an existing theorem, remove.
- Prefer problems where the proof route adapts a known tool to a genuinely new obstruction.
