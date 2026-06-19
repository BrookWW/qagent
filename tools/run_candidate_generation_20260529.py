from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


BATCH = Path("outputs/batch_20260529_213619")
PAPER_IDS = ["paper_001", "paper_002", "paper_003"]


def score(
    *,
    novelty_confidence: int,
    already_done_risk: int,
    fast_sci_route: int,
    small_method_delta: int,
    too_ambitious_penalty: int,
    too_easy_to_publish_penalty: int,
    qed_gpt_attackability: int,
    sci_publishable_potential: int,
    nontriviality: int,
    novelty_potential: int,
    feasibility: int,
    clarity: int,
    qed_suitability: int,
    duplicate_risk: int,
    counterexample_risk: int,
    too_broad_penalty: int,
    too_trivial_penalty: int,
    survey_duplicate_risk: int,
    successful_transfer_fit: int,
    feedback_alignment: int,
) -> dict[str, int]:
    data = locals()
    final = (
        45 * novelty_confidence
        + 35 * fast_sci_route
        + 30 * small_method_delta
        + 25 * qed_gpt_attackability
        + 25 * sci_publishable_potential
        + 20 * feasibility
        + 15 * qed_suitability
        + 15 * nontriviality
        + 15 * successful_transfer_fit
        + 15 * feedback_alignment
        + 10 * novelty_potential
        + 10 * clarity
        - 45 * already_done_risk
        - 35 * survey_duplicate_risk
        - 30 * too_ambitious_penalty
        - 25 * duplicate_risk
        - 20 * counterexample_risk
        - 20 * too_broad_penalty
        - 20 * too_trivial_penalty
        - 20 * too_easy_to_publish_penalty
    )
    data["final_score"] = final
    data["weighted_score"] = final
    return data


SCORES = [
    score(
        novelty_confidence=4,
        already_done_risk=2,
        fast_sci_route=5,
        small_method_delta=5,
        too_ambitious_penalty=1,
        too_easy_to_publish_penalty=2,
        qed_gpt_attackability=5,
        sci_publishable_potential=4,
        nontriviality=4,
        novelty_potential=4,
        feasibility=5,
        clarity=5,
        qed_suitability=5,
        duplicate_risk=2,
        counterexample_risk=2,
        too_broad_penalty=1,
        too_trivial_penalty=1,
        survey_duplicate_risk=2,
        successful_transfer_fit=5,
        feedback_alignment=5,
    ),
    score(
        novelty_confidence=4,
        already_done_risk=2,
        fast_sci_route=4,
        small_method_delta=5,
        too_ambitious_penalty=2,
        too_easy_to_publish_penalty=1,
        qed_gpt_attackability=4,
        sci_publishable_potential=5,
        nontriviality=5,
        novelty_potential=4,
        feasibility=4,
        clarity=5,
        qed_suitability=4,
        duplicate_risk=2,
        counterexample_risk=2,
        too_broad_penalty=1,
        too_trivial_penalty=1,
        survey_duplicate_risk=2,
        successful_transfer_fit=4,
        feedback_alignment=5,
    ),
    score(
        novelty_confidence=3,
        already_done_risk=3,
        fast_sci_route=4,
        small_method_delta=4,
        too_ambitious_penalty=2,
        too_easy_to_publish_penalty=2,
        qed_gpt_attackability=4,
        sci_publishable_potential=4,
        nontriviality=4,
        novelty_potential=3,
        feasibility=4,
        clarity=4,
        qed_suitability=4,
        duplicate_risk=3,
        counterexample_risk=2,
        too_broad_penalty=2,
        too_trivial_penalty=1,
        survey_duplicate_risk=3,
        successful_transfer_fit=4,
        feedback_alignment=4,
    ),
    score(
        novelty_confidence=3,
        already_done_risk=2,
        fast_sci_route=4,
        small_method_delta=3,
        too_ambitious_penalty=2,
        too_easy_to_publish_penalty=2,
        qed_gpt_attackability=4,
        sci_publishable_potential=3,
        nontriviality=4,
        novelty_potential=3,
        feasibility=3,
        clarity=4,
        qed_suitability=4,
        duplicate_risk=2,
        counterexample_risk=3,
        too_broad_penalty=2,
        too_trivial_penalty=2,
        survey_duplicate_risk=2,
        successful_transfer_fit=3,
        feedback_alignment=4,
    ),
    score(
        novelty_confidence=3,
        already_done_risk=3,
        fast_sci_route=3,
        small_method_delta=4,
        too_ambitious_penalty=3,
        too_easy_to_publish_penalty=1,
        qed_gpt_attackability=3,
        sci_publishable_potential=4,
        nontriviality=5,
        novelty_potential=4,
        feasibility=3,
        clarity=4,
        qed_suitability=3,
        duplicate_risk=3,
        counterexample_risk=4,
        too_broad_penalty=2,
        too_trivial_penalty=1,
        survey_duplicate_risk=3,
        successful_transfer_fit=3,
        feedback_alignment=3,
    ),
    score(
        novelty_confidence=2,
        already_done_risk=3,
        fast_sci_route=3,
        small_method_delta=3,
        too_ambitious_penalty=3,
        too_easy_to_publish_penalty=2,
        qed_gpt_attackability=3,
        sci_publishable_potential=3,
        nontriviality=4,
        novelty_potential=3,
        feasibility=3,
        clarity=3,
        qed_suitability=3,
        duplicate_risk=3,
        counterexample_risk=3,
        too_broad_penalty=3,
        too_trivial_penalty=2,
        survey_duplicate_risk=3,
        successful_transfer_fit=3,
        feedback_alignment=3,
    ),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def ids(cards: list[dict[str, Any]], key: str, fallback: str) -> list[str]:
    out = []
    for index, card in enumerate(cards, 1):
        label = str(card.get(key) or card.get("theorem_label") or card.get("method") or f"{fallback}{index}")
        out.append(label[:80])
    return out


def card_basis(paper_dir: Path, gap_index: int) -> dict[str, list[str]]:
    theorem_cards = read_json(paper_dir / "theorem_cards.json")
    gap_cards = read_json(paper_dir / "gap_cards.json")
    method_cards = read_json(paper_dir / "method_cards.json")
    limitation_cards = read_json(paper_dir / "limitation_cards.json")
    method_basis = ids(method_cards, "method", "M")[:2] or ["methods_from_input_theorem_cards"]
    return {
        "based_on_theorem_cards": ids(theorem_cards, "theorem_label", "T")[:3],
        "based_on_gap_cards": ids(gap_cards[gap_index - 1 : gap_index], "gap_title", "G") or ids(gap_cards, "gap_title", "G")[:1],
        "based_on_method_cards": method_basis,
        "based_on_limitation_cards": ids(limitation_cards, "limitation", "L")[:2],
    }


def survey_report(paper_dir: Path, profile: dict[str, Any]) -> str:
    title = profile.get("title", paper_dir.name)
    authors = profile.get("authors", "not provided")
    confidence = profile.get("paper_reading_confidence", profile.get("confidence_level", "unknown"))
    return (
        "# Paper-Level Survey Report\n\n"
        f"- Paper: {title}\n"
        f"- Authors: {authors}\n"
        f"- Reading confidence from preflight artifacts: {confidence}\n"
        "- Sources used in this candidate-only phase: local paper_profile.json, theorem_cards.json, proof_cards.json, method_cards.json, limitation_cards.json, gap_cards.json, and paper_reader_report.md.\n"
        "- Nearby-literature anchors: input theorem cards, local method cards, and duplicate-risk query strings already recorded in gap_cards.json.\n"
        "- Google Scholar was not scraped. Network survey and final hard-review selection are intentionally deferred to the local hard_review stage.\n"
        "- Duplicate-risk rule for this phase: direct reproductions of the extracted theorem cards were avoided; every candidate changes the object class, boundary/scale regime, quantitative conclusion, coefficient class, or obstruction.\n"
        "- Phase note: this file only supports candidate generation and does not certify final novelty or final selection.\n"
    )


def candidate(
    paper_dir: Path,
    qid: str,
    rank_index: int,
    title: str,
    labels: list[str],
    statement: str,
    why_natural: str,
    tools: list[str],
    obstacles: str,
    minimal: str,
    ambitious: str,
    novelty: str,
    method_delta: str,
    route: str,
    journal_fit: str,
    gap_index: int,
) -> dict[str, Any]:
    basis = card_basis(paper_dir, gap_index)
    s = dict(SCORES[rank_index - 1])
    if "low-confidence" in novelty.lower():
        s["novelty_confidence"] = max(2, s["novelty_confidence"] - 1)
        s["already_done_risk"] = min(5, s["already_done_risk"] + 1)
        s["survey_duplicate_risk"] = min(5, s["survey_duplicate_risk"] + 1)
        s = score(**{k: v for k, v in s.items() if k not in {"final_score", "weighted_score"}})
    result = {
        "question_id": qid,
        "title": title,
        "mechanism_labels": labels,
        "precise_problem_statement": statement,
        "why_natural": why_natural,
        "expected_tools": tools,
        "possible_obstacles": obstacles,
        "minimal_version": minimal,
        "ambitious_version": ambitious,
        "first_sanity_checks": [
            "Check scaling against the input monotonicity or energy identity.",
            "Verify the candidate is not a theorem-card restatement.",
            "Test the model on a ball or half-ball with smooth data.",
            "Identify the single estimate whose proof is not already in the input paper.",
        ],
        **basis,
        "score_breakdown": s,
        "novelty_assessment": novelty,
        "method_delta": method_delta,
        "fast_sci_route": route,
        "journal_fit": journal_fit,
        "final_score": s["final_score"],
        "weighted_score": s["weighted_score"],
    }
    return result


def paper_001_candidates(paper_dir: Path) -> list[dict[str, Any]]:
    base = {
        "why_natural": "The input paper builds quantitative stratification and sharp regularity estimates for stationary supercritical semilinear elliptic solutions using monotonicity, tangent pairs, cone-splitting, and blow-up analysis.",
        "tools": ["monotonicity formula", "tangent pairs", "cone-splitting", "quantitative stratification", "blow-up analysis"],
        "minimal": "Work in a Euclidean ball, assume smooth stationary solutions first, and keep p away from the integer alpha p threshold.",
        "ambitious": "After the model theorem, allow weak stationary solutions and track endpoint dependence as alpha p approaches an integer.",
    }
    return [
        candidate(
            paper_dir,
            "p001_c01",
            1,
            "Boundary quantitative stratification for supercritical semilinear elliptic solutions",
            ["E. Setting generalization", "G. Strengthening and quantification"],
            "Let B_40^+ be a half-ball in R^n and let u in H^1(B_40^+) cap L^{p+1}(B_40^+) solve -Delta u = |u|^{p-1}u stationarily with smooth Dirichlet data on the flat boundary and theta_40(u,0) <= Lambda. Define boundary tangent pairs using half-space blow-ups and reflected defect measures. Prove that for each k <= n-ceil(alpha p) and epsilon>0, the r-neighborhood of the boundary quantitative k-stratum in B_1^+ has measure at most C r^{n-k}, with C depending only on epsilon, Lambda, n, p and boundary C^2 norms.",
            base["why_natural"],
            base["tools"],
            "The new obstruction is the boundary term in the monotonicity identity and the possibility that reflected tangent pairs create artificial symmetries.",
            base["minimal"],
            base["ambitious"],
            "This is not Theorem 1.16 because the input theorem is interior in balls and its tangent-pair stratification has no boundary defect term. The closest input result is the Minkowski estimate for S^k_{epsilon,r}(u). The closest known pattern is boundary epsilon-regularity for harmonic maps, but here the supercritical potential and tangent-measure component create a separate half-space obstruction. The problem is not too ambitious because it asks for the same exponent and proof skeleton with one boundary error; it is not too easy because the stationarity formula must be rebuilt.",
            "Reuse Naber-Valtorta/Reifenberg covering from the input paper; add only a boundary monotonicity and cone-splitting lemma for half-space tangent pairs.",
            "A short SCI route is 4-6 lemmas: boundary monotonicity, boundary tangent-pair compactness, half-space cone-splitting, discrete Reifenberg covering, and passage from quantitative strata to Minkowski content.",
            "JDE/JMAA/CPAA-level if restricted to smooth boundary data and non-endpoint p; too hard only if one demands sharp free-boundary-type boundary regularity.",
            3,
        ),
        candidate(
            paper_dir,
            "p001_c02",
            2,
            "Lorentz endpoint regularity with a logarithmic loss at integer alpha p",
            ["F. Parameter and regularity variation", "H. Counterexample or sharpness problem"],
            "Let u in H^1(B_40) cap L^{p+1}(B_40) be a stationary solution of -Delta u = |u|^{p-1}u with theta_40(u,0) <= Lambda, and assume alpha p is an integer. For j>=0, prove or disprove the weak endpoint estimate ||D^j u||_{L^{q_j,infty}(B_1, log^{-1})} <= C(j,Lambda,n,p), where q_j is the exponent from the non-integer Corollary 1.27 and the logarithmic Lorentz target is chosen so that the model homogeneous solution is borderline admissible.",
            base["why_natural"],
            base["tools"],
            "The single new obstruction is the defect measure in integer alpha p blow-ups, which the input text says prevents the non-integer regularity improvement.",
            "Prove the logarithmic estimate only for j=0 or j=1 under isolated singularity assumptions.",
            "Classify whether every integer alpha p defect measure produces exactly the logarithmic loss and no worse loss.",
            "This is not Corollary 1.27, which treats alpha p not in Z and gives the sharp weak-L^q estimate. The closest input result is the note that integer alpha p introduces defect measures. The candidate differs by asking for a borderline replacement rather than repeating the non-integer theorem. It is not likely a standard corollary because the defect-measure obstruction is precisely where the input method breaks. It is neither too ambitious nor too easy because the minimal version reduces to a single borderline distribution-function estimate.",
            "Keep the regularity-scale estimate and covering argument; replace the non-integer decay summation by a logarithmic Carleson packing estimate for bad scales.",
            "A fast route is to redo the scale decomposition in Theorem 1.26, isolate scales with nonzero defect, prove logarithmic packing, and test optimality on the homogeneous profile.",
            "Could be a short CPAA/JMAA note if the logarithmic endpoint is clean; if false, the counterexample version is still publishable.",
            5,
        ),
        candidate(
            paper_dir,
            "p001_c03",
            3,
            "Stability-based quantitative stratification for stable supercritical solutions",
            ["D. Object generalization", "B. Analogy between models"],
            "Let u in H^1(B_40) cap L^{p+1}(B_40) be a stable weak solution of -Delta u = |u|^{p-1}u with theta_40(u,0) <= Lambda, but do not assume full stationarity under domain variations. In dimensions and exponents where the stability inequality yields the Pohozaev-type monotonicity defect bounded by Cr^beta, prove a quantitative k-stratification estimate L^n(B_r(S^k_{epsilon,r}(u) cap B_1)) <= C r^{n-k-beta} for all 0<r<1.",
            base["why_natural"],
            base["tools"],
            "The obstruction is that stability gives variational control in the target direction but not exact domain-stationary monotonicity.",
            "Assume an explicit almost-monotonicity formula with exponent beta and prove the covering theorem.",
            "Derive the almost-monotonicity only from stability and minimal integrability assumptions.",
            "This is not the input stationary theorem because the object class changes from stationary solutions to stable solutions. The closest known/input result is Theorem 1.16 plus the discussion that stable solutions form a related but distinct literature. The question differs by quantifying the exact loss beta caused by almost-monotonicity. It is not too ambitious in the minimal version because the hard PDE derivation can be separated; it is not too easy because cone-splitting with errors must be checked.",
            "Reuse the paper's quantitative stratification after replacing exact monotonicity by an error-controlled monotonicity lemma.",
            "A short route is to prove an abstract almost-monotone stratification theorem, then verify the PDE hypotheses for a stable model case.",
            "JDE/CPAA-level if formulated with a proved almost-monotonicity hypothesis; too broad if it claims all stable solutions without exponent restrictions.",
            1,
        ),
        candidate(
            paper_dir,
            "p001_c04",
            4,
            "Uniqueness of tangent pairs under summable density drop",
            ["G. Strengthening and quantification", "A. Direct extraction"],
            "Let u be a stationary solution of -Delta u=|u|^{p-1}u in B_40 with theta_40(u,0)<=Lambda. Suppose at x in B_1 the dyadic density drops sum_j |theta_{2^{-j}}(u,x)-theta_{2^{-j-1}}(u,x)| is finite and the tangent-pair symmetry plane is k-dimensional at one blow-up. Prove that all tangent pairs at x have the same k-plane and that the rescaled defect measures converge without changing subsequences.",
            base["why_natural"],
            base["tools"],
            "The obstruction is rotating symmetry planes of tangent measures despite small total density drop.",
            "Assume an additional Reifenberg flatness summability condition on the quantitative strata.",
            "Remove the extra flatness assumption and obtain a quantitative convergence rate for tangent pairs.",
            "This is not Proposition 1.6 or Theorem 1.21: those give existence and a.e. symmetry of tangent pairs, not uniqueness under a summability condition. The closest known pattern is uniqueness of tangent maps for harmonic maps, but the input tangent pair contains both a function and a measure. It is not too ambitious with summable drop and not too easy because the measure component can still rotate.",
            "Use the monotonicity identity to convert density-drop summability into Cauchy convergence of blow-ups; the only added step is controlling the defect-measure metric.",
            "A short route uses dyadic compactness, a quantitative symmetry-distance estimate, and a telescoping argument in the metric on measures.",
            "JMAA/JDE-level as a local uniqueness criterion rather than a full uniqueness theorem.",
            4,
        ),
        candidate(
            paper_dir,
            "p001_c05",
            5,
            "Sharpness example for tangent-function stratification without tangent measures",
            ["H. Counterexample or sharpness problem", "A. Direct extraction"],
            "Construct, or prove in a radial model, a stationary solution of -Delta u=|u|^{p-1}u in B_1 with alpha p an integer such that the tangent function at the origin is zero but the tangent measure is nonzero, and show that the point is missed by a stratification defined only through tangent functions while it is detected by tangent pairs.",
            base["why_natural"],
            base["tools"],
            "The obstruction is turning the paper's qualitative warning about defect measures into a rigorous stationary example.",
            "Work with the known homogeneous radial profile and prove the measure convergence directly.",
            "Build a nonradial example where the missed stratum has positive Hausdorff dimension.",
            "This is not the input theorem; it tests the necessity of tangent pairs, motivated by Corollary 1.24's discussion of integer alpha p. The closest known/input result is the paper's statement that tangent-function stratification can fail when the tangent function vanishes. It could be known, so duplicate risk is medium, but the narrowed radial verification may still be a useful short note. It is not too easy because stationarity and finite-energy constraints must both be checked.",
            "Use the paper's scaling and density formula; the only new ingredient is explicit computation of the tangent measure for the model profile.",
            "A fast route is to solve for the radial homogeneous profile, verify membership in H^1 cap L^{p+1}, compute scaled energy measures, and compare two stratification definitions.",
            "JMAA-level as a sharpness/counterexample note if not already included in the paper.",
            6,
        ),
        candidate(
            paper_dir,
            "p001_c06",
            6,
            "Parabolic persistence of interior strata for ancient rescaled semilinear flows",
            ["E. Setting generalization", "B. Analogy between models"],
            "Let u(t,x) be an ancient solution of u_t-Delta u=|u|^{p-1}u on (-40^2,0]xB_40 with uniformly bounded parabolic density and assume each time-slice is stationary up to an L^2_t H^{-1}_x error of size eta. Define parabolic tangent pairs at (0,0). Prove a quantitative k-stratification estimate for the time-zero singular set with an error term C eta^gamma + C r^{n-k}.",
            base["why_natural"],
            base["tools"],
            "The obstruction is the time-error term in monotonicity and the mismatch between parabolic and elliptic tangent pairs.",
            "Assume the parabolic almost-monotonicity formula and prove only the time-zero covering result.",
            "Extend to full space-time strata with parabolic Hausdorff dimension estimates.",
            "This is not already the input elliptic theorem because it introduces an ancient-flow perturbation and an explicit eta error. The closest known pattern is stationary-to-flow transfer for harmonic map heat flow, but the supercritical source and tangent measures alter the compactness. It is more ambitious than the other candidates, so it ranks lower; still, a minimal almost-stationary theorem is plausible and not a direct corollary.",
            "Keep the elliptic Reifenberg argument on good time slices; add one parabolic density-drop estimate controlling the time defect.",
            "A short route exists only for the minimal version: freeze a good time, prove an elliptic estimate with eta-error, then integrate bad-scale counts.",
            "CPAA-level if narrowed to almost-stationary time slices; too hard as a full parabolic singular-set theory.",
            2,
        ),
    ]


def paper_002_candidates(paper_dir: Path) -> list[dict[str, Any]]:
    why = "The input paper concerns two-dimensional homogenization for elliptic systems with lower-order terms; the local evidence is weak, so candidates are prototype theorem-level variants anchored to the title and gap cards."
    tools = ["periodic homogenization", "energy estimates", "correctors", "duality in two dimensions", "compactness"]
    return [
        candidate(
            paper_dir,
            "p002_c01",
            1,
            "Uniform H1 error estimate for two-dimensional elliptic systems with skew lower-order drift",
            ["C. Operator generalization", "G. Strengthening and quantification"],
            "Let Omega be a bounded C^{1,1} domain in R^2. For epsilon>0 let u_epsilon in H^1_0(Omega;R^m) solve -div(A(x/epsilon) grad u_epsilon)+B(x/epsilon) grad u_epsilon+c(x/epsilon)u_epsilon=f, where A is uniformly elliptic, periodic, and Holder continuous, B is periodic and skew-symmetric in the system indices, c>=0 is bounded periodic, and f in L^2. Prove an H^1 error estimate ||u_epsilon-u_0-epsilon chi(x/epsilon)grad u_0||_{H^1(Omega)} <= C epsilon^{1/2} ||f||_{L^2}, with homogenized lower-order terms included explicitly.",
            why,
            tools,
            "The obstruction is that first-order terms are critical in two dimensions and may not be absorbed by the principal elliptic part without skew or sign structure.",
            "Assume smooth coefficients and u_0 in H^2.",
            "Remove Holder continuity and prove the estimate for VMO periodic coefficients.",
            "Low-confidence card basis: this is not a restatement of the abstract_main_result because the local theorem card does not state a corrector error estimate. The closest input result is the paper's general homogenization theorem for elliptic systems with lower-order terms in dimension two. The candidate differs by imposing skew/sign structure and asking for an explicit H1 rate. This is likely not automatically known in the exact system/lower-order configuration; it is not too ambitious because the two-dimensional structure is narrowed, and not too easy because the drift-corrector commutator must be controlled.",
            "Reuse standard periodic correctors from elliptic homogenization; add only one lower-order commutator estimate using skew-symmetry and the two-dimensional energy embedding.",
            "A fast route is 5 lemmas: cell problems, homogenized operator identification, smoothing of u_0, residual expansion, energy estimate for the error.",
            "JMAA/CPAA-level as a clean quantitative homogenization estimate under structural lower-order assumptions.",
            5,
        ),
        candidate(
            paper_dir,
            "p002_c02",
            2,
            "Boundary layer corrector for Dirichlet homogenization with lower-order terms in R2",
            ["E. Setting generalization", "F. Parameter and regularity variation"],
            "Let Omega subset R^2 be C^{2}. For periodic uniformly elliptic A and bounded periodic lower-order coefficients B,c satisfying c>=0 and div_y B=0, let u_epsilon solve the Dirichlet elliptic system with zero boundary data and f in L^q(Omega), q>2. Prove that adding a boundary layer corrector supported in an epsilon-neighborhood of partial Omega improves the L^2 convergence rate from O(epsilon^{1/2}) to O(epsilon) for smooth homogenized solution u_0.",
            why,
            tools,
            "The obstruction is the interaction between oscillating lower-order drift and the boundary cutoff gradient.",
            "Prove the result in a disk with scalar equations and smooth periodic coefficients.",
            "Extend to systems and Lipschitz domains with nontangential maximal estimates.",
            "This is not already the input theorem because it asks for a boundary-layer improvement and an explicit rate, while the card only records a broad homogenization result. The closest known result is classical Dirichlet corrector theory without lower-order critical terms. The small difference is the drift-boundary commutator, which makes the problem publishable rather than cosmetic. It is neither too ambitious nor too easy in the smooth two-dimensional case.",
            "Use the paper's homogenization framework and insert a standard boundary layer cutoff; estimate the new lower-order residual in L^2 by two-dimensional Sobolev embedding.",
            "Fast route: derive two-scale expansion, define boundary cutoff, compute residual, use coercivity, and optimize the boundary layer thickness.",
            "JDE/JMAA-level if the rate improvement is stated under smooth coefficients and domain.",
            3,
        ),
        candidate(
            paper_dir,
            "p002_c03",
            3,
            "Endpoint Lq compactness for critical lower-order terms in planar homogenization",
            ["F. Parameter and regularity variation", "D. Object generalization"],
            "Let Omega subset R^2 and let u_epsilon solve -div(A(x/epsilon)grad u_epsilon)+b(x/epsilon).grad u_epsilon=f_epsilon with uniformly bounded H^1_0 norm, periodic A, mean-zero periodic b in L^2_y, and f_epsilon compact in H^{-1}. Prove that after subsequence u_epsilon converges strongly in L^q(Omega) for every finite q and identify the homogenized equation, assuming the drift cell problem has an H^1 periodic solution.",
            why,
            tools,
            "The obstruction is endpoint control of the drift b in L^2_y, which is critical only in dimension two.",
            "Take scalar equations and smooth b, then pass to L^2_y by approximation.",
            "Prove a quantitative logarithmic modulus for the convergence in all finite q.",
            "This is not the input theorem because it narrows to endpoint drift compactness and strong Lq convergence, not a full general homogenization result. The closest known result is compactness for bounded lower-order terms; the L2_y critical drift with a cell-problem assumption is the new obstruction. It may be known in some scalar cases, so risk is medium, but the exact system theorem is plausible.",
            "Reuse two-scale convergence and compensated compactness; add a single cell-problem estimate for the critical drift term.",
            "Short route: approximate b, solve cell problem, test the equation with corrected oscillatory functions, prove strong Lq via Trudinger-type compactness.",
            "CPAA-level if narrowed to scalar or diagonal systems; too broad for arbitrary systems.",
            1,
        ),
        candidate(
            paper_dir,
            "p002_c04",
            4,
            "Green function expansion with lower-order periodic terms in two dimensions",
            ["A. Direct extraction", "G. Strengthening and quantification"],
            "For scalar uniformly elliptic periodic coefficients in R^2 with bounded periodic lower-order terms satisfying a coercive sign condition, let G_epsilon(x,y) be the Dirichlet Green function in a smooth bounded domain. Prove that away from |x-y|<=4epsilon, G_epsilon(x,y)=G_0(x,y)+epsilon chi(x/epsilon).grad_x G_0(x,y)+epsilon chi^*(y/epsilon).grad_y G_0(x,y)+R_epsilon(x,y), with |R_epsilon(x,y)|<=C epsilon |x-y|^{-1}.",
            why,
            tools,
            "The obstruction is that two-dimensional Green functions are logarithmic and lower-order terms create non-selfadjoint adjoint correctors.",
            "Prove the expansion only for x,y separated by a fixed positive distance.",
            "Track the singular zone and obtain a global weak-L^2 gradient bound for the remainder.",
            "This is not the input theorem because it asks for a pointwise Green-function expansion, not merely homogenized convergence. The closest classical result is Green expansion for principal-part periodic elliptic operators. Lower-order non-selfadjoint correctors in dimension two are the precise method delta. It is moderately ambitious but can become a short JDE-style result if restricted to scalar smooth coefficients.",
            "Use the input homogenization machinery plus adjoint correctors; the only new obstruction is the logarithmic Green singularity coupled to lower-order residuals.",
            "Fast route: construct primal/adjoint correctors, write residual equation for G_epsilon expansion, estimate by known 2D Green bounds.",
            "JDE-level in scalar smooth case; too hard for rough systems.",
            4,
        ),
        candidate(
            paper_dir,
            "p002_c05",
            5,
            "Failure of homogenized coercivity without sign control on lower-order terms",
            ["H. Counterexample or sharpness problem", "C. Operator generalization"],
            "Construct a periodic scalar two-dimensional elliptic operator -div(A(y)grad u)+b(y).grad u+c(y)u with uniformly elliptic A and bounded b,c, but without c>=0 or a divergence-free/skew condition, such that the epsilon-problems are uniformly solvable while the formal homogenized lower-order operator fails coercivity in H^1_0 for a bounded domain.",
            why,
            tools,
            "The obstruction is separating true lower-order homogenized instability from a bad choice of cell representatives.",
            "Construct the example for A=I and one oscillatory potential term.",
            "Show loss of uniform resolvent bounds, not just failure of the formal bilinear form.",
            "This is not a restatement because it targets the necessity of structural assumptions that the input title suggests may be important. The closest known result is standard coercive homogenization with sign conditions. It differs by producing a sharpness example. It is not too ambitious in the scalar A=I case and not too easy because the example must survive the homogenization limit.",
            "Use elementary two-scale ansatz and spectral perturbation; the new step is choosing b,c so the averaged effective zeroth-order term is negative.",
            "A short route is to compute the cell problem explicitly for trigonometric coefficients and verify the first eigenvalue of the effective operator changes sign.",
            "JMAA-level as a focused counterexample/sharpness note.",
            2,
        ),
        candidate(
            paper_dir,
            "p002_c06",
            6,
            "Nonperiodic perturbation stability for planar lower-order homogenization",
            ["B. Analogy between models", "E. Setting generalization"],
            "Let A(y),B(y),c(y) be periodic coefficients covered by the input paper's two-dimensional elliptic-system homogenization theorem. Perturb the lower-order coefficients by eta D(x,y), eta e(x,y), where D,e are bounded, slowly varying in x, and periodic in y. Prove that the homogenized operator and weak solutions depend Lipschitz-continuously on eta in H^{-1}->H^1_0 operator norm for |eta| sufficiently small.",
            why,
            tools,
            "The obstruction is that the lower-order corrector equations are not purely local in y once slow x-dependence is introduced.",
            "Assume all coefficients are smooth and D,e have compact x-support away from the boundary.",
            "Allow VMO dependence in x and obtain a quantitative two-scale error estimate.",
            "This is not already the input theorem because it asks for stability under a small locally periodic perturbation, not the base periodic homogenization theorem. The closest known result is locally periodic homogenization for principal terms; the lower-order planar system setting is distinct. It is lower ranked because it may require broader theory, but the small-eta version keeps one new obstruction.",
            "Linearize the periodic cell problems in eta; the small method delta is differentiating the cell problems and bounding the perturbed correctors.",
            "Fast route: solve perturbed cell problems by implicit function theorem, identify effective coefficients, compare weak formulations, and estimate the solution difference.",
            "CPAA-level if kept to smooth small perturbations; too ambitious for fully nonperiodic coefficients.",
            4,
        ),
    ]


def paper_003_candidates(paper_dir: Path) -> list[dict[str, Any]]:
    why = "The input paper proves improved convergence for Landau-de Gennes minimizers in the vanishing elasticity limit using monotonicity, blow-up analysis, bad-set covering, and sharp potential-energy estimates."
    tools = ["modified monotonicity formula", "blow-up analysis", "bad-set covering", "small-energy regularity", "Landau-de Gennes compactness"]
    return [
        candidate(
            paper_dir,
            "p003_c01",
            1,
            "Boundary bad-set covering for Landau-de Gennes minimizers near smooth anchoring",
            ["E. Setting generalization", "G. Strengthening and quantification"],
            "Let Omega subset R^3 be C^2 and let Q_epsilon minimize the Landau-de Gennes energy with smooth N-valued Dirichlet anchoring Q_b. For x0 in partial Omega and scales r in (Lambda epsilon, r0), define the boundary bad set where dist(Q_epsilon,N)>=delta or the regularity scale is below eta r. Prove a half-ball covering estimate L^3(B_r(Bad_boundary(Q_epsilon;eta r,delta)) cap B_{r0}(x0)) <= C r^3 with constants depending only on a,b,c,Omega,Q_b,M,delta.",
            why,
            tools,
            "The obstruction is boundary flattening: the modified monotonicity formula acquires curvature and anchoring errors at the same scales as the bad-set covering.",
            "Assume flat boundary and constant anchoring in a half-ball.",
            "Allow C^2 boundaries and nonconstant smooth N-valued anchoring with explicit curvature dependence.",
            "This is not Theorem 1.2 or Corollary 1.6, which give convergence and boundary-value convergence, nor Lemma 3.4, which gives a near-boundary regularity statement. The candidate asks for a boundary analogue of the interior bad-set covering Lemma 3.3. The closest known result is boundary partial regularity for harmonic maps, but the epsilon-dependent bulk potential creates a distinct obstruction. It is a realistic short result because the interior proof is already local and the new term is boundary error control.",
            "Reuse Lemmas 2.5-3.3 from the input paper; add a boundary flattening and reflected/anchored monotonicity estimate.",
            "Fast SCI route: prove flat-boundary monotonicity, boundary epsilon-regularity, one-step boundary trapping, Vitali covering, then pass to curved boundary by charts.",
            "JDE/JMAA-level if stated as a boundary covering theorem, with direct use in global convergence.",
            3,
        ),
        candidate(
            paper_dir,
            "p003_c02",
            2,
            "Quantitative rate for strong H1 convergence away from the singular set of Q0",
            ["G. Strengthening and quantification", "F. Parameter and regularity variation"],
            "Let Q_epsilon be local minimizers of the Landau-de Gennes energy in Omega subset R^3 satisfying the uniform energy and L_infty bound of Theorem 1.2, and let Q0 be the limiting N-valued local minimizer. If K compactly contained in Omega\\sing(Q0) and dist(K,sing(Q0))>=rho>0, prove ||Q_epsilon-Q0||_{H^1(K)} <= C_K epsilon^{1/2} after fixing a smooth nearest-point gauge to N, with C_K depending on rho, M, a,b,c and local C^2 bounds for Q0.",
            why,
            tools,
            "The obstruction is that the paper proves strong convergence and potential-energy rate, but an explicit H1 rate needs linearization around the vacuum manifold and control of tangential modes.",
            "Prove the estimate for a ball where Q0 is smooth and the image lies in a single coordinate chart of N.",
            "Improve epsilon^{1/2} to epsilon if the bulk Hessian is uniformly nondegenerate in normal directions and Q0 is analytic.",
            "This is not Theorem 1.2 because the input theorem gives convergence and an integral potential bound, not an explicit local H1 rate away from singularities. The closest external pattern is convergence-rate theory for Ginzburg-Landau/Allen-Cahn away from interfaces. The method delta is small: linearize the Euler-Lagrange equation around Q0 and exploit the bulk normal coercivity. It is not too ambitious in a fixed compact regular region, and not too easy because tangential gauge terms must be handled.",
            "Reuse the strong H1 convergence and small-potential estimates; add one quantitative linearized coercivity estimate in normal/tangential decomposition.",
            "A short route has 5 lemmas: tubular projection to N, normal coercivity, equation for the tangential error, Caccioppoli inequality, and absorption of epsilon residual terms.",
            "JMAA/CPAA-level as a rate refinement on regular compact subsets.",
            5,
        ),
        candidate(
            paper_dir,
            "p003_c03",
            3,
            "Sharp lower bound for potential energy near a hedgehog defect",
            ["H. Counterexample or sharpness problem", "A. Direct extraction"],
            "Let Q_epsilon be the radial hedgehog-type minimizers in B_1 subset R^3 with boundary trace Q_b(x)=s_*(x/|x| tensor x/|x|-I/3). Prove that for every fixed tau in (0,1), integral_{B_tau} epsilon^{-2} f(Q_epsilon) dx >= c epsilon for all sufficiently small epsilon, and identify c>0 in terms of the one-dimensional core profile whenever the profile is unique.",
            why,
            tools,
            "The obstruction is converting the paper's sharpness construction into an explicit lower-bound constant rather than only the order epsilon.",
            "Prove only the order-sharp lower bound c epsilon without identifying c.",
            "Derive the Gamma-limit of the rescaled core energy and uniqueness of the optimal profile.",
            "This is not Proposition 4.1 if the input proposition only establishes order-sharpness for a concrete example; this candidate asks for an explicit local hedgehog lower bound and possible constant identification. The closest known result is radial Landau-de Gennes core-energy asymptotics, so duplicate risk is medium. It is not too ambitious in the order-sharp version and not too easy because topology prevents N-valued filling.",
            "Reuse the topological obstruction Lemma 4.3 and potential-energy sharpness argument; add a radial-profile lower-bound computation.",
            "Fast route: reduce to radial ansatz, prove no N-valued competitor, rescale the core, establish compactness of profiles, and compute/estimate the limiting core energy.",
            "JMAA-level if the constant identification is included; order-only version may be too close to the input paper.",
            6,
        ),
        candidate(
            paper_dir,
            "p003_c04",
            4,
            "Bad-set diameter estimate under one-dimensional approximate symmetry",
            ["G. Strengthening and quantification", "D. Object generalization"],
            "Let Q_epsilon be a local Landau-de Gennes minimizer in B_20r(x) with r^{-1}E_epsilon(Q_epsilon,B_20r(x))+||Q_epsilon||_{L_infty}<=M and r in (Lambda epsilon,1). Assume the monotonicity drop at some y in B_2r(x) is below eta and Q_epsilon is approximately invariant in one direction in the sense r^{-1} integral_{B_r(x)} |v dot grad Q_epsilon|^2 < eta. Prove that the bad set Bad(Q_epsilon;eta' r,delta) cap B_r(x) has diameter at most beta r outside one ball centered on the approximate symmetry axis.",
            why,
            tools,
            "The obstruction is strengthening Proposition 2.10 from containment in a ball to a diameter/axis localization statement without assuming exact symmetry.",
            "Prove the estimate with an additional L^2 closeness assumption to a one-dimensional comparison map.",
            "Upgrade to a Reifenberg-flatness statement for the bad set across many scales.",
            "This is not Proposition 2.10 because the input result traps the bad set in a ball under small monotonicity drop; the candidate asks for axis-sensitive diameter localization using approximate one-dimensional symmetry. The closest known pattern is cone-splitting in harmonic-map quantitative stratification. The new obstruction is the epsilon-scale vacuum constraint, so the problem is neither a direct corollary nor a huge new theory.",
            "Reuse Proposition 2.10 and add a cone-splitting style contradiction argument with blow-ups of Q_epsilon.",
            "Fast route: assume failure, rescale, pass to a limiting N-valued harmonic map/local minimizer, invoke one-dimensional symmetry, and contradict two separated bad points.",
            "JDE/CPAA-level as a quantitative-regularity strengthening.",
            1,
        ),
        candidate(
            paper_dir,
            "p003_c05",
            5,
            "Local minimizer convergence with weak anchoring surface energy",
            ["C. Operator generalization", "E. Setting generalization"],
            "Let Q_epsilon minimize Landau-de Gennes energy in a smooth bounded Omega subset R^3 with weak anchoring term gamma_epsilon integral_{partial Omega} |Q-Q_b|^2 dS, where gamma_epsilon -> infinity and epsilon gamma_epsilon -> 0. Assuming the same uniform energy and L_infty bounds as Theorem 1.2, prove that a subsequence converges strongly in H^1_loc(Omega) to an N-valued local minimizer Q0 and determine whether Q0 satisfies the strong anchoring trace Q_b.",
            why,
            tools,
            "The obstruction is a boundary layer whose energy scale may be invisible to interior compactness but decisive for the trace.",
            "Prove only interior strong H1 convergence, without identifying the limiting trace.",
            "Find the sharp threshold in gamma_epsilon for strong anchoring of Q0.",
            "This is not Corollary 1.6 because the input boundary result assumes fixed Dirichlet trace. The closest known theory is weak anchoring in liquid crystals, but the vanishing-elasticity convergence with singular Q0 has a distinct boundary-layer obstruction. It is more ambitious than an interior estimate, but the minimal interior compactness version is a small method delta.",
            "Reuse the interior compactness proof of Theorem 1.2; add an energy comparison for the weak anchoring layer and a trace compactness argument.",
            "Fast route: establish uniform local estimates away from boundary, prove interior convergence as in Theorem 1.2, then analyze a one-dimensional boundary layer for the trace threshold.",
            "CPAA/JMAA-level if restricted to smooth Q_b and gamma_epsilon regimes.",
            2,
        ),
        candidate(
            paper_dir,
            "p003_c06",
            6,
            "Almost-minimizer version of improved Landau-de Gennes convergence",
            ["D. Object generalization", "F. Parameter and regularity variation"],
            "Let Q_epsilon in H^1_loc(Omega,S0) be (omega_epsilon,rho)-almost minimizers of the Landau-de Gennes energy, meaning E_epsilon(Q_epsilon,B_r)<=E_epsilon(P,B_r)+omega_epsilon r for every competitor P with same trace on partial B_r and r>=rho epsilon. If omega_epsilon ->0 and the uniform energy/L_infty bound of Theorem 1.2 holds, prove strong H^1_loc convergence to an N-valued local minimizer of the Dirichlet energy, with potential-energy bound integral_K epsilon^{-2}f(Q_epsilon)<=C epsilon + C omega_epsilon.",
            why,
            tools,
            "The obstruction is that monotonicity and bad-set covering acquire almost-minimality errors at every scale.",
            "Assume omega_epsilon <= epsilon and prove the same O(epsilon) potential bound.",
            "Allow Dini-scale almost-minimality and derive an optimal error modulus.",
            "This is not Theorem 1.2 because the object class changes from exact local minimizers to almost minimizers. The closest known pattern is almost-minimizer regularity for harmonic maps and Ginzburg-Landau. The method delta is controlled: each variational comparison gains an omega_epsilon error. It is not too ambitious in the Dini/small-error case and not too easy because the covering lemma must accumulate errors correctly.",
            "Reuse the paper's monotonicity, small-energy, and covering proof; add a bookkeeping lemma showing almost-minimality errors remain summable.",
            "Fast route: prove almost-monotonicity, modify Lemmas 2.5-2.6 with error, redo the bad-set covering, and pass to compactness.",
            "JDE/CPAA-level if the almost-minimality modulus is explicit.",
            4,
        ),
    ]


GENERATORS = {
    "paper_001": paper_001_candidates,
    "paper_002": paper_002_candidates,
    "paper_003": paper_003_candidates,
}


def write_phase_result(paper_dir: Path, profile: dict[str, Any], candidates: list[dict[str, Any]], ranked: list[dict[str, Any]]) -> None:
    write_json(
        paper_dir / "result.json",
        {
            "phase": "candidate_generation",
            "mode": "Deep Mode",
            "refinement_rounds_a": 1,
            "final_questions_per_paper_b": 3,
            "initial_candidate_questions_per_paper": 6,
            "paper_id": paper_dir.name,
            "paper_title": profile.get("title"),
            "paper_reading_confidence": profile.get("paper_reading_confidence", profile.get("confidence_level")),
            "selected_question_ids": [],
            "selected_phase_has_run": False,
            "candidate_questions_path": str(paper_dir / "candidate_questions.json"),
            "ranked_questions_path": str(paper_dir / "ranked_questions.json"),
            "candidate_count": len(candidates),
            "ranked_count": len(ranked),
        },
    )


def validate() -> dict[str, Any]:
    details = []
    ok = True
    paper_dirs = [BATCH / pid for pid in PAPER_IDS]
    selected_dirs = sorted(BATCH.glob("paper_*/selected"))
    for paper_dir in paper_dirs:
        candidates = read_json(paper_dir / "candidate_questions.json")
        ranked = read_json(paper_dir / "ranked_questions.json")
        candidate_ids = [item["question_id"] for item in candidates]
        ranked_ids = [item["question_id"] for item in ranked]
        sorted_ok = ranked == sorted(ranked, key=lambda item: item["final_score"], reverse=True)
        paper_ok = (
            paper_dir.exists()
            and len(candidates) == 6
            and len(ranked) == 6
            and set(candidate_ids) == set(ranked_ids)
            and len(candidate_ids) == len(set(candidate_ids))
            and sorted_ok
            and not (paper_dir / "selected").exists()
        )
        ok = ok and paper_ok
        details.append(
            {
                "paper_id": paper_dir.name,
                "exists": paper_dir.exists(),
                "candidate_questions": len(candidates),
                "ranked_questions": len(ranked),
                "ranked_sorted_by_final_score_desc": sorted_ok,
                "selected_directory_exists": (paper_dir / "selected").exists(),
                "ok": paper_ok,
            }
        )
    ok = ok and len(paper_dirs) == 3 and not selected_dirs
    return {
        "phase": "candidate_generation",
        "expected_paper_directories": 3,
        "paper_directories_checked": len(paper_dirs),
        "selected_directories_found": [str(path) for path in selected_dirs],
        "ok": ok,
        "details": details,
    }


def main() -> None:
    for paper_id in PAPER_IDS:
        paper_dir = BATCH / paper_id
        if (paper_dir / "selected").exists():
            shutil.rmtree(paper_dir / "selected")
        profile = read_json(paper_dir / "paper_profile.json")
        survey_path = paper_dir / "survey_report.md"
        if not survey_path.exists():
            survey_path.write_text(survey_report(paper_dir, profile), encoding="utf-8")
        candidates = GENERATORS[paper_id](paper_dir)
        ranked = sorted(candidates, key=lambda item: item["final_score"], reverse=True)
        for rank, item in enumerate(ranked, 1):
            item["rank"] = rank
        write_json(paper_dir / "candidate_questions.json", candidates)
        write_json(paper_dir / "ranked_questions.json", ranked)
        write_phase_result(paper_dir, profile, candidates, ranked)
    validation = validate()
    write_json(BATCH / "candidate_generation_validation.json", validation)
    print(json.dumps(validation, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
