#!/usr/bin/env python3
"""Run the offline Core Eval Harness v0."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.eval_harness import (
    ALL_SUITES,
    DEFAULT_REPORT_DIR,
    format_markdown_report,
    run_suites,
    write_report_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic eval harness suites.")
    parser.add_argument(
        "--suite",
        action="append",
        choices=("all", *ALL_SUITES),
        default=None,
        help="Suite to run. Repeatable. Default: all.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Stdout format. Default: markdown.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"Write latest JSON/Markdown under {DEFAULT_REPORT_DIR}.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help=f"Output directory for --write. Default: {DEFAULT_REPORT_DIR}.",
    )
    args = parser.parse_args(argv)

    try:
        report = run_suites(args.suite or ["all"])
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        paths = write_report_files(report, args.output_dir)
        print(f"Wrote {paths['json']}", file=sys.stderr)
        print(f"Wrote {paths['markdown']}", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_markdown_report(report), end="")

    return 0 if report["overall_status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
