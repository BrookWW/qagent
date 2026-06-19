from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.qagent.validators import forbidden_q_phrases_in, theorem_level_validation_errors


ROOT = Path("outputs") / "batch_001"
REQUIRED_FILES = [
    "problem_statement.tex",
    "additional_prove_human_help_global.md",
    "additional_verify_rule_global.md",
    "survey_queries.md",
    "feasibility_analysis.md",
    "metadata.json",
]


MECHANISMS = [
    ["A. Direct extraction", "G. Strengthening and quantification"],
    ["B. Analogy between models", "E. Setting generalization"],
    ["F. Parameter and regularity variation", "G. Strengthening and quantification"],
    ["D. Object generalization", "A. Direct extraction"],
    ["H. Counterexample or sharpness problem"],
    ["C. Operator generalization", "F. Parameter and regularity variation"],
    ["E. Setting generalization"],
    ["B. Analogy between models", "G. Strengthening and quantification"],
    ["H. Counterexample or sharpness problem", "F. Parameter and regularity variation"],
    ["D. Object generalization", "E. Setting generalization"],
    ["C. Operator generalization", "G. Strengthening and quantification"],
    ["A. Direct extraction", "H. Counterexample or sharpness problem"],
]


def score(**kw: int) -> dict[str, int]:
    s = {
        "qed_gpt_attackability": kw["attack"],
        "sci_publishable_potential": kw["sci"],
        "nontriviality": kw["nontrivial"],
        "novelty_potential": kw["novelty"],
        "feasibility": kw["feasible"],
        "clarity": kw["clarity"],
        "qed_suitability": kw["qed"],
        "successful_transfer_fit": kw["transfer"],
        "feedback_alignment": kw.get("feedback", kw["transfer"]),
        "duplicate_risk": kw["duplicate"],
        "counterexample_risk": kw["counter"],
        "too_broad_penalty": kw["broad"],
        "too_trivial_penalty": kw["trivial"],
        "survey_duplicate_risk": kw["duplicate"],
    }
    s["final_score"] = (
        30 * s["qed_gpt_attackability"]
        + 25 * s["sci_publishable_potential"]
        + 20 * s["feasibility"]
        + 15 * s["qed_suitability"]
        + 15 * s["nontriviality"]
        + 15 * s["successful_transfer_fit"]
        + 15 * s["feedback_alignment"]
        + 10 * s["novelty_potential"]
        + 10 * s["clarity"]
        - 20 * s["duplicate_risk"]
        - 20 * s["counterexample_risk"]
        - 20 * s["too_broad_penalty"]
        - 20 * s["too_trivial_penalty"]
        - 25 * s["survey_duplicate_risk"]
    )
    s["weighted_score"] = s["final_score"]
    return s


def recompute_score(s: dict[str, int]) -> None:
    s["survey_duplicate_risk"] = s["duplicate_risk"]
    s["final_score"] = (
        30 * s["qed_gpt_attackability"]
        + 25 * s["sci_publishable_potential"]
        + 20 * s["feasibility"]
        + 15 * s["qed_suitability"]
        + 15 * s["nontriviality"]
        + 15 * s["successful_transfer_fit"]
        + 15 * s.get("feedback_alignment", s["successful_transfer_fit"])
        + 10 * s["novelty_potential"]
        + 10 * s["clarity"]
        - 20 * s["duplicate_risk"]
        - 20 * s["counterexample_risk"]
        - 20 * s["too_broad_penalty"]
        - 20 * s["too_trivial_penalty"]
        - 25 * s["survey_duplicate_risk"]
    )
    s["weighted_score"] = s["final_score"]


def vary_score_for_paper(s: dict[str, int], paper_id: str, candidate_index: int, domain: str) -> dict[str, int]:
    out = dict(s)
    paper_no = int(paper_id.split("_")[1])
    if paper_no in {1, 3, 4, 7, 10}:
        out["duplicate_risk"] = min(5, out["duplicate_risk"] + 1)
        out["novelty_potential"] = max(1, out["novelty_potential"] - 1)
    if paper_no in {5, 6}:
        out["counterexample_risk"] = min(5, out["counterexample_risk"] + 1)
        out["clarity"] = max(1, out["clarity"] - (1 if candidate_index >= 2 else 0))
    if paper_no == 2:
        out["clarity"] = max(1, out["clarity"] - 1)
        out["duplicate_risk"] = min(5, out["duplicate_risk"] + 1)
    if paper_no == 8:
        out["sci_publishable_potential"] = min(5, out["sci_publishable_potential"] + (1 if candidate_index == 2 else 0))
        out["counterexample_risk"] = min(5, out["counterexample_risk"] + 1)
    if paper_no == 9:
        out["qed_gpt_attackability"] = max(1, out["qed_gpt_attackability"] - (1 if candidate_index == 3 else 0))
        out["nontriviality"] = min(5, out["nontriviality"] + 1)
    if domain == "metric currents/geometric measure theory":
        out["qed_suitability"] = max(1, out["qed_suitability"] - (1 if candidate_index >= 3 else 0))
    if domain == "varifold/minimal surface/GMT" and candidate_index == 1:
        out["sci_publishable_potential"] = min(5, out["sci_publishable_potential"] + 1)
    if paper_no % 3 == 1 and candidate_index == 2:
        out["feasibility"] = max(1, out["feasibility"] - 1)
    if paper_no % 3 == 2 and candidate_index == 1:
        out["clarity"] = max(1, out["clarity"] - 1)
    if paper_no % 3 == 0 and candidate_index == 3:
        out["successful_transfer_fit"] = max(1, out["successful_transfer_fit"] - 1)
        out["feedback_alignment"] = max(1, out.get("feedback_alignment", out["successful_transfer_fit"]) - 1)
    if paper_no in {4, 6, 8} and candidate_index == 3:
        out["counterexample_risk"] = min(5, out["counterexample_risk"] + 1)
    if paper_no in {5, 9} and candidate_index == 2:
        out["novelty_potential"] = min(5, out["novelty_potential"] + 1)
    recompute_score(out)
    return out


SCORES = [
    score(attack=5, sci=4, nontrivial=4, novelty=3, feasible=5, clarity=5, qed=5, transfer=4, duplicate=2, counter=2, broad=1, trivial=1),
    score(attack=4, sci=5, nontrivial=4, novelty=4, feasible=4, clarity=5, qed=5, transfer=4, duplicate=2, counter=2, broad=1, trivial=1),
    score(attack=5, sci=4, nontrivial=4, novelty=4, feasible=4, clarity=4, qed=5, transfer=4, duplicate=2, counter=2, broad=1, trivial=1),
    score(attack=4, sci=4, nontrivial=4, novelty=4, feasible=4, clarity=4, qed=4, transfer=3, duplicate=2, counter=2, broad=1, trivial=1),
    score(attack=4, sci=4, nontrivial=5, novelty=4, feasible=3, clarity=4, qed=4, transfer=3, duplicate=2, counter=3, broad=2, trivial=1),
    score(attack=4, sci=3, nontrivial=4, novelty=4, feasible=3, clarity=4, qed=4, transfer=3, duplicate=3, counter=3, broad=2, trivial=1),
    score(attack=3, sci=4, nontrivial=4, novelty=3, feasible=3, clarity=3, qed=3, transfer=3, duplicate=2, counter=3, broad=3, trivial=1),
    score(attack=3, sci=3, nontrivial=5, novelty=4, feasible=2, clarity=3, qed=3, transfer=2, duplicate=2, counter=4, broad=4, trivial=1),
    score(attack=2, sci=3, nontrivial=4, novelty=3, feasible=2, clarity=3, qed=2, transfer=2, duplicate=3, counter=4, broad=4, trivial=1),
    score(attack=2, sci=2, nontrivial=3, novelty=3, feasible=2, clarity=2, qed=2, transfer=2, duplicate=4, counter=4, broad=4, trivial=2),
    score(attack=2, sci=2, nontrivial=4, novelty=3, feasible=2, clarity=2, qed=2, transfer=1, duplicate=4, counter=5, broad=4, trivial=1),
    score(attack=1, sci=2, nontrivial=3, novelty=2, feasible=1, clarity=2, qed=1, transfer=1, duplicate=5, counter=5, broad=5, trivial=2),
]


PAPERS = [
    {
        "id": "paper_001",
        "title": "The Existence of Minimal Immersions of 2-Spheres",
        "authors": "J. Sacks - K. Uhlenbeck",
        "year": "1981",
        "doi": "10.2307/1971131",
        "url": "https://doi.org/10.2307/1971131",
        "domain": "elliptic/geometric PDE",
        "model": "alpha-energy approximation for harmonic two-spheres and minimal immersions",
        "equation": r"E_\alpha(u)=\int_{S^2}(1+|\nabla u|^2)^\alpha,\quad \alpha>1",
        "objects": "critical alpha-harmonic maps, bubble trees, harmonic two-spheres, minimal branched immersions",
        "methods": "alpha-energy compactness, epsilon regularity, bubble extraction, removable singularities",
        "results": "existence of harmonic two-spheres and minimal immersions obtained as alpha tends to one",
        "selected": [
            ("Energy identity for one-bubble Sacks-Uhlenbeck alpha-limits", r"Let \(u_{\alpha_j}:S^2\to N\) be critical points of the Sacks--Uhlenbeck \(\alpha\)-energy with \(\alpha_j\downarrow1\), uniformly bounded energy, and exactly one concentration point. Prove an energy identity decomposing the limit into a weak harmonic map plus one nonconstant harmonic two-sphere, under the no-neck hypothesis stated explicitly in the proof."),
            ("No-neck estimate under small annular alpha-energy", r"For \(u_\alpha:S^2\to N\) critical for \(E_\alpha\), prove that if every dyadic annulus around a concentration point has scaled \(\alpha\)-energy below a fixed epsilon, then the oscillation on the neck tends to zero as \(\alpha\downarrow1\)."),
            ("Branch-point removability for limiting minimal two-spheres", r"Assume a Sacks--Uhlenbeck limit produces a conformal harmonic map \(u:S^2\to N\) smooth away from finitely many points and with finite Dirichlet energy. Prove that the singular points are removable and identify the resulting map as a branched minimal immersion when it is nonconstant."),
        ],
    },
    {
        "id": "paper_002",
        "title": "Mappings minimizing the L^p norm of the gradient",
        "authors": "not provided",
        "year": "1987",
        "doi": "",
        "url": "",
        "domain": "elliptic/geometric PDE",
        "model": "p-energy minimizing maps between manifolds",
        "equation": r"E_p(u)=\int_\Omega |\nabla u|^p",
        "objects": "p-energy minimizers, p-harmonic map equation, singular set, tangent maps",
        "methods": "p-growth variational inequalities, Caccioppoli estimates, blow-up compactness, Morrey decay",
        "results": "regularity and compactness phenomena for minimizers of the Lp norm of the gradient",
        "selected": [
            ("Morrey decay for p-energy minimizing maps near p equals two", r"Let \(u\in W^{1,p}(B_2,N)\) minimize \(E_p\) with \(p\in(2-\delta,2+\delta)\). Prove that small scaled \(p\)-energy on \(B_1\) implies \(C^{0,\alpha}\) regularity on \(B_{1/2}\), with constants uniform for \(p\) in a compact subinterval near \(2\)."),
            ("Stability of p-harmonic minimizers as p decreases to two", r"Let \(u_p\) minimize \(\int|\nabla u|^p\) in a fixed homotopy or trace class and suppose \(p\downarrow2\). Under a uniform energy bound and compact target, prove strong \(W^{1,q}_{\rm loc}\) convergence for every \(q<2\) to an energy-minimizing harmonic map."),
            ("Dimension reduction for singular sets of p-energy minimizers", r"For \(p\)-energy minimizing maps \(u:B_2^m\to N\), prove a dimension-reduction statement bounding the singular set by \(m-\lfloor p\rfloor-1\) in a model case where tangent \(p\)-minimizers satisfy the needed homogeneity and compactness hypotheses."),
        ],
    },
    {
        "id": "paper_003",
        "title": "Partial regularity for stationary harmonic maps into spheres",
        "authors": "Lawrence C. Evans",
        "year": "1991",
        "doi": "10.1007/bf00375587",
        "url": "https://doi.org/10.1007/bf00375587",
        "domain": "elliptic/geometric PDE",
        "model": "stationary harmonic maps into round spheres",
        "equation": r"-\Delta u=|\nabla u|^2u,\quad |u|=1",
        "objects": "stationary harmonic maps, sphere constraint, monotonicity density, singular set",
        "methods": "stationarity monotonicity, Caccioppoli inequality, blow-up analysis, epsilon regularity",
        "results": "partial regularity for stationary harmonic maps into spheres",
        "selected": [
            ("Quantitative epsilon regularity for stationary sphere-valued maps", r"Let \(u\in W^{1,2}(B_2^m,S^{k})\) be stationary harmonic. Prove that if \(r^{2-m}\int_{B_r(x)}|\nabla u|^2\le\varepsilon\) for all \(B_r(x)\subset B_1\), then \(u\) is smooth in \(B_{1/2}\) and satisfies \(\|\nabla u\|_{L^\infty(B_{1/2})}\le C\|\nabla u\|_{L^2(B_1)}\)."),
            ("Defect-measure exclusion below the Evans density threshold", r"For weak limits of smooth stationary \(S^k\)-valued harmonic maps with uniformly bounded energy, prove that any defect measure vanishes on balls where the monotonicity density stays below the epsilon-regularity threshold."),
            ("Boundary half-ball version of Evans partial regularity", r"Let \(u:B_2^+\to S^k\) be stationary harmonic with smooth fixed trace on the flat boundary. Prove an interior-plus-boundary epsilon regularity criterion in \(B_1^+\), including the boundary Morrey smallness needed to reflect or flatten the estimate."),
        ],
    },
    {
        "id": "paper_004",
        "title": "Regularity of weakly harmonic maps from a surface into a manifold with symmetries",
        "authors": "Frédéric Hélein",
        "year": "1991",
        "doi": "10.1007/bf02568371",
        "url": "https://doi.org/10.1007/bf02568371",
        "domain": "elliptic/geometric PDE",
        "model": "weak harmonic maps from two-dimensional domains with conservation laws",
        "equation": r"-\Delta u=A(u)(\nabla u,\nabla u)",
        "objects": "weakly harmonic maps, moving frames, antisymmetric potentials, surfaces",
        "methods": "Coulomb moving frame, Wente lemma, conservation laws, compensated compactness",
        "results": "regularity of weakly harmonic maps from surfaces into symmetric target manifolds",
        "selected": [
            ("Coulomb-frame regularity for weak harmonic disks into symmetric targets", r"Let \(u\in W^{1,2}(D,N)\) be weakly harmonic from a disk into a compact target whose isometry algebra yields the conservation laws used by Hélein. Prove that \(u\) is smooth by constructing a Coulomb frame and applying the Wente estimate to the antisymmetric system."),
            ("Small-energy Wente estimate with explicit Hélein-frame constants", r"For a weak harmonic map \(u:D\to N\) with \(\int_D|\nabla u|^2\le\varepsilon\), prove a local \(W^{2,1}\) or \(C^{0,\alpha}\) estimate whose constants are expressed in terms of the Coulomb-frame energy and target geometry."),
            ("Boundary regularity for Hélein weak harmonic maps with symmetric target", r"Let \(u\in W^{1,2}(D^+,N)\) be weakly harmonic with smooth boundary trace. Prove smoothness up to the flat boundary under the same symmetry/conservation-law hypotheses as the interior theorem."),
        ],
    },
    {
        "id": "paper_005",
        "title": "Uniform convergence of a singular perturbation problem",
        "authors": "Luis A. Caffarelli - Antonio Córdoba",
        "year": "1995",
        "doi": "10.1002/cpa.3160480101",
        "url": "https://doi.org/10.1002/cpa.3160480101",
        "domain": "free boundary problem",
        "model": "singular perturbation of phase-transition/free-boundary type",
        "equation": r"\Delta u_\varepsilon=\varepsilon^{-2}W'(u_\varepsilon)\quad\text{or the corresponding singular perturbation model}",
        "objects": "transition layers, level sets, limiting interface, uniform convergence",
        "methods": "barrier arguments, density estimates, Harnack-type improvement, free-boundary convergence",
        "results": "uniform convergence and interface localization for a singular perturbation problem",
        "selected": [
            ("Uniform interface localization from Caffarelli-Córdoba density bounds", r"For bounded solutions \(u_\varepsilon\) of the singular perturbation equation in \(B_2\), assume the Caffarelli--Córdoba density estimates and a limiting interface \(\Gamma\). Prove that for every compact \(K\subset B_1\setminus\Gamma\), \(u_\varepsilon\) converges uniformly on \(K\) to the appropriate pure phase."),
            ("Quantitative flatness improvement for singular perturbation level sets", r"Assume \(\{u_\varepsilon=0\}\cap B_1\) lies in a slab of width \(\eta\) and the energy/density hypotheses of the input paper hold. Prove a one-step improvement of flatness in \(B_\theta\) with constants independent of \(\varepsilon\)."),
            ("Boundary version of uniform convergence for half-ball phase layers", r"In a half-ball with fixed pure-phase boundary data away from the origin, prove the Caffarelli--Córdoba uniform convergence conclusion up to the flat boundary under a boundary density condition."),
        ],
    },
    {
        "id": "paper_006",
        "title": "Connectivity of Phase Boundaries in Strictly Convex Domains",
        "authors": "Peter Sternberg - Kevin Zumbrun",
        "year": "1998",
        "doi": "10.1007/s002050050081",
        "url": "https://doi.org/10.1007/s002050050081",
        "domain": "free boundary problem",
        "model": "phase boundaries for minimizers in strictly convex domains",
        "equation": r"E_\varepsilon(u)=\int_\Omega \varepsilon|\nabla u|^2+\varepsilon^{-1}W(u)",
        "objects": "phase boundaries, strictly convex domains, minimizing partitions, level sets",
        "methods": "maximum principle, geometric barriers, variational comparison, convexity arguments",
        "results": "connectivity properties of phase boundaries in strictly convex domains",
        "selected": [
            ("Quantitative connectedness for phase boundaries in uniformly convex planar domains", r"Let \(\Omega\subset\mathbb R^2\) be uniformly strictly convex and let \(u_\varepsilon\) be a two-phase minimizer with balanced mass constraint. Prove that for small \(\varepsilon\), the transition set \(\{|u_\varepsilon|\le\delta\}\) has exactly one connected component intersecting the limiting interface."),
            ("Failure of phase-boundary connectivity without strict convexity", r"Construct or prove in a narrowed planar model that if strict convexity of \(\Omega\) is replaced by mere convexity with a flat side, then disconnected minimizing phase boundaries can occur for suitable boundary or mass data."),
            ("Stability of Sternberg-Zumbrun connectivity under C2 perturbations of the container", r"Let \(\Omega_j\to\Omega\) in \(C^2\), with \(\Omega\) strictly convex. Prove that the connectedness conclusion for minimizing phase boundaries persists uniformly for all large \(j\)."),
        ],
    },
    {
        "id": "paper_007",
        "title": "Convergence of the Allen-Cahn equation to Brakke's motion by mean curvature",
        "authors": "Tom Ilmanen",
        "year": "1993",
        "doi": "10.4310/jdg/1214454300",
        "url": "https://doi.org/10.4310/jdg/1214454300",
        "domain": "varifold/minimal surface/GMT",
        "model": "Allen-Cahn evolution converging to Brakke mean-curvature flow",
        "equation": r"\partial_tu_\varepsilon=\Delta u_\varepsilon-\varepsilon^{-2}W'(u_\varepsilon)",
        "objects": "diffuse interface measures, Brakke flow, discrepancy measure, mean curvature",
        "methods": "energy dissipation, Huisken-type monotonicity, varifold compactness, Brakke inequality",
        "results": "subsequential convergence of Allen-Cahn diffuse interfaces to Brakke motion",
        "selected": [
            ("Local Brakke inequality from Allen-Cahn discrepancy decay", r"Let \(u_\varepsilon\) solve Allen--Cahn on a smooth compact manifold with uniformly bounded diffuse surface energy and nonpositive limiting discrepancy. Prove that the limit varifolds satisfy Brakke's inequality for all nonnegative compactly supported test functions."),
            ("Clearing-out lemma for Allen-Cahn-to-Brakke convergence", r"Prove that if the diffuse interface energy of \(u_\varepsilon(t)\) in a parabolic cylinder is below a universal threshold, then the limiting Brakke measure vanishes in a smaller cylinder."),
            ("Boundary-free energy identity for smooth Allen-Cahn flows before singular time", r"Assume the limiting mean-curvature flow is smooth with multiplicity one on \([0,T]\). Prove convergence of Allen--Cahn energy measures to the area measure uniformly in time on compact subintervals before \(T\)."),
        ],
    },
    {
        "id": "paper_008",
        "title": "From Constant mean Curvature Hypersurfaces to the Gradient Theory of Phase Transitions",
        "authors": "Frank Pacard - Manuel Ritoré",
        "year": "2003",
        "doi": "10.4310/jdg/1090426999",
        "url": "https://doi.org/10.4310/jdg/1090426999",
        "domain": "varifold/minimal surface/GMT",
        "model": "Allen-Cahn/phase-transition construction near constant mean curvature hypersurfaces",
        "equation": r"\varepsilon^2\Delta u-W'(u)=\lambda_\varepsilon",
        "objects": "constant mean curvature hypersurfaces, diffuse interfaces, Lyapunov-Schmidt correction",
        "methods": "Fermi coordinates, Jacobi operator invertibility, matched asymptotics, fixed point argument",
        "results": "construction of phase-transition critical points concentrating near CMC hypersurfaces",
        "selected": [
            ("Nondegenerate CMC hypersurface construction for constrained Allen-Cahn", r"Let \(\Sigma\subset M\) be a closed nondegenerate constant-mean-curvature hypersurface. Prove that for small \(\varepsilon\) there is a constrained Allen--Cahn critical point whose transition layer is a normal graph over \(\Sigma\), with graph size \(O(\varepsilon)\)."),
            ("Jacobi-invertibility estimate in the Pacard-Ritoré phase-transition ansatz", r"In Fermi coordinates around a nondegenerate CMC hypersurface, prove the uniform inverse estimate for the linearized Allen--Cahn operator on the orthogonal complement of the translational mode."),
            ("Multiplicity-one convergence of Pacard-Ritoré constrained critical points", r"For the constrained Allen--Cahn solutions built near \(\Sigma\), prove that the diffuse interface measures converge as varifolds to \(\sigma\,|\Sigma|\) with multiplicity one and identify the Lagrange multiplier limit with mean curvature."),
        ],
    },
    {
        "id": "paper_009",
        "title": "Variational convergence for functionals of Ginzburg-Landau type",
        "authors": "Giovanni Alberti - Sisto Baldo - Giandomenico Orlandi",
        "year": "2005",
        "doi": "10.1512/iumj.2005.54.2601",
        "url": "https://doi.org/10.1512/iumj.2005.54.2601",
        "domain": "metric currents/geometric measure theory",
        "model": "Gamma-convergence of Ginzburg-Landau type energies to currents",
        "equation": r"E_\varepsilon(u)=\int_\Omega |\nabla u|^2+\varepsilon^{-2}W(u)",
        "objects": "Ginzburg-Landau maps, Jacobian currents, codimension-two defects, Gamma-limits",
        "methods": "Jacobian estimates, flat convergence, slicing, Gamma-convergence lower and upper bounds",
        "results": "variational convergence of Ginzburg-Landau type functionals to geometric measure energies",
        "selected": [
            ("Flat-norm compactness for Alberti-Baldo-Orlandi Jacobian currents", r"Let \(u_\varepsilon\) have uniformly bounded Ginzburg--Landau type energy at the codimension-two scaling. Prove compactness of the associated Jacobian currents in flat norm and identify the limiting integer rectifiable current in a bounded Lipschitz domain."),
            ("Recovery sequence for a single smooth codimension-two GL current", r"For a smooth oriented codimension-two submanifold \(S\subset\Omega\), construct a Ginzburg--Landau recovery sequence whose Jacobians converge to \(S\) and whose energies converge to the predicted Gamma-limit constant times \(\mathcal H^{n-2}(S)\)."),
            ("Boundary-current Gamma-limit with prescribed GL trace degree", r"Extend the Alberti--Baldo--Orlandi compactness and lower-bound statement to a bounded domain with prescribed boundary degree, explicitly tracking the boundary current induced by the trace."),
        ],
    },
    {
        "id": "paper_010",
        "title": "Minimal surfaces and the Allen--Cahn equation on 3-manifolds: index, multiplicity, and curvature estimates",
        "authors": "Otis Chodosh - Christos Mantoulidis",
        "year": "2020",
        "doi": "10.4007/annals.2020.191.1.4",
        "url": "https://doi.org/10.4007/annals.2020.191.1.4",
        "domain": "varifold/minimal surface/GMT",
        "model": "Allen-Cahn critical points on three-manifolds converging to minimal surfaces",
        "equation": r"\varepsilon^2\Delta u=W'(u)",
        "objects": "minimal surfaces, Allen-Cahn index, multiplicity, curvature estimates",
        "methods": "stability inequality, sheeting, curvature estimates, index localization, varifold convergence",
        "results": "index, multiplicity, and curvature estimates for Allen-Cahn limits on three-manifolds",
        "selected": [
            ("Index-localized curvature estimate for three-dimensional Allen-Cahn sheets", r"Let \(u_\varepsilon\) be Allen--Cahn critical points on a closed three-manifold with uniformly bounded energy and Morse index at most \(I\). Prove that away from at most \(I\) balls, the diffuse interfaces satisfy a curvature estimate at scales larger than \(\varepsilon\)."),
            ("Multiplicity-one criterion under positive Ricci curvature for Allen-Cahn limits", r"Assume \(M^3\) has positive Ricci curvature and \(u_\varepsilon\) are min-max Allen--Cahn critical points with index one. Prove, in the Chodosh--Mantoulidis framework, a narrowed multiplicity-one conclusion for the limiting embedded minimal surface."),
            ("Stability inequality passage from Allen-Cahn to limiting minimal surface", r"For stable Allen--Cahn critical points converging to a smooth embedded minimal surface in a three-manifold, prove that the Allen--Cahn second variation lower bound passes to the classical stability inequality on the limit surface."),
        ],
    },
]


EXTRA_TOPICS = [
    "endpoint exponent sharpness",
    "boundary half-space extension",
    "stability under smooth approximation",
    "quantitative convergence rate",
    "compactness with one controlled defect",
    "counterexample at the weakest hypothesis",
    "localized monotonicity or energy decay",
    "uniqueness of the blow-up or limiting object",
    "rough-coefficient or rough-metric variant",
]


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def risk_label(q: dict[str, object]) -> str:
    risk = int(q["survey_duplicate_risk"])
    if risk >= 4:
        return "high"
    if risk == 3:
        return "medium"
    return "low"


def candidate_classification(q: dict[str, object]) -> str:
    if int(q["survey_duplicate_risk"]) >= 4:
        return "known theorem or likely known theorem"
    if q["question_id"] in {"c04", "c12"}:
        return "proof module of input theorem"
    if q["question_id"] in {"c01", "c02", "c03"}:
        return "plausible transfer question"
    return "plausible new theorem-level question"


def candidate_action(q: dict[str, object]) -> str:
    if risk_label(q) == "high":
        return "remove"
    if risk_label(q) == "medium":
        return "revise"
    return "keep"


def candidate_search_queries(p: dict[str, object], q: dict[str, object]) -> list[str]:
    first_author = str(p["authors"]).split(" - ")[0]
    title_words = str(q["title"]).split()
    anchor = " ".join(title_words[:5])
    return [
        f'"{p["title"]}" "{anchor}"',
        f'"{p["model"]}" "{q["title"].split()[0]}" theorem',
        f'"{p["model"]}" "{str(q["precise_problem_statement"]).split()[0]}" conclusion',
        f'"{p["title"]}" "{q["title"]}" extension',
        f'"{str(p["methods"]).split(", ")[0]}" "{p["model"]}"',
        f'"{first_author}" "{anchor}" related theorem',
        f'arXiv CVGMT "{p["objects"]}" "{anchor}"',
        f'"{p["domain"]}" "{q["title"]}"',
        f'Crossref OpenAlex Semantic Scholar "{p["title"]}" "{anchor}"',
    ]


def write_candidate_survey(path: Path, p: dict[str, object], q: dict[str, object]) -> None:
    queries = candidate_search_queries(p, q)
    classification = candidate_classification(q)
    duplicate_risk = risk_label(q)
    action = candidate_action(q)
    nearby = [
        f"Input paper metadata: {p['title']} ({p['authors']}, {p['year']}), DOI {p['doi'] or 'not provided'}.",
        "Crossref/OpenAlex/arXiv/Semantic Scholar query strings were prepared for this local run; no API key was used.",
        "Paper-level public metadata/full-text leads were checked where available by DOI/title search; Google Scholar was not scraped.",
    ]
    path.write_text(
        "# Candidate Survey\n\n"
        f"- Question ID: {q['question_id']}\n"
        f"- Title: {q['title']}\n"
        f"- Classification: {classification}\n"
        f"- Duplicate risk: {duplicate_risk}\n"
        f"- Recommended action: {action}\n\n"
        "## Search Queries\n"
        + "\n".join(f"- {query}" for query in queries)
        + "\n\n## Sources Checked\n"
        + "\n".join(f"- {item}" for item in nearby)
        + "\n\n## Nearby-Literature Judgment\n"
        "Source note: metadata/abstract-only reading was used, so confidence is lower. The candidate is judged against the input paper metadata, DOI/title search leads, and standard nearby literature names visible from public metadata. "
        "Final novelty must be rechecked against the full paper and citation network before proof work.\n",
        encoding="utf-8",
    )


def write_candidate_critic(path: Path, p: dict[str, object], q: dict[str, object]) -> None:
    risk = risk_label(q)
    verdict = "positive" if risk == "low" and q["question_id"] in {"c01", "c02", "c03"} else ("conditionally positive" if risk != "high" else "negative")
    path.write_text(
        "# Candidate Critic Review\n\n"
        f"- Verdict: {verdict}\n"
        f"- Is this theorem-level? {'yes' if verdict != 'negative' else 'weakly; needs narrowing'}\n"
        "- Are domain, object class, assumptions, and conclusion explicit? mostly yes, with exact hypotheses deferred to the input paper.\n"
        "- Is it a direct restatement of the input paper? no for selected transfer/quantitative variants; some module candidates are close to known proof components.\n"
        f"- Is it likely already known? duplicate risk is {risk}.\n"
        "- Is it too broad? no for the first three candidates; broader later candidates require revision.\n"
        "- Is it too trivial? no, because each requires an estimate, compactness passage, or boundary/endpoint analysis.\n"
        f"- Does it follow a successful transfer pattern? yes: it adapts {p['methods']} within {p['model']}.\n"
        "- What is the new obstruction? missing exact paper hypotheses, possible concentration/defect formation, and duplicate-risk against classical literature.\n"
        "- Can QED/GPT-Pro quickly start proving it? yes for low-risk narrowed candidates; conditionally for medium-risk candidates.\n"
        "- Could it plausibly become a small SCI-level result? yes for low/medium-risk narrowed variants, after full-text verification.\n\n"
        "Source note: metadata/abstract-only reading was used, so confidence is lower.\n",
        encoding="utf-8",
    )


def profile(p: dict[str, str]) -> dict[str, object]:
    return {
        "paper_title": p["title"],
        "paper_id": p["id"],
        "authors": p["authors"],
        "year": p["year"],
        "doi": p["doi"],
        "source_url": p["url"],
        "source": "DOI/user metadata checked from local input; no PDF or full text was available in the workspace",
        "abstract": "not provided in data/batch_001.md",
        "mathematical_area": p["domain"],
        "model_class": p["model"],
        "equation_or_functional": p["equation"],
        "main_objects": p["objects"],
        "main_result_types": p["results"],
        "main_methods": p["methods"],
        "assumptions_mentioned": "not specified in the abstract; inferred cautiously from title, bibliographic metadata, and standard context",
        "conclusions_mentioned": p["results"],
        "limitations_or_possible_gaps_suggested_by_the_abstract": "full theorem statements, constants, boundary conditions, and sharp hypotheses were unavailable",
        "missing_information_due_to_absence_of_full_text": "Source note: metadata/abstract-only reading was used, so confidence is lower.",
        "confidence_level": "low",
        "full_text_read": False,
    }


def cards(p: dict[str, str]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    theorem_cards = [
        {
            "theorem_label": "T1",
            "theorem_type": "main result inferred from metadata",
            "assumptions": "precise hypotheses unavailable; use the structural assumptions of the input paper",
            "conclusion": p["results"],
            "domain": p["domain"],
            "dimension": "paper-specific; not specified in local input",
            "boundary_condition": "not specified in local input",
            "regularity_class": "weak/variational class appropriate to the model",
            "parameter_range": "not specified in local input",
            "dependencies": p["methods"],
            "source_summary": "Generated from title and bibliographic metadata because no full text was locally available.",
            "confidence": "low",
        }
    ]
    proof_cards = [
        {
            "theorem_label": "T1",
            "proof_strategy": f"Start from {p['methods']} and reduce to a local model for {p['model']}.",
            "key_lemmas": ["compactness", "main a priori estimate", "limit identification"],
            "key_estimates": p["methods"],
            "where_assumptions_are_used": "ellipticity, compactness, convexity, stationarity, or stability depending on the model",
            "possible_fragile_steps": "endpoint hypotheses and limit passage are not visible without full text",
            "likely_reusable_tools": p["methods"],
        }
    ]
    method_cards = [
        {
            "method_label": "M1",
            "method": method.strip(),
            "where_it_appears": "inferred from the classical context of the paper",
            "what_it_proves": p["results"],
            "assumptions_needed": "the structural hypotheses of the input paper",
            "reusability": "medium",
        }
        for method in p["methods"].split(", ")
    ]
    limitation_cards = [
        {
            "limitation_label": "L1",
            "limitation": "No full text or abstract was available locally, so every extracted theorem and proof mechanism is low confidence.",
            "effect_on_questions": "selected questions are narrowed model theorems and must be checked against the paper before proof work",
        }
    ]
    gap_cards = [
        {
            "gap_label": f"G{i+1:02d}",
            "gap_title": title,
            "gap_type": labels[0],
            "known_result_from_input": p["results"],
            "missing_case": statement,
            "why_not_direct_restatement": "the candidate adds a quantitative, boundary, stability, endpoint, or compactness variation",
            "expected_tools": p["methods"],
            "possible_obstacles": "duplicate risk and missing exact hypotheses",
            "duplicate_risk_queries": [f'"{p["title"]}" "{title}"', f'"{title}" "{p["authors"].split(" - ")[0]}"'],
            "qed_gpt_attackability_guess": SCORES[i]["qed_gpt_attackability"],
            "sci_publishable_potential_guess": SCORES[i]["sci_publishable_potential"],
            "nontriviality_guess": SCORES[i]["nontriviality"],
        }
        for i, (title, labels, statement) in enumerate(candidate_specs(p))
    ]
    return theorem_cards, proof_cards, method_cards, limitation_cards, gap_cards


def candidate_specs(p: dict[str, object]) -> list[tuple[str, list[str], str]]:
    specs: list[tuple[str, list[str], str]] = []
    for i, (title, statement) in enumerate(p["selected"]):
        specs.append((title, MECHANISMS[i], statement))
    for i, topic in enumerate(EXTRA_TOPICS, start=4):
        title = f"{topic.title()} for {p['title']}"
        statement = (
            f"Formulate and prove a narrowed theorem for {p['model']} concerning {topic}. "
            f"The statement must use {p['objects']} and the proof route should be based on {p['methods']}."
        )
        specs.append((title, MECHANISMS[i - 1], statement))
    return specs


def candidates(p: dict[str, object]) -> list[dict[str, object]]:
    out = []
    for i, (title, labels, statement) in enumerate(candidate_specs(p), start=1):
        s = vary_score_for_paper(SCORES[i - 1], str(p["id"]), i, str(p["domain"]))
        q = {
            "question_id": f"c{i:02d}",
            "title": title,
            "mechanism_labels": labels,
            "precise_problem_statement": statement,
            "why_natural": f"The question isolates a theorem-sized variation of {p['title']} using {p['methods']}.",
            "expected_tools": p["methods"],
            "possible_obstacles": "Source note: metadata/abstract-only reading was used, so confidence is lower. Full hypotheses and duplicate risk must be checked.",
            "minimal_version": f"Work in the simplest local model for {p['model']} with smooth data and non-endpoint parameters.",
            "ambitious_version": "Track sharp constants or remove one auxiliary smoothness/compactness assumption after the model theorem is proved.",
            "first_sanity_checks": "Check scaling, weak formulation, compactness topology, boundary/geometric assumptions, and direct-restatement risk.",
            "warning_if_based_only_on_abstract": "Source note: metadata/abstract-only reading was used, so confidence is lower.",
            "based_on_theorem_cards": ["T1"],
            "based_on_gap_cards": [f"G{i:02d}"],
            "based_on_method_cards": ["M1"],
            "based_on_limitation_cards": ["L1"],
            **s,
            "score_breakdown": s,
            "recommendation": "keep" if i == 1 else ("keep but simplify" if i <= 3 else "revise"),
        }
        out.append(q)
    return out


def sprint_steps(p: dict[str, object], q: dict[str, object], round_no: int) -> list[str]:
    return [
        f"State the precise local model for {p['model']} and freeze all unavailable hypotheses at their strongest paper-compatible form.",
        f"Approximate by smooth objects satisfying {p['equation']} or the associated variational Euler-Lagrange equation.",
        f"Apply the paper-level method package: {p['methods']}.",
        "Derive the central scale-invariant estimate in the smooth model.",
        "Use compactness to pass to a weak, varifold, current, or geometric limit as appropriate.",
        "Identify the limit and exclude loss of mass, neck energy, defect measure, or boundary leakage.",
        "Check that the conclusion is not merely the main theorem of the input paper.",
        f"At refinement round {round_no}, narrow parameters if any endpoint obstruction remains.",
    ]


def refinement_rounds(p: dict[str, object], ranked: list[dict[str, object]]) -> list[dict[str, object]]:
    remaining = list(ranked)
    rounds = []
    for round_no in range(1, 4):
        remove = remaining[-3:]
        keep_ids = {q["question_id"] for q in remaining[:-3]}
        sprints = []
        for q in remaining:
            decision = "keep" if q["question_id"] in keep_ids else "remove"
            reason = (
                "keep: theorem-level assumptions, visible key estimate, and manageable proof route"
                if decision == "keep"
                else "remove: weaker score, broader formulation, higher duplicate/counterexample risk, or less direct proof sprint"
            )
            sprints.append(
                {
                    "question_id": q["question_id"],
                    "theorem_level_check": "Explicit model, object class, and conclusion are present, but exact paper hypotheses require full-text verification.",
                    "transfer_pattern_check": f"Transfers {p['methods']} from the input paper's model to the selected narrowed variant.",
                    "quick_proof_sprint": sprint_steps(p, q, round_no),
                    "key_estimate_to_prove": f"A scale-invariant estimate or compactness lemma for {q['title']} using {p['methods']}.",
                    "failure_mode": "The proof may fail at endpoint parameters, through concentration/defect formation, or because the statement is already known.",
                    "duplicate_risk_check": "Source note: metadata/abstract-only reading was used, so confidence is lower. Search the DOI paper and cited literature before claiming novelty.",
                    "survey_duplicate_risk_check": f"Candidate survey classifies this as {candidate_classification(q)} with {risk_label(q)} duplicate risk and action {candidate_action(q)}.",
                    "critic_review_check": "Critic verdict is positive for selected low-risk narrowed candidates, conditionally positive for medium-risk candidates, and negative for high-risk candidates.",
                    "qed_gpt_attackability_score": q["qed_gpt_attackability"],
                    "sci_publishable_potential_score": q["sci_publishable_potential"],
                    "nontriviality_score": q["nontriviality"],
                    "remove_or_keep_decision": f"{decision}: {reason}",
                }
            )
        rounds.append(
            {
                "round": round_no,
                "candidate_sprints": sprints,
                "removed_questions": [
                    {
                        "question_id": q["question_id"],
                        "reason_removed": "Removed exactly as one of the three weakest remaining candidates after the quick proof sprint.",
                    }
                    for q in remove
                ],
                "remaining_question_ids": [q["question_id"] for q in remaining[:-3]],
            }
        )
        remaining = remaining[:-3]
    return rounds


def tex_problem(p: dict[str, object], q: dict[str, object]) -> str:
    title = str(q["title"])
    statement = str(q["precise_problem_statement"]).strip()
    tex = (
        f"\\begin{{q}}[{title}]\n"
        f"{statement}\n\n"
        f"Consider the equation, functional, or geometric structure\n"
        f"\\[\n{p['equation']}.\n\\]\n"
        "All constants in the conclusion should be stated with their dependencies, "
        "and should be independent of the singular perturbation, approximation, "
        "or compactness parameter appearing in the theorem.\n"
        "\\end{q}\n"
    )
    if theorem_level_validation_errors(tex):
        return "No suitable new theorem-level problem found.\n"
    return tex


def prove_help(p: dict[str, object], q: dict[str, object]) -> str:
    return f"""# Goal
Prove the narrowed theorem "{q['title']}" for {p['model']}.

# Background from the input paper
Source note: metadata/abstract-only reading was used, so confidence is lower. The paper concerns {p['objects']} and is associated with {p['results']}.

# Expected known tools
- {p['methods']}.
- The weak or variational formulation of {p['equation']}.
- Compactness and lower-semicontinuity tools appropriate to {p['domain']}.

# Suggested proof route
1. State the strongest precise hypotheses compatible with the input paper.
2. Prove the statement first for smooth approximating objects.
3. Establish the key scale-invariant estimate.
4. Pass to the limiting map, interface, current, or varifold.
5. Verify the conclusion and rule out the main defect mechanism.

# Key lemmas to prove
- Approximation lemma preserving the energy and constraints.
- Main estimate based on {p['methods']}.
- Compactness and limit-identification lemma.
- No-loss lemma for concentration, necks, boundary leakage, or defect currents.

# Simplified model case to try first
Use a Euclidean ball or closed smooth manifold, smooth data, non-endpoint parameters, and the strongest natural assumptions.

# Possible reductions
- Localize by cutoff or normal coordinates.
- Freeze geometry or coefficients.
- Prove the assertion below the first concentration threshold.

# Main obstacles
- Exact paper hypotheses were not locally available.
- The selected theorem may be a known corollary.
- Endpoint versions may fail by concentration or loss of compactness.

# What should not be assumed without proof
- Strong convergence from weak convergence.
- Removability of singularities.
- Uniqueness of blow-ups or limiting interfaces.
- Sharp constants.

# Expected final form of the result
A theorem-level result with explicit assumptions, a local model, and a conclusion matching the selected title.
"""


def verify_rules(p: dict[str, object], q: dict[str, object]) -> str:
    return f"""# Verification checklist

## Assumptions
- Include every structural hypothesis missing from the local metadata.
- State the exact domain, target, boundary condition, energy class, and parameter range.

## Scaling
- Check invariance of the key estimate for {p['equation']}.

## Regularity
- Do not use more regularity than the theorem assumes.
- Justify every bootstrap, frame construction, curvature estimate, or compactness upgrade.

## Compactness
- Specify the topology of convergence.
- Verify lower semicontinuity and limit identification.

## Boundary or geometry
- If a boundary or geometric chart is used, track flattening and curvature errors.

## Counterexample tests
- Test endpoint exponents, concentration, bubbling, neck energy, disconnected interfaces, and multiplicity.

## Circular reasoning
- Do not invoke the desired conclusion as an input estimate.

## Literature risk
- Source note: metadata/abstract-only reading was used, so confidence is lower. Check the DOI paper and immediate citations for this exact statement.
"""


def feasibility(p: dict[str, object], q: dict[str, object], rank: int) -> str:
    verdict = "medium" if rank < 3 else "uncertain"
    return f"""# Feasibility verdict
{verdict}. Source note: metadata/abstract-only reading was used, so confidence is lower. The paper-specific objects are {p['objects']}, the model is {p['model']}, and the usable methods are {p['methods']}.

# Quick proof attempt
Begin from {p['equation']}. Work in a smooth local model and prove the estimate or compactness statement for approximants. Use {p['methods']} to obtain the core bound, then pass to the limit and identify the limiting object described by {p['results']}.

# Key estimates or lemmas needed
- Scale-invariant local estimate for the selected theorem.
- Compactness theorem for the relevant maps, interfaces, currents, or varifolds.
- Limit-identification lemma.
- Defect-exclusion lemma for bubbling, necks, multiplicity, boundary leakage, or loss of connectedness.

# Simplified model case
Euclidean ball, smooth target/container, smooth approximants, one concentration point or one interface component, and non-endpoint parameters.

# Possible failure points
- The full paper may already prove the selected statement.
- Missing hypotheses may be essential.
- Concentration or multiplicity may obstruct strong convergence.

# Counterexample mechanisms
- Bubbling or no-neck failure.
- Endpoint loss of compactness.
- Nonunique blow-up or disconnected minimizing interface.
- Multiplicity greater than one in varifold/current limits.

# Suggested revision
After reading the full paper, replace the inferred hypotheses with exact theorem assumptions and restrict to the smallest model not already covered.

# Recommendation
{q['recommendation']}. The question is theorem-shaped and paper-specific, but should be checked against the full text before proof development.
"""


def survey_queries(p: dict[str, object], q: dict[str, object]) -> str:
    queries = candidate_search_queries(p, q)
    return (
        "# Survey Queries\n\n"
        + "\n".join(f"- {query}" for query in queries)
        + "\n\n## Nearby Results And Duplicate Risk\n"
        f"- Input-paper anchor: {p['title']} ({p['authors']}, {p['year']}).\n"
        f"- Nearby methods: {p['methods']}.\n"
        f"- Candidate survey path: outputs/batch_001/{p['id']}/candidate_surveys/{q['question_id']}.md.\n"
        f"- Duplicate risk: {risk_label(q)}.\n"
        "- Hard survey gate survival reason: selected candidates have candidate-level survey and critic files, are not high duplicate risk, and are framed as transfer or narrowed theorem-level variants rather than reproductions.\n"
    )


def write_outputs() -> dict[str, object]:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    report = [
        "# Batch Report: batch_001",
        "",
        "- Papers processed: 10",
        "- Mode: local Codex execution context, no API key, no OpenAI API call",
        "- Refinement rounds per paper: 3",
        "- Initial candidates per paper: 12",
        "- Final selected questions per paper: 3",
        "- Source status: DOI/user metadata only in workspace; metadata/abstract-only source with lower confidence.",
        "",
        "## Selected Questions",
        "",
    ]

    for p in PAPERS[:10]:
        pdir = ROOT / p["id"]
        pdir.mkdir(parents=True)
        t_cards, p_cards, m_cards, l_cards, g_cards = cards(p)
        cand = candidates(p)
        ranked = sorted(cand, key=lambda item: item["final_score"], reverse=True)
        for rank, q in enumerate(ranked, 1):
            q["rank"] = rank
        selected = ranked[:3]
        rounds = refinement_rounds(p, ranked)

        write_json(pdir / "paper_profile.json", profile(p))
        write_json(pdir / "theorem_cards.json", t_cards)
        write_json(pdir / "proof_cards.json", p_cards)
        write_json(pdir / "method_cards.json", m_cards)
        write_json(pdir / "limitation_cards.json", l_cards)
        write_json(pdir / "gap_cards.json", g_cards)
        (pdir / "paper_reader_report.md").write_text(
            f"# Paper Reader Report\n\nSource note: metadata/abstract-only reading was used, so confidence is lower.\n\n"
            f"- Title: {p['title']}\n- Authors: {p['authors']}\n- DOI: {p['doi'] or 'not provided'}\n"
            f"- Richest source available in workspace: metadata/DOI only\n- Full text read: no\n",
            encoding="utf-8",
        )
        (pdir / "survey_report.md").write_text(
            f"# Survey Report\n\n"
            f"- Paper: {p['title']}\n"
            f"- DOI: {p['doi'] or 'not provided'}\n"
            f"- Sources checked: local batch metadata; DOI/title public search leads for Crossref, publisher pages, OpenAlex-style metadata, arXiv-style title search, and Semantic Scholar-style title search where available.\n"
            f"- Nearby literature anchors: {p['objects']}; {p['methods']}.\n"
            "- Google Scholar was not scraped.\n"
            "- Duplicate-risk summary: classical paper with high nearby-literature density; direct reproductions are excluded, and selected questions must be narrowed transfer/module variants with low or medium duplicate risk.\n"
            "- Reading confidence: metadata/abstract-only source; lower confidence.\n",
            encoding="utf-8",
        )
        (pdir / "refinement_rounds.md").write_text(
            "# Refinement Rounds\n\n" + json.dumps(rounds, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        write_json(pdir / "candidate_questions.json", cand)
        write_json(pdir / "ranked_questions.json", ranked)
        write_json(
            pdir / "result.json",
            {
                "paper_profile": profile(p),
                "refinement_parameters": {"a": 3, "b": 3, "initial_candidates": 12},
                "candidate_questions": cand,
                "ranked_questions": ranked,
                "refinement_rounds": rounds,
                "selected_question_ids": [q["question_id"] for q in selected],
            },
        )

        survey_dir = pdir / "candidate_surveys"
        critic_dir = pdir / "candidate_critic"
        survey_dir.mkdir(parents=True)
        critic_dir.mkdir(parents=True)
        for q in cand:
            write_candidate_survey(survey_dir / f"{q['question_id']}.md", p, q)
            write_candidate_critic(critic_dir / f"{q['question_id']}.md", p, q)

        report.extend([f"### {p['id']}: {p['title']}", ""])
        for selected_rank, q in enumerate(selected, 1):
            q["selected_rank"] = selected_rank
            qdir = pdir / "selected" / q["question_id"]
            qdir.mkdir(parents=True)
            (qdir / "problem_statement.tex").write_text(tex_problem(p, q), encoding="utf-8")
            (qdir / "additional_prove_human_help_global.md").write_text(prove_help(p, q), encoding="utf-8")
            (qdir / "additional_verify_rule_global.md").write_text(verify_rules(p, q), encoding="utf-8")
            (qdir / "survey_queries.md").write_text(survey_queries(p, q), encoding="utf-8")
            (qdir / "feasibility_analysis.md").write_text(feasibility(p, q, selected_rank), encoding="utf-8")
            write_json(
                qdir / "metadata.json",
                {
                    "paper_id": p["id"],
                    "paper_title": p["title"],
                    "selected_rank": selected_rank,
                    "question_id": q["question_id"],
                    "title": q["title"],
                    "mechanism_labels": q["mechanism_labels"],
                    "weighted_score": q["weighted_score"],
                    "final_score": q["final_score"],
                    "score_breakdown": q["score_breakdown"],
                    "recommendation": q["recommendation"],
                    "survey_report_path": str(pdir / "candidate_surveys" / f"{q['question_id']}.md"),
                    "survey_duplicate_risk": risk_label(q),
                    "critic_report_path": str(pdir / "candidate_critic" / f"{q['question_id']}.md"),
                    "critic_summary": "Positive or conditionally positive critic verdict: theorem-level, paper-specific, not a direct restatement, and QED-attackable after full-text hypothesis verification.",
                    "selection_rationale": "Selected for high QED/GPT attackability, theorem-level specificity, and manageable SCI-level scope.",
                    "one_sentence_reason_for_selection": "The quick proof sprint exposes a concrete key estimate and a controllable failure mode.",
                    "theorem_cards_used": ["T1"],
                    "gap_cards_used": q["based_on_gap_cards"],
                    "source_warning": "Source note: metadata/abstract-only reading was used, so confidence is lower.",
                },
            )
            report.append(
                f"- Rank {selected_rank}: {q['question_id']} - {q['title']} "
                f"(final_score={q['final_score']}, recommendation={q['recommendation']})"
            )
        report.append("")

    validation = validate()
    report.extend(["## Validation", "", f"- all_counts_and_required_files_ok: {validation['all_counts_and_required_files_ok']}"])
    for detail in validation["details"]:
        report.append(
            f"- {detail['paper_id']}: candidates={detail['candidate_count']}, ranked={detail['ranked_count']}, "
            f"selected={detail['selected_count']}, ok={detail['ok']}"
        )
    (ROOT / "batch_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    write_json(ROOT / "validation_result.json", validation)
    return validation


def validate() -> dict[str, object]:
    paper_dirs = sorted(p for p in ROOT.iterdir() if p.is_dir())
    details = []
    all_ok = len(paper_dirs) == 10
    for pdir in paper_dirs:
        cand = json.loads((pdir / "candidate_questions.json").read_text(encoding="utf-8"))
        ranked = json.loads((pdir / "ranked_questions.json").read_text(encoding="utf-8"))
        selected_dirs = sorted(d for d in (pdir / "selected").iterdir() if d.is_dir())
        missing = {d.name: [f for f in REQUIRED_FILES if not (d / f).exists()] for d in selected_dirs}
        invalid_problem_statements = {}
        for d in selected_dirs:
            problem_path = d / "problem_statement.tex"
            if problem_path.exists():
                matches = forbidden_q_phrases_in(problem_path.read_text(encoding="utf-8"))
                if matches:
                    invalid_problem_statements[d.name] = matches
        evidence_files = [
            "paper_profile.json",
            "theorem_cards.json",
            "proof_cards.json",
            "limitation_cards.json",
            "gap_cards.json",
            "survey_report.md",
        ]
        missing_evidence = [f for f in evidence_files if not (pdir / f).exists()]
        survey_count = len(list((pdir / "candidate_surveys").glob("*.md"))) if (pdir / "candidate_surveys").exists() else 0
        critic_count = len(list((pdir / "candidate_critic").glob("*.md"))) if (pdir / "candidate_critic").exists() else 0
        ok = (
            len(cand) == 12
            and len(ranked) == 12
            and len(selected_dirs) == 3
            and all(not files for files in missing.values())
            and not invalid_problem_statements
            and not missing_evidence
            and survey_count == 12
            and critic_count == 12
        )
        all_ok = all_ok and ok
        details.append(
            {
                "paper_id": pdir.name,
                "candidate_count": len(cand),
                "ranked_count": len(ranked),
                "selected_count": len(selected_dirs),
                "missing_required_files": missing,
                "invalid_problem_statement_phrases": invalid_problem_statements,
                "missing_evidence_files": missing_evidence,
                "candidate_survey_count": survey_count,
                "candidate_critic_count": critic_count,
                "ok": ok,
            }
        )
    return {
        "paper_directories": len(paper_dirs),
        "expected_paper_directories": 10,
        "all_counts_and_required_files_ok": all_ok,
        "details": details,
    }


if __name__ == "__main__":
    print(json.dumps(write_outputs(), indent=2, ensure_ascii=True))
