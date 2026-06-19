from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .runner import CODEX_DEFAULT_MODEL_SOURCE, codex_backend_metadata
from .runner import CODEX_DEFAULT_REASONING_EFFORT


@dataclass
class BackendDiagnostics:
    backend: str
    api_mode: str
    model: str
    model_source: str
    codex_path: str
    codex_cli_available: bool
    codex_cli_version: str
    supports_model_override: bool
    supports_search_flag: bool
    search_enabled: bool
    reasoning_effort: str
    command_template: str
    error_message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_backend_diagnostics(
    model: str = "",
    timeout_seconds: int = 10,
    *,
    use_search: bool = True,
    reasoning_effort: str = CODEX_DEFAULT_REASONING_EFFORT,
) -> BackendDiagnostics:
    meta = codex_backend_metadata(model, use_search=use_search, reasoning_effort=reasoning_effort)
    codex_path = shutil.which("codex") or ""
    command_template = "codex"
    if use_search:
        command_template += " --search"
    if model.strip():
        command_template += f" -m {model.strip()}"
    if reasoning_effort.strip():
        command_template += f' -c model_reasoning_effort="{reasoning_effort.strip()}"'
    command_template += ' exec --json --skip-git-repo-check -C <workspace> "<prompt>"'

    if not codex_path:
        return BackendDiagnostics(
            backend=meta["backend"],
            api_mode=meta["api_mode"],
            model=meta["model"],
            model_source=meta["model_source"],
            codex_path="",
            codex_cli_available=False,
            codex_cli_version="",
            supports_model_override=False,
            supports_search_flag=False,
            search_enabled=use_search,
            reasoning_effort=reasoning_effort,
            command_template=command_template,
            error_message="Codex CLI was not found on PATH.",
        )

    version_result = _run([codex_path, "--version"], timeout_seconds)
    help_result = _run([codex_path, "exec", "--help"], timeout_seconds)
    help_text = f"{help_result.get('stdout', '')}\n{help_result.get('stderr', '')}"
    supports_model = "--model <MODEL>" in help_text or "-m, --model" in help_text
    root_help_result = _run([codex_path, "--help"], timeout_seconds)
    root_help_text = f"{root_help_result.get('stdout', '')}\n{root_help_result.get('stderr', '')}"
    supports_search = "--search" in root_help_text or "--search" in help_text
    error = ""
    if version_result["return_code"] != 0:
        error = version_result["stderr"] or version_result["stdout"] or "Unable to read Codex CLI version."
    elif help_result["return_code"] != 0:
        error = help_result["stderr"] or help_result["stdout"] or "Unable to read Codex exec help."
    elif model.strip() and not supports_model:
        error = "A model override was provided, but this Codex CLI help output does not advertise --model support."

    return BackendDiagnostics(
        backend=meta["backend"],
        api_mode=meta["api_mode"],
        model=meta["model"],
        model_source=meta["model_source"],
        codex_path=codex_path,
        codex_cli_available=version_result["return_code"] == 0,
        codex_cli_version=(version_result["stdout"] or version_result["stderr"]).strip(),
        supports_model_override=supports_model,
        supports_search_flag=supports_search,
        search_enabled=use_search,
        reasoning_effort=reasoning_effort,
        command_template=command_template,
        error_message=error.strip(),
    )


def write_backend_info(output_dir: Path, diagnostics: BackendDiagnostics) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "backend_info.json"
    path.write_text(json.dumps(diagnostics.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_backend_info_markdown(output_dir: Path, diagnostics: BackendDiagnostics) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "backend_info.md"
    path.write_text(backend_info_markdown(diagnostics), encoding="utf-8")
    return path


def patch_selected_metadata_backend_info(output_dir: Path) -> dict[str, Any]:
    backend_info = _read_json(output_dir / "backend_info.json")
    if not isinstance(backend_info, dict):
        result = {
            "ok": False,
            "patched_files": [],
            "skipped_files": [],
            "error_message": "backend_info.json is missing or invalid.",
        }
        _write_patch_report(output_dir, result)
        return result

    patch_values = {
        "generation_backend": backend_info.get("backend", ""),
        "generation_api_mode": backend_info.get("api_mode", ""),
        "generation_model": backend_info.get("model", ""),
        "generation_model_source": backend_info.get("model_source", ""),
        "generation_search_enabled": backend_info.get("search_enabled", ""),
        "generation_reasoning_effort": backend_info.get("reasoning_effort", ""),
        "codex_cli_version": backend_info.get("codex_cli_version", ""),
    }
    patched_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []

    for metadata_path in sorted(output_dir.glob("paper_*/selected/*/metadata.json")):
        metadata = _read_json(metadata_path)
        if not isinstance(metadata, dict):
            skipped_files.append({"path": metadata_path.as_posix(), "reason": "invalid metadata JSON"})
            continue

        added = {}
        for key, value in patch_values.items():
            if not metadata.get(key) and value:
                metadata[key] = value
                added[key] = value

        if added:
            metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            patched_files.append({"path": metadata_path.as_posix(), "added_fields": sorted(added)})
        else:
            skipped_files.append({"path": metadata_path.as_posix(), "reason": "backend fields already present"})

    result = {
        "ok": True,
        "patched_files": patched_files,
        "skipped_files": skipped_files,
        "error_message": "",
    }
    _write_patch_report(output_dir, result)
    return result


def backend_info_markdown(diagnostics: BackendDiagnostics) -> str:
    return "\n".join(
        [
            "# Backend Info",
            "",
            f"- Backend: {diagnostics.backend}",
            f"- API mode: {diagnostics.api_mode}",
            f"- Model: {diagnostics.model}",
            f"- Model source: {diagnostics.model_source or CODEX_DEFAULT_MODEL_SOURCE}",
            f"- Codex path: `{diagnostics.codex_path or 'not found'}`",
            f"- Codex CLI available: {diagnostics.codex_cli_available}",
            f"- Codex CLI version: {diagnostics.codex_cli_version or 'unknown'}",
            f"- Supports `--model`: {diagnostics.supports_model_override}",
            f"- Supports `--search`: {diagnostics.supports_search_flag}",
            f"- Search enabled: {diagnostics.search_enabled}",
            f"- Reasoning effort: {diagnostics.reasoning_effort}",
            f"- Command template: `{diagnostics.command_template}`",
            f"- Error: {diagnostics.error_message or 'none'}",
            "",
        ]
    )


def _run(command: list[str], timeout_seconds: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "return_code": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
        }
    except Exception as exc:
        return {
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_patch_report(output_dir: Path, result: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "metadata_backend_patch.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
