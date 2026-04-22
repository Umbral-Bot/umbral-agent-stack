"""
Notion Read-Only Audit — Compare local schema against Notion DB metadata.

Compares the approved local Publicaciones schema (YAML) against either a
fixture JSON file or a live Notion database (via GET only).  Produces a
structured audit report with severity levels: blocker, warning, info.

**No writes to Notion.**  Only GET is used when fetching live metadata.
Fixture mode requires no environment variables at all.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from infra.notion_schema import load_schema

# ---------------------------------------------------------------------------
# Critical fields — missing or type-mismatched = blocker
# ---------------------------------------------------------------------------

CRITICAL_FIELDS: frozenset[str] = frozenset({
    "aprobado_contenido",
    "autorizar_publicacion",
    "gate_invalidado",
    "content_hash",
    "idempotency_key",
    "canal",
    "estado",
})

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize a property name for comparison.

    - Lowercase
    - Replace spaces and hyphens with underscores
    - Strip accents (NFD decomposition, remove combining chars)
    """
    # NFD decompose then strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Schema loaders
# ---------------------------------------------------------------------------


def load_expected_schema(path: str | Path) -> dict[str, Any]:
    """Load the local YAML schema and return it."""
    return load_schema(path)


def load_actual_database_metadata(path_or_dict: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load Notion database metadata from a JSON fixture file or dict."""
    if isinstance(path_or_dict, dict):
        return path_or_dict
    p = Path(path_or_dict)
    if not p.exists():
        raise FileNotFoundError(f"Fixture file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Fixture must be a JSON object: {p}")
    return data


def fetch_database_metadata_readonly(
    database_id: str,
    notion_token: str,
) -> dict[str, Any]:
    """Fetch database metadata from Notion API (GET only).

    Parameters
    ----------
    database_id:
        The Notion database ID.
    notion_token:
        The Notion integration token.  **Never printed or logged.**

    Returns
    -------
    dict
        The parsed JSON response from ``GET /v1/databases/{database_id}``.

    Raises
    ------
    ValueError
        If token is empty.
    RuntimeError
        If the API call fails.
    """
    if not notion_token or not notion_token.strip():
        raise ValueError(
            "NOTION_API_KEY is required for live database fetch. "
            "Use --fixture for offline mode."
        )
    if not database_id or not database_id.strip():
        raise ValueError("database_id must not be empty.")

    url = f"https://api.notion.com/v1/databases/{database_id.strip()}"
    req = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {notion_token.strip()}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(
            f"Notion API returned HTTP {exc.code} for database {database_id}. "
            "Check that the database ID is correct and the integration has access."
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"Failed to connect to Notion API: {exc.reason}"
        ) from exc


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------


def _extract_expected_properties(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract properties from local schema, keyed by normalized name."""
    props = {}
    for p in schema.get("properties", []):
        name = p.get("name", "")
        norm = normalize_name(name)
        props[norm] = {
            "original_name": name,
            "type": p.get("type", ""),
            "required": p.get("required", False),
            "options": _extract_options(p),
        }
    return props


def _extract_actual_properties(db_meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract properties from Notion database metadata, keyed by normalized name."""
    props = {}
    for name, config in db_meta.get("properties", {}).items():
        norm = normalize_name(name)
        ptype = config.get("type", "")
        props[norm] = {
            "original_name": name,
            "type": ptype,
            "options": _extract_actual_options(config, ptype),
        }
    return props


def _extract_options(prop: dict[str, Any]) -> list[str]:
    """Extract option names from a local schema property."""
    ptype = prop.get("type", "")
    if ptype in ("select", "multi_select"):
        return [o.get("name", "") for o in prop.get("options", [])]
    if ptype == "status":
        options = []
        for group in prop.get("groups", []):
            for s in group.get("statuses", []):
                options.append(s.get("name", ""))
        return options
    return []


def _extract_actual_options(config: dict[str, Any], ptype: str) -> list[str]:
    """Extract option names from Notion API property config."""
    if ptype in ("select", "multi_select"):
        sub = config.get(ptype, {})
        return [o.get("name", "") for o in sub.get("options", [])]
    if ptype == "status":
        sub = config.get("status", {})
        return [o.get("name", "") for o in sub.get("options", [])]
    return []


def compare_schema_to_database(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare local schema against Notion DB metadata.

    Returns a list of difference dicts, each with keys:
    ``field``, ``issue``, ``severity``, ``detail``.
    """
    diffs: list[dict[str, Any]] = []

    exp_props = _extract_expected_properties(expected)
    act_props = _extract_actual_properties(actual)

    exp_keys = set(exp_props.keys())
    act_keys = set(act_props.keys())

    # Missing properties
    for norm in sorted(exp_keys - act_keys):
        ep = exp_props[norm]
        is_critical = norm in CRITICAL_FIELDS
        diffs.append({
            "field": ep["original_name"],
            "normalized": norm,
            "issue": "missing_property",
            "severity": "blocker" if is_critical else "warning",
            "detail": f"Expected property '{ep['original_name']}' ({ep['type']}) not found in Notion DB.",
        })

    # Extra properties
    for norm in sorted(act_keys - exp_keys):
        ap = act_props[norm]
        diffs.append({
            "field": ap["original_name"],
            "normalized": norm,
            "issue": "extra_property",
            "severity": "info",
            "detail": f"Property '{ap['original_name']}' ({ap['type']}) exists in Notion but not in local schema.",
        })

    # Shared properties — check type and options
    for norm in sorted(exp_keys & act_keys):
        ep = exp_props[norm]
        ap = act_props[norm]
        is_critical = norm in CRITICAL_FIELDS

        # Name casing difference
        if ep["original_name"] != ap["original_name"]:
            diffs.append({
                "field": ep["original_name"],
                "normalized": norm,
                "issue": "name_casing",
                "severity": "warning",
                "detail": f"Name differs: schema='{ep['original_name']}', Notion='{ap['original_name']}'.",
            })

        # Type mismatch
        if ep["type"] != ap["type"]:
            diffs.append({
                "field": ep["original_name"],
                "normalized": norm,
                "issue": "type_mismatch",
                "severity": "blocker" if is_critical else "warning",
                "detail": f"Type differs: schema='{ep['type']}', Notion='{ap['type']}'.",
            })

        # Option differences (select, multi_select, status)
        exp_options = set(ep["options"])
        act_options = set(ap["options"])

        missing_options = exp_options - act_options
        extra_options = act_options - exp_options

        if missing_options:
            diffs.append({
                "field": ep["original_name"],
                "normalized": norm,
                "issue": "missing_options",
                "severity": "warning",
                "detail": f"Missing options in Notion: {sorted(missing_options)}.",
            })

        if extra_options:
            diffs.append({
                "field": ep["original_name"],
                "normalized": norm,
                "issue": "extra_options",
                "severity": "info",
                "detail": f"Extra options in Notion: {sorted(extra_options)}.",
            })

    return diffs


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_audit_report(
    schema_path: str,
    actual_source: str,
    diffs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a structured audit report."""
    blockers = [d for d in diffs if d["severity"] == "blocker"]
    warnings = [d for d in diffs if d["severity"] == "warning"]
    infos = [d for d in diffs if d["severity"] == "info"]

    return {
        "schema_path": schema_path,
        "actual_source": actual_source,
        "total_differences": len(diffs),
        "blockers": len(blockers),
        "warnings": len(warnings),
        "infos": len(infos),
        "verdict": "FAIL" if blockers else ("WARN" if warnings else "PASS"),
        "differences": diffs,
    }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_audit_json(report: dict[str, Any]) -> str:
    """Serialize audit report as JSON."""
    return json.dumps(report, indent=2, ensure_ascii=False)


def format_audit_markdown(report: dict[str, Any]) -> str:
    """Render audit report as Markdown."""
    lines: list[str] = []
    lines.append("# Notion Publicaciones — Read-Only Audit Report")
    lines.append("")
    lines.append(f"- **Schema**: `{report['schema_path']}`")
    lines.append(f"- **Actual source**: `{report['actual_source']}`")
    lines.append(f"- **Verdict**: **{report['verdict']}**")
    lines.append(f"- **Total differences**: {report['total_differences']}")
    lines.append(f"- **Blockers**: {report['blockers']}")
    lines.append(f"- **Warnings**: {report['warnings']}")
    lines.append(f"- **Info**: {report['infos']}")
    lines.append("")

    if not report["differences"]:
        lines.append("No differences found. Schema and database are aligned.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Differences")
    lines.append("")
    lines.append("| Severity | Field | Issue | Detail |")
    lines.append("|----------|-------|-------|--------|")
    for d in report["differences"]:
        sev = d["severity"].upper()
        lines.append(f"| {sev} | {d['field']} | {d['issue']} | {d['detail']} |")
    lines.append("")

    return "\n".join(lines)
