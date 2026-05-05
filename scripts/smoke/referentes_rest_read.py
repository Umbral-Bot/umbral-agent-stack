#!/usr/bin/env python3
"""Smoke test read-only para la DB Notion `Referentes`.

Autoridad runtime: mismo `NOTION_API_KEY` que usa `worker.config`.

Notas de seguridad:
- No lee secretos desde `notion-governance`.
- No usa PATCH, DELETE ni endpoints de escritura.
- Notion REST expone la lectura de filas de una data source como
  `POST /v1/data_sources/{id}/query`; este script permite solo ese POST
  read-only y bloquea cualquier otro POST.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

NOTION_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_API_VERSION = "2025-09-03"

REFERENTES_REGISTRY_KEY = "referencias_referentes"
EXPECTED_ROW_COUNT = 26

NEW_CHANNEL_COLUMNS = [
    "LinkedIn activity feed",
    "YouTube channel",
    "Web / Newsletter",
    "RSS feed",
    "Otros canales",
    "Última actividad detectada",
    "Confianza canales",
    "Flags canales",
    "Notas canales",
    "Última auditoría canales",
]
CHANNEL_COLUMNS = [
    "LinkedIn activity feed",
    "YouTube channel",
    "Web / Newsletter",
    "RSS feed",
    "Otros canales",
]
ALLOWED_CONFIANZA = {"ALTA", "MEDIA", "BAJA", "DUPLICADO"}
ALLOWED_FLAGS = {
    "ACTIVIDAD_BAJA",
    "POSIBLE_INACTIVO",
    "SLUG_DIFIERE",
    "DUP",
    "RSS_NO_CONFIRMADO",
    "REQUIERE_VERIFICACION_MANUAL",
    "SIN_LINKEDIN",
    "CAMBIO_DE_PLATAFORMA",
}
REQUIRED_SAMPLE_CONFIDENCES = ("ALTA", "MEDIA", "DUPLICADO")


class SmokeSetupError(RuntimeError):
    """Raised when local/runtime prerequisites are not available."""


@dataclass(frozen=True)
class RegistryEntry:
    data_source_id: str
    database_id: str | None
    expected_row_count: int
    expected_columns: list[str]
    expected_confianza: set[str]
    expected_flags: set[str]
    registry_path: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_registry_path() -> Path:
    return repo_root().parent / "notion-governance" / "registry" / "notion-data-sources.template.yaml"


def resolve_registry_path(explicit_path: str | None = None) -> Path:
    path = Path(explicit_path).expanduser() if explicit_path else default_registry_path()
    if path.exists():
        return path

    raise SmokeSetupError(
        "Missing notion-governance registry. Mount the sibling repo at "
        f"{default_registry_path()} or pass --registry <path>. "
        "Do not hardcode data_source_id in this repo."
    )


def load_registry_entry(path: Path) -> RegistryEntry:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entry = _find_referentes_registry_entry(data)
    if not isinstance(entry, dict):
        raise SmokeSetupError(
            f"Registry key {REFERENTES_REGISTRY_KEY} not found in {path}"
        )

    data_source_id = str(entry.get("data_source_id") or "").strip()
    if not data_source_id:
        raise SmokeSetupError(f"Registry entry {REFERENTES_REGISTRY_KEY} has no data_source_id")

    runtime_notes = entry.get("runtime_notes") or {}
    schema_extension = runtime_notes.get("schema_extension_2026_05_05") or {}
    new_columns = schema_extension.get("new_columns") or []

    expected_columns: list[str] = []
    expected_confianza = set(ALLOWED_CONFIANZA)
    expected_flags = set(ALLOWED_FLAGS)
    for column in new_columns:
        if not isinstance(column, dict):
            continue
        name = str(column.get("name") or "").strip()
        if name:
            expected_columns.append(name)
        if name == "Confianza canales" and isinstance(column.get("values"), list):
            expected_confianza = {str(v) for v in column["values"]}
        if name == "Flags canales" and isinstance(column.get("values"), list):
            expected_flags = {str(v) for v in column["values"]}

    if not expected_columns:
        expected_columns = list(NEW_CHANNEL_COLUMNS)

    expected_row_count = int(runtime_notes.get("population_2026_05_05") or EXPECTED_ROW_COUNT)

    return RegistryEntry(
        data_source_id=data_source_id,
        database_id=str(entry.get("database_id") or "").strip() or None,
        expected_row_count=expected_row_count,
        expected_columns=expected_columns,
        expected_confianza=expected_confianza,
        expected_flags=expected_flags,
        registry_path=str(path),
    )


def _find_referentes_registry_entry(data: dict[str, Any]) -> dict[str, Any] | None:
    for section_name in ("critical_databases", "reference_systems"):
        section = data.get(section_name) or {}
        entry = section.get(REFERENTES_REGISTRY_KEY)
        if isinstance(entry, dict):
            return entry
    return None


def get_runtime_notion_api_key() -> str:
    # Import intentionally happens at runtime so `worker.config` can load
    # ~/.config/openclaw/env on VPS/Linux exactly as the worker does.
    from worker import config

    api_key = config.NOTION_API_KEY
    if not api_key:
        raise SmokeSetupError(
            "NOTION_API_KEY is not configured in the worker runtime environment. "
            "Source it from the same environment used by umbral-worker before running this smoke."
        )
    return api_key


def notion_api_version() -> str:
    return os.environ.get("NOTION_API_VERSION") or DEFAULT_NOTION_API_VERSION


def _headers(api_key: str, api_version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": api_version,
        "Content-Type": "application/json",
    }


def _notion_request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    api_key: str,
    api_version: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method = method.upper()
    if method in {"PATCH", "DELETE"}:
        raise RuntimeError(f"Mutation method blocked in smoke script: {method}")
    if method == "POST" and not path.endswith("/query"):
        raise RuntimeError(f"Non-query POST blocked in smoke script: {path}")

    response = client.request(
        method,
        f"{NOTION_BASE_URL}{path}",
        headers=_headers(api_key, api_version),
        json=payload if method == "POST" else None,
    )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Notion {method} {path} failed ({response.status_code}): {detail}")
    return response.json()


def fetch_data_source_rows(
    data_source_id: str,
    *,
    api_key: str,
    api_version: str,
    timeout: float = 30.0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout) as client:
        data_source = _notion_request(
            client,
            "GET",
            f"/data_sources/{data_source_id}",
            api_key=api_key,
            api_version=api_version,
        )
        start_cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            page = _notion_request(
                client,
                "POST",
                f"/data_sources/{data_source_id}/query",
                api_key=api_key,
                api_version=api_version,
                payload=payload,
            )
            rows.extend(page.get("results") or [])
            if not page.get("has_more"):
                break
            start_cursor = page.get("next_cursor")
            if not start_cursor:
                break
    return data_source, rows


def extract_property_value(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(item.get("plain_text", "") for item in prop.get("title") or [])
    if prop_type == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text") or [])
    if prop_type == "url":
        return prop.get("url")
    if prop_type == "select":
        selected = prop.get("select")
        return selected.get("name") if isinstance(selected, dict) else None
    if prop_type == "multi_select":
        return [item.get("name") for item in prop.get("multi_select") or [] if item.get("name")]
    if prop_type == "date":
        date = prop.get("date")
        return date.get("start") if isinstance(date, dict) else None
    return prop.get(prop_type)


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    properties = row.get("properties") or {}
    normalized = {name: extract_property_value(value) for name, value in properties.items()}
    return {
        "id": row.get("id"),
        "url": row.get("url"),
        "properties": normalized,
        "raw_property_names": set(properties.keys()),
    }


def is_valid_url(value: str | None) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _safe_row_sample(row: dict[str, Any]) -> dict[str, Any]:
    props = row["properties"]
    populated_channels = [
        channel for channel in CHANNEL_COLUMNS if str(props.get(channel) or "").strip()
    ]
    row_id = str(row.get("id") or "")
    return {
        "row_id_tail": row_id[-8:] if row_id else None,
        "nombre": props.get("Nombre"),
        "confianza_canales": props.get("Confianza canales"),
        "flags_canales": props.get("Flags canales") or [],
        "channels_populated": populated_channels,
    }


def make_check(passed: bool, reason: str, **extra: Any) -> dict[str, Any]:
    return {"pass": bool(passed), "reason": reason, **extra}


def build_report(
    *,
    registry: RegistryEntry,
    data_source: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_rows = [normalize_row(row) for row in rows]
    row_count = len(normalized_rows)

    schema_properties = set((data_source.get("properties") or {}).keys())
    missing_schema_columns = [
        column for column in registry.expected_columns if column not in schema_properties
    ]

    observed_confianza = {
        row["properties"].get("Confianza canales")
        for row in normalized_rows
        if row["properties"].get("Confianza canales")
    }
    observed_flags = {
        flag
        for row in normalized_rows
        for flag in (row["properties"].get("Flags canales") or [])
        if flag
    }

    invalid_confianza = sorted(observed_confianza - registry.expected_confianza)
    invalid_flags = sorted(observed_flags - registry.expected_flags)

    invalid_urls = []
    for row in normalized_rows:
        value = row["properties"].get("LinkedIn activity feed")
        if value and not is_valid_url(str(value)):
            invalid_urls.append(
                {
                    "row_id_tail": str(row.get("id") or "")[-8:],
                    "nombre": row["properties"].get("Nombre"),
                    "field": "LinkedIn activity feed",
                    "value": value,
                }
            )

    samples_by_confidence: dict[str, dict[str, Any]] = {}
    sample_missing_columns: dict[str, list[str]] = {}
    for target in REQUIRED_SAMPLE_CONFIDENCES:
        for row in normalized_rows:
            if row["properties"].get("Confianza canales") != target:
                continue
            row_id = str(row.get("id") or "")
            if any(str(sample.get("id") or "") == row_id for sample in samples_by_confidence.values()):
                continue
            samples_by_confidence[target] = row
            missing = [
                column for column in registry.expected_columns if column not in row["raw_property_names"]
            ]
            if missing:
                sample_missing_columns[target] = missing
            break

    missing_sample_confidences = [
        confidence for confidence in REQUIRED_SAMPLE_CONFIDENCES if confidence not in samples_by_confidence
    ]
    sample_rows = [
        _safe_row_sample(samples_by_confidence[confidence])
        for confidence in REQUIRED_SAMPLE_CONFIDENCES
        if confidence in samples_by_confidence
    ]

    checks = {
        "a_three_distinct_profiles_with_10_columns": make_check(
            not missing_sample_confidences and not sample_missing_columns and not missing_schema_columns,
            "Required ALTA/MEDIA/DUPLICADO samples and 10-channel columns are readable"
            if not missing_sample_confidences and not sample_missing_columns and not missing_schema_columns
            else "Missing required samples or expected columns",
            missing_sample_confidences=missing_sample_confidences,
            missing_schema_columns=missing_schema_columns,
            sample_missing_columns=sample_missing_columns,
        ),
        "b_row_count_26": make_check(
            row_count == registry.expected_row_count,
            f"row_count={row_count}, expected={registry.expected_row_count}",
        ),
        "c_linkedin_activity_feed_urls": make_check(
            not invalid_urls,
            "All populated LinkedIn activity feed values are valid http(s) URLs"
            if not invalid_urls
            else "Invalid LinkedIn activity feed URLs found",
            invalid_count=len(invalid_urls),
        ),
        "d_confianza_enum": make_check(
            not invalid_confianza,
            "Confianza canales values are within enum",
            invalid_values=invalid_confianza,
        ),
        "e_flags_enum": make_check(
            not invalid_flags,
            "Flags canales values are within enum",
            invalid_values=invalid_flags,
        ),
    }
    overall_pass = all(check["pass"] for check in checks.values())

    return {
        "overall_pass": overall_pass,
        "authority": {
            "mode": "notion_rest_read_only",
            "credential": "worker.config.NOTION_API_KEY",
            "api_version": notion_api_version(),
            "mutation_endpoints_used": False,
            "query_note": "Notion data source row reads use POST /data_sources/{id}/query as a read-only endpoint.",
        },
        "registry": {
            "path": registry.registry_path,
            "data_source_id": registry.data_source_id,
            "database_id": registry.database_id,
        },
        "data_source_id": registry.data_source_id,
        "row_count": row_count,
        "checks": checks,
        "observed_enums": {
            "confianza_canales": sorted(observed_confianza),
            "flags_canales": sorted(observed_flags),
        },
        "invalid_urls": invalid_urls,
        "sample_rows": sample_rows,
    }


def run_smoke(registry_path: str | None = None) -> dict[str, Any]:
    registry = load_registry_entry(resolve_registry_path(registry_path))
    api_key = get_runtime_notion_api_key()
    api_version = notion_api_version()
    data_source, rows = fetch_data_source_rows(
        registry.data_source_id,
        api_key=api_key,
        api_version=api_version,
    )
    return build_report(registry=registry, data_source=data_source, rows=rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke read-only REST para DB Referentes usada por Stage 1 LinkedIn."
    )
    parser.add_argument(
        "--registry",
        help=(
            "Path a notion-governance/registry/notion-data-sources.template.yaml. "
            "Default: sibling ../notion-governance/registry/notion-data-sources.template.yaml"
        ),
    )
    parser.add_argument("--output", help="Path opcional para escribir el reporte JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = run_smoke(args.registry)
        exit_code = 0 if report["overall_pass"] else 2
    except SmokeSetupError as exc:
        report = {
            "overall_pass": False,
            "setup_error": str(exc),
            "checks": {},
        }
        exit_code = 3
    except Exception as exc:  # pragma: no cover - exercised by live runtime failures.
        report = {
            "overall_pass": False,
            "runtime_error": str(exc),
            "checks": {},
        }
        exit_code = 4

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
