# Active Transfer Pattern Catalog

Use this compact catalog during candidate generation as a source of ideas, not as a mandatory template. QAgent must first read the paper mechanism, theorem cards, proof cards, limitation cards, gap cards, feedback examples, and survey evidence. Only then should it choose a transfer pattern.

A pattern match is useful only when it identifies a concrete new mathematical obstruction. A candidate that merely imitates pattern language, adds a generic perturbation, or restates the input theorem must be rejected or given a very low score.

## Core Rule

A good transfer question is not "apply the same theorem again." It transfers a robust proof mechanism to a nearby setting where one primary new obstruction appears. Secondary technical issues may exist, but the candidate must name the main obstruction that makes the theorem nontrivial. The minimal version should look like a short JDE/JMAA/CPAA/CPDE-level theorem, not a broad program.

## Universal Parent Patterns

Before choosing a detailed TP pattern, classify the candidate under one broad parent pattern:

1. **Perturbation Transfer:** add a lower-order term, rough coefficient, nonlocal term, anisotropy, or small coupling.
2. **Setting Transfer:** move an interior or flat theorem to boundary, manifold, corner-free, metric, or localized settings.
3. **Dynamic Transfer:** transfer stationary or elliptic analysis to flow, parabolic, convergence, or stability problems.
4. **Compactness and Defect Transfer:** adapt compactness, blow-up, defect-measure, almost-solution, or finite-index arguments.
5. **Quantitative Refinement:** turn qualitative compactness, convergence, or regularity into rates, moduli, or stability estimates.
6. **Sharpness or Counterexample:** test threshold sharpness, sign failure, one-dimensional obstructions, or cell-problem obstructions.
7. **Low-Regularity / Endpoint Variant:** weaken data, coefficients, domains, exponents, or topology in a controlled model case.
8. **Proof-Module Extraction:** isolate a useful theorem-level lemma or identity. This is allowed only when labeled as a module, not as a new research theorem.

The detailed TP patterns below are subpatterns and examples. They should guide generation, but pattern fit alone must never rescue a vague, already-known, or non-theorem-level candidate.

## Domain-Gate Rule

Do not choose a specialized mechanism from keywords alone. Before assigning a TP pattern, state:

- the paper's mathematical domain;
- why the pattern is appropriate for this domain;
- which tempting but irrelevant mechanisms were intentionally avoided.

Highly specialized mechanisms may be used only when the paper or target model genuinely belongs to that domain:

- Use no-neck, bubble tree, energy identity, or neck-region language only for papers involving concentration, bubbling, harmonic maps, Ginzburg-Landau vortices, phase-field concentration, or related compactness failure.
- Use varifold compactness, first variation, tangent cones, density gap, or sheeting only for GMT, phase-field limits, currents, minimal surfaces, or varifold papers.
- Use De Giorgi iteration only for PDE regularity problems where level-set iteration or energy truncation is relevant.
- Use Yamabe, conformal Laplacian, Green-function blow-up, positive mass, or rough metrics only for conformal/Riemannian geometry papers.
- Use dispersive, Strichartz, resonance, or trapped-ray language only for dispersive PDE or wave/Schrodinger-type papers.
- Use obstacle, Weiss monotonicity, free-boundary stratification, or contact set language only for obstacle/free-boundary papers.

## Patterns

### TP01 Lower-Order Perturbation
- Source: estimate, compactness, maximum principle, or energy method for the unperturbed equation.
- Target: add a drift, potential, reaction term, damping, or source term in a controlled class.
- Obstruction: absorption, sign loss, scaling threshold, or loss of coercivity.
- Minimal theorem: prove the original estimate under smallness, Kato, Morrey, Dini, or subcritical assumptions on the perturbation.

### TP02 Coefficient Roughening
- Source: smooth or Holder coefficient theorem.
- Target: VMO, Dini, piecewise smooth, measurable-in-one-variable, or small-BMO coefficients.
- Obstruction: commutator or freezing error.
- Minimal theorem: preserve the key regularity/estimate with explicit modulus dependence.

### TP03 Boundary Transfer
- Source: interior theorem.
- Target: boundary, mixed boundary, Robin, conormal, or corner-free domain version.
- Obstruction: boundary flattening error, trace term, compatibility condition, or boundary layer.
- Minimal theorem: boundary Caccioppoli, boundary epsilon regularity, boundary gradient estimate, or boundary compactness.

### TP04 Geometry Perturbation
- Source: Euclidean or flat-domain result.
- Target: Riemannian manifold, curved boundary, graph domain, or small metric perturbation.
- Obstruction: curvature terms, injectivity radius, coordinate distortion, or metric commutators.
- Minimal theorem: local estimate under bounded geometry and small coordinate-scale curvature.

### TP05 Elliptic-To-Parabolic
- Source: elliptic regularity, Liouville theorem, or compactness method.
- Target: parabolic flow, time-dependent coefficients, or evolutionary analogue.
- Obstruction: time scaling, initial layer, energy dissipation, or lack of elliptic symmetry.
- Minimal theorem: short-time/local parabolic estimate using the elliptic method plus one time-regularity lemma.

### TP06 Stationary-To-Dynamic Stability
- Source: stationary classification, minimizer theorem, or steady-state estimate.
- Target: convergence, stability, or near-stationary dynamics.
- Obstruction: spectral gap, modulation, Lyapunov functional, or slow drift.
- Minimal theorem: stability under small perturbations around a model stationary solution.

### TP07 Local-To-Nonlocal
- Source: local elliptic/parabolic estimate.
- Target: fractional, integral, tail-interaction, or nonlocal operator.
- Obstruction: tail control, kernel asymmetry, nonlocal boundary data, or truncation error.
- Minimal theorem: model nonlocal estimate with symmetric kernels and controlled tails.

### TP08 Isotropic-To-Anisotropic
- Source: isotropic diffusion/energy theorem.
- Target: anisotropic coefficients, Finsler-type energy, directional diffusion, or weighted geometry.
- Obstruction: directional degeneracy, anisotropic Sobolev embedding, or missing rotation invariance.
- Minimal theorem: preserve a key estimate under uniform anisotropy bounds.

### TP09 Scalar-To-System With Structure
- Source: scalar maximum principle, energy estimate, or regularity theorem.
- Target: vectorial/system version with monotonicity, convexity, triangular structure, or small coupling.
- Obstruction: loss of scalar comparison, cross terms, or coercivity of coupling.
- Minimal theorem: system estimate under structural monotonicity or small coupling.

### TP10 Exact-To-Approximate Equation
- Source: theorem for exact solutions.
- Target: almost solutions, perturbed Euler-Lagrange equations, tension field, residual forcing, or numerical defect.
- Obstruction: error accumulation and compactness defect.
- Minimal theorem: stability estimate with a quantitative residual term.

### TP11 Compactness With Small Defect
- Source: compactness or blow-up proof.
- Target: sequences with small defect measure, weak forcing, boundary error, or coefficient oscillation.
- Obstruction: defect concentration, loss of strong convergence, or missing lower semicontinuity.
- Minimal theorem: compactness if the defect is small in a scale-invariant norm.

### TP12 Monotonicity-To-Almost-Monotonicity
- Source: exact monotonicity formula.
- Target: perturbed equation, curved geometry, boundary case, or weighted functional.
- Obstruction: error terms in derivative of monotonic quantity.
- Minimal theorem: almost-monotonicity with integrable error and a consequence such as density existence.

### TP13 Rigidity-To-Quantitative Stability
- Source: rigidity or uniqueness theorem.
- Target: near-equality or small-defect stability.
- Obstruction: compactness gap, normalization, or noncompact symmetry group.
- Minimal theorem: quantitative distance-to-model estimate under a small deficit.

### TP14 Qualitative-To-Rate
- Source: existence, convergence, compactness, or regularity without explicit rate.
- Target: rate, modulus, or quantitative estimate.
- Obstruction: tracking constants, spectral gap, or iterative decay.
- Minimal theorem: explicit algebraic/logarithmic/exponential rate under one extra assumption.

### TP15 Critical-To-Subcritical Safe Version
- Source: critical theorem or hard endpoint method.
- Target: slightly subcritical regime, small energy regime, or bounded parameter window.
- Obstruction: borderline compactness, concentration, or endpoint embedding.
- Minimal theorem: prove a clean subcritical or smallness theorem as a publishable stepping stone.

### TP16 Endpoint Failure-To-Sharp Counterexample
- Source: theorem requiring a threshold.
- Target: show the threshold is sharp or identify a counterexample mechanism.
- Obstruction: construction must respect the model and scaling.
- Minimal theorem: explicit counterexample or non-improvement result in a model class.

### TP17 Liouville-To-Local Estimate
- Source: Liouville theorem or global classification.
- Target: local a priori estimate by blow-up contradiction.
- Obstruction: rescaling limit, boundary/domain loss, or compactness of normalized sequence.
- Minimal theorem: local estimate with assumptions chosen so the blow-up limit falls under the Liouville theorem.

### TP18 Blow-Up Classification-To-Stability
- Source: classification of blow-up profiles or tangent cones.
- Target: uniqueness/stability/rate of approach to one profile.
- Obstruction: spectral mode, epiperimetric inequality, or logarithmic drift.
- Minimal theorem: conditional stability near a nondegenerate model profile.

### TP19 Concentration / Defect-Control Transfer
- Source: compactness theorem, blow-up analysis, defect-measure argument, bubble analysis, concentration-compactness method, or energy quantization result.
- Target: nearby setting where compactness may fail through concentration, neck loss, boundary leakage, residual forcing, coefficient oscillation, topology, or a weak compactness defect.
- Obstruction: identify the exact channel through which compactness can fail.
- Minimal theorem: compactness, no-defect, energy-quantization, sharp compactness criterion, or counterexample statement under one explicit scale-invariant condition.
- Domain gate: use no-neck or energy-identity language only for papers that actually involve bubbles, neck regions, harmonic maps, Ginzburg-Landau vortices, phase-field concentration, or related concentration phenomena.

### TP20 Homogenization Transfer
- Source: elliptic homogenization or corrector estimate.
- Target: parabolic, boundary, nonlinear monotone, random, or lower-order perturbed version.
- Obstruction: corrector growth, boundary layer, time oscillation, or stochastic integrability.
- Minimal theorem: first-order error estimate or compactness homogenization in a simplified regime.

### TP21 Variational-To-Gamma/Stability
- Source: variational existence or minimizer regularity.
- Target: perturbed functional, Gamma-limit, penalized model, or constrained minimizer.
- Obstruction: coercivity, recovery sequence, or constraint compactness.
- Minimal theorem: convergence/stability of minimizers plus one regularity consequence.

### TP22 Obstacle / Free-Boundary Perturbation
- Source: obstacle/free-boundary regularity theorem.
- Target: variable coefficients, thin obstacle, dynamic obstacle, or weak forcing.
- Obstruction: nondegeneracy, Weiss-type monotonicity error, or contact set geometry.
- Minimal theorem: regularity or nondegeneracy under small perturbation.

### TP23 Finite-Index / Stable Extension
- Source: theorem for minimizing or stable objects.
- Target: finite-index, almost-stable, or locally stable class.
- Obstruction: bad balls, covering argument, or loss of global inequality.
- Minimal theorem: same estimate away from finitely many controlled regions.

### TP24 Coupled-Field Perturbation
- Source: scalar PDE/geometric theorem.
- Target: weakly coupled system such as Boussinesq, MHD-type, thermoelastic, chemotaxis, or fluid-structure model.
- Obstruction: cross-energy terms, coupling regularity, or loss of maximum principle.
- Minimal theorem: small-coupling or one-way-coupled estimate.

### TP25 Dispersive With Small Potential
- Source: dispersive/Strichartz/decay estimate for free equation.
- Target: equation with small potential, damping, variable coefficient, or boundary perturbation.
- Obstruction: resonance, trapped rays, or commutator loss.
- Minimal theorem: model estimate under no-resonance and smallness assumptions.

### TP26 Maximum-Principle Replacement
- Source: proof using maximum principle.
- Target: system, nonlocal, weak solution, or sign-changing coefficient case where maximum principle fails.
- Obstruction: replacement by De Giorgi, energy, comparison in cones, or entropy method.
- Minimal theorem: recover one consequence of the maximum principle under structural assumptions.

### TP27 Interior-Regularity-To-Singular-Set Estimate
- Source: epsilon regularity or partial regularity theorem.
- Target: dimension estimate, stratification, boundary singular set, or quantitative singular set.
- Obstruction: covering, frequency monotonicity, or quantitative compactness.
- Minimal theorem: upper bound on singular set size in a restricted model.

### TP28 Smooth-Data-To-Low-Regularity Data
- Source: well-posedness or regularity for smooth data.
- Target: rough initial/boundary data, measure data, or borderline integrability.
- Obstruction: approximation stability and compactness.
- Minimal theorem: existence/estimate for data in a precise low-regularity space.

### TP29 Global-To-Localized Version
- Source: global theorem using strong assumptions.
- Target: local or conditional version with cutoff, localized energy, or local geometry.
- Obstruction: cutoff errors and boundary of cylinders/balls.
- Minimal theorem: local estimate with explicit dependence on localized norms.

### TP30 Model-Case-To-Parameter-Family
- Source: theorem at a special parameter, exponent, dimension, or symmetry.
- Target: nearby parameter range or symmetry-broken case.
- Obstruction: uniform constants, bifurcation, or parameter-dependent compactness.
- Minimal theorem: perturbative theorem for small parameter change.

## Candidate Fields To Fill

For each candidate, include:

- `transfer_pattern_used`: one pattern id and short name, for example `TP03 Boundary Transfer`.
- `parent_transfer_pattern`: one of the broad parent patterns above.
- `domain_gate`: why this pattern is appropriate for the input paper's mathematical domain.
- `source_theorem_or_method`: the theorem/proof tool being transferred.
- `target_model`: the new model, setting, or object class.
- `new_obstruction`: the single obstruction that makes the question nontrivial.
- `why_old_proof_may_survive`: the specific proof modules expected to carry over.
- `minimal_publishable_version`: the smallest theorem that could plausibly become a short SCI paper.
- `forbidden_mechanisms_avoided`: irrelevant specialized mechanisms that were not used, such as no-neck, varifolds, Yamabe, De Giorgi, or dispersive estimates when they do not belong to the paper domain.
- `transfer_pattern_fit_score`: integer 0-10.

Weak or missing pattern fields should lower ranking but should not stop the batch. A high `transfer_pattern_fit_score` is a weak positive signal only. Final ranking must be driven primarily by theorem-level clarity, survey/duplicate-risk evidence, proof-sprint viability, one concrete new obstruction, and plausible short-SCI value.
