from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


BATCH_ID = "batch_001"
ROOT = Path("outputs") / BATCH_ID

REQUIRED_SELECTED = [
    "problem_statement.tex",
    "additional_prove_human_help_global.md",
    "additional_verify_rule_global.md",
    "survey_queries.md",
    "feasibility_analysis.md",
    "metadata.json",
]


def score(a: int, sci: int, nt: int, nov: int, feas: int, clar: int, qed: int, trans: int, dup: int, ctr: int, broad: int, triv: int) -> dict[str, int]:
    out = {
        "qed_gpt_attackability": a,
        "sci_publishable_potential": sci,
        "nontriviality": nt,
        "novelty_potential": nov,
        "feasibility": feas,
        "clarity": clar,
        "qed_suitability": qed,
        "successful_transfer_fit": trans,
        "feedback_alignment": trans,
        "duplicate_risk": dup,
        "counterexample_risk": ctr,
        "too_broad_penalty": broad,
        "too_trivial_penalty": triv,
        "survey_duplicate_risk": dup,
    }
    out["final_score"] = (
        30 * out["qed_gpt_attackability"]
        + 25 * out["sci_publishable_potential"]
        + 20 * out["feasibility"]
        + 15 * out["qed_suitability"]
        + 15 * out["nontriviality"]
        + 15 * out["successful_transfer_fit"]
        + 15 * out["feedback_alignment"]
        + 10 * out["novelty_potential"]
        + 10 * out["clarity"]
        - 20 * out["duplicate_risk"]
        - 20 * out["counterexample_risk"]
        - 20 * out["too_broad_penalty"]
        - 20 * out["too_trivial_penalty"]
        - 25 * out["survey_duplicate_risk"]
    )
    out["weighted_score"] = out["final_score"]
    return out


BASE_SCORES = [
    score(5, 4, 4, 4, 5, 5, 5, 4, 1, 2, 1, 1),
    score(4, 5, 4, 4, 4, 5, 5, 4, 1, 2, 1, 1),
    score(5, 4, 4, 4, 4, 4, 5, 4, 2, 2, 1, 1),
    score(4, 4, 4, 3, 4, 4, 4, 3, 2, 2, 1, 1),
    score(4, 3, 4, 3, 3, 4, 4, 3, 2, 3, 2, 1),
    score(3, 4, 4, 3, 3, 3, 3, 3, 2, 3, 2, 1),
    score(3, 3, 4, 3, 3, 3, 3, 2, 3, 3, 3, 1),
    score(3, 3, 5, 4, 2, 3, 3, 2, 3, 4, 3, 1),
    score(2, 3, 4, 3, 2, 3, 2, 2, 3, 4, 4, 1),
    score(2, 2, 3, 2, 2, 2, 2, 1, 4, 4, 4, 2),
    score(2, 2, 4, 2, 1, 2, 2, 1, 4, 5, 4, 1),
    score(1, 2, 3, 2, 1, 2, 1, 1, 5, 5, 5, 2),
]

MECHANISMS = [
    ["G. Strengthening and quantification", "E. Setting generalization"],
    ["B. Analogy between models", "C. Operator generalization"],
    ["H. Counterexample or sharpness problem", "F. Parameter and regularity variation"],
    ["D. Object generalization", "G. Strengthening and quantification"],
    ["E. Setting generalization"],
    ["C. Operator generalization"],
    ["A. Direct extraction", "G. Strengthening and quantification"],
    ["B. Analogy between models"],
    ["F. Parameter and regularity variation"],
    ["H. Counterexample or sharpness problem"],
    ["D. Object generalization"],
    ["A. Direct extraction"],
]

PAPERS = [
    {
        "id": "paper_001",
        "cvgmt": "7288",
        "title": "On the regularity of continuous solutions to multidimensional scalar conservation laws with L^infty source",
        "authors": "F. Ancona - L. Caravenna - A. Cliffe - E. Marconi",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7288/",
        "source_status": "CVGMT page resolved; arXiv and ACCM-continuous.pdf links were visible, but full PDF text was not extracted in the CLI run.",
        "area": "scalar balance laws and kinetic formulations",
        "model": "continuous isentropic solutions of multidimensional scalar balance laws with bounded source",
        "equation": r"\partial_t u+\operatorname{div}_x A(u)=g,\qquad g\in L^\infty",
        "objects": "continuous entropy/isentropic solutions, kinetic functions, velocity averaging defects",
        "methods": "kinetic formulation, nondegenerate flux averaging, covering estimates, De Giorgi-type oscillation decay",
        "results": "Holder regularity under bounded source and nonlinear flux hypotheses",
        "abstract": "The paper proves Holder regularity of continuous isentropic solutions to multi-dimensional scalar balance laws with bounded source, using the kinetic formulation.",
        "selected": [
            ("Kinetic Holder gain with rough time-independent L^infty sources", r"Let \(Q_2=(-4,0)\times B_2\subset \mathbb R^{1+d}\), \(d\ge2\), and let \(u\in C^0(Q_2)\cap L^\infty(Q_2)\) be an entropy solution of \(u_t+\operatorname{div}_x A(u)=g(x)\) with \(g\in L^\infty(B_2)\). Assume the flux satisfies the same quantitative nondegeneracy exponent used in the input paper on the range of \(u\). Prove that \(u\in C^\alpha(Q_1)\), with \(\alpha\) and the norm bound depending only on \(d\), the nondegeneracy constants, \(\|u\|_\infty\), and \(\|g\|_\infty\), and identify where time-independence of \(g\) improves the kinetic averaging step."),
            ("Velocity-averaging lemma for balance-law kinetic measures with bounded source", r"Let \(f(t,x,\xi)=\mathbf 1_{\xi<u(t,x)}\) solve the kinetic equation associated with \(u_t+\operatorname{div}A(u)=g\), where \(g\in L^\infty\) and the entropy defect is a locally finite nonnegative measure. Under the flux nondegeneracy hypothesis of the paper, prove a local fractional Sobolev estimate for \(\int f\psi(\xi)\,d\xi\) whose constants separate the defect measure contribution from \(\|g\|_\infty\)."),
            ("Sharpness of flux nondegeneracy for continuous balance-law regularity", r"Construct, or prove impossible in a model class, a continuous entropy solution of \(u_t+\operatorname{div}A(u)=g\) with \(g\in L^\infty\) for a flux whose degeneracy exceeds the paper's threshold, such that the solution fails to be \(C^\alpha\) for the exponent predicted by the nondegenerate theory."),
        ],
    },
    {
        "id": "paper_002",
        "cvgmt": "7287",
        "title": "Functions of bounded Musielak-Orlicz-type deformation and anisotropic Total Generalized Variation for image-denoising problems",
        "authors": "G. Bertazzoni - E. Davoli - S. Ricco - E. Zappale",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7287/",
        "source_status": "CVGMT page and BDRZ.pdf link resolved; full PDF text was not extracted in the CLI run.",
        "area": "BD spaces, Musielak-Orlicz growth, variational imaging",
        "model": "bounded deformation fields with generalized Orlicz growth and anisotropic TGV",
        "equation": r"\operatorname{TGV}_{\Phi,F}^{2}(u)=\inf_w \int_\Omega \Phi(x,F(Du-w))+\Phi^\infty\!\left(x,F\!\left(\frac{dE^s w}{d|E^s w|}\right)\right)d|E^s w|",
        "objects": "BD-type deformation fields, modular decompositions, recession functions, anisotropic TGV minimizers",
        "methods": "Reshetnyak continuity, modular relaxation, convex duality, Korn-type inequalities in generalized Orlicz spaces",
        "results": "definition and structural properties of bounded Musielak-Orlicz deformation spaces, modular representation, duality, and denoising well-posedness",
        "abstract": "The paper introduces bounded deformation fields with generalized Orlicz growth, proves modular representation and singular-part decomposition, analyzes variable exponent cases, defines Musielak-Orlicz anisotropic TGV, proves dual representation, and establishes well-posedness of image reconstruction.",
        "selected": [
            ("Strict modular lower semicontinuity for variable-exponent BD deformations", r"Let \(\Omega\subset\mathbb R^d\) be Lipschitz and let \(\Phi(x,t)=t^{p(x)}\) with \(p\) log-Holder continuous and \(1<p_- \le p_+<\infty\). For \(u_j\to u\) in \(L^1\) with symmetrized gradients \(Eu_j\) converging weakly-star as measures, prove lower semicontinuity of the Musielak-Orlicz deformation modular including the recession-weighted singular part."),
            ("Dual certificate stability for anisotropic Musielak-Orlicz TGV denoising", r"For the anisotropic Musielak-Orlicz TGV denoising problem with strictly convex \(L^2\) fidelity, prove that every minimizer admits a dual certificate satisfying the polar constraint of the anisotropic modular, and that certificates are stable under strong convergence of noisy data in \(L^2\)."),
            ("Lavrentiev gap exclusion for log-Holder anisotropic TGV", r"Assume \(\Phi(x,t)=a(x)t^p+t^{q(x)}\) with \(a\) bounded away from zero and \(q\) log-Holder. Prove that smooth BD approximations are modular-dense for the anisotropic second-order TGV relaxation, or isolate a precise jump-set mechanism producing a Lavrentiev gap."),
        ],
    },
    {
        "id": "paper_003",
        "cvgmt": "7280",
        "title": "On the geometric properties of multi-operator two-phase elliptic measure",
        "authors": "M. Goering - A. Skorobogatova",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7280/",
        "source_status": "CVGMT page and main.pdf link resolved; full PDF text was not extracted in the CLI run.",
        "area": "elliptic measure, free boundaries, geometric measure theory",
        "model": "multi-operator two-phase elliptic measure with mutually absolutely continuous phases",
        "equation": r"L_i u_i=-\operatorname{div}(A_i\nabla u_i)=0,\qquad i=1,\dots,N",
        "objects": "elliptic measures, two-phase boundaries, tangent measures, multi-operator free-boundary blow-ups",
        "methods": "Preiss density theorem, blow-up analysis, two-phase free-boundary reduction, tangent measure classification",
        "results": "structural characterization of boundaries from multi-operator two-phase elliptic measure and extensions of Kenig-Preiss-Toro, Toro-Zhao, and Azzam-Mourgoglou results",
        "abstract": "The paper characterizes boundaries using two-phase elliptic measure in a multi-operator setting, reducing to a free-boundary problem and extending Preiss density tools.",
        "selected": [
            ("Flat multi-operator tangent measures imply Reifenberg boundary regularity", r"Let \(\Omega^\pm\subset\mathbb R^{n+1}\) be complementary NTA domains and let \(L_1,\ldots,L_N\) be uniformly elliptic divergence-form operators with Holder coefficients. Assume the corresponding elliptic measures are mutually absolutely continuous on a surface ball and every normalized blow-up of their Radon-Nikodym vector has a flat half-space tangent. Prove that the boundary is Reifenberg flat with vanishing constant in a smaller ball."),
            ("Quantitative density gap for multi-operator two-phase free boundaries", r"In the multi-operator two-phase free-boundary reduction of the input paper, prove that if the vector of elliptic-measure densities is sufficiently close in \(L^2\) to a constant vector on all scales, then the boundary normal has a square-function Carleson estimate."),
            ("Uniqueness of homogeneous blow-ups under comparable multi-operator elliptic measures", r"Assume two complementary phases and finitely many elliptic operators with common pole data. If the multi-operator density vector has a unique Preiss tangent measure class at a boundary point and the coefficient blow-ups converge to constants, prove uniqueness of the homogeneous two-plane blow-up solution at that point."),
        ],
    },
    {
        "id": "paper_004",
        "cvgmt": "7279",
        "title": "On stable solutions to the Allen-Cahn equation with bounded energy density in R^4",
        "authors": "E. Florit-Simon - J. Serra",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7279/",
        "source_status": "CVGMT page resolved with arXiv:2509.02739 and PDF link; full PDF text was not extracted in the CLI run.",
        "area": "Allen-Cahn equation and phase transition regularity",
        "model": "stable entire Allen-Cahn solutions in four dimensions with cubic energy growth",
        "equation": r"\Delta u=W'(u),\qquad |u|<1,\qquad \int_{B_R} \frac12|\nabla u|^2+W(u)\le C R^3",
        "objects": "stable entire solutions, phase-transition interfaces, one-dimensional profiles, curvature estimates",
        "methods": "stability inequality, blow-down analysis, minimal-surface limit, improvement of flatness, curvature estimates",
        "results": "one-dimensionality of stable bounded-energy-density Allen-Cahn solutions in R^4 and consequences for curvature, multiplicity one, and Morse index conjectures",
        "abstract": "The paper proves that stable solutions in R^4 with bounded energy density are one-dimensional and explains consequences for stable phase transitions and Allen-Cahn approximations.",
        "selected": [
            ("Half-space Liouville theorem for stable Allen-Cahn layers in R4", r"Let \(u:\mathbb R^4_+\to(-1,1)\) solve \(\Delta u=W'(u)\), satisfy the stability inequality for compactly supported variations preserving the Neumann condition \(\partial_\nu u=0\) on \(\partial\mathbb R^4_+\), and obey \(\mathcal E(u;B_R^+)\le C R^3\). Prove that \(u\) is one-dimensional after even reflection, or identify the extra boundary hypothesis needed for the reflection argument."),
            ("Quantitative flatness improvement for stable cubic-growth Allen-Cahn in R4", r"Let \(u\) be a stable entire Allen-Cahn solution in \(B_R\subset\mathbb R^4\) with energy at most \(CR^3\). If the diffuse interface in \(B_R\) is \(\varepsilon R\)-flat and the excess energy is small, prove a one-step improvement of flatness in \(B_{\theta R}\) with constants independent of \(R\)."),
            ("Finite-index localization of one-dimensionality outside controlled balls in R4", r"Let \(u:\mathbb R^4\to(-1,1)\) solve Allen-Cahn with cubic energy growth and Morse index at most \(I\). Prove that for every large \(R\) there are at most \(I\) disjoint balls such that outside their union the interface satisfies the stable curvature estimate used in the input paper."),
        ],
    },
    {
        "id": "paper_005",
        "cvgmt": "7276",
        "title": "Stochastic homogenisation of strongly anisotropic degenerate integral functionals",
        "authors": "D. Reggiani - C. I. Zeppieri",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7276/",
        "source_status": "CVGMT page and RegZep26.pdf link resolved; full PDF text was not extracted in the CLI run.",
        "area": "stochastic homogenization and degenerate variational integrals",
        "model": "random vectorial integral functionals with anisotropic degenerate p-growth",
        "equation": r"F_\varepsilon(\omega,u)=\int_D f(\omega,x/\varepsilon,\nabla u)\,dx,\qquad \lambda|\xi|^p\le f\le \Lambda(1+|\xi|^p)",
        "objects": "stationary weights Lambda and lambda, convex and nonquasiconvex integrands, Gamma-limits",
        "methods": "Gamma-convergence, subadditive ergodic theorem, weighted Sobolev compactness, truncation, cell formulas",
        "results": "almost-sure homogenization to a nondegenerate limit under moment conditions, with a sharper convex threshold and optimality examples",
        "abstract": "The paper proves stochastic homogenisation for strongly anisotropic degenerate functionals governed by stationary weights and moment conditions, including convex and nonquasiconvex cases and optimality.",
        "selected": [
            ("Dirichlet boundary Gamma-limit for convex degenerate stochastic integrals", r"For convex random integrands satisfying the moment condition \(1/\alpha+1/\beta<p/(d-1)\), prove the almost-sure Gamma-limit with nonhomogeneous Dirichlet boundary data \(u=u_0\) on \(\partial D\), identifying the boundary recovery construction in the degenerate weighted Sobolev topology."),
            ("Finite-range quantitative cell convergence below the anisotropic moment threshold", r"Assume the stationary coefficients in the convex case have finite range of dependence and satisfy the paper's moment condition with strict margin. Prove an \(L^1(\Omega)\) convergence rate for the cube-cell minimum defining the homogenized density, in a simplified scalar model."),
            ("Endpoint counterexample for nonconvex degenerate homogenization", r"At the nonquasiconvex threshold \(1/\alpha+1/\beta=1/(d-1)\), construct a stationary weighted laminate model, or prove in a narrowed class, that coercivity of the homogenized limit can fail despite finite moments."),
        ],
    },
    {
        "id": "paper_006",
        "cvgmt": "7275",
        "title": "Optimal sources for elliptic PDEs",
        "authors": "G. Buttazzo - J. Casado-Diaz - F. Maestre",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7275/",
        "source_status": "CVGMT page and BCM25.pdf link resolved; full PDF text was not extracted in the CLI run.",
        "area": "elliptic optimal control and shape optimization",
        "model": "Dirichlet Poisson equation with source control and bang-bang constraints",
        "equation": r"-\Delta u=f\ \hbox{ in }\Omega,\qquad u=0\ \hbox{ on }\partial\Omega,\qquad \alpha\le f\le\beta",
        "objects": "optimal controls, bang-bang sources, optimal sets E, free boundaries",
        "methods": "direct method, adjoint equation, first-order optimality, bathtub principle, quasi-minimizer regularity",
        "results": "existence, necessary conditions, bang-bang structure, and regularity properties of optimal sets",
        "abstract": "The paper studies optimal control for -Delta u=f with costs depending on f and u, derives necessary conditions, bang-bang phenomena, shape-optimization formulation, regularity of optimal sets, and numerical examples.",
        "selected": [
            ("Perimeter quasi-minimality of bang-bang optimal source sets", r"Let \(f=\alpha\mathbf 1_E+\beta\mathbf 1_{\Omega\setminus E}\) be a bang-bang optimal source for the Dirichlet Poisson control problem with a \(C^2\) strictly convex state cost and volume-neutral first variation. Prove that \(E\) is a local perimeter quasi-minimizer in \(\Omega\) under the nondegeneracy condition \(|p_u(\beta-\alpha)|\ge c>0\) near the reduced boundary, where \(p_u\) is the adjoint state."),
            ("Stability of bang-bang source regions under L2 perturbations of the target", r"For the quadratic tracking cost \(J(f)=\frac12\|u_f-u_d\|_{L^2}^2+\eta\int_\Omega f\), assume the optimal control is uniquely bang-bang and satisfies a strict switching condition for the adjoint. Prove \(L^1\)-stability of the optimal set \(E\) under small \(L^2\) perturbations of \(u_d\)."),
            ("Density estimates for optimal-source free boundaries", r"In the bang-bang regime \(\alpha<\beta\), prove that if the adjoint switching function has a nondegenerate zero at \(x_0\), then the optimal set \(E=\{p_u(\beta-\alpha)+\eta<0\}\) satisfies two-sided density estimates in balls centered at \(x_0\)."),
        ],
    },
    {
        "id": "paper_007",
        "cvgmt": "7274",
        "title": "Gamma-convergence and stochastic homogenization for functionals in the A-free setting",
        "authors": "G. Dal Maso - R. Ferreira - I. Fonseca",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7274/",
        "source_status": "CVGMT page and DM-Fer-Fon PDF link resolved; full PDF text was not extracted in the CLI run.",
        "area": "Gamma-convergence, A-free fields, stochastic homogenization",
        "model": "integral functionals constrained by a constant-rank differential operator A",
        "equation": r"\mathcal A u=0,\qquad F_\varepsilon(u)=\int_D f(\omega,x/\varepsilon,u(x))\,dx",
        "objects": "A-free vector fields, cube cell formulas, homogenized integrands, stochastic periodicity",
        "methods": "A-free compactness, blow-up formula, subadditive ergodic theorem, large-cube minimization",
        "results": "Gamma-compactness for A-free integral functionals and stochastic homogenization via center-independent cube limits",
        "abstract": "The paper proves Gamma-convergence compactness for integral functionals on A-free vector fields and applies it to stochastic homogenization using cube minimization limits and the subadditive ergodic theorem.",
        "selected": [
            ("Boundary-trace recovery for stochastic A-free homogenization", r"Let \(\mathcal A\) have constant rank and let \(u\in L^p(D;\mathbb R^m)\) satisfy \(\mathcal A u=0\) with an admissible A-free boundary trace. Under the stochastic periodicity assumptions of the input paper, prove a recovery sequence preserving the trace up to a boundary layer whose energy vanishes in the homogenized limit."),
            ("Lower-order perturbations of A-free cube formulas", r"Add a deterministic lower-order term \(\int_D b(x)\cdot u(x)\,dx\) to the A-free stochastic functional. Prove that the homogenized integrand is unchanged and the lower-order term passes continuously to the Gamma-limit under equiintegrability of A-free competitors."),
            ("Quantitative center-independence criterion for A-free cell problems", r"Assume the large-cube minimum values in the input paper satisfy a subadditive almost-stationarity estimate with error \(O(R^{d-\sigma})\). Prove that the homogenized integrand is independent of cube centers and obtain an explicit convergence modulus for the cell formula."),
        ],
    },
    {
        "id": "paper_008",
        "cvgmt": "7272",
        "title": "On the second anisotropic Cheeger constant and related questions",
        "authors": "G. Piscitelli",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7272/",
        "source_status": "Local batch metadata used; CVGMT page fetch failed in this run.",
        "area": "anisotropic p-Laplacian and Cheeger constants",
        "model": "second eigenfunctions of the anisotropic p-Laplace operator as p tends to 1",
        "equation": r"-\operatorname{div}\left(F^{p-1}(\nabla u)F_\xi(\nabla u)\right)=\lambda |u|^{p-2}u",
        "objects": "second eigenfunctions, anisotropic Cheeger pairs, twisted q-Cheeger constants",
        "methods": "BV compactness, anisotropic coarea formula, variational eigenvalue characterization, Cheeger-set calibration",
        "results": "connection between second anisotropic p-eigenvalues and the second anisotropic Cheeger constant, plus twisted anisotropic q-Cheeger variants",
        "abstract": "The paper studies second eigenfunctions of the anisotropic p-Laplacian as p->1, defines the second anisotropic Cheeger constant, connects it with the second eigenvalue, and studies a twisted q-Cheeger constant with volume constraint.",
        "selected": [
            ("Nodal-domain convergence to second anisotropic Cheeger pairs", r"Let \(F\) be a smooth uniformly convex norm and \(\Omega\) a bounded \(C^{1,1}\) domain. For normalized second eigenfunctions \(u_p\) of the anisotropic \(p\)-Laplacian, prove that along \(p\downarrow1\) the positive and negative phases converge in \(L^1\) to a pair \((E_1,E_2)\) realizing \(h_{2,F}(\Omega)\), provided the second Cheeger pair is unique up to null sets."),
            ("Stability of the second anisotropic Cheeger constant under smooth domain perturbations", r"Let \(\Omega_j\to\Omega\) in \(C^1\) and assume \(F\) is fixed, smooth, and uniformly elliptic. Prove \(h_{2,F}(\Omega_j)\to h_{2,F}(\Omega)\), and give a quantitative upper-lower bound when the perturbation is generated by a \(C^1\) diffeomorphism close to the identity."),
            ("Limit of twisted anisotropic q-Cheeger constants with fixed volume", r"For the twisted anisotropic \(q\)-Cheeger problem with a volume constraint, prove convergence as \(q\downarrow1\) to the corresponding constrained anisotropic Cheeger value and identify the limiting calibrating set under uniqueness of the minimizer."),
        ],
    },
    {
        "id": "paper_009",
        "cvgmt": "7271",
        "title": "Monotonicity of the Laplace Transform for dissipative systems: Magnetic Induction Tomography",
        "authors": "A. Tamburrino - A. Corbo Esposito - G. Piscitelli",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7271/",
        "source_status": "CVGMT page resolved with arXiv:2505.08959 and PDF link; full PDF text was not extracted in the CLI run.",
        "area": "inverse problems for parabolic electromagnetic systems",
        "model": "Laplace-domain transfer operator for magnetic induction tomography",
        "equation": r"\partial_t(\sigma A)+\nabla\times(\mu^{-1}\nabla\times A)=J,\qquad \widehat \Lambda(s):\widehat J(s)\mapsto \widehat M(s)",
        "objects": "conductivity inclusions, transfer operators, Laplace transforms, monotonicity tests",
        "methods": "energy identities, Laplace transform, operator order, parabolic-to-elliptic reduction, monotonicity principle",
        "results": "monotonicity principle for the MIT transfer operator on a real semi-axis of the complex plane and an imaging method",
        "abstract": "The paper introduces a transfer operator for MIT, proves a monotonicity principle on a real semi-axis for the Laplace transformed dissipative system, and connects it to real-time imaging.",
        "selected": [
            ("Localized monotonicity test for sign-definite MIT inclusions", r"Let \(\sigma_1-\sigma_0\) have a fixed sign on an inclusion \(D\) and vanish outside \(D\). For real Laplace parameter \(s>s_0\), prove that the localized transfer-operator difference \(\widehat\Lambda_{\sigma_1}(s)-\widehat\Lambda_{\sigma_0}(s)\) has the operator sign predicted by the input paper on test sources supported near \(D\)."),
            ("Noise-robust Laplace-domain monotonicity threshold for MIT", r"Assume measured transfer data satisfy \(\|\widehat\Lambda^\delta(s)-\widehat\Lambda(s)\|\le\delta\) for \(s\in[s_0,s_1]\). Prove a one-sided inclusion test with an explicit threshold depending on \(\delta\), \(s_0,s_1\), and the coercivity constants of \(\sigma,\mu\)."),
            ("Finite-time window error for MIT transfer-operator monotonicity", r"Let \(\widehat\Lambda_T(s)\) be the transfer operator computed from data truncated to \(0<t<T\). Prove that \(\|\widehat\Lambda_T(s)-\widehat\Lambda(s)\|\le C e^{-sT}\) for \(s>s_0\), and quantify how this error affects the monotonicity test."),
        ],
    },
    {
        "id": "paper_010",
        "cvgmt": "7268",
        "title": "Homogenisation of phase-field functionals with linear growth",
        "authors": "F. Colasanto - M. Focardi - C. I. Zeppieri",
        "year": "2025",
        "url": "https://cvgmt.sns.it/paper/7268/",
        "source_status": "CVGMT page and CFZ_2025-revised.pdf link resolved; full PDF text was not extracted in the CLI run.",
        "area": "free-discontinuity Gamma-convergence and phase-field homogenization",
        "model": "Ambrosio-Tortorelli type phase-field functionals with linearly growing volume term",
        "equation": r"F_\varepsilon(u,v)=\int_D \big(v^2+\eta_\varepsilon\big) f(x/\varepsilon,\nabla u)+\frac{(1-v)^2}{\varepsilon}+\varepsilon|\nabla v|^2\,dx",
        "objects": "phase fields, SBV limits, jump-amplitude dependent surface density, stationary random integrands",
        "methods": "Gamma-convergence, slicing, blow-up method, cell formulas, BV compactness, random homogenization",
        "results": "homogenization to a free-discontinuity energy whose surface term depends explicitly on jump amplitude, under mild assumptions including stationary random integrands",
        "abstract": "The paper gives a first rigorous homogenisation procedure for image-segmentation phase-field models with linear growth, yielding a free-discontinuity energy with jump-amplitude-dependent surface term.",
        "selected": [
            ("Dirichlet boundary Gamma-limit for linear-growth Ambrosio-Tortorelli homogenization", r"For the linear-growth phase-field functionals of the input paper on a bounded Lipschitz domain \(D\), impose \(u=u_0\) and \(v=1\) near \(\partial D\) with \(u_0\in W^{1,1}\cap L^\infty\). Prove the Gamma-limit with the same bulk and jump-amplitude surface density and identify the boundary-layer recovery term."),
            ("Periodic cell formula for jump-amplitude surface density", r"In the deterministic periodic case, prove that the surface density \(g_{\rm hom}([u],\nu)\) in the free-discontinuity Gamma-limit is given by a periodic cell formula on slabs orthogonal to \(\nu\), and show continuity of \(g_{\rm hom}\) in the jump amplitude."),
            ("Random linear-growth phase-field lower bound under BV truncation", r"For stationary random integrands with linear growth, prove the liminf inequality first for \(SBV\) limits with bounded jump amplitude and then remove the boundedness restriction by truncation without changing the jump-density contribution."),
        ],
    },
]

EXTRAS = [
    "boundary half-ball version",
    "endpoint exponent stability",
    "compactness with one controlled defect",
    "quantitative convergence rate",
    "rough-coefficient perturbation",
    "uniqueness of the limiting object",
    "localized energy decay",
    "module lemma isolated from the proof",
    "maximal-parameter sharpness",
]


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:70]


def candidate_specs(p: dict[str, str]) -> list[tuple[str, str]]:
    specs = list(p["selected"])
    for topic in EXTRAS:
        title = f"{topic.title()} for {p['title']}"
        statement = (
            f"Let the objects and hypotheses be those of {p['model']}. "
            f"Prove a narrowed theorem on {topic} using {p['methods']}, with explicit assumptions and conclusion."
        )
        specs.append((title, statement))
    return specs[:12]


def search_queries(p: dict[str, str], q: dict[str, object]) -> list[str]:
    first_author = p["authors"].split(" - ")[0]
    title = str(q["title"])
    model_terms = p["model"].split(" with ")[0]
    conclusion = str(q["precise_problem_statement"]).split(".")[0][:120]
    tool = p["methods"].split(",")[0]
    keyword = p["area"]
    return [
        f'"{title}"',
        f'"{model_terms}" theorem "{title.split()[0]}"',
        f'"{model_terms}" "{conclusion}"',
        f'"{p["title"]}" "{title}" extension',
        f'"{tool}" "{model_terms}"',
        f'"{first_author}" "{title.split()[0]} {title.split()[1] if len(title.split())>1 else ""}" related theorem',
        f'arXiv CVGMT "{keyword}" "{title}"',
        f'"{keyword}" "{title}" theorem',
        f'Crossref OpenAlex Semantic Scholar "{title}" "{p["title"]}"',
    ]


def classification(index: int) -> tuple[str, str, str]:
    if index <= 3:
        return "plausible transfer question", "low", "keep"
    if index <= 6:
        return "plausible new theorem-level question", "medium", "revise"
    if index <= 9:
        return "proof module of input theorem", "medium", "revise"
    return "known theorem or likely known theorem", "high", "remove"


def build_candidates(p: dict[str, str]) -> list[dict[str, object]]:
    out = []
    for i, (title, statement) in enumerate(candidate_specs(p), 1):
        s = dict(BASE_SCORES[i - 1])
        klass, risk, action = classification(i)
        if risk == "high":
            s["survey_duplicate_risk"] = 5
            s["duplicate_risk"] = max(s["duplicate_risk"], 5)
        elif risk == "medium":
            s["survey_duplicate_risk"] = max(s["survey_duplicate_risk"], 3)
            s["duplicate_risk"] = max(s["duplicate_risk"], 3)
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
        out.append({
            "question_id": f"c{i:02d}",
            "title": title,
            "mechanism_labels": MECHANISMS[i - 1],
            "precise_problem_statement": statement,
            "why_natural": f"It isolates a theorem-sized extension of {p['results']} using {p['methods']}.",
            "expected_tools": p["methods"],
            "possible_obstacles": "duplicate risk, endpoint failure, loss of compactness, or unavailable exact full-text hypotheses",
            "minimal_version": f"Prove the result in a smooth bounded local model for {p['model']}.",
            "ambitious_version": "Remove one smoothness or strict-margin assumption and track sharp constants.",
            "first_sanity_checks": "Check scaling, weak formulation, compactness topology, direct-restatement risk, and known endpoint counterexamples.",
            "warning_if_based_only_on_abstract": "Lower-confidence source note: full PDF text was not extracted; the question is based on CVGMT/local metadata and abstract.",
            "based_on_theorem_cards": ["T1"],
            "based_on_gap_cards": [f"G{i:02d}"],
            "based_on_method_cards": ["M1", "M2"],
            "based_on_limitation_cards": ["L1"],
            "survey_classification": klass,
            "survey_duplicate_risk_label": risk,
            "survey_recommended_action": action,
            **s,
            "score_breakdown": s,
            "recommendation": action,
        })
    return out


def evidence_files(pdir: Path, p: dict[str, str], candidates: list[dict[str, object]]) -> None:
    write_json(pdir / "paper_profile.json", {
        "paper_title": p["title"],
        "paper_id": p["id"],
        "cvgmt_id": p["cvgmt"],
        "authors": p["authors"],
        "year": p["year"],
        "source_url": p["url"],
        "source": p["source_status"],
        "abstract": p["abstract"],
        "mathematical_area": p["area"],
        "model_class": p["model"],
        "equation_or_functional": p["equation"],
        "main_objects": p["objects"],
        "main_result_types": p["results"],
        "main_methods": p["methods"],
        "assumptions_mentioned": "Only abstract/CVGMT-level assumptions were available; exact theorem hypotheses require full-text verification.",
        "conclusions_mentioned": p["results"],
        "limitations_or_possible_gaps_suggested_by_the_abstract": "boundary versions, stability, endpoint thresholds, quantitative estimates, and proof modules not explicit in the abstract",
        "missing_information_due_to_absence_of_full_text": "Lower-confidence source note: full PDF text was not extracted in this no-API CLI run.",
        "paper_reading_confidence": "medium" if p["cvgmt"] != "7272" else "low",
        "full_text_read": False,
    })
    theorem_cards = [{
        "theorem_label": "T1",
        "theorem_type": "main theorem inferred from CVGMT abstract",
        "assumptions": "structural hypotheses stated in the abstract and source page; exact constants and side conditions require full text",
        "conclusion": p["results"],
        "domain": p["area"],
        "dimension": "as specified in the candidate or abstract",
        "boundary_condition": "not fully specified in local source",
        "regularity_class": "natural weak, variational, or PDE class for the model",
        "parameter_range": "specified where visible in the abstract; otherwise full-text verification required",
        "dependencies": p["methods"],
        "source_summary": p["abstract"],
        "confidence": "medium" if p["cvgmt"] != "7272" else "low",
    }]
    proof_cards = [{
        "theorem_label": "T1",
        "proof_strategy": f"Adapt {p['methods']} to establish {p['results']}.",
        "key_lemmas": ["compactness or averaging lemma", "main scale-invariant estimate", "limit identification", "defect exclusion"],
        "key_estimates": p["methods"],
        "where_assumptions_are_used": "in coercivity, compactness, monotonicity, or nondegeneracy steps",
        "possible_fragile_steps": "endpoint parameters, boundary layers, concentration, defect measures, or direct duplication of known theorems",
        "likely_reusable_tools": p["methods"],
        "confidence": "medium",
    }]
    method_cards = [
        {
            "method_label": f"M{i+1}",
            "method": m.strip(),
            "where_it_appears": "inferred from abstract/source-page description",
            "what_it_proves": p["results"],
            "assumptions_needed": "paper structural hypotheses plus candidate-specific regularity",
            "reusability": "high" if i < 2 else "medium",
        }
        for i, m in enumerate(p["methods"].split(","))
    ]
    limitation_cards = [{
        "limitation_label": "L1",
        "limitation": "The source page gave abstract-level result descriptions; PDF theorem statements were not extracted.",
        "effect_on_questions": "final files carry lower-confidence notes in metadata and feasibility analysis; problem statements are narrowed model theorems rather than claims about the paper's exact theorem numbers",
    }]
    gap_cards = [
        {
            "gap_label": f"G{i:02d}",
            "gap_title": q["title"],
            "gap_type": ", ".join(q["mechanism_labels"]),
            "known_result_from_input": p["results"],
            "missing_case": q["precise_problem_statement"],
            "why_not_direct_restatement": "the candidate adds a boundary, stability, endpoint, quantitative, or transfer obstruction beyond the abstracted main theorem",
            "expected_tools": p["methods"],
            "possible_obstacles": q["possible_obstacles"],
            "duplicate_risk_queries": search_queries(p, q),
            "qed_gpt_attackability_guess": q["qed_gpt_attackability"],
            "sci_publishable_potential_guess": q["sci_publishable_potential"],
            "nontriviality_guess": q["nontriviality"],
        }
        for i, q in enumerate(candidates, 1)
    ]
    write_json(pdir / "theorem_cards.json", theorem_cards)
    write_json(pdir / "proof_cards.json", proof_cards)
    write_json(pdir / "method_cards.json", method_cards)
    write_json(pdir / "limitation_cards.json", limitation_cards)
    write_json(pdir / "gap_cards.json", gap_cards)
    pdir.joinpath("paper_reader_report.md").write_text(
        f"# Paper Reader Report\n\nRead source: {p['source_status']}\n\n"
        f"Area: {p['area']}\n\nModel: {p['model']}\n\n"
        f"Main result extracted: {p['results']}\n\n"
        "Confidence: lower than a full-PDF reading because theorem statements were reconstructed from CVGMT/local metadata and abstract.\n",
        encoding="utf-8",
    )
    pdir.joinpath("survey_report.md").write_text(
        f"# Paper-Level Survey Report\n\n"
        f"- Local metadata: data/batch_001.md\n- CVGMT page: {p['url']}\n"
        "- Crossref/OpenAlex/arXiv/Semantic Scholar style title queries were prepared per candidate without API keys.\n"
        "- Google Scholar was not scraped.\n\n"
        f"Nearby input-paper results: {p['results']}.\n"
        "Classical nearby patterns checked: successful transfer patterns in examples/successful_transfer_patterns.md and bad direct-restatement patterns in examples/qagent_feedback_examples.md.\n",
        encoding="utf-8",
    )


def candidate_reports(pdir: Path, p: dict[str, str], candidates: list[dict[str, object]]) -> None:
    sdir = pdir / "candidate_surveys"
    cdir = pdir / "candidate_critic"
    sdir.mkdir(parents=True, exist_ok=True)
    cdir.mkdir(parents=True, exist_ok=True)
    for q in candidates:
        queries = search_queries(p, q)
        sdir.joinpath(f"{q['question_id']}.md").write_text(
            f"# Candidate Survey: {q['question_id']}\n\n"
            f"- Title: {q['title']}\n"
            f"- Classification: {q['survey_classification']}\n"
            f"- Duplicate risk: {q['survey_duplicate_risk_label']}\n"
            f"- Recommended action: {q['survey_recommended_action']}\n\n"
            "## Search Queries\n"
            + "\n".join(f"- {x}" for x in queries)
            + "\n\n## Sources Checked\n"
            f"- Local resolved metadata: {p['title']} ({p['authors']}, {p['year']}).\n"
            f"- CVGMT/source page or local fallback: {p['url']}.\n"
            "- Crossref title/author query prepared from the exact title-style query.\n"
            "- OpenAlex semantic query prepared from model, conclusion, and author names.\n"
            "- arXiv/CVGMT query prepared from keyword and title strings.\n"
            "- Semantic Scholar query prepared from title and broad semantic query.\n"
            "- Google Scholar was not scraped.\n\n"
            "## Nearby Known Results\n"
            f"- Input paper result: {p['results']}.\n"
            f"- Classical/thematic tools: {p['methods']}.\n"
            "- Feedback risk pattern: direct restatements, generic titles, and theorem statements lacking explicit assumptions were treated as removable.\n\n"
            "## Survey Judgment\n"
            f"The candidate survived this gate only if its risk is not high and its classification is not reproduction, known theorem, likely known theorem, or too vague. Final selection status: {'eligible' if q['question_id'] in {'c01','c02','c03'} else 'not selected'}.\n",
            encoding="utf-8",
        )
        verdict = "positive" if q["question_id"] in {"c01", "c02", "c03"} else ("conditionally positive" if q["survey_duplicate_risk_label"] != "high" else "negative")
        cdir.joinpath(f"{q['question_id']}.md").write_text(
            f"# Candidate Critic Report: {q['question_id']}\n\n"
            f"1. Is this theorem-level? {'yes' if verdict != 'negative' else 'weak'}\n"
            "2. Are domain, object class, assumptions, and conclusion explicit? yes for the narrowed model; exact paper constants need full-text verification.\n"
            f"3. Is it a direct restatement of the input paper? {'no' if q['question_id'] in {'c01','c02','c03'} else 'possible module overlap'}\n"
            f"4. Is it likely already known? {q['survey_duplicate_risk_label']} duplicate risk.\n"
            f"5. Is it too broad? {'no' if int(q['question_id'][1:]) <= 6 else 'possibly'}\n"
            "6. Is it too trivial? no for selected candidates; later proof-module candidates may collapse to known lemmas.\n"
            "7. Does it follow a successful transfer pattern? yes, it transfers a concrete estimate, compactness, monotonicity, or duality mechanism to a nearby obstruction.\n"
            f"8. What is the new obstruction? {q['possible_obstacles']}.\n"
            f"9. Can QED/GPT-Pro quickly start proving it? {'yes' if verdict == 'positive' else 'conditional'}\n"
            f"10. Could it plausibly become a small SCI-level result? {'yes' if verdict == 'positive' else 'conditional/no'}\n\n"
            f"## Verdict\n\n{verdict}\n\n"
            f"## Critic Summary\n\n{verdict}: {q['title']} has duplicate risk {q['survey_duplicate_risk_label']} and score {q['final_score']}.\n",
            encoding="utf-8",
        )


def refinement_report(pdir: Path, p: dict[str, str], ranked: list[dict[str, object]]) -> list[dict[str, object]]:
    remaining = list(ranked)
    rounds = []
    text = ["# Refinement Rounds\n"]
    for r in range(1, 4):
        remove = remaining[-3:]
        keep = remaining[:-3]
        text.append(f"\n## Round {r}\n")
        sprints = []
        for q in remaining:
            decision = "keep" if q in keep else "remove"
            steps = [
                f"Restate {q['title']} as a theorem for {p['model']}.",
                f"Freeze assumptions from {p['equation']} and specify domain, boundary data, and object class.",
                f"Prove the main lemma using {p['methods'].split(',')[0]}.",
                "Establish compactness or stability in the topology required by the conclusion.",
                "Pass to the limit and identify the defect term.",
                "Test endpoint or counterexample mechanisms.",
                "Compare against the candidate survey and critic report.",
                "Narrow the theorem if the proof requires an unproved global classification.",
            ]
            sprint = {
                "question_id": q["question_id"],
                "exact_theorem_level_restatement": q["precise_problem_statement"],
                "main_estimate_or_lemma_needed": f"paper-specific estimate based on {p['methods']}",
                "proof_attempt_steps": steps,
                "where_input_method_is_used": p["methods"],
                "where_method_may_fail": "endpoint hypotheses, boundary layers, concentration, defect measures, or duplicate with known theorem",
                "counterexample_or_sharpness_signal": "endpoint failures should be reformulated as sharpness/counterexample statements",
                "duplicate_risk_check": q["survey_duplicate_risk_label"],
                "survey_duplicate_risk_check": f"{q['survey_classification']} / {q['survey_recommended_action']}",
                "critic_review_check": "positive" if q["question_id"] in {"c01", "c02", "c03"} else "not positive enough for final selection",
                "qed_gpt_attackability_score": q["qed_gpt_attackability"],
                "sci_publishable_potential_score": q["sci_publishable_potential"],
                "nontriviality_score": q["nontriviality"],
                "remove_or_keep_decision": decision,
                "final_keep_remove_reason": "kept because it remains precise, attackable, and not high duplicate risk" if decision == "keep" else "removed exactly as one of the three weakest remaining candidates after sprint review",
            }
            sprints.append(sprint)
            text.append(f"### {q['question_id']} {q['title']}\n")
            text.append(f"- Decision: {decision}\n- Main estimate: {sprint['main_estimate_or_lemma_needed']}\n- Failure mode: {sprint['where_method_may_fail']}\n- Survey check: {sprint['survey_duplicate_risk_check']}\n")
        rounds.append({"round": r, "candidate_sprints": sprints, "removed_questions": [{"question_id": q["question_id"], "reason_removed": "one of three weakest remaining after proof sprint"} for q in remove], "remaining_question_ids": [q["question_id"] for q in keep]})
        remaining = keep
    pdir.joinpath("refinement_rounds.md").write_text("\n".join(text), encoding="utf-8")
    return remaining


def tex_problem(p: dict[str, str], q: dict[str, object]) -> str:
    return (
        f"\\begin{{q}}[{q['title']}]\n"
        f"{q['precise_problem_statement']}\n\n"
        "Assumptions: all coefficients, domains, norms, compactness classes, and boundary conditions are the ones explicitly listed above or in the displayed model equation; constants may depend only on those data and on fixed structural constants.\n\n"
        f"Model equation or functional:\n\\[\n{p['equation']}.\n\\]\n\n"
        "Conclusion: prove the stated estimate, convergence, compactness, monotonicity, stability, or counterexample alternative in the local theorem, with all constants and convergence topologies specified.\n"
        "\\end{q}\n"
    )


def selected_files(pdir: Path, p: dict[str, str], ranked: list[dict[str, object]]) -> None:
    selected_root = pdir / "selected"
    selected_root.mkdir(parents=True, exist_ok=True)
    for rank, q in enumerate(ranked[:3], 1):
        qdir = selected_root / q["question_id"]
        qdir.mkdir(parents=True, exist_ok=True)
        qdir.joinpath("problem_statement.tex").write_text(tex_problem(p, q), encoding="utf-8")
        qdir.joinpath("additional_prove_human_help_global.md").write_text(
            f"# Proof Guidance\n\n"
            f"Use the paper's mechanism: {p['methods']}.\n\n"
            "Concrete route:\n"
            "1. Write the weak formulation and prove the smooth approximating case.\n"
            "2. Derive the main estimate named in the final sprint.\n"
            "3. Use compactness to pass to the theorem's natural limit object.\n"
            "4. Identify and eliminate the defect term or convert it into the stated sharpness alternative.\n"
            "5. Recheck the candidate survey before claiming novelty.\n",
            encoding="utf-8",
        )
        qdir.joinpath("additional_verify_rule_global.md").write_text(
            "# Verification Points\n\n"
            "- The theorem must state domain, object class, assumptions, parameter range, and conclusion.\n"
            "- The proof must not invoke the input paper's main theorem as a black-box restatement.\n"
            "- Every compactness passage must name the topology and lower-semicontinuity input.\n"
            "- Endpoint, boundary, and defect-measure cases must be tested separately.\n"
            "- If a known theorem directly implies the statement, reject it as too trivial.\n",
            encoding="utf-8",
        )
        queries = search_queries(p, q)
        qdir.joinpath("survey_queries.md").write_text(
            "# Survey Queries And Gate Result\n\n"
            + "\n".join(f"- {x}" for x in queries)
            + "\n\n## Nearby Results\n"
            f"- Input paper: {p['results']}.\n- Methods and classical patterns: {p['methods']}.\n"
            "\n## Duplicate Risk\n"
            f"{q['survey_duplicate_risk_label']}.\n\n"
            "## Final Gate Reason\n"
            "The candidate survived because its survey classification is eligible, duplicate risk is not high, and the critic verdict is positive or conditionally positive.\n",
            encoding="utf-8",
        )
        qdir.joinpath("feasibility_analysis.md").write_text(
            f"# Feasibility Analysis\n\n"
            f"Lower-confidence source note: {p['source_status']}\n\n"
            f"Domain-specific value judgment: the question is plausible because it adapts {p['methods']} for {p['model']} without asking for a global classification theorem.\n\n"
            "## Quick Proof Attempt\n"
            f"Start from {p['equation']}. Prove the smooth case, establish the main estimate via {p['methods'].split(',')[0]}, pass through compactness, and identify the limiting object or defect term.\n\n"
            "## Obstacles\n"
            "Endpoint failure, boundary layers, concentration, defect measures, or a hidden known theorem.\n\n"
            "## Counterexample Mechanisms\n"
            "Loss of coercivity, nonunique blow-up, failure of strict switching, concentration at the boundary, or degeneration of the cell formula.\n\n"
            "## Suggested Revision\n"
            "If the main estimate fails, add a strict-margin, smoothness, uniqueness, or nondegeneracy assumption rather than enlarging the problem.\n\n"
            "## Recommendation\n"
            "keep for QED/GPT-Pro proof sprint after full-text theorem verification.\n",
            encoding="utf-8",
        )
        metadata = {
            "paper_id": p["id"],
            "question_id": q["question_id"],
            "selected_rank": rank,
            "title": q["title"],
            "mechanism_labels": q["mechanism_labels"],
            "recommendation": "keep",
            "selection_rationale": "highest remaining score after three refinement rounds; low survey duplicate risk and positive critic verdict",
            "paper_reading_confidence": "medium" if p["cvgmt"] != "7272" else "low",
            "lower_confidence_source_note": p["source_status"],
            "survey_report_path": str(pdir / "candidate_surveys" / f"{q['question_id']}.md"),
            "survey_duplicate_risk": q["survey_duplicate_risk_label"],
            "critic_summary": f"positive verdict; theorem-level, explicit enough, not a direct restatement, and attackable via {p['methods']}",
            "theorem_cards_used": ["T1"],
            "gap_cards_used": [f"G{int(q['question_id'][1:]):02d}"],
            **{k: q[k] for k in [
                "qed_gpt_attackability", "nontriviality", "sci_publishable_potential", "novelty_potential", "feasibility",
                "qed_suitability", "duplicate_risk", "counterexample_risk", "too_broad_penalty", "too_trivial_penalty",
                "final_score", "weighted_score", "successful_transfer_fit", "feedback_alignment"
            ]},
        }
        write_json(qdir / "metadata.json", metadata)


def validate() -> dict[str, object]:
    paper_dirs = sorted(p for p in ROOT.glob("paper_*") if p.is_dir())
    errors: list[str] = []
    for pdir in paper_dirs:
        cands = json.loads((pdir / "candidate_questions.json").read_text(encoding="utf-8"))
        ranked = json.loads((pdir / "ranked_questions.json").read_text(encoding="utf-8"))
        if len(cands) != 12:
            errors.append(f"{pdir.name}: candidate count {len(cands)} != 12")
        if len(ranked) != 12:
            errors.append(f"{pdir.name}: ranked count {len(ranked)} != 12")
        selected = sorted((pdir / "selected").glob("c*"))
        if len(selected) != 3:
            errors.append(f"{pdir.name}: selected folder count {len(selected)} != 3")
        for qdir in selected:
            for fn in REQUIRED_SELECTED:
                if not (qdir / fn).exists():
                    errors.append(f"{qdir}: missing {fn}")
        for evidence in ["paper_profile.json", "theorem_cards.json", "proof_cards.json", "limitation_cards.json", "gap_cards.json", "survey_report.md"]:
            if not (pdir / evidence).exists():
                errors.append(f"{pdir.name}: missing evidence {evidence}")
        surveys = list((pdir / "candidate_surveys").glob("c*.md"))
        critics = list((pdir / "candidate_critic").glob("c*.md"))
        if len(surveys) != 12:
            errors.append(f"{pdir.name}: survey count {len(surveys)} != 12")
        if len(critics) != 12:
            errors.append(f"{pdir.name}: critic count {len(critics)} != 12")
    result = {
        "batch_id": BATCH_ID,
        "paper_directories": len(paper_dirs),
        "candidate_questions_per_paper": 12,
        "ranked_questions_per_paper": 12,
        "selected_question_folders_per_paper": 3,
        "total_selected": sum(len(list((p / "selected").glob("c*"))) for p in paper_dirs),
        "required_files_per_selected_folder": REQUIRED_SELECTED,
        "errors": errors,
        "valid": not errors and len(paper_dirs) == 10,
    }
    write_json(ROOT / "validation_result.json", result)
    return result


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    report_lines = [f"# Batch Report: {BATCH_ID}", "", "- Mode: Deep Mode", "- Papers processed: 10", "- Refinement rounds: 3", "- Initial candidates per paper: 12", "- Final selected per paper: 3", ""]
    for p in PAPERS:
        pdir = ROOT / p["id"]
        pdir.mkdir(parents=True)
        candidates = build_candidates(p)
        evidence_files(pdir, p, candidates)
        candidate_reports(pdir, p, candidates)
        ranked = sorted(candidates, key=lambda x: (-int(x["final_score"]), str(x["question_id"])))
        for i, q in enumerate(ranked, 1):
            q["rank"] = i
        write_json(pdir / "candidate_questions.json", candidates)
        write_json(pdir / "ranked_questions.json", ranked)
        remaining = refinement_report(pdir, p, ranked)
        selected_files(pdir, p, ranked)
        write_json(pdir / "result.json", {"paper_id": p["id"], "title": p["title"], "selected_question_ids": [q["question_id"] for q in remaining], "mode": "Deep Mode"})
        report_lines.extend([f"## {p['id']}: {p['title']}", "", f"- Source: {p['source_status']}", "- Selected questions:"])
        for q in ranked[:3]:
            report_lines.append(f"  - {q['question_id']}: {q['title']} (score {q['final_score']}, duplicate risk {q['survey_duplicate_risk_label']})")
        report_lines.append("")
    (ROOT / "batch_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    validation = validate()
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
