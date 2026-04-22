#!/usr/bin/env python3
"""
CLI: Audit Notion Publicaciones DB against local schema (read-only).

Compares the approved local schema against a Notion database metadata
fixture or a live Notion database via GET only.  No writes to Notion.

Usage::

    # Fixture mode (offline, no env vars needed)
    PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \\
        --fixture tests/fixtures/notion/publicaciones_database_valid.json

    # Live read-only mode (requires NOTION_API_KEY env var)
    PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \\
        --database-id <id>
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from infra.notion_readonly_audit import (
    build_audit_report,
    compare_schema_to_database,
    fetch_database_metadata_readonly,
    format_audit_json,
    format_audit_markdown,
    load_actual_database_metadata,
    load_expected_schema,
)
from infra.notion_schema import validate_schema

DEFAULT_SCHEMA = "notion/schemas/publicaciones.schema.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Notion Publicaciones DB against local schema (read-only)."
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Path to local schema YAML (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Path to Notion database metadata JSON fixture (offline mode).",
    )
    parser.add_argument(
        "--database-id",
        default=None,
        help="Notion database ID for live read-only fetch (requires NOTION_API_KEY).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output report as JSON.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        dest="output_markdown",
        help="Output report as Markdown.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write report to file instead of stdout.",
    )
    parser.add_argument(
        "--fail-on-blocker",
        action="store_true",
        help="Exit with code 1 if any blocker is found.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with code 1 if any warning is found.",
    )
    parser.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate the local schema before auditing.",
    )

    args = parser.parse_args(argv)

    # Must have fixture or database-id
    if not args.fixture and not args.database_id:
        print(
            "ERROR: Either --fixture or --database-id is required.\n"
            "  Use --fixture for offline audit against a JSON fixture.\n"
            "  Use --database-id for live read-only audit (requires NOTION_API_KEY).",
            file=sys.stderr,
        )
        return 1

    # Load schema
    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        return 1

    try:
        schema = load_expected_schema(schema_path)
    except Exception as exc:
        print(f"ERROR: Failed to load schema: {exc}", file=sys.stderr)
        return 1

    # Optional schema validation
    if args.validate_schema:
        errors = validate_schema(schema)
        if errors:
            print(
                f"ERROR: Schema validation failed with {len(errors)} error(s):",
                file=sys.stderr,
            )
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1

    # Load actual metadata
    actual_source: str
    try:
        if args.fixture:
            actual = load_actual_database_metadata(args.fixture)
            actual_source = args.fixture
        else:
            token = os.environ.get("NOTION_API_KEY", "")
            if not token:
                print(
                    "ERROR: NOTION_API_KEY environment variable is required "
                    "for --database-id mode. Use --fixture for offline mode.",
                    file=sys.stderr,
                )
                return 1
            actual = fetch_database_metadata_readonly(args.database_id, token)
            actual_source = f"notion:{args.database_id}"
    except Exception as exc:
        print(f"ERROR: Failed to load actual metadata: {exc}", file=sys.stderr)
        return 1

    # Compare
    diffs = compare_schema_to_database(schema, actual)
    report = build_audit_report(str(schema_path), actual_source, diffs)

    # Format
    if args.output_json:
        output = format_audit_json(report)
    elif args.output_markdown:
        output = format_audit_markdown(report)
    else:
        # Default: human-readable summary
        lines = [
            f"Audit: {report['schema_path']} vs {report['actual_source']}",
            f"  Verdict: {report['verdict']}",
            f"  Differences: {report['total_differences']}",
            f"  Blockers: {report['blockers']}",
            f"  Warnings: {report['warnings']}",
            f"  Info: {report['infos']}",
        ]
        if report["differences"]:
            lines.append("")
            for d in report["differences"]:
                lines.append(f"  [{d['severity'].upper()}] {d['field']}: {d['detail']}")
        output = "\n".join(lines)

    # Write or print
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output + "\n", encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(output)

    # Exit code
    if args.fail_on_blocker and report["blockers"] > 0:
        return 1
    if args.fail_on_warning and report["warnings"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
