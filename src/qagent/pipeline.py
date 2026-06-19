"""Mock QAgent batch pipeline."""

from __future__ import annotations

from pathlib import Path

from .exporter import write_batch_report, write_mock_outputs
from .parser import parse_batch


def run_batch(input_path: Path, batch_id: str, mock: bool = True) -> Path:
    if not mock:
        raise NotImplementedError("Only mock mode is implemented.")

    papers = parse_batch(input_path)
    output_root = Path("outputs") / batch_id
    output_root.mkdir(parents=True, exist_ok=True)

    for paper in papers:
        write_mock_outputs(output_root, paper)

    return write_batch_report(output_root, batch_id, papers)
