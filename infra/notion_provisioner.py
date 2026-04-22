"""
Notion Provisioner — Offline dry-run planner for Notion DB provisioning.

Reads a validated local schema (YAML) and produces a structured provisioning
plan compatible with the Notion API ``databases.create`` payload shape.

**No HTTP calls are made.**  The ``apply`` path is intentionally not
implemented in this version and raises ``NotImplementedError``.

Usage::

    from infra.notion_provisioner import build_provisioning_plan

    plan = build_provisioning_plan("notion/schemas/publicaciones.schema.yaml")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.notion_schema import load_schema, validate_schema

# ---------------------------------------------------------------------------
# Notion property-type converters
# ---------------------------------------------------------------------------

# Maps local schema type names to Notion API property config builders.
# Each builder receives the property dict from the YAML and returns the
# Notion API property configuration value (the dict that goes inside
# ``properties.<name>``).

def _title_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"title": {}}


def _rich_text_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"rich_text": {}}


def _select_config(prop: dict[str, Any]) -> dict[str, Any]:
    options = []
    for opt in prop.get("options", []):
        entry: dict[str, Any] = {"name": opt["name"]}
        if "color" in opt:
            entry["color"] = opt["color"]
        options.append(entry)
    return {"select": {"options": options}}


def _status_config(prop: dict[str, Any]) -> dict[str, Any]:
    groups = []
    for group in prop.get("groups", []):
        statuses = []
        for s in group.get("statuses", []):
            entry: dict[str, Any] = {"name": s["name"]}
            if "color" in s:
                entry["color"] = s["color"]
            statuses.append(entry)
        groups.append({"name": group["name"], "statuses": statuses})
    return {"status": {"groups": groups}}


def _checkbox_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"checkbox": {}}


def _date_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"date": {}}


def _url_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"url": {}}


def _number_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"number": {}}


def _relation_config(prop: dict[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = {"relation": {}}
    if "relation_database" in prop:
        cfg["relation"]["database_name"] = prop["relation_database"]
    return cfg


def _created_by_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"created_by": {}}


def _last_edited_time_config(prop: dict[str, Any]) -> dict[str, Any]:
    return {"last_edited_time": {}}


def _multi_select_config(prop: dict[str, Any]) -> dict[str, Any]:
    options = []
    for opt in prop.get("options", []):
        entry: dict[str, Any] = {"name": opt["name"]}
        if "color" in opt:
            entry["color"] = opt["color"]
        options.append(entry)
    return {"multi_select": {"options": options}}


def _formula_config(prop: dict[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    if "expression" in prop:
        cfg["expression"] = prop["expression"]
    return {"formula": cfg}


def _rollup_config(prop: dict[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for key in ("relation_property", "rollup_property", "function"):
        if key in prop:
            cfg[key] = prop[key]
    return {"rollup": cfg}


_TYPE_CONVERTERS: dict[str, Any] = {
    "title": _title_config,
    "rich_text": _rich_text_config,
    "select": _select_config,
    "multi_select": _multi_select_config,
    "status": _status_config,
    "checkbox": _checkbox_config,
    "date": _date_config,
    "url": _url_config,
    "number": _number_config,
    "relation": _relation_config,
    "created_by": _created_by_config,
    "last_edited_time": _last_edited_time_config,
    "formula": _formula_config,
    "rollup": _rollup_config,
}


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def convert_property(prop: dict[str, Any]) -> dict[str, Any]:
    """Convert a single schema property to Notion API property config.

    Returns a dict with keys: ``name``, ``type``, ``config``, ``required``,
    and ``description``.
    """
    ptype = prop.get("type", "")
    converter = _TYPE_CONVERTERS.get(ptype)
    if converter is None:
        config = {ptype: {}}
    else:
        config = converter(prop)
    return {
        "name": prop.get("name", ""),
        "type": ptype,
        "config": config,
        "required": prop.get("required", False),
        "description": (prop.get("description") or "").strip(),
    }


def build_provisioning_plan(
    schema_path: str | Path,
    *,
    validate: bool = True,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Build a structured provisioning plan from a local schema file.

    Parameters
    ----------
    schema_path:
        Path to the YAML schema file.
    validate:
        Run schema validation before building the plan.  Raises
        ``ValueError`` if validation fails.
    dry_run:
        Must be ``True``.  Exists for forward-compatibility; passing
        ``False`` raises ``NotImplementedError``.

    Returns
    -------
    dict
        A JSON-serialisable plan suitable for review, persistence, or
        future execution against the Notion API.
    """
    if not dry_run:
        raise NotImplementedError(
            "apply mode is intentionally disabled in this version. "
            "Pass dry_run=True (the default) to generate an offline plan."
        )

    schema = load_schema(schema_path)

    if validate:
        errors = validate_schema(schema)
        if errors:
            raise ValueError(
                f"Schema validation failed with {len(errors)} error(s):\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    db = schema.get("database", {})
    properties_raw = schema.get("properties", [])
    invariants_raw = schema.get("invariants", [])
    views_raw = schema.get("recommended_views", [])
    sm = schema.get("state_machine", {})

    # Convert properties
    properties = [convert_property(p) for p in properties_raw]

    # Build Notion API-shaped properties dict
    api_properties: dict[str, Any] = {}
    for p in properties:
        api_properties[p["name"]] = p["config"]

    # Parent policy
    parent_policy = db.get("parent_policy", {})

    # Invariants as documentation
    invariants = []
    for inv in invariants_raw:
        invariants.append({
            "name": inv.get("name", ""),
            "description": (inv.get("description") or "").strip(),
            "check": (inv.get("check") or "").strip() or None,
        })

    # Recommended views as documentation
    views = []
    for v in views_raw:
        views.append({
            "name": v.get("name", ""),
            "type": v.get("type", ""),
            "group_by": v.get("group_by"),
            "filter": v.get("filter"),
            "sort": v.get("sort"),
            "description": (v.get("description") or "").strip() or None,
        })

    # State machine summary
    state_machine = None
    if sm:
        transitions = []
        for t in sm.get("transitions", []):
            transitions.append({
                "from": t.get("from"),
                "to": t.get("to"),
                "trigger": (t.get("trigger") or "").strip(),
                "gate": t.get("gate"),
            })
        state_machine = {
            "initial": sm.get("initial"),
            "transitions": transitions,
        }

    plan: dict[str, Any] = {
        "dry_run": True,
        "schema_path": str(schema_path),
        "database": {
            "name": db.get("name", ""),
            "version": db.get("version", ""),
            "status": db.get("status", ""),
            "owner": db.get("owner", ""),
            "description": (db.get("description") or "").strip(),
        },
        "parent_policy": {
            "recommended_parent": parent_policy.get("recommended_parent"),
            "forbidden_parents": parent_policy.get("forbidden_parents", []),
        },
        "properties": properties,
        "api_properties": api_properties,
        "state_machine": state_machine,
        "invariants": invariants,
        "recommended_views": views,
        "summary": {
            "total_properties": len(properties),
            "required_properties": sum(
                1 for p in properties if p["required"]
            ),
            "property_types": _count_types(properties),
            "channels": _extract_channels(properties),
        },
    }
    return plan


def _count_types(properties: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in properties:
        t = p["type"]
        counts[t] = counts.get(t, 0) + 1
    return dict(sorted(counts.items()))


def _extract_channels(properties: list[dict[str, Any]]) -> list[str]:
    for p in properties:
        if p["name"] == "Canal" and p["type"] == "select":
            options = p["config"].get("select", {}).get("options", [])
            return [o["name"] for o in options]
    return []


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def plan_to_json(plan: dict[str, Any]) -> str:
    """Serialise plan as indented JSON."""
    return json.dumps(plan, indent=2, ensure_ascii=False)


def plan_to_markdown(plan: dict[str, Any]) -> str:
    """Render plan as human-readable Markdown."""
    lines: list[str] = []
    db = plan["database"]
    lines.append(f"# Provisioning Plan: {db['name']}")
    lines.append("")
    lines.append(f"- **Version**: {db['version']}")
    lines.append(f"- **Status**: {db['status']}")
    lines.append(f"- **Owner**: {db['owner']}")
    lines.append(f"- **Dry run**: {plan['dry_run']}")
    lines.append(f"- **Schema**: `{plan['schema_path']}`")
    lines.append("")

    if db.get("description"):
        lines.append(f"> {db['description']}")
        lines.append("")

    # Parent policy
    pp = plan.get("parent_policy", {})
    if pp.get("recommended_parent"):
        lines.append("## Parent Policy")
        lines.append("")
        lines.append(f"- **Recommended parent**: {pp['recommended_parent']}")
        if pp.get("forbidden_parents"):
            lines.append(f"- **Forbidden parents**: {', '.join(pp['forbidden_parents'])}")
        lines.append("")

    # Summary
    s = plan["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total properties: {s['total_properties']}")
    lines.append(f"- Required: {s['required_properties']}")
    lines.append(f"- Channels: {', '.join(s['channels']) if s['channels'] else 'none'}")
    lines.append(f"- Property types: {s['property_types']}")
    lines.append("")

    # Properties table
    lines.append("## Properties")
    lines.append("")
    lines.append("| Name | Type | Required |")
    lines.append("|------|------|----------|")
    for p in plan["properties"]:
        req = "yes" if p["required"] else "no"
        lines.append(f"| {p['name']} | {p['type']} | {req} |")
    lines.append("")

    # State machine
    if plan.get("state_machine"):
        sm = plan["state_machine"]
        lines.append("## State Machine")
        lines.append("")
        lines.append(f"- **Initial**: {sm['initial']}")
        lines.append("")
        lines.append("| From | To | Gate |")
        lines.append("|------|----|------|")
        for t in sm["transitions"]:
            frm = t["from"] if isinstance(t["from"], str) else ", ".join(t["from"])
            gate = t.get("gate") or ""
            lines.append(f"| {frm} | {t['to']} | {gate} |")
        lines.append("")

    # Invariants
    if plan.get("invariants"):
        lines.append("## Invariants")
        lines.append("")
        for inv in plan["invariants"]:
            lines.append(f"- **{inv['name']}**: {inv['description']}")
        lines.append("")

    # Recommended views
    if plan.get("recommended_views"):
        lines.append("## Recommended Views")
        lines.append("")
        for v in plan["recommended_views"]:
            desc = f" — {v['description']}" if v.get("description") else ""
            lines.append(f"- **{v['name']}** ({v['type']}){desc}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Apply stub
# ---------------------------------------------------------------------------

def apply_plan(plan: dict[str, Any], *, apply: bool = False) -> None:
    """Apply a provisioning plan to Notion.

    **Not implemented.**  This function exists as a forward-compatibility
    stub.  A future PR will implement the actual Notion API call once
    the safety checklist is satisfied.

    Raises
    ------
    NotImplementedError
        Always, in this version.
    """
    raise NotImplementedError(
        "apply is intentionally disabled in this PR. "
        "The provisioner is dry-run only."
    )
