from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


TEXT_DIR = Path("data") / "paper_text"


@dataclass
class TextExtractionResult:
    paper_id: str
    text_path: str
    full_text_read: bool
    extraction_confidence: str
    sections: dict[str, str]
    log: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_paper_text(fetch_result: dict[str, Any], entry: dict[str, Any]) -> TextExtractionResult:
    paper_id = fetch_result.get("paper_id", entry.get("paper_id", "paper"))
    cache_key = str(fetch_result.get("cache_key") or paper_id)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    text_path = TEXT_DIR / f"{cache_key}.txt"
    log: list[str] = []
    source_type = _source_type(fetch_result)
    pdf_path = fetch_result.get("pdf_path", "")

    if text_path.exists():
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        if source_type in {"pdf", "cached_pdf"} and pdf_path:
            log.append("PDF source is available; re-extracting from PDF instead of trusting cached text")
        elif _looks_like_full_text(text) or source_type not in {"pdf", "cached_pdf", "html"}:
            full_text = _looks_like_full_text(text)
            return TextExtractionResult(
                paper_id,
                str(text_path),
                full_text,
                _confidence_from_text(text, source_type),
                extract_sections(text),
                ["Using cached extracted text"],
            )
        else:
            log.append("Cached text looked too short for full-text PDF/HTML source; re-extracting")

    text = ""
    full_text_read = False
    confidence = "low"
    if pdf_path:
        text, pdf_log = _extract_pdf_text(pdf_path)
        log.extend(pdf_log)
        full_text_read = _looks_like_full_text(text)
        confidence = _confidence_from_text(text, source_type)

    if not text and fetch_result.get("html_text"):
        text = fetch_result["html_text"]
        full_text_read = _looks_like_full_text(text)
        confidence = _confidence_from_text(text, "html")
        log.append("Using fetched HTML text")

    if not text:
        text = _metadata_text(entry)
        full_text_read = False
        confidence = "low"
        log.append("Using abstract/metadata text only")

    text_path.write_text(text, encoding="utf-8")
    return TextExtractionResult(paper_id, str(text_path), full_text_read, confidence, extract_sections(text), log)


def _source_type(fetch_result: dict[str, Any]) -> str:
    return str(fetch_result.get("source_type") or fetch_result.get("source") or "")


def _extract_pdf_text(pdf_path: str) -> tuple[str, list[str]]:
    log: list[str] = []
    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(pages)
        log.append(f"pypdf extracted text from {len(pages)} PDF pages")
    except ImportError:
        log.append("pypdf is not installed; trying PyMuPDF fallback")
    except Exception as exc:
        log.append(f"pypdf extraction failed: {exc}; trying PyMuPDF fallback")

    if _looks_like_full_text(text):
        return text, log

    fallback_text = ""
    try:
        import fitz

        document = fitz.open(pdf_path)
        pages = [page.get_text("text") or "" for page in document]
        fallback_text = "\n\n".join(pages)
        log.append(f"PyMuPDF extracted text from {len(pages)} PDF pages")
    except ImportError:
        log.append("PyMuPDF is not installed; PDF fallback unavailable")
    except Exception as exc:
        log.append(f"PyMuPDF extraction failed: {exc}")

    if len(fallback_text.strip()) > len(text.strip()):
        return fallback_text, log

    external_text, external_log = _extract_pdf_text_with_external_python(pdf_path)
    log.extend(external_log)
    if len(external_text.strip()) > len(text.strip()):
        return external_text, log
    return text, log


def _extract_pdf_text_with_external_python(pdf_path: str) -> tuple[str, list[str]]:
    candidates = [
        "/mnt/c/tools/Python313/python.exe",
        "/mnt/c/tools/Python312/python.exe",
        "/mnt/c/tools/Python311/python.exe",
    ]
    executable = next((path for path in candidates if Path(path).exists()), "")
    if not executable:
        return "", ["External Windows Python fallback unavailable"]

    windows_pdf_path = _windows_path_for_external_python(pdf_path)
    code = r"""
import json
import sys

pdf_path = sys.argv[1]
log = []
text = ""
try:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(pages)
    log.append(f"external pypdf extracted text from {len(pages)} PDF pages")
except Exception as exc:
    log.append(f"external pypdf failed: {exc}")

if len(text.strip()) < 1500:
    try:
        import fitz
        document = fitz.open(pdf_path)
        pages = [page.get_text("text") or "" for page in document]
        fallback = "\n\n".join(pages)
        log.append(f"external PyMuPDF extracted text from {len(pages)} PDF pages")
        if len(fallback.strip()) > len(text.strip()):
            text = fallback
    except Exception as exc:
        log.append(f"external PyMuPDF failed: {exc}")

print(json.dumps({"text": text, "log": log}, ensure_ascii=True))
"""
    try:
        completed = subprocess.run(
            [executable, "-c", code, windows_pdf_path],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except Exception as exc:
        return "", [f"External Windows Python fallback failed to launch: {exc}"]

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return "", [f"External Windows Python fallback failed: {detail[:500]}"]
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return "", ["External Windows Python fallback returned non-JSON output"]
    return str(payload.get("text", "")), [str(item) for item in payload.get("log", [])]


def _windows_path_for_external_python(path: str) -> str:
    resolved = Path(path).resolve().as_posix()
    match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", resolved)
    if match:
        drive, rest = match.groups()
        windows_rest = rest.replace("/", "\\")
        return f"{drive.upper()}:\\{windows_rest}"
    return str(Path(path))


def _looks_like_full_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) < 1500:
        return False
    lower = clean.lower()
    signals = sum(
        1
        for term in ["abstract", "introduction", "theorem", "proof", "lemma", "references", "bibliography"]
        if term in lower
    )
    return signals >= 2 or len(clean) >= 5000


def _confidence_from_text(text: str, source_type: str) -> str:
    clean_len = len(re.sub(r"\s+", " ", text).strip())
    if _looks_like_full_text(text):
        return "high" if source_type in {"pdf", "cached_pdf"} and clean_len >= 5000 else "medium"
    if clean_len >= 800:
        return "medium"
    return "low"


def extract_sections(text: str) -> dict[str, str]:
    return {
        "title_page": text[:3000],
        "abstract": _section(text, "abstract", ["introduction", "1 introduction"]),
        "introduction": _section(text, "introduction", ["preliminaries", "main result", "theorem"]),
        "theorem_like_statements": "\n\n".join(extract_theorem_like_blocks(text)),
        "remarks": _matching_blocks(text, r"(?im)^\s*Remark\b.*?(?=^\s*(?:Theorem|Lemma|Proposition|Corollary|Remark|Section|\d+\.|\Z))"),
        "open_problems": _matching_blocks(text, r"(?im)^\s*(?:Open problem|Question|Conjecture)\b.*?(?=^\s*(?:Theorem|Lemma|Proposition|Corollary|Remark|Section|\d+\.|\Z))"),
        "conclusion": _section(text, "conclusion", ["references", "bibliography"]),
        "bibliography_metadata": _section(text, "references", []),
    }


def extract_theorem_like_blocks(text: str) -> list[str]:
    pattern = r"(?ims)^\s*(Theorem|Proposition|Lemma|Corollary)\s+[\w.\-]*.*?(?=^\s*(?:Theorem|Proposition|Lemma|Corollary|Remark|Proof|Section|\d+\.|\Z))"
    return [re.sub(r"\s+", " ", match.group(0)).strip()[:3000] for match in re.finditer(pattern, text)]


def _section(text: str, heading: str, end_headings: list[str]) -> str:
    start = re.search(rf"(?im)^\s*(?:\d+\.?\s*)?{re.escape(heading)}\b.*$", text)
    if not start:
        return ""
    end = len(text)
    for candidate in end_headings:
        match = re.search(rf"(?im)^\s*(?:\d+\.?\s*)?{re.escape(candidate)}\b.*$", text[start.end() :])
        if match:
            end = start.end() + match.start()
            break
    return text[start.start() : end].strip()[:8000]


def _matching_blocks(text: str, pattern: str) -> str:
    return "\n\n".join(match.group(0).strip()[:2000] for match in re.finditer(pattern, text))[:8000]


def _metadata_text(entry: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            str(entry.get("title", "")),
            str(entry.get("authors", "")),
            str(entry.get("year", "")),
            str(entry.get("abstract", "")),
        ]
    )
