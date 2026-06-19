"""Command-line interface for QAgent."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qagent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_batch_parser = subparsers.add_parser(
        "run-batch",
        help="Run a markdown paper batch through the QAgent pipeline.",
    )
    run_batch_parser.add_argument("input_path", type=Path)
    run_batch_parser.add_argument("--batch-id", required=True)
    run_batch_parser.add_argument(
        "--mock",
        action="store_true",
        help="Run the deterministic mock pipeline instead of calling an API.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-batch":
        if not args.mock:
            parser.error("Only --mock mode is implemented in this version.")
        report_path = run_batch(args.input_path, batch_id=args.batch_id, mock=args.mock)
        print(f"Batch complete: {report_path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
