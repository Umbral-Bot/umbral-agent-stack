#!/usr/bin/env python3
"""
CLI: Notion Publicaciones setup checklist (offline).

Generates a human-readable checklist for manually creating the Notion
Publicaciones database structure.  No Notion API calls.  No environment
variables required.

Usage::

    PYTHONPATH=. .venv/bin/python scripts/notion_publicaciones_setup_checklist.py
    PYTHONPATH=. .venv/bin/python scripts/notion_publicaciones_setup_checklist.py --json
    PYTHONPATH=. .venv/bin/python scripts/notion_publicaciones_setup_checklist.py --include-property-table
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from infra.notion_provisioner import build_provisioning_plan

DEFAULT_SCHEMA = "notion/schemas/publicaciones.schema.yaml"
DEFAULT_PARENT = "Sistema Editorial Rick"

CRITICAL_PROPERTIES = [
    "aprobado_contenido",
    "autorizar_publicacion",
    "gate_invalidado",
    "content_hash",
    "idempotency_key",
]


def _build_checklist_data(
    plan: dict,
    parent_name: str,
) -> dict:
    """Build structured checklist data from a provisioning plan."""
    db = plan["database"]
    summary = plan["summary"]

    critical_found = []
    for p in plan["properties"]:
        if p["name"].lower().replace(" ", "_") in CRITICAL_PROPERTIES:
            critical_found.append({"name": p["name"], "type": p["type"]})

    statuses = []
    if plan.get("state_machine"):
        for t in plan["state_machine"].get("transitions", []):
            if isinstance(t["from"], list):
                for f in t["from"]:
                    if f not in statuses:
                        statuses.append(f)
            elif t["from"] not in statuses:
                statuses.append(t["from"])
            if t["to"] not in statuses:
                statuses.append(t["to"])
        if plan["state_machine"].get("initial") and plan["state_machine"]["initial"] not in statuses:
            statuses.insert(0, plan["state_machine"]["initial"])

    views = []
    for v in plan.get("recommended_views", []):
        views.append({
            "name": v["name"],
            "type": v["type"],
            "group_by": v.get("group_by"),
            "filter": v.get("filter"),
        })

    return {
        "title": "Setup checklist — Publicaciones",
        "parent_name": parent_name,
        "database_name": db["name"],
        "database_version": db["version"],
        "total_properties": summary["total_properties"],
        "required_properties": summary["required_properties"],
        "channels": summary["channels"],
        "critical_properties": critical_found,
        "statuses": statuses,
        "recommended_views": views,
        "properties": plan["properties"],
        "invariants": plan.get("invariants", []),
        "rick_status": "Rick todavía no participa. No activar Rick hasta que la DB esté creada, auditada con 0 blockers, y David apruebe explícitamente.",
        "post_creation_steps": [
            "Copiar database ID de Publicaciones.",
            "Registrar ID en docs/ops/notion-publicaciones-ids-template.md.",
            "Correr auditor read-only: scripts/audit_notion_publicaciones.py --database-id <id> --fail-on-blocker",
            "Verificar 0 blockers.",
            "No activar Rick todavía.",
        ],
    }


def _format_markdown(
    data: dict,
    include_property_table: bool = False,
    include_view_checklist: bool = False,
    include_audit_next_steps: bool = False,
) -> str:
    """Render checklist as Markdown."""
    lines: list[str] = []
    lines.append(f"# {data['title']}")
    lines.append("")
    lines.append(f"- **Parent page**: {data['parent_name']}")
    lines.append(f"- **Database**: {data['database_name']} v{data['database_version']}")
    lines.append(f"- **Total properties**: {data['total_properties']} ({data['required_properties']} required)")
    lines.append(f"- **Channels**: {', '.join(data['channels'])}")
    lines.append("")

    # Critical properties
    lines.append("## Critical properties")
    lines.append("")
    for cp in data["critical_properties"]:
        lines.append(f"- [ ] `{cp['name']}` ({cp['type']})")
    lines.append("")

    # Channels
    lines.append("## Channels")
    lines.append("")
    for ch in data["channels"]:
        note = " — preparado, no prioritario v1" if ch == "newsletter" else ""
        lines.append(f"- [ ] `{ch}`{note}")
    lines.append("")

    # Statuses
    if data["statuses"]:
        lines.append("## Statuses")
        lines.append("")
        for s in data["statuses"]:
            lines.append(f"- [ ] {s}")
        lines.append("")

    # Property table
    if include_property_table:
        lines.append("## Properties")
        lines.append("")
        lines.append("| Name | Type | Required |")
        lines.append("|------|------|----------|")
        for p in data["properties"]:
            req = "yes" if p["required"] else "no"
            lines.append(f"| {p['name']} | {p['type']} | {req} |")
        lines.append("")

    # View checklist
    if include_view_checklist:
        lines.append("## Recommended views")
        lines.append("")
        for v in data["recommended_views"]:
            f = f", filter: {v['filter']}" if v.get("filter") else ""
            g = f", group by: {v['group_by']}" if v.get("group_by") else ""
            lines.append(f"- [ ] **{v['name']}** ({v['type']}{g}{f})")
        lines.append("")

    # Rick status
    lines.append("## Rick status")
    lines.append("")
    lines.append(f"> {data['rick_status']}")
    lines.append("")

    # Post-creation steps
    lines.append("## Post-creation steps")
    lines.append("")
    for step in data["post_creation_steps"]:
        lines.append(f"1. {step}")
    lines.append("")

    # Audit next steps
    if include_audit_next_steps:
        lines.append("## Audit next steps")
        lines.append("")
        lines.append("After DB is created and ID is registered:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Generate provisioning plan")
        lines.append("PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --markdown")
        lines.append("")
        lines.append("# Run read-only audit against real DB")
        lines.append("export NOTION_API_KEY=\"ntn_...\"")
        lines.append("PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \\")
        lines.append("    --database-id <publicaciones-db-id> --validate-schema --fail-on-blocker")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Notion Publicaciones setup checklist (offline)."
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Path to schema YAML (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--parent-name",
        default=DEFAULT_PARENT,
        help=f"Suggested parent page name (default: {DEFAULT_PARENT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        dest="output_markdown",
        help="Output as Markdown (default).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write to file instead of stdout.",
    )
    parser.add_argument(
        "--include-property-table",
        action="store_true",
        help="Include full property table in output.",
    )
    parser.add_argument(
        "--include-view-checklist",
        action="store_true",
        help="Include recommended views checklist.",
    )
    parser.add_argument(
        "--include-audit-next-steps",
        action="store_true",
        help="Include audit commands as next steps.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="(NOT AVAILABLE) This runbook does not support apply.",
    )

    args = parser.parse_args(argv)

    if args.apply:
        print(
            "ERROR: --apply is not available. This is a setup runbook/checklist "
            "for manual creation. No automated apply exists.",
            file=sys.stderr,
        )
        return 1

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        return 1

    try:
        plan = build_provisioning_plan(schema_path, validate=True, dry_run=True)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    data = _build_checklist_data(plan, args.parent_name)

    if args.output_json:
        output = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        output = _format_markdown(
            data,
            include_property_table=args.include_property_table,
            include_view_checklist=args.include_view_checklist,
            include_audit_next_steps=args.include_audit_next_steps,
        )

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output + "\n", encoding="utf-8")
        print(f"Checklist written to {out_path}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
