"""Stage 7.5 helper — read-only audit of the Publicaciones DB schema.

Compares the live Notion schema for the Publicaciones DB
(``e6817ec4698a4f0fbbc8fedcf4e52472``) against the spec required by Stage 7.5
(Hilo A) and emits a JSON diff to stdout.

Required (per Stage 7.5 spec):

    | Property         | Type      | Notes                               |
    | ---------------- | --------- | ----------------------------------- |
    | Copy LinkedIn    | rich_text | created if missing                  |
    | Estado           | select    | options: Borrador, En revisión,     |
    |                  |           | Autorizado, Rechazado, Publicado    |
    | Visual asset URL | url       | should already exist (Stage 8)      |

Notion API divergences this script tolerates:
  * If ``Estado`` exists as ``status`` (not ``select``) — Notion does not let
    integrations mutate ``status`` options via the REST API; we report
    ``type_mismatch_no_action`` and surface the existing status options so
    Hilo A can map ``En revisión → Revisión pendiente`` (or equivalent).
  * If ``Estado`` is a ``select`` and only some required options are missing,
    we report ``options_missing`` with the list to add (additively, never
    destructively).

Output is a JSON document with a top-level ``ok`` flag (``true`` iff every
required property is present with a matching type and no missing options).
The script is purely read-only; it never PATCHes anything.

Usage::

    python scripts/discovery/check_publicaciones_schema.py [--db-id ID]
                                                           [--pretty]

Exit codes::

    0 — schema matches spec (``ok=true``)
    1 — divergence (``ok=false``)
    2 — unrecoverable error (auth, network, 401/403/404)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
DEFAULT_DB_ID = "e6817ec4698a4f0fbbc8fedcf4e52472"

REQUIRED_PROPS: dict[str, dict[str, Any]] = {
    "Copy LinkedIn": {"type": "rich_text"},
    "Estado": {
        "type": "select",
        "options": ["Borrador", "En revisión", "Autorizado", "Rechazado", "Publicado"],
    },
    "Visual asset URL": {"type": "url"},
}


# ---------------------------------------------------------------------------
# Notion HTTP
# ---------------------------------------------------------------------------

def build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def fetch_database(client: httpx.Client, db_id: str) -> dict[str, Any]:
    r = client.get(f"/databases/{db_id}")
    r.raise_for_status()
    return r.json()


def fetch_data_source(client: httpx.Client, data_source_id: str) -> dict[str, Any]:
    r = client.get(f"/data_sources/{data_source_id}")
    r.raise_for_status()
    return r.json()


def resolve_data_source_id(database: dict[str, Any]) -> str | None:
    """Return the first data_source id of the DB (API 2025-09-03)."""
    sources = database.get("data_sources") or []
    if sources:
        return sources[0].get("id")
    return None


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

@dataclass
class PropertyCheck:
    name: str
    required_type: str
    actual_type: str | None
    status: str  # ok | missing_property | type_mismatch | options_missing | type_mismatch_no_action
    required_options: list[str] = field(default_factory=list)
    actual_options: list[str] = field(default_factory=list)
    missing_options: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _option_names(prop: dict[str, Any]) -> list[str]:
    """Return the option names of a select/multi_select/status property."""
    t = prop.get("type")
    if t in ("select", "multi_select", "status"):
        return [o.get("name", "") for o in (prop.get(t) or {}).get("options", [])]
    return []


def diff_property(
    name: str, required: dict[str, Any], actual: dict[str, Any] | None
) -> PropertyCheck:
    req_type = required["type"]
    req_options = list(required.get("options") or [])

    if actual is None:
        return PropertyCheck(
            name=name,
            required_type=req_type,
            actual_type=None,
            status="missing_property",
            required_options=req_options,
        )

    act_type = actual.get("type")
    act_options = _option_names(actual)

    if act_type != req_type:
        # Special case: Estado spec asks `select` but Notion may host it as
        # `status`. Status options are not API-mutable; report and move on.
        if req_type == "select" and act_type == "status":
            missing = [o for o in req_options if o not in act_options]
            return PropertyCheck(
                name=name,
                required_type=req_type,
                actual_type=act_type,
                status="type_mismatch_no_action",
                required_options=req_options,
                actual_options=act_options,
                missing_options=missing,
                note=(
                    "Estado is a 'status' property; Notion API cannot mutate "
                    "status options. Map required options to existing status "
                    "options in Stage 7.5 (Hilo A) instead of migrating."
                ),
            )
        return PropertyCheck(
            name=name,
            required_type=req_type,
            actual_type=act_type,
            status="type_mismatch",
            required_options=req_options,
            actual_options=act_options,
            note="Type mismatch; manual reconciliation required.",
        )

    # Same type. Check options for select / multi_select only.
    if req_options and act_type in ("select", "multi_select"):
        missing = [o for o in req_options if o not in act_options]
        if missing:
            return PropertyCheck(
                name=name,
                required_type=req_type,
                actual_type=act_type,
                status="options_missing",
                required_options=req_options,
                actual_options=act_options,
                missing_options=missing,
            )

    return PropertyCheck(
        name=name,
        required_type=req_type,
        actual_type=act_type,
        status="ok",
        required_options=req_options,
        actual_options=act_options,
    )


def build_report(
    database: dict[str, Any],
    data_source: dict[str, Any] | None,
    *,
    db_id: str,
) -> dict[str, Any]:
    ds_id = resolve_data_source_id(database)
    props = (data_source or {}).get("properties", {}) if data_source else {}

    checks: list[PropertyCheck] = []
    for name, spec in REQUIRED_PROPS.items():
        checks.append(diff_property(name, spec, props.get(name)))

    ok = all(c.status == "ok" for c in checks)

    return {
        "ok": ok,
        "db_id": db_id,
        "data_source_id": ds_id,
        "checks": [c.to_dict() for c in checks],
        "summary": {
            "missing_properties": [c.name for c in checks if c.status == "missing_property"],
            "type_mismatches": [c.name for c in checks if c.status == "type_mismatch"],
            "type_mismatches_no_action": [
                c.name for c in checks if c.status == "type_mismatch_no_action"
            ],
            "options_missing": {
                c.name: c.missing_options for c in checks if c.status == "options_missing"
            },
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(
    db_id: str,
    *,
    token: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Public entrypoint used by tests."""
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
        ds = fetch_data_source(client, ds_id) if ds_id else None
        return build_report(db, ds, db_id=db_id)
    finally:
        if own_client:
            client.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-id", default=DEFAULT_DB_ID)
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = run(args.db_id)
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

    indent = 2 if args.pretty else None
    print(json.dumps(report, indent=indent, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
