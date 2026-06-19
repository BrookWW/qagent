# QAgent theorem-level problem generation rules

## 0. Core objective

QAgent must not generate loose, vague, or template-like questions.

The goal is to generate **clean theorem-level research problems**. Each problem should look like a carefully written mathematical theorem prompt that could be copied directly into the configured model backend or QED as the main task.

The generated problem should be:

* theorem-level;
* self-contained;
* precise in assumptions and conclusion;
* not a reproduction of the input paper;
* not a standard corollary;
* not merely a known follow-up theorem;
* nontrivial enough to plausibly lead to an SCI-level note or paper if successful;
* still realistic enough to attack with the configured Codex/model backend or QED plus human mathematical guidance.

If no such problem can be found, QAgent must say so. It must not output a weak or fake problem just to produce something.

---

## 1. Absolute rule for `\begin{q}...\end{q}`

The content inside

```latex
\begin{q}
...
\end{q}
```

must contain **only the mathematical problem itself**.

It must not contain meta text, generation notes, confidence notes, or instruction-template language.

This rule is narrow: do not ban ordinary mathematical words such as `Assume`,
`Suppose`, `Define`, `Prove`, `More precisely`, `Conclusion`, `compactness`,
`regularity`, `convergence`, or `no-neck` when they are used as part of a
genuine theorem statement.

### Forbidden inside `q`

The following meta/template headings and phrases are forbidden inside
`\begin{q}...\end{q}`:

```text
\textbf{Model.}
\textbf{Objects.}
\textbf{Novelty condition.}
\textbf{QED suitability.}
\textbf{User rating.}
\textbf{Why this is good.}
\textbf{Feasibility.}
Generated from metadata
Generated from metadata/abstract only
confidence lower
paper-specific smooth model
work in the paper-specific smooth model
choose assumptions to match the input paper
chosen to match the input paper
under the paper-specific hypotheses
precise structural assumptions should be chosen
the precise structural assumptions should be chosen
theorem-level assertion in the assumptions
this is not to reproduce the input paper
the expected proof should decompose into
QED suitable
QED suitability
the stated compactness, regularity, convergence, connectedness, curvature, or counterexample conclusion
the stated compactness, regularity, convergence, or counterexample conclusion
the indicated narrowed model
the main regularity mechanism
the principal conclusion
```

If any of these phrases appear inside `q`, reject and regenerate.

The `q` environment may contain mathematical labels such as:

```text
Assume:
Suppose:
Define:
Prove:
More precisely:
Conclusion:
```

provided they are used as part of a genuine theorem statement rather than as
template sections.

### What should be inside `q`

Inside `q`, write a complete mathematical theorem-level problem.

It should contain:

1. the domain or manifold;
2. the target or coefficient class;
3. the unknowns;
4. the equation, functional, variational class, or critical-point condition;
5. all regularity assumptions;
6. all energy, index, stability, smallness, or convergence assumptions;
7. all boundary conditions, if any;
8. all definitions needed for the statement;
9. the exact conclusion;
10. the topology of convergence, if relevant;
11. constants and their dependencies;
12. the genuinely new feature built into the theorem itself.

A good `q` should look like this:

```latex
\begin{q}[Precise theorem title]
Let ... . Assume ... . Define ... . Suppose ... . Prove that ... .

More precisely, show that ... .

The constants should depend only on ... and should be independent of ... .
\end{q}
```

A bad `q` looks like this:

```latex
\begin{q}[Vague title]
Generated from metadata/abstract only; confidence lower.
Work in the paper-specific smooth model with the structural hypotheses...
The precise structural assumptions should be chosen to match the input paper.
\end{q}
```

This is forbidden.

---

## 2. Mandatory classification

Before outputting a problem, QAgent must classify it as exactly one of:

```text
Type A: New theorem-level transfer problem
Type B: Sharpness / counterexample problem
Type C: Quantitative refinement problem
Type D: Boundary / endpoint / rough-coefficient variant
Type E: Proof module only, not a new research problem
Type F: Reproduction of known theorem, not acceptable as new
```

Only Type A-D are acceptable for the user's current goal.

If the best possible output is Type E or Type F, QAgent must explicitly say:

```text
No suitable new theorem-level problem found. The best available output is only a proof module / reproduction question.
```

Do not disguise Type E or Type F as a new research problem.

---

## 3. Hard rejection rules

Reject a candidate immediately if any of the following occurs.

### 3.1 Reproduction failure

Reject if the candidate asks to prove:

* the input paper's main theorem;
* a standard corollary of the input paper;
* a known later theorem naturally associated with the input paper;
* a theorem whose title is essentially the same as the input paper.

Examples of bad outputs:

```text
Prove Hutchinson--Tonegawa varifold convergence.
Prove Guaraco finite-index Allen--Cahn regularity.
Prove Lin--Riviere codimension-two current compactness.
Prove Jerrard--Soner Jacobian compactness.
Prove Sacks--Uhlenbeck bubble convergence.
```

These are reproduction or known-theorem outputs, not new problems.

### 3.2 Fake novelty clause

Reject if the candidate merely adds language like

```text
This is not a reproduction of the input paper.
This is a narrowed transfer problem.
This is QED suitable.
```

but does not introduce a real new mathematical obstruction.

A novelty clause is not evidence of novelty.

### 3.3 Undefined assumptions

Reject if the candidate says:

```text
choose assumptions to match the paper
under the paper-specific hypotheses
under the structural assumptions of the input paper
under the standard assumptions
```

without writing the assumptions explicitly.

Every theorem must state all assumptions directly.

### 3.4 Assuming the hard part

Reject if the candidate assumes the main hard step and then asks to prove the conclusion.

Bad examples:

```text
Assume no-neck and prove energy identity.
Assume discrepancy vanishing and prove full varifold convergence.
Assume sheeting and prove regularity.
Assume compactness and prove convergence.
Assume one concentration point and conclude one bubble.
```

If the hard part is assumed, the problem is only a bookkeeping lemma, not a research problem.

### 3.5 Insufficient assumptions

Reject if the assumptions do not logically support the conclusion.

Bad examples:

```text
one concentration point => one bubble
small energy on each dyadic annulus => no-neck
bounded Morse index => multiplicity one
bounded energy => smooth convergence
positive discrepancy vanishes => integrality
```

If a condition is known to be insufficient, do not output the theorem.

### 3.6 Too broad fake transfer

Reject if the only novelty is:

```text
add a potential
add anisotropy
add boundary
add lower-order term
add variable coefficient
```

unless the problem identifies a specific new obstruction.

Acceptable new obstructions include:

* boundary bubbling;
* failure of a pointwise sign estimate;
* sharp rate condition;
* discontinuous coefficient interface;
* explicit cell problem;
* endpoint regularity;
* finite-index localization;
* tangent-map uniqueness;
* quantitative no-neck criterion;
* sharp constant or sharp error term.

---

## 4. What counts as real novelty

A problem has real novelty only if it changes the mathematical obstruction.

Good novelty examples:

```text
Not: prove energy identity.
Better: find a sharp no-neck rate condition.

Not: prove Modica estimate with a variable coefficient.
Better: show the Modica discrepancy sign fails in one dimension and compute the sharp first error.

Not: prove anisotropic Jacobian compactness.
Better: compute the vortex cost at a discontinuous anisotropy interface through a cell problem.

Not: prove finite-index Allen--Cahn regularity.
Better: prove finite-index localization up to Neumann boundary half-balls.

Not: prove boundary regularity.
Better: exclude boundary defect measures under a no-boundary-bubble assumption.

Not: prove partial regularity with a potential.
Better: prove tangent-map uniqueness under an analytic lower-order perturbation.
```

Bad novelty examples:

```text
Add a lower-order term and redo partial regularity.
Add anisotropy without identifying the anisotropic constant.
Add a boundary term but ask only for an interior theorem.
Add finite index but ask for known regularity.
Add a novelty clause but prove the same theorem.
```

---

## 5. Required generation pipeline

QAgent should not directly generate one problem.

It must follow this pipeline.

### Stage 1: Extract paper mechanism

For each input paper, first identify:

```text
Main theorem:
Main mechanism:
Key estimates:
Main assumptions:
Known corollaries:
Likely follow-up literature:
```

Do not generate the final problem yet.

### Stage 2: Generate multiple candidates

Generate at least 8 candidate directions:

```text
1. boundary variant
2. rough coefficient / discontinuous coefficient variant
3. finite-index or stable non-minimizer variant
4. sharpness / counterexample variant
5. quantitative rate variant
6. endpoint regularity variant
7. tangent-map / blow-up uniqueness variant
8. proof module only
```

### Stage 3: Reject weak candidates

For each candidate, assign:

```text
reproduction risk: low / medium / high
literature overlap risk: low / medium / high
new obstruction: explicit / vague / absent
theorem form: clean / incomplete / vague
QED decomposability: good / poor
```

Reject candidates with:

```text
reproduction risk = high
new obstruction = vague or absent
theorem form = incomplete or vague
```

### Stage 4: Polish the best candidate

For the best surviving candidate, rewrite it into a clean theorem statement.

It must specify:

```text
objects
assumptions
functional or PDE
boundary conditions
normalizations
topology
constants
conclusion
proof route
failure modes
literature risk
```

### Stage 5: Final validation

Before outputting the final problem, answer:

```text
Could this already be the main theorem? yes/no
Could this be a standard corollary? yes/no
Could this be solved by simply quoting the input paper? yes/no
Does it contain a genuinely new obstruction? yes/no
Is the theorem statement self-contained? yes/no
Is it plausible but nontrivial? yes/no
```

Only output if the answers are:

```text
no, no, no, yes, yes, yes
```

If not, reject and regenerate.

---

## 6. Scoring gate

Before accepting a generated problem, score it from 0 to 5.

```text
Theorem-form clarity: 0--5
Novelty: 0--5
Nontriviality: 0--5
Feasibility: 0--5
QED decomposability: 0--5
Literature-risk awareness: 0--5
```

Minimum acceptable scores:

```text
Theorem-form clarity >= 4
Novelty >= 4
Nontriviality >= 4
Feasibility >= 3
QED decomposability >= 4
Literature-risk awareness >= 4
```

If any score is below threshold, reject and regenerate.

If after 5 regeneration attempts no candidate passes, output:

```text
No suitable new theorem-level problem found. The best available output is a proof module.
```

Do not lower the standard merely to produce an output.

---

## 7. Required output format

The final answer should have two parts.

### Part I: Metadata outside `q`

Outside `q`, include:

```text
Type:
Source mechanism:
New obstruction:
Why it is not a reproduction:
Literature-risk keywords:
Feasibility comment:
```

This metadata can explain why the problem is interesting.

### Part II: Clean theorem inside `q`

Inside `q`, include only the mathematical problem.

Use this format:

```latex
\begin{q}[<precise theorem title>]
Let ... . Assume ... . Define ... . Suppose ... .

Prove that ... .

More precisely, show that ... .

The constants should depend only on ... and should be independent of ... .
\end{q}
```

Do not put generation notes, novelty explanations, confidence notes, or vague instructions inside `q`.

---

## 8. Clean theorem template

Every accepted theorem-level problem should follow this structure.

```latex
\begin{q}[<precise theorem title>]
Let <domain or manifold> be <regularity and dimension>. Let <target or coefficient
class> satisfy <explicit assumptions>. Let <unknowns> solve/minimize/be critical
for <explicit PDE or functional>.

Assume:
\[
\text{(A1) ...}
\]
\[
\text{(A2) ...}
\]
\[
\text{(A3) ...}
\]

Define <measure/current/varifold/discrepancy/tangent map/neck region> by
\[
...
\]

Prove that <precise conclusion>.

More precisely, show that
\[
...
\]
where the constants depend only on <list> and are independent of <parameter>.

If relevant, also prove <compactness / convergence / sharpness / counterexample /
failure statement>.
\end{q}
```

Reject any output that does not fill every required field.

---

## 9. Examples of acceptable clean `q` statements

### 9.1 Quantitative no-neck criterion

```latex
\begin{q}[Quantitative no-neck criterion for one-bubble Sacks--Uhlenbeck sequences]
Let \(N\subset\mathbb R^L\) be a closed smooth Riemannian submanifold. Let
\(\alpha_j\downarrow1\), and let \(u_j:S^2\to N\) be smooth critical points of
the Sacks--Uhlenbeck energy
\[
E_{\alpha_j}(u)
=
\frac12\int_{S^2}(1+|\nabla u|^2)^{\alpha_j}\,dV .
\]
Assume
\[
\sup_j E_{\alpha_j}(u_j)<\infty,
\]
and suppose that \(u_j\) has exactly one concentration point \(p\in S^2\) and
exactly one bubble scale \(r_j\downarrow0\). In conformal coordinates centered
at \(p\), assume that
\[
(\alpha_j-1)|\log r_j|\to0
\]
and that the Hopf differentials satisfy
\[
\lim_{R\to\infty}\lim_{\delta\downarrow0}\limsup_{j\to\infty}
\int_{B_\delta(p)\setminus B_{Rr_j}(p)}
\left|
\left\langle \partial_z u_j,\partial_z u_j\right\rangle
\right|\,dx
=0 .
\]
Prove the no-neck estimate
\[
\lim_{R\to\infty}\lim_{\delta\downarrow0}\limsup_{j\to\infty}
\operatorname{osc}_{B_\delta(p)\setminus B_{Rr_j}(p)} u_j=0.
\]
Consequently, if \(u_j\rightharpoonup u_0\) weakly in \(W^{1,2}(S^2,N)\) and
the rescaled maps
\[
v_j(y)=u_j(\exp_p(r_jy))
\]
converge locally smoothly on \(\mathbb R^2\) to a nonconstant harmonic sphere
\(\omega:S^2\to N\), prove the one-bubble energy identity
\[
\lim_{j\to\infty}\int_{S^2}|\nabla u_j|^2\,dV
=
\int_{S^2}|\nabla u_0|^2\,dV
+
\int_{S^2}|\nabla \omega|^2\,dV .
\]
\end{q}
```

This is acceptable because it does not merely assume no-neck; it gives concrete quantitative hypotheses intended to imply no-neck.

### 9.2 Sharpness of variable-coefficient Modica discrepancy

```latex
\begin{q}[Sharpness and failure of the Modica discrepancy sign for inhomogeneous Allen--Cahn layers]
Let \(a\in C^3((-2,2))\) be positive and nonconstant, and let \(W\in C^3(\mathbb R)\)
be a smooth balanced double-well potential with nondegenerate wells at \(\pm1\).
Consider one-dimensional transition-layer solutions of
\[
-\varepsilon^2 u_\varepsilon''+a(x)W'(u_\varepsilon)=0
\quad\text{in }(-2,2).
\]
Define the inhomogeneous Modica discrepancy
\[
P_\varepsilon(x)
=
\frac{\varepsilon^2}{2}|u_\varepsilon'(x)|^2
-
a(x)W(u_\varepsilon(x)).
\]
Construct solutions concentrating near a point \(x_0\in(-1,1)\), and derive the
first nonzero asymptotic term of \(P_\varepsilon\) in the transition region
\(x=x_0+\varepsilon t\). In particular, determine whether the sign condition
\[
P_\varepsilon\leq0
\]
can fail when \(a'(x_0)\neq0\), and prove that any general pointwise
Modica-type estimate must contain an error of order at least
\[
\varepsilon |a'(x_0)|.
\]
\end{q}
```

This is acceptable because it asks for a sharp obstruction rather than a broad, possibly known, variable-coefficient estimate.

### 9.3 Discontinuous anisotropy vortex cost

```latex
\begin{q}[Jacobian compactness and vortex pinning for discontinuous anisotropic Ginzburg--Landau energies]
Let \(U\subset\mathbb R^2\) be a smooth bounded domain. Let
\(A:U\to\operatorname{Sym}^+(2)\) be uniformly elliptic and piecewise \(C^1\),
with a jump discontinuity across a smooth curve \(\Gamma\subset U\). Define
\[
I_\varepsilon^A(u)
=
\frac{1}{\log(1/\varepsilon)}
\int_U
\left(
\frac12 A(x)\nabla u:\nabla u
+
\frac{1}{4\varepsilon^2}(1-|u|^2)^2
\right)\,dx .
\]
Assume
\[
\sup_{\varepsilon>0} I_\varepsilon^A(u_\varepsilon)<\infty.
\]
First prove compactness of \(J u_\varepsilon\) in \((C_c^{0,\alpha}(U))^*\).
Then study the \(\Gamma\)-liminf when a vortex concentrates at a point
\(a\in\Gamma\). Determine whether the effective vortex cost at \(a\) is
\[
\min\{\omega_{A^+}(a),\omega_{A^-}(a)\},
\]
an averaged cost, or a new transmission cost determined by an interface cell
problem.
\end{q}
```

This is acceptable because the discontinuity creates a genuine cell-problem obstruction.

---

## 10. Paper-specific blacklist examples

### Sacks--Uhlenbeck

For Sacks--Uhlenbeck, do not output as a new problem:

```text
prove existence of a harmonic two-sphere;
prove bubble convergence for alpha-harmonic maps;
prove energy identity under assumed no-neck;
prove one-bubble energy identity from one concentration point;
prove bubble-tree decomposition without a new hypothesis.
```

A valid new problem should involve:

```text
quantitative no-neck rate;
failure mechanism;
boundary bubbling;
free-boundary version;
sharp concentration-rate condition;
neck length;
Hopf differential control.
```

### Hutchinson--Tonegawa

Do not output:

```text
prove phase-interface varifold convergence;
prove integrality of the limit;
prove mean-curvature identification;
```

unless explicitly labelled as reproduction or proof module.

A valid new problem should involve:

```text
new forcing;
boundary effects;
anisotropic discrepancy;
finite-parameter quantitative estimates;
weaker hypotheses;
failure of discrepancy control.
```

### Guaraco

Do not output:

```text
bounded-index Allen--Cahn critical points converge to smooth minimal hypersurfaces;
one-parameter min-max gives embedded minimal hypersurface;
bounded index implies multiplicity one.
```

A valid new problem should involve:

```text
finite-index localization near boundary;
Neumann/free-boundary modules;
forced Allen--Cahn;
quantitative finite-epsilon estimates;
noncompact or singular ambient settings;
sharp multiplicity obstruction.
```

### Lin--Riviere / Jerrard--Soner

Do not output:

```text
Jacobian currents are compact;
limits are integral codimension-two currents;
GL minimizers converge to area-minimizing currents;
bounded normalized energy implies compactness in dual Holder norm.
```

A valid new problem should involve:

```text
finite-index non-minimizers;
stationary but non-minimizing currents;
rough or discontinuous coefficients;
interface cell problems;
boundary vortex pinning;
sharp vortex cost.
```

---

## 11. Final self-check before output

Before finalizing, QAgent must answer internally:

```text
1. Is this the input paper's main theorem?
2. Is this a standard corollary?
3. Is this likely a known follow-up theorem?
4. What exact mathematical obstruction is new?
5. Which assumption is the most delicate?
6. Which conclusion is the main nontrivial point?
7. What is the first lemma one would try to prove?
8. What literature search could kill this problem?
9. Can the proof be decomposed into QED-verifiable pieces?
10. If false, what counterexample mechanism is most likely?
```

If questions 1-3 are yes, reject.

If question 4 has no concrete answer, reject.

If question 7 has no concrete lemma, reject.

---

## 12. Final instruction

QAgent should prefer saying

```text
No suitable new theorem-level problem found.
```

over outputting a bad, vague, or already-known problem.

The user wants fewer but much better problems.

Each accepted problem should look as if a strong configured model session had been used specifically to formulate that theorem. The `q` environment must be clean enough to copy directly into a proof agent without further rewriting.
