#!/usr/bin/env python3
"""
validate_notion_schema.py — Validate Notion DB schema specs.

Loads a schema YAML, validates structure, and prints a summary.
Exit code 0 if valid, 1 if errors.

Usage:
  python scripts/validate_notion_schema.py
  python scripts/validate_notion_schema.py --schema notion/schemas/publicaciones.schema.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from infra.notion_schema import (
    load_schema,
    summarize_schema,
    validate_schema,
)

_DEFAULT_SCHEMA = Path("notion/schemas/publicaciones.schema.yaml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Notion DB schema spec.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=_DEFAULT_SCHEMA,
        help=f"Path to schema YAML (default: {_DEFAULT_SCHEMA})",
    )
    args = parser.parse_args(argv)

    try:
        schema = load_schema(args.schema)
    except (FileNotFoundError, ValueError, ImportError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    errors = validate_schema(schema)
    summary = summarize_schema(schema)

    print(f"Schema: {args.schema}")
    print(f"  Database: {summary['name']} v{summary['version']} ({summary['status']})")
    print(f"  Properties: {summary['total_properties']} ({summary['required_properties']} required)")
    print(f"  Property types: {summary['property_types']}")
    print(f"  Channels: {', '.join(summary['channels'])}")
    print(f"  Statuses: {', '.join(summary['statuses'])}")
    print(f"  Transitions: {summary['transitions']}")
    print(f"  Invariants: {summary['invariants']}")
    print(f"  Recommended views: {summary['recommended_views']}")

    if errors:
        print(f"\n{len(errors)} validation error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
