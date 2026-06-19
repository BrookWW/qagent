from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile


REQUIRED_SELECTED_FILES = [
    "problem_statement.tex",
    "additional_prove_human_help_global.md",
    "additional_verify_rule_global.md",
    "survey_queries.md",
    "feasibility_analysis.md",
    "metadata.json",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def count_paper_entries(markdown: str) -> int:
    return len(re.findall(r"^##\s+", markdown, flags=re.MULTILINE))


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text.strip() else 0


def estimate_output_tokens(output_dir: Path) -> int:
    if not output_dir.exists():
        return 0
    total_chars = 0
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".tex"}:
            total_chars += len(read_text(path))
    return total_chars // 4


def paper_dirs(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    return sorted(path for path in output_dir.iterdir() if path.is_dir())


def question_ids(final_count: int) -> list[str]:
    return [f"q{index:02d}" for index in range(1, final_count + 1)]


def validate_outputs(output_dir: Path, final_count: int) -> tuple[list[str], bool]:
    messages: list[str] = []
    papers = paper_dirs(output_dir)
    messages.append(f"Paper folders found: {len(papers)}")
    ok = len(papers) == 10

    expected_questions = question_ids(final_count)
    for paper_dir in papers:
        selected_dir = paper_dir / "selected"
        found = [qid for qid in expected_questions if (selected_dir / qid).is_dir()]
        messages.append(f"{paper_dir.name}: {len(found)}/{final_count} final question folders found")
        ok = ok and len(found) == final_count

        for qid in expected_questions:
            qdir = selected_dir / qid
            missing = [name for name in REQUIRED_SELECTED_FILES if not (qdir / name).is_file()]
            if missing:
                messages.append(f"{paper_dir.name}/{qid}: missing {', '.join(missing)}")
                ok = False

    return messages, ok


def zip_directory(root: Path) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root.parent))
    buffer.seek(0)
    return buffer.getvalue()
