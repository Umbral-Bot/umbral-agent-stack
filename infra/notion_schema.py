"""
Notion Schema — Loader and structural validator for Notion DB schema specs.

Loads schema YAML files and validates structural integrity: properties,
state machines, invariants, and recommended views.  No Notion API calls.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Valid Notion property types
# ---------------------------------------------------------------------------

VALID_PROPERTY_TYPES = frozenset({
    "title",
    "rich_text",
    "number",
    "select",
    "multi_select",
    "status",
    "date",
    "people",
    "files",
    "checkbox",
    "url",
    "email",
    "phone_number",
    "formula",
    "relation",
    "rollup",
    "created_time",
    "created_by",
    "last_edited_time",
    "last_edited_by",
})

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _require_yaml() -> None:
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load a Notion schema YAML file."""
    _require_yaml()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Schema file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Schema must be a YAML mapping: {p}")
    return data


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_database_metadata(schema: dict[str, Any]) -> list[str]:
    """Validate the database top-level metadata."""
    errors: list[str] = []
    db = schema.get("database")
    if not isinstance(db, dict):
        errors.append("Missing 'database' section")
        return errors
    for field in ("name", "version", "status"):
        if not db.get(field):
            errors.append(f"database.{field} is missing or empty")
    return errors


def validate_properties(schema: dict[str, Any]) -> list[str]:
    """Validate properties section."""
    errors: list[str] = []
    props = schema.get("properties")
    if not isinstance(props, list):
        errors.append("Missing 'properties' list")
        return errors

    names_seen: set[str] = set()
    has_title = False

    for i, prop in enumerate(props):
        if not isinstance(prop, dict):
            errors.append(f"Property {i} is not a mapping")
            continue

        name = prop.get("name", "")
        if not name:
            errors.append(f"Property {i} missing 'name'")
        elif name in names_seen:
            errors.append(f"Duplicate property name: {name}")
        names_seen.add(name)

        ptype = prop.get("type", "")
        if not ptype:
            errors.append(f"Property '{name}' missing 'type'")
        elif ptype not in VALID_PROPERTY_TYPES:
            errors.append(f"Property '{name}' invalid type: {ptype}")

        if ptype == "title":
            has_title = True

        if ptype == "select" and "options" in prop:
            option_names = [o.get("name", "") for o in prop["options"]]
            if len(option_names) != len(set(option_names)):
                errors.append(f"Property '{name}' has duplicate select options")

    if not has_title:
        errors.append("No property with type 'title' found (Notion requires one)")

    return errors


def validate_state_machine(schema: dict[str, Any]) -> list[str]:
    """Validate state machine transitions reference valid statuses."""
    errors: list[str] = []
    sm = schema.get("state_machine")
    if not isinstance(sm, dict):
        return errors  # state_machine is optional

    # Collect all status names from the Estado property
    all_statuses: set[str] = set()
    props = schema.get("properties", [])
    for prop in props:
        if prop.get("name") == "Estado" and prop.get("type") == "status":
            for group in prop.get("groups", []):
                for status in group.get("statuses", []):
                    all_statuses.add(status.get("name", ""))

    if not all_statuses:
        errors.append("State machine defined but no statuses found in Estado property")
        return errors

    initial = sm.get("initial")
    if initial and initial not in all_statuses:
        errors.append(f"State machine initial '{initial}' not in statuses")

    transitions = sm.get("transitions", [])
    for i, t in enumerate(transitions):
        froms = t.get("from", [])
        if isinstance(froms, str):
            froms = [froms]
        to = t.get("to", "")

        for f in froms:
            if f not in all_statuses:
                errors.append(f"Transition {i} 'from' status '{f}' not defined")
        if to and to not in all_statuses:
            errors.append(f"Transition {i} 'to' status '{to}' not defined")

    return errors


def validate_invariants(schema: dict[str, Any]) -> list[str]:
    """Validate invariants have required fields."""
    errors: list[str] = []
    invariants = schema.get("invariants")
    if not isinstance(invariants, list):
        return errors  # invariants are optional

    names_seen: set[str] = set()
    for i, inv in enumerate(invariants):
        if not isinstance(inv, dict):
            errors.append(f"Invariant {i} is not a mapping")
            continue
        name = inv.get("name", "")
        if not name:
            errors.append(f"Invariant {i} missing 'name'")
        elif name in names_seen:
            errors.append(f"Duplicate invariant name: {name}")
        names_seen.add(name)

        if not inv.get("description"):
            errors.append(f"Invariant '{name}' missing 'description'")

    return errors


def validate_schema(schema: dict[str, Any]) -> list[str]:
    """Run all validators on a schema and return combined errors."""
    errors: list[str] = []
    errors.extend(validate_database_metadata(schema))
    errors.extend(validate_properties(schema))
    errors.extend(validate_state_machine(schema))
    errors.extend(validate_invariants(schema))
    return errors


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def summarize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a summary of the schema for reporting."""
    db = schema.get("database", {})
    props = schema.get("properties", [])
    sm = schema.get("state_machine", {})
    invariants = schema.get("invariants", [])
    views = schema.get("recommended_views", [])

    prop_types: dict[str, int] = {}
    for p in props:
        t = p.get("type", "unknown")
        prop_types[t] = prop_types.get(t, 0) + 1

    required_count = sum(1 for p in props if p.get("required") is True)

    statuses: list[str] = []
    for p in props:
        if p.get("type") == "status":
            for g in p.get("groups", []):
                for s in g.get("statuses", []):
                    statuses.append(s.get("name", ""))

    channels: list[str] = []
    for p in props:
        if p.get("name") == "Canal" and p.get("type") == "select":
            channels = [o.get("name", "") for o in p.get("options", [])]

    return {
        "name": db.get("name", ""),
        "version": db.get("version", ""),
        "status": db.get("status", ""),
        "total_properties": len(props),
        "required_properties": required_count,
        "property_types": dict(sorted(prop_types.items())),
        "statuses": statuses,
        "channels": channels,
        "transitions": len(sm.get("transitions", [])),
        "invariants": len(invariants),
        "recommended_views": len(views),
    }
