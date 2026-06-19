from __future__ import annotations

from dataclasses import dataclass, asdict
from html import unescape
import hashlib
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import urljoin, urlparse


PDF_DIR = Path("data") / "pdfs"
MIN_PDF_BYTES = 10_000
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) QAgent/0.1"
    )
}


@dataclass
class FetchResult:
    paper_id: str
    cache_key: str
    source_type: str
    source_url: str
    pdf_path: str
    html_text: str
    confidence: str
    log: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_best_source(
    entry: dict[str, Any],
    try_online: bool = True,
    timeout: int = 10,
    cache_key: str | None = None,
) -> FetchResult:
    paper_id = entry.get("paper_id") or _paper_id(entry)
    cache_key = cache_key or _source_cache_key(entry, paper_id)
    log: list[str] = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    pdf_urls = _candidate_pdf_urls(entry)
    pdf_path = PDF_DIR / f"{cache_key}.pdf"
    repository_name, repository_urls = _repository_priority_pdf_urls(entry)
    if try_online and repository_urls:
        log.append(f"Repository priority source: {repository_name}")
        try:
            import requests

            downloaded_url = _download_first_valid_pdf(requests, repository_urls, pdf_path, timeout, log)
            if downloaded_url:
                return FetchResult(
                    paper_id,
                    cache_key,
                    "pdf",
                    downloaded_url,
                    str(pdf_path),
                    "",
                    "high",
                    log + [f"Downloaded repository PDF from {downloaded_url}"],
                )
        except ImportError:
            log.append("requests is not installed; repository PDF fetching skipped")
        except Exception as exc:
            log.append(f"Repository PDF fetch failed: {exc}")

    local_pdf = _local_pdf_from_entry(entry)
    if local_pdf and local_pdf != "not provided":
        tried_paths: list[str] = []
        source_path = _resolve_existing_local_pdf_path(local_pdf, tried_paths)
        if source_path is not None:
            if source_path.resolve() != pdf_path.resolve():
                shutil.copyfile(source_path, pdf_path)
            else:
                log.append(f"Local PDF is already in cache path: {source_path}")
            if _valid_cached_pdf(pdf_path):
                return FetchResult(
                    paper_id,
                    cache_key,
                    "pdf",
                    source_path.as_posix(),
                    str(pdf_path),
                    "",
                    "high",
                    log + [f"Using local PDF from {source_path}"],
                )
            pdf_path.unlink(missing_ok=True)
            log.append(f"Local PDF path was not a valid PDF: {source_path}")
        else:
            log.append(f"Local PDF path not found. Tried: {', '.join(tried_paths) or local_pdf}")
    if _valid_cached_pdf(pdf_path):
        return FetchResult(
            paper_id,
            cache_key,
            "cached_pdf",
            pdf_urls[0] if pdf_urls else "",
            str(pdf_path),
            "",
            "high",
            log + ["Using cached PDF"],
        )
    if pdf_path.exists():
        log.append(f"Ignoring invalid cached PDF at {pdf_path}")

    if try_online:
        try:
            import requests

            enriched = _metadata_pdf_candidates(requests, entry, timeout)
            for url in enriched:
                if url not in pdf_urls:
                    pdf_urls.append(url)
            if enriched:
                log.append(f"Added {len(enriched)} PDF/link candidate(s) from Crossref/OpenAlex metadata")

            html_url = _field(entry, "url")
            if html_url and html_url != "not provided":
                html_response = _get(requests, html_url, timeout)
                if html_response is not None:
                    content_type = html_response.headers.get("content-type", "").lower()
                    if _is_pdf_response(html_response, content_type):
                        pdf_path.write_bytes(html_response.content)
                        if _valid_cached_pdf(pdf_path):
                            return FetchResult(paper_id, cache_key, "pdf", html_url, str(pdf_path), "", "high", [f"Downloaded PDF from {html_url}"])
                        pdf_path.unlink(missing_ok=True)
                        log.append(f"Rejected invalid PDF response from {html_url}")
                    if "text/html" in content_type or "<html" in html_response.text[:500].lower():
                        discovered = _discover_pdf_urls_from_html(html_response.text, html_url)
                        discovered.extend(_publisher_pdf_candidates_from_html(html_response.text, html_url))
                        for url in discovered:
                            if url not in pdf_urls:
                                pdf_urls.append(url)
                        if discovered:
                            log.append(f"Discovered {len(discovered)} PDF link(s) from HTML page {html_url}")
        except ImportError:
            log.append("requests is not installed; online fetching skipped")
        except Exception as exc:
            log.append(f"HTML/PDF discovery failed: {exc}")

    if try_online and pdf_urls:
        try:
            import requests

            for pdf_url in pdf_urls[:16]:
                downloaded_url = _download_first_valid_pdf(requests, [pdf_url], pdf_path, timeout, log, discovery_pool=pdf_urls)
                if downloaded_url:
                    return FetchResult(paper_id, cache_key, "pdf", downloaded_url, str(pdf_path), "", "high", log + [f"Downloaded PDF from {downloaded_url}"])
        except ImportError:
            log.append("requests is not installed; could not download PDF candidates")
        except Exception as exc:
            log.append(f"PDF fetch loop failed: {exc}")

    html_url = _field(entry, "url")
    if try_online and html_url and html_url != "not provided":
        try:
            import requests

            response = _get(requests, html_url, timeout)
            if response is None:
                log.append(f"HTML fetch failed for {html_url}")
                raise RuntimeError("HTML fetch failed")
            if response.status_code == 200 and "text/html" in response.headers.get("content-type", "").lower():
                text = _strip_html(response.text)
                return FetchResult(paper_id, cache_key, "html", html_url, "", text, "medium", log + [f"Fetched HTML from {html_url}"])
        except Exception as exc:
            log.append(f"HTML fetch failed for {html_url}: {exc}")

    abstract = _field(entry, "abstract")
    if abstract and abstract != "not provided":
        return FetchResult(paper_id, cache_key, "abstract_metadata", "", "", "", "low", log + ["Using abstract and metadata only"])

    return FetchResult(paper_id, cache_key, "user_metadata", "", "", "", "low", log + ["Using user-provided information only"])


def _paper_id(entry: dict[str, Any]) -> str:
    cvgmt_id = _field(entry, "cvgmt_id")
    if cvgmt_id and cvgmt_id != "not provided":
        return f"cvgmt_{cvgmt_id}"
    title = _field(entry, "title") or "paper"
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug[:80] or "paper"


def _field(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key, "")
    return str(value).strip()


def _local_pdf_from_entry(entry: dict[str, Any]) -> str:
    for key in ["pdf_path", "pdf_url", "url"]:
        value = _field(entry, key)
        if _looks_like_local_pdf_path(value):
            return _normalize_local_pdf_path(value)
    return ""


def _resolve_existing_local_pdf_path(value: str, tried_paths: list[str] | None = None) -> Path | None:
    for candidate in _local_pdf_path_candidates(value):
        path = Path(candidate).expanduser()
        if tried_paths is not None:
            tried_paths.append(str(path))
        if path.is_file() and path.suffix.lower() == ".pdf":
            return path
    return None


def _local_pdf_path_candidates(value: str) -> list[str]:
    text = _normalize_local_pdf_path(value)
    candidates = [text]

    drive_match = re.match(r"^([A-Za-z]):[\\/](.*)$", text)
    if drive_match:
        drive, rest = drive_match.groups()
        rest_posix = rest.replace("\\", "/")
        candidates.append(f"/mnt/{drive.lower()}/{rest_posix}")

    mnt_match = re.match(r"^/mnt/([A-Za-z])/(.*)$", text)
    if mnt_match:
        drive, rest = mnt_match.groups()
        rest_windows = rest.replace("/", "\\")
        candidates.append(f"{drive.upper()}:\\{rest_windows}")

    slash_drive_match = re.match(r"^/([A-Za-z]):/(.*)$", text)
    if slash_drive_match:
        drive, rest = slash_drive_match.groups()
        rest_windows = rest.replace("/", "\\")
        candidates.append(f"{drive.upper()}:\\{rest_windows}")
        candidates.append(f"/mnt/{drive.lower()}/{rest}")

    return _dedupe(candidates)


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


def _candidate_pdf_urls(entry: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ["pdf_url", "pdf", "url"]:
        value = _field(entry, key)
        if _looks_like_pdf_url(value):
            urls.append(value)
    url = _field(entry, "url")
    doi = _field(entry, "doi")
    cvgmt_id = _field(entry, "cvgmt_id")
    if not cvgmt_id or cvgmt_id == "not provided":
        cvgmt_id = _cvgmt_id(" ".join(str(entry.get(key, "")) for key in ["url", "doi", "title", "abstract"]))
    arxiv_id = _arxiv_id(url) or _arxiv_id(
        " ".join(str(entry.get(key, "")) for key in ["doi", "title", "abstract", "matched_keywords"])
    )
    if arxiv_id:
        urls.extend(_arxiv_pdf_urls(arxiv_id))
    if "arxiv.org/pdf/" in url:
        urls.append(url)
    if cvgmt_id and cvgmt_id != "not provided":
        urls.extend(
            [
                f"https://cvgmt.sns.it/paper/{cvgmt_id}/",
                f"https://cvgmt.sns.it/paper/{cvgmt_id}",
                f"https://cvgmt.sns.it/media/doc/paper/{cvgmt_id}/{cvgmt_id}.pdf",
                f"https://cvgmt.sns.it/media/doc/paper/{cvgmt_id}/main.pdf",
            ]
        )
    if doi and doi != "not provided":
        urls.extend(_doi_pdf_url_guesses(doi))
    return _dedupe(urls)


def _repository_priority_pdf_urls(entry: dict[str, Any]) -> tuple[str, list[str]]:
    text = " ".join(str(entry.get(key, "")) for key in ["url", "pdf_url", "pdf", "doi", "title", "abstract", "matched_keywords"])
    arxiv_id = _arxiv_id(text)
    if arxiv_id:
        return "arXiv", _arxiv_pdf_urls(arxiv_id)

    cvgmt_id = _field(entry, "cvgmt_id")
    if not cvgmt_id or cvgmt_id == "not provided":
        cvgmt_id = _cvgmt_id(text)
    if cvgmt_id and cvgmt_id != "not provided":
        return (
            "CVGMT",
            _dedupe(
                [
                    f"https://cvgmt.sns.it/paper/{cvgmt_id}/",
                    f"https://cvgmt.sns.it/paper/{cvgmt_id}",
                    f"https://cvgmt.sns.it/media/doc/paper/{cvgmt_id}/{cvgmt_id}.pdf",
                    f"https://cvgmt.sns.it/media/doc/paper/{cvgmt_id}/main.pdf",
                ]
            ),
        )
    return "", []


def _arxiv_pdf_urls(arxiv_id: str) -> list[str]:
    clean = re.sub(r"v\d+$", "", arxiv_id.strip(), flags=re.IGNORECASE)
    return [
        f"https://arxiv.org/pdf/{clean}",
        f"https://arxiv.org/pdf/{clean}.pdf",
        f"https://export.arxiv.org/pdf/{clean}",
        f"https://export.arxiv.org/pdf/{clean}.pdf",
    ]


def _discover_pdf_urls_from_html(html: str, base_url: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"""(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", html):
        raw, anchor_text = match.groups()
        href = unescape(raw.strip())
        absolute = urljoin(base_url, href)
        label_context = _strip_html(anchor_text).lower()
        if _looks_like_pdf_url(absolute) or "pdf" in label_context or "download" in label_context:
            candidates.append(absolute)
    for raw in re.findall(r"""(?i)https?://[^\s"'<>]+\.pdf(?:\?[^\s"'<>]*)?""", html):
        candidates.append(unescape(raw.strip()))
    return _dedupe(candidates)


def _download_first_valid_pdf(
    requests: Any,
    urls: list[str],
    pdf_path: Path,
    timeout: int,
    log: list[str],
    discovery_pool: list[str] | None = None,
) -> str:
    pending = list(urls)
    seen: set[str] = set()
    while pending:
        pdf_url = pending.pop(0)
        if pdf_url in seen:
            continue
        seen.add(pdf_url)
        response = _get(requests, pdf_url, timeout)
        if response is None:
            log.append(f"PDF fetch failed for {pdf_url}")
            continue
        content_type = response.headers.get("content-type", "").lower()
        if _is_pdf_response(response, content_type):
            pdf_path.write_bytes(response.content)
            if _valid_cached_pdf(pdf_path):
                return pdf_url
            pdf_path.unlink(missing_ok=True)
            log.append(f"Rejected invalid or tiny PDF from {pdf_url}")
            continue
        if "text/html" in content_type or "<html" in response.text[:500].lower():
            discovered = _discover_pdf_urls_from_html(response.text, pdf_url)
            discovered.extend(_publisher_pdf_candidates_from_html(response.text, pdf_url))
            new_urls = [url for url in discovered if url not in seen and url not in pending]
            pending.extend(new_urls)
            if discovery_pool is not None:
                discovery_pool.extend(url for url in new_urls if url not in discovery_pool)
            if new_urls:
                log.append(f"Discovered {len(new_urls)} PDF link(s) from candidate page {pdf_url}")
            continue
        status = getattr(response, "status_code", "unknown")
        log.append(f"PDF candidate did not return a PDF: {pdf_url} (status={status}, content-type={content_type})")
    return ""


def _publisher_pdf_candidates_from_html(html: str, base_url: str) -> list[str]:
    candidates: list[str] = []

    pii = _science_direct_pii(html) or _science_direct_pii(base_url)
    if pii:
        candidates.extend(
            [
                f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?isDTMRedir=true&download=true",
                f"https://www.sciencedirect.com/science/article/pii/{pii}/pdf",
            ]
        )

    doi = _doi_from_text(html) or _doi_from_text(base_url)
    if doi:
        candidates.extend(_doi_pdf_url_guesses(doi))

    for match in re.finditer(r"""(?is)<meta\b[^>]+(?:name|property)\s*=\s*["'](?:citation_pdf_url|dc.identifier|og:url)["'][^>]+content\s*=\s*["']([^"']+)["']""", html):
        candidates.append(unescape(match.group(1).strip()))
    for match in re.finditer(r"""(?is)<meta\b[^>]+content\s*=\s*["']([^"']+)["'][^>]+(?:name|property)\s*=\s*["'](?:citation_pdf_url|dc.identifier|og:url)["']""", html):
        candidates.append(unescape(match.group(1).strip()))

    return _dedupe(candidates)


def _metadata_pdf_candidates(requests: Any, entry: dict[str, Any], timeout: int) -> list[str]:
    candidates: list[str] = []
    doi = _field(entry, "doi")
    if doi and doi != "not provided":
        candidates.extend(_crossref_link_candidates(requests, doi, timeout))
        candidates.extend(_openalex_pdf_candidates(requests, doi, timeout))
    if not candidates:
        title = _field(entry, "title")
        if title and title != "not provided":
            candidates.extend(_openalex_pdf_candidates(requests, title, timeout))
    return _dedupe(candidates)


def _crossref_link_candidates(requests: Any, doi: str, timeout: int) -> list[str]:
    try:
        response = _get(requests, f"https://api.crossref.org/works/{doi}", timeout)
        if response is None or response.status_code != 200:
            return []
        message = response.json().get("message", {})
        urls = []
        for link in message.get("link", []):
            url = str(link.get("URL", "")).strip()
            content_type = str(link.get("content-type", "")).lower()
            intended = str(link.get("intended-application", "")).lower()
            if url and ("pdf" in content_type or "pdf" in url.lower() or intended == "text-mining"):
                urls.append(url)
        return urls
    except Exception:
        return []


def _openalex_pdf_candidates(requests: Any, doi_or_title: str, timeout: int) -> list[str]:
    try:
        doi = _doi_from_text(doi_or_title)
        if doi:
            response = requests.get(
                "https://api.openalex.org/works",
                params={"filter": f"doi:https://doi.org/{doi}", "per-page": 1},
                timeout=timeout,
                headers=REQUEST_HEADERS,
            )
            works = response.json().get("results", []) if response.status_code == 200 else []
        else:
            response = requests.get(
                "https://api.openalex.org/works",
                params={"search": doi_or_title, "per-page": 3},
                timeout=timeout,
                headers=REQUEST_HEADERS,
            )
            works = response.json().get("results", []) if response.status_code == 200 else []
        urls: list[str] = []
        for work in works:
            for location_key in ["best_oa_location", "primary_location"]:
                location = work.get(location_key) or {}
                for key in ["pdf_url", "landing_page_url"]:
                    value = str(location.get(key) or "").strip()
                    if value:
                        urls.append(value)
            for location in work.get("locations", []) or []:
                for key in ["pdf_url", "landing_page_url"]:
                    value = str((location or {}).get(key) or "").strip()
                    if value:
                        urls.append(value)
        return urls
    except Exception:
        return []


def _doi_pdf_url_guesses(doi: str) -> list[str]:
    clean = doi.strip().lower().removeprefix("https://doi.org/")
    guesses: list[str] = []
    if clean.startswith("10.1007/"):
        guesses.extend(
            [
                f"https://link.springer.com/content/pdf/{clean}.pdf",
                f"https://link.springer.com/content/pdf/{clean}",
            ]
        )
    if clean.startswith("10.1006/") or clean.startswith("10.1016/"):
        # ScienceDirect often needs a PII; DOI pages may expose it in the linking-hub HTML.
        guesses.append(f"https://doi.org/{clean}")
    if clean.startswith("10.1515/"):
        guesses.extend(
            [
                f"https://www.degruyter.com/document/doi/{clean}/pdf",
                f"https://www.degruyter.com/document/doi/{clean}/pdf?download=true",
            ]
        )
    return guesses

def _looks_like_pdf_url(url: str) -> bool:
    value = (url or "").lower().split("?", 1)[0]
    return value.endswith(".pdf") or "/pdf/" in value or "arxiv.org/pdf/" in value


def _arxiv_id(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"\barxiv\s*:\s*([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"\b10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
        r"arxiv\.org/(?:abs|pdf)/([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
        r"\barxiv\s*:\s*([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
        r"\b10\.48550/arxiv\.([a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v\d+)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _doi_from_text(text: str) -> str:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text or "")
    return match.group(0).rstrip(".,);") if match else ""


def _science_direct_pii(text: str) -> str:
    match = re.search(r"\bS\d{16,18}\b", text or "")
    return match.group(0) if match else ""


def _cvgmt_id(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"cvgmt\.sns\.it/paper/(\d+)", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _source_cache_key(entry: dict[str, Any], fallback: str = "paper") -> str:
    identity = " ".join(str(entry.get(key, "")) for key in ["doi", "url", "title"]).strip()
    arxiv_id = _arxiv_id(identity)
    if arxiv_id:
        return "arxiv_" + re.sub(r"[^A-Za-z0-9]+", "_", arxiv_id).strip("_").lower()
    doi = _field(entry, "doi")
    if doi and doi != "not provided":
        digest = hashlib.sha1(doi.lower().encode("utf-8")).hexdigest()[:12]
        return f"doi_{digest}"
    title = _field(entry, "title")
    if title and title != "not provided":
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:48]
        digest = hashlib.sha1(title.lower().encode("utf-8")).hexdigest()[:8]
        return f"title_{slug}_{digest}".strip("_")
    return re.sub(r"[^a-z0-9]+", "_", fallback.lower()).strip("_") or "paper"


def _is_pdf_response(response: Any, content_type: str) -> bool:
    return (
        response.status_code == 200
        and len(getattr(response, "content", b"")) >= MIN_PDF_BYTES
        and ("pdf" in content_type or response.content.startswith(b"%PDF"))
    )


def _get(requests: Any, url: str, timeout: int, attempts: int = 2) -> Any | None:
    normalized = _normalize_url(url)
    for _ in range(attempts):
        try:
            response = requests.get(normalized, timeout=timeout, headers=REQUEST_HEADERS, allow_redirects=True)
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                continue
            return response
        except Exception:
            continue
    return None


def _normalize_url(url: str) -> str:
    clean = (url or "").strip()
    if clean.startswith("http://arxiv.org/"):
        return "https://" + clean[len("http://") :]
    if clean.startswith("http://export.arxiv.org/"):
        return "https://" + clean[len("http://") :]
    return clean


def _valid_cached_pdf(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= MIN_PDF_BYTES and path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def _dedupe(urls: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        clean = url.strip()
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()
