#!/usr/bin/env python3
"""
CLI: Plan Notion Publicaciones provisioning (dry-run only).

Reads the approved local schema and generates a structured provisioning
plan.  No Notion API calls are made.  No environment variables required.

Usage::

    PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py
    PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate
    PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --json
    PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --markdown
    PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --json --output plan.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from infra.notion_provisioner import (
    build_provisioning_plan,
    plan_to_json,
    plan_to_markdown,
)

DEFAULT_SCHEMA = "notion/schemas/publicaciones.schema.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan Notion Publicaciones DB provisioning (dry-run only)."
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Path to schema YAML (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run schema validation before generating the plan.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output plan as JSON.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        dest="output_markdown",
        help="Output plan as Markdown.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write plan to file instead of stdout.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="(DISABLED) Apply the plan to Notion. Fails with an error.",
    )

    args = parser.parse_args(argv)

    if args.apply:
        print(
            "ERROR: --apply is intentionally disabled in this PR. "
            "The provisioner is dry-run only. No Notion API calls are made.",
            file=sys.stderr,
        )
        return 1

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        return 1

    try:
        plan = build_provisioning_plan(
            schema_path,
            validate=args.validate,
            dry_run=True,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Format output
    if args.output_json:
        output = plan_to_json(plan)
    elif args.output_markdown:
        output = plan_to_markdown(plan)
    else:
        # Default: human-readable summary
        s = plan["summary"]
        db = plan["database"]
        lines = [
            f"Provisioning plan (dry run): {db['name']} v{db['version']}",
            f"  Schema: {plan['schema_path']}",
            f"  Properties: {s['total_properties']} ({s['required_properties']} required)",
            f"  Channels: {', '.join(s['channels'])}",
            f"  Property types: {s['property_types']}",
        ]
        if plan.get("state_machine"):
            lines.append(
                f"  Transitions: {len(plan['state_machine']['transitions'])}"
            )
        lines.append(f"  Invariants: {len(plan['invariants'])}")
        lines.append(f"  Recommended views: {len(plan['recommended_views'])}")
        if args.validate:
            lines.append("  Validation: passed")
        output = "\n".join(lines)

    # Write or print
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output + "\n", encoding="utf-8")
        print(f"Plan written to {out_path}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
