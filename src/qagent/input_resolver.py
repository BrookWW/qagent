from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Any


MISSING = "not provided"


def resolve_paper_entries(raw_text: str, try_online: bool = True) -> dict[str, Any]:
    blocks = _split_blocks(raw_text)
    entries = []
    resolver_log = []
    warnings = []

    for index, block in enumerate(blocks, 1):
        entry = _parse_block(block)
        entry["source"] = "user"
        entry["match_confidence"] = "low"
        entry["possible_matches"] = []

        if try_online:
            enrichment = _enrich_online(entry)
            entry = enrichment["entry"]
            resolver_log.extend(f"Entry {index}: {line}" for line in enrichment["log"])
        else:
            resolver_log.append(f"Entry {index}: online enrichment disabled")

        if not entry["title"] or entry["title"] == MISSING:
            warnings.append(f"Entry {index}: no clear title found; inferred from first nonempty line if possible.")
        if entry["match_confidence"] == "low":
            warnings.append(f"Entry {index}: low confidence metadata match.")
        entries.append(entry)

    normalized = _to_markdown(entries)
    return {
        "normalized_markdown": normalized,
        "entries": entries,
        "resolver_log": resolver_log,
        "warnings": warnings,
    }


def _split_blocks(raw_text: str) -> list[str]:
    text = raw_text.strip()
    if not text:
        return []

    heading_matches = list(re.finditer(r"(?m)^##\s+", text))
    if heading_matches:
        blocks = []
        for i, match in enumerate(heading_matches):
            start = match.start()
            end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(text)
            block = text[start:end].strip()
            block = re.sub(r"(?m)^---\s*$", "", block).strip()
            if block:
                blocks.append(block)
        return blocks

    separator_blocks = [block.strip() for block in re.split(r"(?m)^---\s*$", text) if block.strip()]
    if len(separator_blocks) > 1:
        return separator_blocks

    paragraph_blocks = [block.strip() for block in re.split(r"\n\s*\n(?=\S)", text) if block.strip()]
    if len(paragraph_blocks) > 1:
        return paragraph_blocks

    return [text]


def _parse_block(block: str) -> dict[str, Any]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    title = _field(block, ["Title", "title", "Paper", "paper"])
    if not title:
        heading = re.search(r"(?m)^##\s+(.+)$", block)
        title = heading.group(1).strip() if heading else ""
    loose_title = _loose_quoted_title(block)
    if not title and loose_title:
        title = loose_title
    if not title and lines:
        title = re.sub(r"^[-*]\s*", "", lines[0]).strip()
        title = re.sub(r"^##\s*", "", title).strip()
    title = _clean_title(title)

    authors = _field(block, ["Authors", "Author"])
    if not authors:
        authors = _loose_authors(block)

    year = _field(block, ["Year"])
    if not year:
        year_m = re.search(r"\b(19|20)\d{2}\b", block)
        year = year_m.group(0) if year_m else ""

    doi = _field(block, ["DOI", "doi"])
    if not doi:
        doi_m = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", block)
        doi = doi_m.group(0).rstrip(".,") if doi_m else ""

    url = _field(block, ["URL", "Url", "url"])
    if not url:
        url_m = re.search(r"https?://\S+", block)
        url = url_m.group(0).rstrip(".,") if url_m else ""
    pdf_url = _field(block, ["PDF URL", "PDF", "pdf_url", "pdf"])
    arxiv_id = _arxiv_id(block)
    if arxiv_id:
        url = _arxiv_abs_url(arxiv_id)
        pdf_url = _arxiv_pdf_url(arxiv_id)
    pdf_path = _field(block, ["PDF Path", "Local PDF", "pdf_path"])
    if not pdf_path:
        pdf_path = _local_pdf_path_from_text(block)
    if not pdf_path:
        for candidate in [pdf_url, url]:
            if _looks_like_local_pdf_path(candidate):
                pdf_path = _normalize_local_pdf_path(candidate)
                break

    cvgmt_id = _field(block, ["CVGMT ID", "CVGMT", "cvgmt id"])
    if not cvgmt_id:
        cvgmt_m = re.search(r"cvgmt\.sns\.it/paper/(\d+)", block, re.I)
        cvgmt_id = cvgmt_m.group(1) if cvgmt_m else ""

    abstract = _abstract(block)
    keywords = _field(block, ["Matched keywords", "Keywords", "Key words"])

    return {
        "title": title or MISSING,
        "authors": authors or MISSING,
        "year": year or MISSING,
        "doi": doi or MISSING,
        "url": url or MISSING,
        "pdf_url": pdf_url or MISSING,
        "pdf_path": pdf_path or MISSING,
        "cvgmt_id": cvgmt_id or MISSING,
        "matched_keywords": keywords or MISSING,
        "abstract": abstract or MISSING,
        "source": "user",
        "match_confidence": "low",
        "possible_matches": [],
    }


def _field(block: str, names: list[str]) -> str:
    for name in names:
        pattern = rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(name)}\s*:(?:\*\*)?\s*(.+?)\s*$"
        match = re.search(pattern, block)
        if match:
            return match.group(1).strip()
    return ""


def _abstract(block: str) -> str:
    match = re.search(r"(?ims)^\s*(?:[-*]\s*)?(?:\*\*)?Abstract\s*:(?:\*\*)?\s*(.*)$", block)
    if not match:
        return ""
    abstract = match.group(1).strip()
    abstract = re.split(
        r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:Title|Authors?|Year|DOI|URL|CVGMT ID|Matched keywords|Keywords)\s*:(?:\*\*)?",
        abstract,
    )[0]
    return re.sub(r"\s+", " ", abstract).strip()


def _loose_quoted_title(block: str) -> str:
    match = re.search(r'"([^"]{6,})"', block)
    return match.group(1).strip() if match else ""


def _loose_authors(block: str) -> str:
    quote = re.search(r'^\s*(.+?),\s*"[^"]{6,}"', block, re.S)
    if quote:
        return re.sub(r"\s+", " ", quote.group(1)).strip()
    return ""


def _clean_title(title: str) -> str:
    title = re.sub(r"^\s*\d+\s*[\.)]\s*", "", title or "").strip()
    return re.sub(r"\s+", " ", title)


def _enrich_online(entry: dict[str, Any]) -> dict[str, Any]:
    log = []
    try:
        import requests
    except ImportError:
        return {"entry": entry, "log": ["requests is not installed; kept user metadata"]}

    if _has_local_pdf(entry):
        entry["source"] = "user+local-pdf"
        entry["match_confidence"] = "high"
        log.append("Local PDF path provided; skipped online DOI/title enrichment")
        return {"entry": entry, "log": log}

    if _repository_preferred_url(entry):
        entry["source"] = "user+repository"
        entry["match_confidence"] = "high"
        _preserve_repository_priority(entry)
        log.append("Repository URL provided; preserved arXiv/CVGMT metadata before online enrichment")
        return {"entry": entry, "log": log}

    if entry.get("cvgmt_id") not in ("", MISSING):
        entry["source"] = "user+cvgmt"
        entry["match_confidence"] = "high"
        log.append("CVGMT ID provided; preserved user metadata")
        return {"entry": entry, "log": log}

    doi = entry.get("doi")
    if doi and doi != MISSING:
        found = _crossref_by_doi(requests, doi)
        if found:
            _merge_high_confidence(entry, found)
            entry["source"] = "crossref-doi"
            entry["match_confidence"] = "high"
            log.append("DOI matched through Crossref")
            return {"entry": entry, "log": log}
        log.append("DOI lookup failed; kept user metadata")

    query = _title_query(entry)
    if not query:
        log.append("No usable title-like query for online enrichment")
        return {"entry": entry, "log": log}

    arxiv_matches = _arxiv_search(requests, query)
    if arxiv_matches:
        entry["possible_matches"] = arxiv_matches[:5]
        best_arxiv = arxiv_matches[0]
        confidence = _confidence(entry, best_arxiv)
        if confidence in {"high", "medium"}:
            _merge_high_confidence(entry, best_arxiv)
            _preserve_repository_priority(entry)
            entry["source"] = "arxiv"
            entry["match_confidence"] = "high" if confidence == "high" else "medium"
            log.append("arXiv title match found; using arXiv repository URL before publisher DOI")
            return {"entry": entry, "log": log}
        log.append("arXiv search returned only weak title matches; continuing metadata enrichment")

    matches = _openalex_search(requests, query) + _crossref_search(requests, query)
    entry["possible_matches"] = matches[:5]
    best = matches[0] if matches else None
    if not best:
        log.append("No online match found")
        return {"entry": entry, "log": log}

    confidence = _confidence(entry, best)
    entry["match_confidence"] = confidence
    if confidence == "high":
        _merge_high_confidence(entry, best)
        entry["source"] = best.get("source", "online")
        log.append("High-confidence title match; normalized metadata")
    elif confidence == "medium":
        entry["source"] = "user+possible-online-match"
        log.append("Medium-confidence online match; preserved user metadata and recorded possible matches")
    else:
        log.append("Weak online match; preserved user metadata")
    return {"entry": entry, "log": log}


def _crossref_by_doi(requests: Any, doi: str) -> dict[str, Any] | None:
    try:
        response = requests.get(f"https://api.crossref.org/works/{doi}", timeout=5)
        if response.status_code != 200:
            return None
        item = response.json().get("message", {})
        return _crossref_item(item)
    except Exception:
        return None


def _crossref_search(requests: Any, query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            "https://api.crossref.org/works",
            params={"query.title": query, "rows": 3},
            timeout=5,
        )
        if response.status_code != 200:
            return []
        return [_crossref_item(item) for item in response.json().get("message", {}).get("items", [])]
    except Exception:
        return []


def _openalex_search(requests: Any, query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": 3},
            timeout=5,
        )
        if response.status_code != 200:
            return []
        return [_openalex_item(item) for item in response.json().get("results", [])]
    except Exception:
        return []


def _arxiv_search(requests: Any, query: str) -> list[dict[str, Any]]:
    try:
        from urllib.parse import quote_plus

        url = f"https://export.arxiv.org/api/query?search_query=ti:{quote_plus(query)}&start=0&max_results=5"
        response = requests.get(url, timeout=8)
        if response.status_code != 200:
            return []
        entries = re.findall(r"(?s)<entry>(.*?)</entry>", response.text)
        return [_arxiv_item(entry) for entry in entries]
    except Exception:
        return []


def _crossref_item(item: dict[str, Any]) -> dict[str, Any]:
    year_parts = item.get("published-print", item.get("published-online", {})).get("date-parts", [[]])
    authors = []
    for author in item.get("author", [])[:8]:
        name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
        if name:
            authors.append(name)
    return {
        "title": (item.get("title") or [""])[0],
        "authors": " - ".join(authors),
        "year": str(year_parts[0][0]) if year_parts and year_parts[0] else "",
        "doi": item.get("DOI", ""),
        "url": item.get("URL", ""),
        "source": "crossref",
    }


def _openalex_item(item: dict[str, Any]) -> dict[str, Any]:
    authors = [
        authorship.get("author", {}).get("display_name", "")
        for authorship in item.get("authorships", [])[:8]
    ]
    return {
        "title": item.get("title", ""),
        "authors": " - ".join(author for author in authors if author),
        "year": str(item.get("publication_year") or ""),
        "doi": (item.get("doi") or "").replace("https://doi.org/", ""),
        "url": item.get("primary_location", {}).get("landing_page_url") or item.get("id", ""),
        "source": "openalex",
    }


def _arxiv_item(entry: str) -> dict[str, Any]:
    title = _xml_text(entry, "title")
    published = _xml_text(entry, "published")
    abs_url = _xml_text(entry, "id")
    arxiv_id = _arxiv_id(abs_url)
    authors = " - ".join(re.findall(r"(?s)<author>\s*<name>(.*?)</name>\s*</author>", entry))
    return {
        "title": re.sub(r"\s+", " ", title).strip(),
        "authors": re.sub(r"\s+", " ", authors).strip(),
        "year": published[:4],
        "doi": f"10.48550/arXiv.{arxiv_id}" if arxiv_id else "",
        "url": _arxiv_abs_url(arxiv_id) if arxiv_id else abs_url,
        "pdf_url": _arxiv_pdf_url(arxiv_id) if arxiv_id else "",
        "source": "arxiv",
    }


def _merge_high_confidence(entry: dict[str, Any], found: dict[str, Any]) -> None:
    preferred_url = _repository_preferred_url(entry)
    preferred_pdf = entry.get("pdf_url") if _repository_preferred_url({"url": entry.get("pdf_url", "")}) else ""
    for key in ["title", "authors", "year", "doi", "url", "pdf_url"]:
        if found.get(key):
            entry[key] = found[key]
    if preferred_url:
        entry["url"] = preferred_url
    if preferred_pdf:
        entry["pdf_url"] = preferred_pdf
    _preserve_repository_priority(entry)


def _title_query(entry: dict[str, Any]) -> str:
    title = _clean_title(entry.get("title", ""))
    if title and title != MISSING:
        return title
    return ""


def _confidence(entry: dict[str, Any], match: dict[str, Any]) -> str:
    user_title = _clean_title(entry.get("title", ""))
    found_title = match.get("title", "")
    ratio = SequenceMatcher(None, _norm(user_title), _norm(found_title)).ratio()
    year_overlap = entry.get("year") not in ("", MISSING) and entry.get("year") == match.get("year")
    author_overlap = _author_overlap(entry.get("authors", ""), match.get("authors", ""))
    if ratio > 0.96:
        return "high"
    if ratio > 0.92 and (year_overlap or author_overlap):
        return "high"
    if ratio > 0.82:
        return "medium"
    return "low"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _author_overlap(a: str, b: str) -> bool:
    if a in ("", MISSING) or b in ("", MISSING):
        return False
    a_tokens = set(_norm(a).split())
    b_tokens = set(_norm(b).split())
    return bool(a_tokens & b_tokens)


def _xml_text(text: str, tag: str) -> str:
    match = re.search(rf"(?s)<{tag}>(.*?)</{tag}>", text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _arxiv_id(text: str) -> str:
    value = str(text or "")
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"\barxiv\s*:\s*([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"\b10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"arxiv\.org/(?:abs|pdf)/([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
        r"\barxiv\s*:\s*([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
        r"\b10\.48550/arxiv\.([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _arxiv_abs_url(arxiv_id: str) -> str:
    clean = re.sub(r"v\d+$", "", str(arxiv_id).strip(), flags=re.IGNORECASE)
    return f"https://arxiv.org/abs/{clean}" if clean else ""


def _arxiv_pdf_url(arxiv_id: str) -> str:
    clean = re.sub(r"v\d+$", "", str(arxiv_id).strip(), flags=re.IGNORECASE)
    return f"https://arxiv.org/pdf/{clean}.pdf" if clean else ""


def _repository_preferred_url(entry: dict[str, Any]) -> str:
    text = " ".join(str(entry.get(key, "")) for key in ["url", "pdf_url", "doi", "cvgmt_id"])
    arxiv_id = _arxiv_id(text)
    if arxiv_id:
        return _arxiv_abs_url(arxiv_id)
    cvgmt_id = str(entry.get("cvgmt_id", "")).strip()
    if cvgmt_id and cvgmt_id != MISSING:
        return f"https://cvgmt.sns.it/paper/{cvgmt_id}/"
    cvgmt_match = re.search(r"cvgmt\.sns\.it/paper/(\d+)", text, re.I)
    if cvgmt_match:
        return f"https://cvgmt.sns.it/paper/{cvgmt_match.group(1)}/"
    return ""


def _has_local_pdf(entry: dict[str, Any]) -> bool:
    for key in ["pdf_path", "pdf_url", "url"]:
        if _looks_like_local_pdf_path(str(entry.get(key, ""))):
            entry["pdf_path"] = _normalize_local_pdf_path(str(entry.get(key, "")))
            return True
    return False


def _local_pdf_path_from_text(text: str) -> str:
    patterns = [
        r"file:///[A-Za-z]:/[^ \n\r\t]+?\.pdf",
        r"file://[^ \n\r\t]+?\.pdf",
        r"[A-Za-z]:\\[^ \n\r\t]+?\.pdf",
        r"/mnt/[a-zA-Z]/[^ \n\r\t]+?\.pdf",
        r"/[^ \n\r\t]+?\.pdf",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _normalize_local_pdf_path(match.group(0).rstrip(".,);]\"'"))
    return ""


def _looks_like_local_pdf_path(value: str) -> bool:
    text = str(value or "").strip().strip("<>")
    if not text.lower().endswith(".pdf"):
        return False
    if re.match(r"(?i)^https?://", text):
        return False
    return bool(
        re.match(r"(?i)^file://", text)
        or re.match(r"^[A-Za-z]:[\\/]", text)
        or text.startswith("/mnt/")
        or text.startswith("/")
    )


def _normalize_local_pdf_path(value: str) -> str:
    text = str(value or "").strip().strip("<>").rstrip(".,);]\"'")
    if text.lower().startswith("file:///"):
        text = text[8:]
        if re.match(r"^[A-Za-z]:/", text):
            text = text.replace("/", "\\")
        return text
    if text.lower().startswith("file://"):
        return text[7:]
    return text


def _preserve_repository_priority(entry: dict[str, Any]) -> None:
    arxiv_id = _arxiv_id(" ".join(str(entry.get(key, "")) for key in ["url", "pdf_url", "doi"]))
    if arxiv_id:
        entry["url"] = _arxiv_abs_url(arxiv_id)
        entry["pdf_url"] = _arxiv_pdf_url(arxiv_id)
        return
    cvgmt_url = _repository_preferred_url(entry)
    if cvgmt_url and "cvgmt.sns.it" in cvgmt_url:
        entry["url"] = cvgmt_url


def _to_markdown(entries: list[dict[str, Any]]) -> str:
    chunks = []
    for entry in entries:
        chunks.append(
            "\n".join(
                [
                    f"## {entry.get('title') or MISSING}",
                    "",
                    f"- **CVGMT ID:** {entry.get('cvgmt_id') or MISSING}",
                    f"- **Authors:** {entry.get('authors') or MISSING}",
                    f"- **Year:** {entry.get('year') or MISSING}",
                    f"- **DOI:** {entry.get('doi') or MISSING}",
                    f"- **URL:** {entry.get('url') or MISSING}",
                    f"- **PDF URL:** {entry.get('pdf_url') or MISSING}",
                    f"- **PDF Path:** {entry.get('pdf_path') or MISSING}",
                    f"- **Matched keywords:** {entry.get('matched_keywords') or MISSING}",
                    f"- **Source:** {entry.get('source') or MISSING}",
                    f"- **Match confidence:** {entry.get('match_confidence') or MISSING}",
                    "",
                    "**Abstract:**",
                    "",
                    entry.get("abstract") or MISSING,
                ]
            )
        )
    return "\n\n---\n\n".join(chunks) + ("\n" if chunks else "")
