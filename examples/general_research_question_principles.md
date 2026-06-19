# General Research Question Principles

Use these principles when QAgent runs in general question style. They are a
generation workflow, not just a scoring rubric. Do not ask "what is a good
research question inspired by this paper?" Ask instead: "at which exact point in
the proof does the theorem almost fail, and what one-step change creates a real
new obstruction?"

The workflow is:

1. Extract theorem skeletons from the input paper.
2. Mine proof-level pressure points from those skeletons.
3. Build an adjacent model pool from the paper's load-bearing proof modules.
4. Build a method transfer map from that pool.
5. Generate candidates by either modifying one pressure point or moving one
   method module to a structurally adjacent model.
6. Try direct-corollary attacks.
7. Keep only candidates with a real obstruction, independent research value,
   and a short proof route.

Prefer candidates that arise naturally from the input proof, but are not forced
into a narrow transfer pattern.

## Stage 1: Theorem Skeleton Extraction

Before generating questions, identify the theorem skeletons of the input paper.
For each main theorem, record:

- theorem label or description;
- main assumptions;
- main conclusion;
- proof modules used;
- fragile hypotheses;
- endpoint restrictions;
- compactness steps;
- estimates where loss occurs;
- boundary, topology, coefficient, coupling, or stability assumptions that seem
  essential.

Good questions usually come from the proof step where something just barely
works, not from the abstract topic alone.

If the available input does not contain enough proof-level information to
identify where an assumption is used, do not invent the proof step. Mark the
pressure point as "evidence insufficient" and either:

1. use only theorem-level candidates with lower confidence, anchored in the
   theorem statement rather than a fabricated proof step; or
2. request or rely on full-paper search before generating proof-level
   candidates.

Never fabricate a proof module, bottleneck, or fragile hypothesis that is not
supported by the extracted text, theorem cards, proof cards, or survey evidence.

## Stage 2: Pressure Point Mining

Identify 5-8 pressure points before proposing candidates. Each pressure point
must contain:

- the original theorem, lemma, proposition, or proof module;
- the assumption or conclusion under pressure;
- where it is used in the proof;
- what would break if it were weakened, removed, localized, quantified, or moved
  to an adjacent model;
- whether the obstruction is analytic, geometric, topological, compactness,
  boundary/interface, coefficient, coupling, or stability related.

Do not generate a candidate from general mathematical taste alone. Every
candidate must be traceable to either one pressure point or one method-transfer
entry. A candidate that merely turns an input lemma or proof module into a
problem is not acceptable in general style.

## Stage 2.4: Adjacent Model Pool

Before building the transfer map, create `adjacent_model_pool.json`. This file
forces the agent to think beyond the input paper while remaining general. It
should not list fashionable equations or named domains. It should list target
models because they share a load-bearing mathematical structure.

Each entry must contain:

- `target_model`;
- `shared_structure`: the common energy, scale, compactness object,
  cancellation, monotonicity, entropy, comparison principle, variational
  identity, conservation law, defect measure, or topological invariant;
- `new_obstruction`: the exact new term or proof failure that appears after
  transfer;
- `transfer_plausibility`: numeric 0-10;
- `why_this_is_not_a_topic_keyword_match`: why this is structural adjacency,
  not a keyword analogy.

The pool should be broad enough to give genuine alternatives, but narrow enough
that each target has a plausible first proof route. If every target is just the
input model with one local hypothesis changed, the pool has failed.

## Stage 2.5: Method Transfer Map

This stage is mandatory in general question style. Before candidate generation,
write `method_transfer_map.json` from `adjacent_model_pool.json`. Its purpose is
to force mathematical invention before report writing. The map should convert
the input paper's proof modules into nearby models where the same module almost
works but one new term, sign issue, compactness loss, or structural obstruction
appears.

For each method module, record:

- `method_module_id`: stable id such as `MM01`.
- `source_theorem_or_proof_step`: theorem, lemma, estimate, or proof step from
  the input evidence.
- `method_module`: the real technique, for example monotonicity, blow-up,
  Caccioppoli iteration, compensation compactness, entropy, Carleman estimate,
  De Giorgi iteration, maximum principle, stress-energy identity, calibration,
  epiperimetric inequality, barrier construction, or compactness plus
  lower-semicontinuity.
- `load_bearing_structure`: scaling, energy or norm, compactness object,
  cancellation or sign, and boundary/topology condition that make the method
  work.
- `nearby_models`: structurally adjacent targets. Each target must name the
  shared invariant, structural match score, new failure term, failure type, one
  new lemma needed, and why the transfer is not random.

A good transfer candidate must pass three gates:

1. Method module similarity: the target model has the same kind of proof
   engine, not merely the same broad subject label.
2. Invariant similarity: the target has a comparable energy, scale, conserved
   quantity, entropy, monotonicity, compactness object, defect measure, or
   topological charge.
3. Failure term: after transfer, name the exact obstruction: boundary term,
   curvature error, commutator, nonlocal tail, coupling term, anisotropy,
   pressure term, loss of sign, topology, forcing/noise, or compactness defect.

Do not use domain-specific examples as templates. Use a structural principle:
extract the abstract role of the method, then ask where that role survives in a
different but adjacent model. The target is acceptable only if it shares the
load-bearing structure and introduces exactly one named obstruction that is not
present in the input paper.

If evidence is too weak to identify proof-level method modules, write
`evidence insufficient` in the map and generate lower-confidence theorem-level
candidates. Do not invent a hidden proof step just to create a transfer.

## What Makes A Good Candidate

- Isolate one pressure point in the input theorem: a sharp hypothesis, endpoint,
  compactness step, boundary condition, coefficient class, topology, convergence
  mode, or stability estimate.
- Change exactly one meaningful ingredient whenever possible. Good candidates
  usually modify one assumption, one norm, one geometry, one forcing term, one
  asymptotic regime, or one conclusion.
- Keep the proof route short. A publishable small result should plausibly start
  from the input method plus one new lemma, estimate, comparison, compactness
  argument, or counterexample construction.
- Prefer questions that can be attacked by an AI-assisted human quickly: a
  narrowed theorem, a model case, a quantitative refinement, a sharpness check,
  or a robustness/stability statement.
- Require independent research value. A solved candidate should plausibly be a
  small theorem paper, not just a useful lemma inside the input proof.
- Avoid fake novelty. Every candidate should identify the closest input theorem
  and the closest standard theorem, then say why the proposed statement is not a
  direct corollary.
- Avoid huge theory-building. Do not propose complete classifications, arbitrary
  nonlinear frameworks, all-dimensional endpoint theories, or open programs.
- Avoid trivial variants. Do not merely rename variables, add routine smoothness,
  restate a lemma, or apply a standard theorem without a new obstruction.
- Avoid proof-module questions. In general style, do not output a candidate
  whose value is only "prove this lemma" or "make this proof step explicit".
- Suppress raw proof details. Local proof devices, coordinate choices,
  cutoff/covering steps, approximation devices, and parameter bookkeeping are
  evidence for a mechanism, not research objects. A candidate should be about
  the main equation, variational problem, flow, operator, solution class,
  geometric object, or adjacent target model.

## Useful General Strategies

- Endpoint or sharpness: move an exponent, regularity threshold, integrability
  assumption, or geometric hypothesis to a borderline case.
- Robustness: test whether the main estimate survives lower regularity,
  perturbations, approximate solutions, weak convergence, or noisy data.
- Quantitative refinement: turn a qualitative compactness/convergence/existence
  statement into a rate, stability estimate, error bound, or modulus.
- Local-to-global or global-to-local: isolate whether the input proof is local,
  then ask for the smallest global conclusion or the sharp local version.
- Boundary/interface variant: move an interior argument to boundary, interface,
  transmission, free-boundary, or mixed-condition settings only when a real new
  boundary term appears.
- Converse or rigidity: ask whether equality, extremality, uniqueness, or
  stability forces the input paper's structure.
- Counterexample or obstruction: if a tempting strengthening probably fails,
  formulate a precise counterexample or sharp failure mechanism.
- Model-case theorem: narrow a broad idea to the simplest smooth model where the
  new obstruction is visible and the proof can fit in a short paper.
- Survey-guided adjacent-model transfer: move the input paper's method module to
  a nearby model only when the survey or paper evidence supports a shared
  structure. For example, an energy-bootstrap method, entropy estimate,
  compactness argument, maximum principle, monotonicity formula, or sharp
  interpolation lemma may transfer to a neighboring PDE, variational model, or
  geometric flow. The target must be mathematically adjacent, not a random
  change of subject.
- Method-module transfer: choose a `source_method_module_id` from
  `method_transfer_map.json`, then formulate the smallest target-model theorem
  where the shared invariant still exists but the named failure term forces one
  new lemma.

## Direct Corollary Filter

Before proposing a candidate, check whether the input theorem plus a standard
known theorem would immediately imply it. Attempt three attacks:

- Attack A: Can the input theorem imply it after a simple parameter, exponent,
  notation, or setting substitution?
- Attack B: Can a standard theorem imply it after applying the input estimate?
- Attack C: Can it be obtained by routine approximation, density, regularity
  cleanup, constant tracking, or compactness after the input result?

If any attack succeeds in fewer than five mathematical steps, reject the
candidate before writing it. Reject the idea if it is merely:

- the same theorem with constants tracked;
- routine smoothness or boundary regularity cleanup;
- a direct parameter, exponent, or notation change;
- applying a standard theorem after the input estimate;
- a proof-module restatement with no new obstruction.

Only keep a candidate if it identifies a concrete non-cosmetic obstruction that
survives this filter.

## Hard Rejection Patterns

Reject candidates containing vague phrases such as:

- under suitable assumptions;
- appropriate structural conditions;
- chosen to match the input paper;
- natural generalization;
- extend the main theorem to a broader class;
- develop a theory of;
- classify all;
- arbitrary nonlinear;
- general framework.

Reject candidates whose main change is only:

- replacing smooth by smoother;
- adding compact support without an obstruction;
- tracking constants only;
- changing notation;
- repeating a lemma as a theorem;
- applying a standard compactness theorem after the input result.

Reject candidates whose proof route starts with "by standard arguments" and
does not name the new estimate, compactness step, construction, or obstruction.

## Survey-Guided Small Transfer

Good transfer is small and justified. A transfer candidate must name:

- the source method module from the input paper;
- the target adjacent model;
- the shared structure that makes the transfer reasonable;
- the new obstruction that appears only in the target model;
- the survey or paper evidence supporting the adjacency;
- the smallest publishable transfer theorem.

Do not transfer to a fashionable equation or model unless the input method has
a visible structural match there.

## Abstraction Lift

Before writing a general-style candidate, lift any tempting proof detail through
this chain:

1. Raw proof device: the local device or technical step noticed in the paper.
2. Abstract mechanism: the general role it serves in the proof, such as scale
   separation, concentration control, localization, compactness, coercivity,
   cancellation, boundary error control, or stability.
3. Main research object: the actual mathematical object where a theorem would
   be publishable.
4. Candidate theorem: a question about that object, not about the raw device.

Reject the draft if the title, novelty axis, or theorem statement still centers
on the raw proof device. Keeping the proof device as an anchor is fine; making
it the subject of the research question is not.

## Two-Layer Candidate Evidence

Initial generation should focus on mathematical bones, not report writing. For
each draft candidate, first record only the core generation evidence:

- `candidate_statement`: the theorem-level problem statement. In QAgent output
  this is the same mathematical content as `precise_problem_statement`.
- `input_anchor`: object with closest_result, exact_assumption_changed,
  proof_step_where_used, and why_this_step_is_fragile.
- `one_step_change_from_input`: the single main change from the input theorem.
- `new_obstruction`: the obstruction created by the one-step change.
- `minimal_proof_route`: object with known_modules_reused, one_new_lemma_needed,
  and main_estimate_or_construction.
- `research_level_gate`: object with is_independent_research_problem,
  not_merely_input_lemma, why_publishable_if_solved,
  what_new_object_or_model_is_added, and why_not_just_technical_cleanup.
- `abstraction_lift`: object with raw_proof_detail_used,
  is_raw_detail_suppressed, abstract_mechanism, main_research_object,
  why_mechanism_is_research_level, and candidate_not_about_raw_detail.
- `direct_corollary_attack`: object with attack_from_input_theorem,
  attack_from_standard_theorem, attack_from_routine_approximation, and
  why_all_fail.

The direct-corollary attack must be written as an attempted proof, not as a
verbal judgment. For example:

1. Apply the closest input theorem to the proposed setting.
2. Add the nearest standard compactness or regularity theorem.
3. Explain the precise step where the attempted proof fails.

Do not write only "the assumptions are different"; name the failed proof step.

Only after a candidate survives this core gate should ranking metadata be added:

- `pressure_point_id`: the pressure point from which this candidate was derived.
- `question_strategy_used`: the strategy used.
- `strategy_fit_score`: numeric 0-10 strategy fit score.
- `why_this_is_good_research_question`: research-level value judgment.
- `proof_route_shortness`: why the proof can be started quickly.
- `novelty_defense`: why it is not the input theorem, a standard theorem, or a
  direct corollary.
- `direct_corollary_precheck`: concise summary of the direct-corollary attacks.
- `why_generation_survives_direct_corollary_filter`: concrete survival reason.
- `candidate_origin_type`: one of input-local refinement, survey-supported
  adjacent-model transfer, endpoint/sharpness, quantitative refinement,
  robustness, converse/rigidity, counterexample, or model-case theorem.
- `adjacent_model_transfer`: boolean.
- `target_adjacent_model`: the target model when adjacent_model_transfer is true.
- `shared_method_structure`: the method structure shared by the input and target.
- `new_obstruction_after_transfer`: the obstruction created by the transfer.
- `why_transfer_is_not_random`: the survey/evidence reason the transfer is
  mathematically adjacent.
- `source_method_module_id`: the method module from `method_transfer_map.json`.
- `target_model_from_transfer_map`: target model listed under that method module.
- `shared_invariant`: the comparable energy, scale, monotonicity, entropy,
  compactness object, or conserved quantity.
- `structural_match_score`: numeric 0-10 score for structural match.
- `new_failure_term`: exact term or proof error that appears after transfer.
- `failure_type`: boundary, curvature, commutator, nonlocal_tail, coupling,
  topology, anisotropy, lack_of_sign, pressure, forcing, or other.
- `one_new_lemma_needed`: the single lemma/estimate/construction needed to make
  the transfer publishable.
- `why_not_random_transfer`: concise structural reason this target is adjacent.

## Formal Statement Gate

Before accepting a candidate, check whether the mathematical statement is fully
formalized:

- all objects are defined;
- domains, dimensions, regularity assumptions, boundary conditions, and
  parameter ranges are specified;
- the conclusion is a precise theorem, estimate, counterexample, or rigidity
  statement;
- no phrase like "suitable assumptions", "natural conditions", or "appropriate
  hypotheses" remains.

Reject or repair the candidate if the statement is not formal enough for a
QED-style theorem environment.

## Negative And Positive Examples

Bad candidate:

> Extend the theorem to more general nonlinear systems under suitable
> assumptions.

Why bad:

- no exact input theorem anchor;
- no single changed ingredient;
- no identifiable obstruction;
- too broad;
- not QED-suitable.

Bad candidate:

> Track constants in the input proof to obtain an explicit estimate.

Why bad:

- likely direct corollary;
- no new proof module;
- routine bookkeeping unless a specific loss mechanism is named.

Good candidate pattern:

> The input theorem uses \(A\in C^{0,\alpha}\) in the boundary Caccioppoli step.
> Ask whether the same estimate holds for Dini-continuous \(A\) in a half-ball
> with flattened boundary.

Why good:

- anchored in one proof step;
- changes one coefficient regularity assumption;
- new obstruction is summability of the modulus in the boundary flattening
  error;
- proof route is short: redo boundary Caccioppoli plus Dini iteration.
