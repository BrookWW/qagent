from __future__ import annotations

import unittest

from src.qagent.validators import theorem_body_validation_errors, theorem_level_validation_errors, validate_clean_q_tex


BAD_TEMPLATE_Q = r"""
\begin{q}[Energy identity for one-bubble limits]
Generated from metadata/abstract only; confidence lower.
\textbf{Model.} ...
\textbf{Novelty condition.} ...
The precise assumptions should be chosen to match the input paper.
\end{q}
"""


GOOD_THEOREM_Q = r"""
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
(\alpha_j-1)|\log r_j|\to0 .
\]
Prove the no-neck estimate
\[
\lim_{R\to\infty}\lim_{\delta\downarrow0}\limsup_{j\to\infty}
\operatorname{osc}_{B_\delta(p)\setminus B_{Rr_j}(p)} u_j=0.
\]
\end{q}
"""

BAD_CONCLUSION_LABEL_Q = r"""
\begin{q}[Bad-set diameter estimate under approximate symmetry]
Let $Q_\varepsilon$ be a local minimizer of the Landau-de Gennes energy in
$B_{20r}(x)\subset\mathbb R^3$, and assume
\[
r^{-1}E_\varepsilon(Q_\varepsilon,B_{20r}(x))+\|Q_\varepsilon\|_{L^\infty(B_{20r}(x))}\le M.
\]
Assume there are $y\in B_{2r}(x)$ and a unit vector $v\in S^2$ such that
\[
r^{-1}\int_{B_r(x)} |v\cdot\nabla Q_\varepsilon|^2\,dx<\eta.
\]
Let $\operatorname{Bad}(Q_\varepsilon;\eta' r,\delta)$ be the bad set from the
regularity-scale definition.

Conclusion: for every $\beta\in(0,1/2)$, the set
$\operatorname{Bad}(Q_\varepsilon;\eta' r,\delta)\cap B_r(x)$ is contained in
the union of one ball of radius $\beta r$ and a $\beta r$-neighborhood of a line
parallel to $v$.
\end{q}
"""


class ValidatorTests(unittest.TestCase):
    def test_bad_template_q_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_clean_q_tex(BAD_TEMPLATE_Q)
        self.assertTrue(theorem_level_validation_errors(BAD_TEMPLATE_Q))

    def test_good_clean_theorem_q_passes(self) -> None:
        validate_clean_q_tex(GOOD_THEOREM_Q)
        self.assertEqual(theorem_level_validation_errors(GOOD_THEOREM_Q), [])

    def test_conclusion_label_is_rejected_as_boilerplate(self) -> None:
        with self.assertRaises(ValueError):
            validate_clean_q_tex(BAD_CONCLUSION_LABEL_Q)
        self.assertTrue(theorem_level_validation_errors(BAD_CONCLUSION_LABEL_Q))

    def test_theorem_body_checker_can_validate_candidate_statement(self) -> None:
        body = (
            "Let u be a weak solution of a uniformly elliptic equation on a bounded "
            "domain Omega. Assume u satisfies an energy bound. Prove that u satisfies "
            "a boundary Caccioppoli estimate with constants depending only on the data."
        )
        self.assertEqual(theorem_body_validation_errors(body), [])


if __name__ == "__main__":
    unittest.main()
