from __future__ import annotations

import re
from pathlib import Path


REQUIRED_SELECTED_FILES = [
    "problem_statement.tex",
    "additional_prove_human_help_global.md",
    "additional_verify_rule_global.md",
    "survey_queries.md",
    "feasibility_analysis.md",
    "metadata.json",
]


FORBIDDEN_Q_PHRASES = [
    "Generated from metadata",
    "Generated from metadata/abstract only",
    "confidence lower",
    "paper-specific smooth model",
    "work in the paper-specific smooth model",
    "choose assumptions to match the input paper",
    "chosen to match the input paper",
    "under the paper-specific hypotheses",
    "precise structural assumptions should be chosen",
    "the precise structural assumptions should be chosen",
    "theorem-level assertion in the assumptions",
    "this is not to reproduce the input paper",
    "the expected proof should decompose into",
    "QED suitable",
    "QED suitability",
    "the stated compactness, regularity, convergence, connectedness, curvature, or counterexample conclusion",
    "the stated compactness, regularity, convergence, or counterexample conclusion",
    "the indicated narrowed model",
    "the main regularity mechanism",
    "the principal conclusion",
    "Conclusion:",
    "Conclusions:",
    "In conclusion",
    "To conclude",
    "Summary:",
    "Summarizing,",
    "We conclude that",
]


FORBIDDEN_Q_HEADING_PATTERNS = [
    r"\\textbf\{\s*Model\s*\.?\s*\}",
    r"\\textbf\{\s*Objects\s*\.?\s*\}",
    r"\\textbf\{\s*Novelty condition\s*\.?\s*\}",
    r"\\textbf\{\s*QED suitability\s*\.?\s*\}",
    r"\\textbf\{\s*User rating\s*\.?\s*\}",
    r"\\textbf\{\s*Why this is good\s*\.?\s*\}",
    r"\\textbf\{\s*Feasibility\s*\.?\s*\}",
]

DOMAIN_PATTERNS = [
    r"\bB_\d",
    r"\bB\^\+",
    r"\bball\b",
    r"\bdomain\b",
    r"\bmanifold\b",
    r"\btorus\b",
    r"\bhalf[- ]?ball\b",
    r"\bvarifold\b",
    r"\bcurrent\b",
    r"\\Omega",
    r"\\Sigma",
    r"\\subset",
]

OBJECT_CLASS_PATTERNS = [
    r"\bweak solution\b",
    r"\bsolution\b",
    r"\bminimi[sz]er\b",
    r"\bcritical points?\b",
    r"\bstationary\b",
    r"\bstable\b",
    r"\bbounded[- ]index\b",
    r"\bvarifold\b",
    r"\bcurrent\b",
    r"\bmaps?\b",
    r"\bfunction\b",
    r"\bhypersurface\b",
    r"\btransition[- ]layer\b",
    r"\bsequence\b",
    r"\bQ[- ]?tensors?\b",
    r"\bsolve[s]?\b",
    r"\\in\s*C\^",
    r"\\in\s*H\^",
    r"\\in\s*W\^",
    r"\\in\s*BV",
]

MODEL_PATTERNS = [
    r"\\\[[\s\S]+?\\\]",
    r"\\begin\{equation\}",
    r"\bequation\b",
    r"\benergy\b",
    r"\bfunctional\b",
    r"\bEuler--Lagrange\b",
    r"\bsolve[s]?\b",
    r"\bminimi[sz]e[s]?\b",
    r"\bcritical\b",
    r"\bvarifold\b",
    r"\bcurrent\b",
    r"\bflow\b",
    r"=",
]

ASSUMPTION_PATTERNS = [
    r"\bLet\b",
    r"\bAssume\b",
    r"\bSuppose\b",
    r"\bwith\b",
    r"\bsatisfy(?:ing|ies)?\b",
]

CONCLUSION_PATTERNS = [
    r"\bProve\b",
    r"\bShow\b",
    r"\bConstruct\b",
    r"\bDetermine\b",
    r"\bEstablish\b",
    r"\bderive\b",
    r"\bThen\b",
    r"\bis contained\b",
    r"\bis bounded\b",
    r"\bsatisf(?:y|ies)\b",
    r"\bthere exists\b",
]


def extract_q_body(tex: str) -> str:
    """Return the content inside the first LaTeX q environment."""
    begin = tex.find("\\begin{q}")
    end = tex.find("\\end{q}")
    if begin == -1 or end == -1 or end <= begin:
        return tex
    body_start = tex.find("}", begin)
    if body_start == -1 or body_start >= end:
        return ""
    return tex[body_start + 1 : end].lstrip("\r\n")


def has_q_environment(tex: str) -> bool:
    return "\\begin{q}" in tex and "\\end{q}" in tex


def forbidden_q_phrases_in(tex: str) -> list[str]:
    """Find meta/template phrases inside a q environment.

    This deliberately does not ban ordinary theorem language such as Assume,
    Suppose, Define, Prove, compactness, regularity, convergence, or no-neck
    when those words occur as legitimate mathematics.
    """
    body = extract_q_body(tex)
    body_lower = body.lower()

    matches = [phrase for phrase in FORBIDDEN_Q_PHRASES if phrase.lower() in body_lower]
    for pattern in FORBIDDEN_Q_HEADING_PATTERNS:
        if re.search(pattern, body, flags=re.IGNORECASE):
            matches.append(pattern)
    return matches


def validate_clean_q_tex(tex: str) -> None:
    matches = forbidden_q_phrases_in(tex)
    if matches:
        raise ValueError(f"Forbidden meta/template phrase inside q environment: {matches}")


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def theorem_level_validation_errors(tex: str) -> list[str]:
    if not has_q_environment(tex):
        return ["missing q environment"]

    errors: list[str] = []
    forbidden = forbidden_q_phrases_in(tex)
    if forbidden:
        errors.append(f"forbidden meta/template text: {forbidden}")

    body = extract_q_body(tex)
    errors.extend(theorem_body_validation_errors(body))
    return errors


def theorem_body_validation_errors(body: str) -> list[str]:
    errors: list[str] = []
    if not _matches_any(DOMAIN_PATTERNS, body):
        errors.append("no explicit domain or geometric setting")
    if not _matches_any(OBJECT_CLASS_PATTERNS, body):
        errors.append("no explicit unknown object class")
    if not _matches_any(MODEL_PATTERNS, body):
        errors.append("no explicit equation, functional, energy, flow, current, varifold, or geometric object")
    if not _matches_any(ASSUMPTION_PATTERNS, body):
        errors.append("no explicit assumptions")
    if not _matches_any(CONCLUSION_PATTERNS, body):
        errors.append("no concrete conclusion")

    return errors


def validate_problem_statement_tex(path: str | Path) -> None:
    text = Path(path).read_text(encoding="utf-8")
    errors = theorem_level_validation_errors(text)
    if errors:
        raise ValueError(f"Invalid problem_statement.tex at {path}: {errors}")


def validate_selected_question_folder(folder: str | Path) -> None:
    folder_path = Path(folder)
    missing = [name for name in REQUIRED_SELECTED_FILES if not (folder_path / name).exists()]
    if missing:
        raise ValueError(f"Selected question folder {folder_path} is missing required files: {missing}")
    validate_problem_statement_tex(folder_path / "problem_statement.tex")
