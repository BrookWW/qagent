from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.qagent.backend_diagnostics import (
    BackendDiagnostics,
    backend_info_markdown,
    patch_selected_metadata_backend_info,
    write_backend_info,
)


class BackendDiagnosticsTests(unittest.TestCase):
    def test_backend_info_serializes_model_source(self) -> None:
        diagnostics = BackendDiagnostics(
            backend="codex_cli_logged_in",
            api_mode="no_api",
            model="codex_default",
            model_source="Codex CLI default from logged-in account/config",
            codex_path="C:/bin/codex.exe",
            codex_cli_available=True,
            codex_cli_version="codex-cli 0.134.0",
            supports_model_override=True,
            supports_search_flag=True,
            search_enabled=True,
            reasoning_effort="xhigh",
            command_template='codex --search -c model_reasoning_effort="xhigh" exec --json --skip-git-repo-check -C <workspace> "<prompt>"',
            error_message="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = write_backend_info(Path(tmp), diagnostics)
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["backend"], "codex_cli_logged_in")
        self.assertEqual(data["api_mode"], "no_api")
        self.assertEqual(data["model_source"], "Codex CLI default from logged-in account/config")
        self.assertIn("Supports `--model`: True", backend_info_markdown(diagnostics))
        self.assertIn("Search enabled: True", backend_info_markdown(diagnostics))
        self.assertIn("Reasoning effort: xhigh", backend_info_markdown(diagnostics))

    def test_patch_selected_metadata_backend_info_fills_missing_fields(self) -> None:
        diagnostics = BackendDiagnostics(
            backend="codex_cli_logged_in",
            api_mode="no_api",
            model="o3",
            model_source="explicit codex exec --model o3",
            codex_path="C:/bin/codex.exe",
            codex_cli_available=True,
            codex_cli_version="codex-cli 0.134.0",
            supports_model_override=True,
            supports_search_flag=True,
            search_enabled=True,
            reasoning_effort="xhigh",
            command_template='codex --search -m o3 -c model_reasoning_effort="xhigh" exec --json --skip-git-repo-check -C <workspace> "<prompt>"',
            error_message="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_backend_info(root, diagnostics)
            metadata_path = root / "paper_001" / "selected" / "c01" / "metadata.json"
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text(
                json.dumps(
                    {
                        "question_id": "c01",
                        "generation_model": "already-set",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = patch_selected_metadata_backend_info(root)
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            report = json.loads((root / "metadata_backend_patch.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(data["generation_backend"], "codex_cli_logged_in")
        self.assertEqual(data["generation_api_mode"], "no_api")
        self.assertEqual(data["generation_model"], "already-set")
        self.assertEqual(data["generation_model_source"], "explicit codex exec --model o3")
        self.assertEqual(data["generation_search_enabled"], True)
        self.assertEqual(data["generation_reasoning_effort"], "xhigh")
        self.assertEqual(data["codex_cli_version"], "codex-cli 0.134.0")
        self.assertEqual(len(report["patched_files"]), 1)


if __name__ == "__main__":
    unittest.main()
