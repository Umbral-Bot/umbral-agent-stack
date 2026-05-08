"""Stage 7.5 helper — additive schema migration for the Publicaciones DB.

Reads the live Notion data source schema for the Publicaciones DB and applies
ONLY additive changes:

  * Adds missing properties (``Copy LinkedIn`` rich_text, ``Visual asset URL``
    url) when absent.
  * Adds missing options to ``Estado`` if-and-only-if it is a ``select``
    property (additive, never destructive).

NEVER:

  * Removes existing properties.
  * Removes existing options.
  * Changes a property's type.
  * Mutates ``status`` properties (Notion API does not allow option mutation
    on ``status`` types — those must be edited in the UI). When ``Estado`` is
    type ``status`` the script reports ``type_mismatch_no_action`` and skips.

Default mode is dry-run (no PATCH issued). Pass ``--commit`` to apply changes.
Idempotent: running with ``--commit`` twice in a row leaves the second run
with an empty plan.

Usage::

    python scripts/discovery/migrate_publicaciones_schema.py [--db-id ID]
                                                             [--commit]
                                                             [--pretty]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import httpx

# Allow running this file directly via ``python scripts/discovery/...`` in
# addition to ``python -m scripts.discovery....`` — the former does not put
# the repo root on sys.path automatically.
if __package__ in (None, ""):
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from scripts.discovery.check_publicaciones_schema import (
    DEFAULT_DB_ID,
    NOTION_API_BASE,
    NOTION_VERSION,
    build_headers,
    build_report,
    fetch_data_source,
    fetch_database,
    resolve_data_source_id,
)

# Concrete schema-payload templates used when a property must be created.
PROPERTY_CREATE_TEMPLATES: dict[str, dict[str, Any]] = {
    "rich_text": {"rich_text": {}},
    "url": {"url": {}},
    "select": {"select": {"options": []}},
}


@dataclass
class PlanAction:
    kind: str  # add_property | add_options | skip_status | skip_type_mismatch
    name: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_plan(report: dict[str, Any]) -> list[PlanAction]:
    """Translate the check_schema report into a concrete migration plan."""
    plan: list[PlanAction] = []
    for chk in report["checks"]:
        status = chk["status"]
        name = chk["name"]
        if status == "ok":
            continue
        if status == "missing_property":
            plan.append(
                PlanAction(
                    kind="add_property",
                    name=name,
                    detail={
                        "type": chk["required_type"],
                        "options": chk.get("required_options") or [],
                    },
                )
            )
        elif status == "options_missing":
            plan.append(
                PlanAction(
                    kind="add_options",
                    name=name,
                    detail={
                        "type": chk["actual_type"],
                        "missing_options": chk["missing_options"],
                        "actual_options": chk["actual_options"],
                    },
                )
            )
        elif status == "type_mismatch_no_action":
            plan.append(
                PlanAction(
                    kind="skip_status",
                    name=name,
                    detail={
                        "actual_type": chk["actual_type"],
                        "required_type": chk["required_type"],
                        "missing_options": chk.get("missing_options") or [],
                        "note": chk.get("note"),
                    },
                )
            )
        elif status == "type_mismatch":
            plan.append(
                PlanAction(
                    kind="skip_type_mismatch",
                    name=name,
                    detail={
                        "actual_type": chk["actual_type"],
                        "required_type": chk["required_type"],
                    },
                )
            )
    return plan


def render_property_patch(action: PlanAction) -> dict[str, Any]:
    """Render the JSON fragment for a single property within a PATCH body."""
    if action.kind == "add_property":
        ptype = action.detail["type"]
        if ptype not in PROPERTY_CREATE_TEMPLATES:
            raise ValueError(f"Unsupported property type for creation: {ptype}")
        body = json.loads(json.dumps(PROPERTY_CREATE_TEMPLATES[ptype]))
        if ptype == "select":
            opts = action.detail.get("options") or []
            body["select"]["options"] = [{"name": o} for o in opts]
        return body
    if action.kind == "add_options":
        ptype = action.detail["type"]
        if ptype not in ("select", "multi_select"):
            raise ValueError(f"Cannot add options to non-select type: {ptype}")
        all_opts = list(action.detail["actual_options"]) + [
            o for o in action.detail["missing_options"]
            if o not in action.detail["actual_options"]
        ]
        return {ptype: {"options": [{"name": o} for o in all_opts]}}
    raise ValueError(f"render_property_patch called on non-mutating kind: {action.kind}")


def build_patch_body(plan: list[PlanAction]) -> dict[str, Any] | None:
    """Aggregate the plan into a single ``PATCH /v1/data_sources/{id}`` body."""
    properties: dict[str, Any] = {}
    for action in plan:
        if action.kind in ("add_property", "add_options"):
            properties[action.name] = render_property_patch(action)
    if not properties:
        return None
    return {"properties": properties}


def apply_patch(
    client: httpx.Client, data_source_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    r = client.patch(f"/data_sources/{data_source_id}", json=body)
    r.raise_for_status()
    return r.json()


def run(
    db_id: str,
    *,
    commit: bool = False,
    token: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Public entrypoint used by tests + CLI."""
    token = token or os.environ.get("NOTION_API_KEY", "")
    if not token:
        raise RuntimeError("NOTION_API_KEY not set")

    own_client = client is None
    client = client or httpx.Client(
        base_url=NOTION_API_BASE, headers=build_headers(token), timeout=30.0
    )
    try:
        db = fetch_database(client, db_id)
        ds_id = resolve_data_source_id(db)
        if not ds_id:
            raise RuntimeError(f"DB {db_id} has no data_sources")
        ds = fetch_data_source(client, ds_id)
        report = build_report(db, ds, db_id=db_id)
        plan = build_plan(report)
        patch_body = build_patch_body(plan)

        result: dict[str, Any] = {
            "db_id": db_id,
            "data_source_id": ds_id,
            "dry_run": not commit,
            "plan": [a.to_dict() for a in plan],
            "patch_body": patch_body,
            "applied": False,
            "skipped_due_to_status_property": [
                a.name for a in plan if a.kind == "skip_status"
            ],
            "skipped_due_to_type_mismatch": [
                a.name for a in plan if a.kind == "skip_type_mismatch"
            ],
        }

        if commit and patch_body:
            apply_patch(client, ds_id, patch_body)
            result["applied"] = True
        elif commit and not patch_body:
            # Nothing to do; idempotent no-op.
            result["applied"] = False
            result["note"] = "no_changes_required"

        return result
    finally:
        if own_client:
            client.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-id", default=DEFAULT_DB_ID)
    p.add_argument("--commit", action="store_true",
                   help="Apply additive changes via PATCH. Default: dry-run.")
    p.add_argument("--pretty", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run(args.db_id, commit=args.commit)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except httpx.HTTPStatusError as exc:
        print(
            f"ERROR: Notion API HTTP {exc.response.status_code}: "
            f"{exc.response.text[:300]}",
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
