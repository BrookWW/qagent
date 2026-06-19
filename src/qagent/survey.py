from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import os
import re

from .runner import run_codex_cli


SURVEY_SOURCES = ("Crossref", "OpenAlex", "arXiv", "Semantic Scholar")
SURVEY_ROWS_PER_QUERY = 5


def _survey_headers() -> dict[str, str]:
    email = os.environ.get("QAGENT_SURVEY_EMAIL", "qagent@example.invalid")
    return {
        "User-Agent": f"QAgent/0.1 (mailto:{email})",
        "Accept": "application/json, application/atom+xml, text/xml, */*",
    }


@dataclass
class SurveyResult:
    question_id: str
    search_queries: list[str]
    nearby_papers: list[dict[str, Any]]
    classification: str
    duplicate_risk: str
    recommended_action: str
    novelty_verdict: str
    detailed_novelty_comparison: str
    log: list[str]
    directly_applicable_theorems: list[dict[str, Any]] = field(default_factory=list)
    killer_theorem_attempt: str = ""
    direct_corollary_check: str = ""
    counterexamples_and_pitfalls: list[str] = field(default_factory=list)
    self_verification: dict[str, Any] = field(default_factory=dict)
    survey_confidence: str = "unknown"
    search_backend: str = "local metadata survey"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def survey_candidate(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str = "batch_001",
    try_online: bool = True,
    timeout: int = 8,
) -> SurveyResult:
    if try_online:
        qed_result = survey_candidate_qed_style(candidate, paper_entry, batch_id=batch_id)
        if qed_result is not None:
            return qed_result
    return survey_candidate_local(candidate, paper_entry, batch_id=batch_id, try_online=try_online, timeout=timeout)


def survey_candidate_local(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str = "batch_001",
    try_online: bool = True,
    timeout: int = 8,
) -> SurveyResult:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    queries = generate_search_queries(candidate, paper_entry)
    nearby: list[dict[str, Any]] = []
    log: list[str] = []

    nearby.extend(_local_metadata_matches(candidate, paper_entry))
    if try_online:
        log.append("online survey enabled")
        try:
            import requests

            session = requests.Session()
            session.headers.update(_survey_headers())
            external_before = len(nearby)
            source_counts = {source: 0 for source in SURVEY_SOURCES}
            for query in queries:
                for source, search_fn in [
                    ("Crossref", _crossref_search),
                    ("OpenAlex", _openalex_search),
                    ("arXiv", _arxiv_search),
                    ("Semantic Scholar", _semantic_scholar_search),
                ]:
                    items, source_log = search_fn(session, query, timeout)
                    source_counts[source] += len(items)
                    nearby.extend(items)
                    log.extend(source_log)
            external_hits = max(0, len(nearby) - external_before)
            source_summary = ", ".join(f"{source}: {count}" for source, count in source_counts.items())
            log.append(f"online survey attempted {len(queries)} queries across {', '.join(SURVEY_SOURCES)}")
            log.append(f"online survey source hit counts before dedupe: {source_summary}")
            log.append(f"online survey external hits before dedupe: {external_hits}")
        except ImportError:
            log.append("requests is not installed; online survey skipped")
        except Exception as exc:
            log.append(f"online survey failed before completion: {type(exc).__name__}: {exc}")
    else:
        log.append("online survey disabled")

    nearby = _dedupe_papers(nearby)
    if try_online:
        external_after = sum(1 for item in nearby if item.get("source") != "local resolved paper metadata")
        log.append(f"online survey external hits after dedupe: {external_after}")
        if external_after == 0:
            log.append("online survey produced no external metadata hits; check network access, API availability, or query specificity")
    classification, risk, action, novelty_verdict, novelty_comparison = classify_duplicate_risk(candidate, paper_entry, nearby)
    result = SurveyResult(
        question_id,
        queries,
        nearby[:30],
        classification,
        risk,
        action,
        novelty_verdict,
        novelty_comparison,
        log,
        survey_confidence="medium" if nearby else "low",
        search_backend="local metadata survey",
    )
    write_candidate_survey(result, paper_entry, batch_id)
    return result


def survey_candidate_qed_style(
    candidate: dict[str, Any],
    paper_entry: dict[str, Any],
    batch_id: str = "batch_001",
) -> SurveyResult | None:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    prompt = build_qed_candidate_survey_prompt(candidate, paper_entry, batch_id)
    result = run_codex_cli(prompt, model="gpt-5.5", use_search=True, reasoning_effort="xhigh")
    out_dir = Path("outputs") / batch_id / paper_id / "candidate_surveys"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_log = out_dir / f"{question_id}.run_log.txt"
    run_log.write_text(
        "\n".join(
            [
                "# QED-style Candidate Survey Run Log",
                "",
                f"Command: {result.get('command', '')}",
                f"Return code: {result.get('return_code', '')}",
                f"Error: {result.get('error_message', '')}",
                "",
                "## STDOUT",
                result.get("stdout", ""),
                "",
                "## STDERR",
                result.get("stderr", ""),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if not result.get("ok"):
        return None

    data = _extract_json_object(result.get("stdout", ""))
    if not _valid_qed_survey(data, question_id):
        return None

    json_path = out_dir / f"{question_id}.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    survey = _survey_result_from_qed_json(data)
    write_candidate_survey(survey, paper_entry, batch_id)
    return survey


def build_qed_candidate_survey_prompt(candidate: dict[str, Any], paper_entry: dict[str, Any], batch_id: str) -> str:
    question_id = str(candidate.get("question_id") or candidate.get("id") or "candidate")
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    paper_dir = Path("outputs") / batch_id / paper_id
    paper_survey = _read_json(paper_dir / "paper_literature_survey.json") or {}
    profile = _read_json(paper_dir / "paper_profile.json") or paper_entry
    theorem_cards = _read_json(paper_dir / "theorem_cards.json") or []
    return f"""Please run QAgent QED-style candidate literature survey only.

Scope:
- Work only under `outputs/{batch_id}/{paper_id}/candidate_surveys/`.
- Do not modify candidate_questions.json, ranked_questions.json, selected folders, hard_review, or final outputs.
- Return JSON only in your final response. Do not wrap it in Markdown.

Goal:
Evaluate whether this single candidate research question has already been done, is too close to an existing theorem, or is killed by a directly applicable known result. This is a novelty-search gate, not a literature-review essay. Keep the report short, adversarial, and evidence-focused.

Search requirements:
- Use Codex search. Search arXiv, CVGMT, OpenAlex, Semantic Scholar, Crossref, MathOverflow, Wikipedia/textbook references, and the general web when available.
- Do not scrape Google Scholar.
- Search exact candidate title, theorem keywords, model equation, conclusion phrase, input paper title + extension, target model + conclusion, and key proof mechanism.
- Verify titles/authors/URLs/theorem statements. Remove unverifiable citations.
- Prioritize finding a killer known theorem or a very similar paper over broad related work.

Required JSON schema:
{{
  "question_id": "{question_id}",
  "search_queries": ["..."],
  "related_papers": [
    {{"title": "...", "authors": "...", "year": "...", "source": "...", "url": "...", "relationship": "..."}}
  ],
  "directly_applicable_theorems": [
    {{"theorem_name": "...", "precise_statement": "...", "source": "...", "url": "...", "candidate_direction_killed": "..."}}
  ],
  "killer_theorem_attempt": "...",
  "direct_corollary_check": "...",
  "counterexamples_and_pitfalls": ["only include if it affects duplicate/known-result risk"],
  "duplicate_risk": "low | medium | high | unknown",
  "novelty_verdict": "new enough | direct corollary | likely known | too close to input theorem | insufficient evidence",
  "recommended_action": "keep | revise | remove",
  "classification": "plausible new theorem-level question | plausible new transfer problem | known theorem or likely known theorem | direct restatement of input paper | module of known theorem | insufficient novelty evidence",
  "detailed_novelty_comparison": "closest known result, exact overlap, exact surviving difference, and final duplicate-risk reason",
  "self_verification": {{
    "entries_checked": 0,
    "entries_removed_after_verification": [],
    "source_inaccessible_caveats": [],
    "confidence_in_remaining_entries": "high | medium | low"
  }}
}}

Hard rules:
- If a theorem directly implies the candidate, use novelty_verdict `direct corollary`, duplicate_risk `high`, recommended_action `remove`.
- If the candidate is too close to the input paper's theorem/proof module, use recommended_action `remove`.
- If search was inconclusive, use `insufficient evidence` or `revise`, not confident keep.
- Keep only when there is a concrete non-cosmetic difference and no killer theorem survives.
- Do not spend tokens explaining general motivation, proof taste, or broad related work unless it directly changes duplicate risk.

Input paper profile:
```json
{json.dumps(profile, ensure_ascii=False, indent=2)}
```

Paper-level survey:
```json
{json.dumps(paper_survey, ensure_ascii=False, indent=2)}
```

Theorem cards:
```json
{json.dumps(theorem_cards, ensure_ascii=False, indent=2)}
```

Candidate:
```json
{json.dumps(candidate, ensure_ascii=False, indent=2)}
```"""


def generate_search_queries(candidate: dict[str, Any], paper_entry: dict[str, Any]) -> list[str]:
    title = str(candidate.get("title", "")).strip()
    problem = str(candidate.get("precise_problem_statement", "")).strip()
    paper_title = str(paper_entry.get("title", "")).strip()
    authors = str(paper_entry.get("authors", "")).strip()
    year = str(paper_entry.get("year", "")).strip()
    doi = str(paper_entry.get("doi", "")).strip()
    keywords = str(paper_entry.get("matched_keywords", paper_entry.get("keywords", ""))).strip()
    mechanisms = " ".join(candidate.get("mechanism_labels", [])) if isinstance(candidate.get("mechanism_labels"), list) else ""
    expected_tools = _candidate_field_text(candidate, ["expected_tools", "key_estimate_to_prove", "source_theorem_or_method"])
    obstruction = _candidate_field_text(candidate, ["new_obstruction", "possible_obstacles", "method_delta"])
    theorem_type = _candidate_field_text(candidate, ["classification", "question_type", "theorem_type"])
    raw = [
        doi if doi.lower() not in {"", "not provided"} else "",
        f'"{paper_title}"' if paper_title else "",
        f'"{title}"' if title else "",
        title,
        f"{title} {paper_title}",
        f"{title} {authors} {year}",
        f"{title} {keywords}",
        f"{title} {expected_tools}",
        f"{title} {obstruction}",
        f"{keywords} {theorem_type} {expected_tools}",
        f"{paper_title} {mechanisms}",
        f"{paper_title} {title} proposed extension",
        f"{paper_title} {authors} related theorem",
        _first_words(problem, 12),
        f"{title} already known theorem",
        f"{title} arXiv",
        f"{title} CVGMT",
        f"{paper_title} extension novelty",
        f"{paper_title} small perturbation method",
        f"{keywords} theorem transfer problem",
        f"{paper_title} duplicate theorem",
    ]
    queries = []
    for query in raw:
        clean = re.sub(r"\s+", " ", query).strip()
        if clean and clean not in queries:
            queries.append(clean)
    return queries[:10]


def _extract_json_object(text: str) -> Any:
    text = str(text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _valid_qed_survey(data: Any, question_id: str) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("question_id", "")).strip() != question_id:
        return False
    if str(data.get("duplicate_risk", "")).strip().lower() not in {"low", "medium", "high", "unknown"}:
        return False
    if str(data.get("recommended_action", "")).strip().lower() not in {"keep", "revise", "remove"}:
        return False
    if not str(data.get("novelty_verdict", "")).strip():
        return False
    return isinstance(data.get("search_queries"), list) and isinstance(data.get("related_papers"), list)


def _survey_result_from_qed_json(data: dict[str, Any]) -> SurveyResult:
    novelty = str(data.get("novelty_verdict", "")).strip().lower()
    normalized_novelty = {
        "new enough": "new enough",
        "direct corollary": "too close to input theorem",
        "likely known": "probably already known",
        "too close to input theorem": "too close to input theorem",
        "insufficient evidence": "insufficient evidence",
    }.get(novelty, str(data.get("novelty_verdict", "insufficient evidence")))
    comparison = str(data.get("detailed_novelty_comparison", "")).strip()
    if not comparison:
        comparison = (
            f"Killer theorem attempt: {data.get('killer_theorem_attempt', '')}. "
            f"Direct corollary check: {data.get('direct_corollary_check', '')}."
        )
    log = [
        "QED-style Codex candidate survey completed with --search, gpt-5.5, xhigh reasoning.",
        f"Self verification: {data.get('self_verification', {})}",
    ]
    return SurveyResult(
        question_id=str(data.get("question_id", "")).strip(),
        search_queries=[str(item) for item in data.get("search_queries", [])],
        nearby_papers=[item for item in data.get("related_papers", []) if isinstance(item, dict)],
        classification=str(data.get("classification", "insufficient novelty evidence")),
        duplicate_risk=str(data.get("duplicate_risk", "unknown")).lower(),
        recommended_action=str(data.get("recommended_action", "revise")).lower(),
        novelty_verdict=normalized_novelty,
        detailed_novelty_comparison=comparison,
        log=log,
        directly_applicable_theorems=[
            item for item in data.get("directly_applicable_theorems", []) if isinstance(item, dict)
        ],
        killer_theorem_attempt=str(data.get("killer_theorem_attempt", "")).strip(),
        direct_corollary_check=str(data.get("direct_corollary_check", "")).strip(),
        counterexamples_and_pitfalls=[str(item) for item in data.get("counterexamples_and_pitfalls", [])],
        self_verification=data.get("self_verification", {}) if isinstance(data.get("self_verification"), dict) else {},
        survey_confidence=str(
            (data.get("self_verification", {}) if isinstance(data.get("self_verification"), dict) else {}).get(
                "confidence_in_remaining_entries", "unknown"
            )
        ).lower(),
        search_backend="qed-style codex --search",
    )


def write_candidate_survey(result: SurveyResult, paper_entry: dict[str, Any], batch_id: str) -> Path:
    paper_id = str(paper_entry.get("paper_id") or _paper_id(paper_entry))
    out_dir = Path("outputs") / batch_id / paper_id / "candidate_surveys"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.question_id}.md"
    lines = [
        f"# Candidate Survey: {result.question_id}",
        "",
        "## Search queries used",
        "",
        *[f"- {query}" for query in result.search_queries],
        "",
        "## Nearby papers found",
        "",
    ]
    if result.nearby_papers:
        for paper in result.nearby_papers:
            lines.extend(
                [
                    f"- **{paper.get('title', 'untitled')}**",
                    f"  - Authors: {paper.get('authors', 'not provided')}",
                    f"  - Year: {paper.get('year', 'not provided')}",
                    f"  - Source: {paper.get('source', 'not provided')}",
                    f"  - URL/DOI: {paper.get('url', paper.get('doi', 'not provided'))}",
                ]
            )
    else:
        lines.append("- No nearby papers found by the available metadata sources.")
    lines.extend(
        [
            "",
            "## Classification",
            "",
            f"- Candidate looks like: {result.classification}",
            f"- Duplicate risk: {result.duplicate_risk}",
            f"- Recommended action: {result.recommended_action}",
            f"- Novelty verdict: {result.novelty_verdict}",
            f"- Survey confidence: {result.survey_confidence}",
            f"- Search backend: {result.search_backend}",
            "",
            "## Detailed novelty comparison",
            "",
            result.detailed_novelty_comparison,
            "",
            "## Directly Applicable Theorems",
            "",
            *_format_applicable_theorems(result.directly_applicable_theorems),
            "",
            "## Killer Theorem Attempt",
            "",
            result.killer_theorem_attempt or "No killer theorem attempt recorded.",
            "",
            "## Direct Corollary Check",
            "",
            result.direct_corollary_check or "No direct corollary check recorded.",
            "",
            "## Counterexamples And Pitfalls",
            "",
            *_format_list(result.counterexamples_and_pitfalls, "No pitfalls recorded."),
            "",
            "## Self Verification",
            "",
            json.dumps(result.self_verification, indent=2, ensure_ascii=False),
            "",
            "## Log",
            "",
            *[f"- {line}" for line in result.log],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _format_applicable_theorems(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- None recorded."]
    rows = []
    for item in items[:10]:
        name = str(item.get("theorem_name", "") or item.get("title", "") or "unnamed theorem").strip()
        source = str(item.get("source", "")).strip()
        killed = str(item.get("candidate_direction_killed", "")).strip()
        statement = str(item.get("precise_statement", "")).strip()
        url = str(item.get("url", "")).strip()
        detail = "; ".join(part for part in [source, url, f"kills: {killed}" if killed else "", statement] if part)
        rows.append(f"- {name}: {detail}" if detail else f"- {name}")
    return rows


def _format_list(items: list[str], empty: str) -> list[str]:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return [f"- {empty}"]
    return [f"- {item}" for item in values[:12]]


def classify_duplicate_risk(candidate: dict[str, Any], paper_entry: dict[str, Any], nearby: list[dict[str, Any]]) -> tuple[str, str, str, str, str]:
    candidate_title = str(candidate.get("title", ""))
    paper_title = str(paper_entry.get("title", ""))
    statement = str(candidate.get("precise_problem_statement", ""))
    candidate_text = f"{candidate_title} {statement}"
    novelty_text = str(candidate.get("novelty_assessment", ""))
    method_delta = str(candidate.get("method_delta", ""))
    fast_route = str(candidate.get("fast_sci_route", ""))
    journal_fit = str(candidate.get("journal_fit", ""))
    closest = _closest_title(candidate_title, nearby)
    comparison = (
        f"Input theorem/title comparison: candidate title similarity to input title is "
        f"{_similar(candidate_title, paper_title):.2f}. Closest external title: "
        f"{closest[0] or 'none'} (similarity {closest[1]:.2f}). "
        f"Candidate novelty assessment: {novelty_text or 'missing'}. "
        f"Method delta: {method_delta or 'missing'}. Fast SCI route: {fast_route or 'missing'}. "
        f"Journal fit: {journal_fit or 'missing'}."
    )
    if _similar(candidate_title, paper_title) > 0.82 or "match the hypotheses" in statement.lower():
        return "direct restatement of input paper", "high", "remove", "too close to input theorem", comparison
    if closest[1] > 0.86:
        return "known theorem or likely known theorem", "high", "remove", "probably already known", comparison
    if _missing_novelty_fields(novelty_text, method_delta, fast_route, journal_fit):
        return "insufficient novelty evidence", "medium", "revise", "insufficient evidence", comparison
    if _too_big_or_too_easy(candidate_text, method_delta, fast_route):
        return "poor short-SCI fit", "medium", "remove", "insufficient evidence", comparison
    if any(term in candidate_title.lower() for term in ["identity", "lemma", "module", "first variation"]):
        return "module of known theorem", "medium", "revise", "insufficient evidence", comparison
    if any(label in " ".join(candidate.get("mechanism_labels", [])).lower() for label in ["analogy", "generalization", "transfer"]):
        return "plausible new transfer problem", "low", "keep", "new enough", comparison
    if len(nearby) > 8:
        return "possible known theorem", "medium", "revise", "insufficient evidence", comparison
    return "plausible new theorem-level question", "low", "keep", "new enough", comparison


def _closest_title(candidate_title: str, nearby: list[dict[str, Any]]) -> tuple[str, float]:
    best_title = ""
    best_score = 0.0
    for item in nearby:
        title = str(item.get("title", ""))
        score = _similar(candidate_title, title)
        if score > best_score:
            best_title = title
            best_score = score
    return best_title, best_score


def _missing_novelty_fields(novelty: str, method_delta: str, fast_route: str, journal_fit: str) -> bool:
    return not all(text.strip() and text.strip().lower() not in {"not provided", "unknown"} for text in [novelty, method_delta, fast_route, journal_fit])


def _too_big_or_too_easy(text: str, method_delta: str, fast_route: str) -> bool:
    lower = f"{text} {method_delta} {fast_route}".lower()
    too_big = ["major new theory", "fully classify", "complete classification", "all dimensions", "arbitrary nonlinear"]
    too_easy = ["direct corollary", "apply known theorem", "immediate consequence", "notation change"]
    return any(phrase in lower for phrase in too_big + too_easy)


def _local_metadata_matches(candidate: dict[str, Any], paper_entry: dict[str, Any]) -> list[dict[str, Any]]:
    title = str(paper_entry.get("title", ""))
    if not title:
        return []
    return [
        {
            "title": title,
            "authors": paper_entry.get("authors", ""),
            "year": paper_entry.get("year", ""),
            "source": "local resolved paper metadata",
            "url": paper_entry.get("url", ""),
        }
    ]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _crossref_search(session: Any, query: str, timeout: int) -> tuple[list[dict[str, Any]], list[str]]:
    log: list[str] = []
    try:
        params = {"query.title": query, "rows": SURVEY_ROWS_PER_QUERY}
        response = session.get("https://api.crossref.org/works", params=params, timeout=timeout)
        if response.status_code != 200:
            log.append(f"Crossref query {_short_query(query)!r} returned HTTP {response.status_code}")
            return [], log
        items = response.json().get("message", {}).get("items", [])
        if not items:
            params = {"query.bibliographic": query, "rows": SURVEY_ROWS_PER_QUERY}
            response = session.get("https://api.crossref.org/works", params=params, timeout=timeout)
            if response.status_code != 200:
                log.append(f"Crossref bibliographic query {_short_query(query)!r} returned HTTP {response.status_code}")
                return [], log
            items = response.json().get("message", {}).get("items", [])
        log.append(f"Crossref query {_short_query(query)!r} returned {len(items)} hits")
        return [_crossref_item(item) for item in items], log
    except Exception as exc:
        log.append(f"Crossref query {_short_query(query)!r} failed: {type(exc).__name__}: {exc}")
        return [], log


def _openalex_search(session: Any, query: str, timeout: int) -> tuple[list[dict[str, Any]], list[str]]:
    log: list[str] = []
    try:
        response = session.get("https://api.openalex.org/works", params={"search": query, "per-page": SURVEY_ROWS_PER_QUERY}, timeout=timeout)
        if response.status_code != 200:
            log.append(f"OpenAlex query {_short_query(query)!r} returned HTTP {response.status_code}")
            return [], log
        items = response.json().get("results", [])
        log.append(f"OpenAlex query {_short_query(query)!r} returned {len(items)} hits")
        return [_openalex_item(item) for item in items], log
    except Exception as exc:
        log.append(f"OpenAlex query {_short_query(query)!r} failed: {type(exc).__name__}: {exc}")
        return [], log


def _arxiv_search(session: Any, query: str, timeout: int) -> tuple[list[dict[str, Any]], list[str]]:
    log: list[str] = []
    try:
        url = f"https://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&start=0&max_results={SURVEY_ROWS_PER_QUERY}"
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            log.append(f"arXiv query {_short_query(query)!r} returned HTTP {response.status_code}")
            return [], log
        entries = re.findall(r"(?s)<entry>(.*?)</entry>", response.text)
        log.append(f"arXiv query {_short_query(query)!r} returned {len(entries)} hits")
        return [_arxiv_item(entry) for entry in entries], log
    except Exception as exc:
        log.append(f"arXiv query {_short_query(query)!r} failed: {type(exc).__name__}: {exc}")
        return [], log


def _semantic_scholar_search(session: Any, query: str, timeout: int) -> tuple[list[dict[str, Any]], list[str]]:
    log: list[str] = []
    try:
        response = session.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": SURVEY_ROWS_PER_QUERY, "fields": "title,authors,year,url"},
            timeout=timeout,
        )
        if response.status_code != 200:
            log.append(f"Semantic Scholar query {_short_query(query)!r} returned HTTP {response.status_code}")
            return [], log
        items = response.json().get("data", [])
        log.append(f"Semantic Scholar query {_short_query(query)!r} returned {len(items)} hits")
        return [_semantic_item(item) for item in items], log
    except Exception as exc:
        log.append(f"Semantic Scholar query {_short_query(query)!r} failed: {type(exc).__name__}: {exc}")
        return [], log


def _crossref_item(item: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for author in item.get("author", [])[:6]:
        name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
        if name:
            authors.append(name)
    years = item.get("published-print", item.get("published-online", {})).get("date-parts", [[]])
    return {
        "title": (item.get("title") or [""])[0],
        "authors": " - ".join(authors),
        "year": str(years[0][0]) if years and years[0] else "",
        "doi": item.get("DOI", ""),
        "url": item.get("URL", ""),
        "source": "Crossref",
    }


def _openalex_item(item: dict[str, Any]) -> dict[str, Any]:
    authors = [authorship.get("author", {}).get("display_name", "") for authorship in item.get("authorships", [])[:6]]
    return {
        "title": item.get("title", ""),
        "authors": " - ".join(author for author in authors if author),
        "year": str(item.get("publication_year") or ""),
        "url": item.get("primary_location", {}).get("landing_page_url") or item.get("id", ""),
        "source": "OpenAlex",
    }


def _arxiv_item(entry: str) -> dict[str, Any]:
    title = _xml_text(entry, "title")
    year = _xml_text(entry, "published")[:4]
    authors = " - ".join(re.findall(r"(?s)<author>\s*<name>(.*?)</name>\s*</author>", entry))
    return {"title": title, "authors": authors, "year": year, "url": _xml_text(entry, "id"), "source": "arXiv"}


def _semantic_item(item: dict[str, Any]) -> dict[str, Any]:
    authors = " - ".join(author.get("name", "") for author in item.get("authors", [])[:6])
    return {"title": item.get("title", ""), "authors": authors, "year": str(item.get("year") or ""), "url": item.get("url", ""), "source": "Semantic Scholar"}


def _xml_text(text: str, tag: str) -> str:
    match = re.search(rf"(?s)<{tag}>(.*?)</{tag}>", text)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for paper in papers:
        key = re.sub(r"[^a-z0-9]+", " ", str(paper.get("title", "")).lower()).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(paper)
    return out


def _similar(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _first_words(text: str, count: int) -> str:
    return " ".join(text.split()[:count])


def _candidate_field_text(candidate: dict[str, Any], keys: list[str]) -> str:
    chunks = []
    for key in keys:
        value = candidate.get(key, "")
        if isinstance(value, list):
            chunks.extend(str(item) for item in value)
        elif isinstance(value, dict):
            chunks.extend(str(item) for item in value.values())
        else:
            chunks.append(str(value))
    return " ".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())[:240]


def _short_query(query: str, limit: int = 90) -> str:
    query = re.sub(r"\s+", " ", query).strip()
    return query if len(query) <= limit else query[: limit - 3] + "..."


def _paper_id(entry: dict[str, Any]) -> str:
    cvgmt = str(entry.get("cvgmt_id", "")).strip()
    if cvgmt and cvgmt != "not provided":
        return f"cvgmt_{cvgmt}"
    title = str(entry.get("title", "paper"))
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:80] or "paper"
