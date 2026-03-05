#!/usr/bin/env python3
"""
Audit Traceability Check — Verificación rápida de trazabilidad del sistema.

Lee ops_log.jsonl y evalúa la cobertura de campos de auditoría:
- Estructura de eventos
- Presencia de trace_id, source, task_type
- Conteo de eventos por tipo
- Retención/rotación del archivo
- Veredicto: OK / Parcial / Insuficiente

Uso:
  python scripts/audit_traceability_check.py
  python scripts/audit_traceability_check.py --log-dir /ruta/custom
  python scripts/audit_traceability_check.py --format json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REQUIRED_FIELDS_BY_EVENT = {
    "task_queued": ["task_id", "task", "team", "task_type"],
    "task_completed": ["task_id", "task", "team", "model", "duration_ms"],
    "task_failed": ["task_id", "task", "team", "error"],
    "task_blocked": ["task_id", "task", "team", "reason"],
    "task_retried": ["task_id", "task", "team", "retry_count"],
    "model_selected": ["task_id", "task_type", "model"],
    "quota_warning": ["provider", "usage_pct"],
    "quota_restricted": ["provider", "usage_pct"],
    "worker_health_change": ["worker", "online"],
}

_AUDIT_FIELDS = ["trace_id", "source", "task_type"]

_MAX_HEALTHY_LOG_SIZE_MB = 100


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verificación de trazabilidad Umbral")
    p.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directorio del ops_log (default: ~/.config/umbral o UMBRAL_OPS_LOG_DIR)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato de salida",
    )
    return p.parse_args()


def _resolve_log_path(log_dir: Optional[str]) -> Path:
    if log_dir:
        d = Path(log_dir)
    else:
        d = Path(os.environ.get("UMBRAL_OPS_LOG_DIR", str(Path.home() / ".config" / "umbral")))
    return d / "ops_log.jsonl"


def _load_events(log_path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not log_path.exists():
        return events
    with open(log_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"_parse_error": True, "_line": i})
    return events


def _check_file_stats(log_path: Path) -> Dict[str, Any]:
    if not log_path.exists():
        return {
            "exists": False,
            "size_bytes": 0,
            "size_mb": 0,
            "rotation_files": 0,
        }
    size = log_path.stat().st_size
    rotation_files = len(list(log_path.parent.glob("ops_log.jsonl.*")))
    return {
        "exists": True,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "rotation_files": rotation_files,
    }


def _check_event_structure(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate required fields per event type."""
    event_counts: Counter[str] = Counter()
    missing_fields: Dict[str, Counter[str]] = defaultdict(Counter)
    parse_errors = 0
    unknown_events: Counter[str] = Counter()

    for ev in events:
        if ev.get("_parse_error"):
            parse_errors += 1
            continue
        event_type = ev.get("event", "__missing__")
        event_counts[event_type] += 1

        required = _REQUIRED_FIELDS_BY_EVENT.get(event_type)
        if required is None:
            unknown_events[event_type] += 1
            continue

        for field in required:
            if field not in ev or ev[field] is None:
                missing_fields[event_type][field] += 1

    return {
        "total_events": len(events),
        "parse_errors": parse_errors,
        "event_counts": dict(event_counts.most_common()),
        "unknown_events": dict(unknown_events),
        "missing_required_fields": {
            k: dict(v) for k, v in missing_fields.items()
        },
    }


def _check_audit_fields(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check presence of trace_id, source, task_type in task-lifecycle events."""
    task_events = [
        e for e in events
        if e.get("event") in ("task_queued", "task_completed", "task_failed",
                               "task_blocked", "task_retried")
        and not e.get("_parse_error")
    ]
    total = len(task_events)
    if total == 0:
        return {
            "total_task_events": 0,
            "fields": {f: {"present": 0, "absent": 0, "coverage_pct": 0} for f in _AUDIT_FIELDS},
        }

    field_stats: Dict[str, Dict[str, int]] = {}
    for field in _AUDIT_FIELDS:
        present = sum(1 for e in task_events if e.get(field))
        absent = total - present
        field_stats[field] = {
            "present": present,
            "absent": absent,
            "coverage_pct": round(present / total * 100, 1),
        }

    return {
        "total_task_events": total,
        "fields": field_stats,
    }


def _check_timestamp_coverage(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    timestamps = [e.get("ts") for e in events if e.get("ts") and not e.get("_parse_error")]
    if not timestamps:
        return {"has_timestamps": False, "first_event": None, "last_event": None, "span_days": 0}

    timestamps.sort()
    first = timestamps[0]
    last = timestamps[-1]
    try:
        first_dt = datetime.fromisoformat(first.replace("Z", "+00:00"))
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        span = (last_dt - first_dt).days
    except (ValueError, TypeError):
        span = 0

    return {
        "has_timestamps": True,
        "first_event": first,
        "last_event": last,
        "span_days": span,
    }


def _check_retention(file_stats: Dict[str, Any]) -> Dict[str, Any]:
    has_rotation = file_stats.get("rotation_files", 0) > 0
    size_mb = file_stats.get("size_mb", 0)
    over_limit = size_mb > _MAX_HEALTHY_LOG_SIZE_MB

    return {
        "has_rotation": has_rotation,
        "over_size_limit": over_limit,
        "size_limit_mb": _MAX_HEALTHY_LOG_SIZE_MB,
        "current_size_mb": size_mb,
    }


def _identify_gaps(
    file_stats: Dict[str, Any],
    structure: Dict[str, Any],
    audit_fields: Dict[str, Any],
    retention: Dict[str, Any],
) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []

    if not file_stats.get("exists"):
        gaps.append({
            "id": "G0",
            "description": "ops_log.jsonl no existe — sin datos de auditoría",
            "severity": "ALTO",
        })
        return gaps

    event_counts = structure.get("event_counts", {})
    if event_counts.get("task_queued", 0) == 0:
        gaps.append({
            "id": "G4",
            "description": "task_queued nunca se emite — falta evento de inicio del ciclo de vida",
            "severity": "ALTO",
        })

    fields = audit_fields.get("fields", {})
    if fields.get("trace_id", {}).get("coverage_pct", 0) < 50:
        gaps.append({
            "id": "G2",
            "description": f"trace_id ausente en ops_log (cobertura: {fields.get('trace_id', {}).get('coverage_pct', 0)}%)",
            "severity": "ALTO",
        })

    if fields.get("source", {}).get("coverage_pct", 0) < 50:
        gaps.append({
            "id": "G3",
            "description": f"source (origen) ausente en ops_log (cobertura: {fields.get('source', {}).get('coverage_pct', 0)}%)",
            "severity": "ALTO",
        })

    if fields.get("task_type", {}).get("coverage_pct", 0) < 80:
        gaps.append({
            "id": "G5",
            "description": f"task_type ausente en task_completed/task_failed (cobertura: {fields.get('task_type', {}).get('coverage_pct', 0)}%)",
            "severity": "MEDIO",
        })

    if not retention.get("has_rotation") and retention.get("current_size_mb", 0) > 0:
        gaps.append({
            "id": "G6",
            "description": f"Sin rotación de ops_log — archivo en {retention.get('current_size_mb', 0)} MB, crece indefinidamente",
            "severity": "MEDIO",
        })

    if retention.get("over_size_limit"):
        gaps.append({
            "id": "G6b",
            "description": f"ops_log excede {_MAX_HEALTHY_LOG_SIZE_MB} MB ({retention.get('current_size_mb', 0)} MB) — riesgo de disco",
            "severity": "ALTO",
        })

    missing = structure.get("missing_required_fields", {})
    for event_type, field_counts in missing.items():
        for field, count in field_counts.items():
            gaps.append({
                "id": f"STRUCT-{event_type}-{field}",
                "description": f"{event_type}: campo requerido '{field}' ausente en {count} eventos",
                "severity": "BAJO",
            })

    if structure.get("parse_errors", 0) > 0:
        gaps.append({
            "id": "PARSE",
            "description": f"{structure['parse_errors']} líneas con errores de parsing en ops_log",
            "severity": "BAJO",
        })

    return gaps


def _compute_verdict(gaps: List[Dict[str, Any]], file_stats: Dict[str, Any]) -> str:
    if not file_stats.get("exists"):
        return "INSUFICIENTE"

    high_gaps = sum(1 for g in gaps if g["severity"] == "ALTO")
    medium_gaps = sum(1 for g in gaps if g["severity"] == "MEDIO")

    if high_gaps >= 3:
        return "INSUFICIENTE"
    if high_gaps >= 1 or medium_gaps >= 2:
        return "PARCIAL"
    return "OK"


def run_audit(log_dir: Optional[str] = None) -> Dict[str, Any]:
    log_path = _resolve_log_path(log_dir)
    events = _load_events(log_path)

    file_stats = _check_file_stats(log_path)
    structure = _check_event_structure(events)
    audit_fields = _check_audit_fields(events)
    timestamps = _check_timestamp_coverage(events)
    retention = _check_retention(file_stats)
    gaps = _identify_gaps(file_stats, structure, audit_fields, retention)
    verdict = _compute_verdict(gaps, file_stats)

    return {
        "log_path": str(log_path),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "file": file_stats,
        "structure": structure,
        "audit_fields": audit_fields,
        "timestamps": timestamps,
        "retention": retention,
        "gaps": gaps,
        "verdict": verdict,
    }


def _format_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    v = report["verdict"]
    icon = {"OK": "✅", "PARCIAL": "⚠️", "INSUFICIENTE": "❌"}.get(v, "❓")
    lines.append(f"{'='*60}")
    lines.append(f"  Umbral — Audit Traceability Check")
    lines.append(f"{'='*60}")
    lines.append(f"  Log: {report['log_path']}")
    lines.append(f"  Checked: {report['checked_at']}")
    lines.append("")

    f = report["file"]
    lines.append(f"📁 Archivo")
    lines.append(f"  Existe: {'Sí' if f['exists'] else 'No'}")
    if f["exists"]:
        lines.append(f"  Tamaño: {f['size_mb']} MB ({f['size_bytes']:,} bytes)")
        lines.append(f"  Archivos de rotación: {f['rotation_files']}")
    lines.append("")

    s = report["structure"]
    lines.append(f"📊 Estructura ({s['total_events']} eventos)")
    if s["event_counts"]:
        for ev, cnt in s["event_counts"].items():
            lines.append(f"  {ev}: {cnt}")
    if s["parse_errors"]:
        lines.append(f"  ⚠️  Parse errors: {s['parse_errors']}")
    lines.append("")

    a = report["audit_fields"]
    lines.append(f"🔍 Campos de auditoría ({a['total_task_events']} eventos de tarea)")
    for field, stats in a.get("fields", {}).items():
        bar = "✅" if stats["coverage_pct"] >= 80 else ("⚠️" if stats["coverage_pct"] > 0 else "❌")
        lines.append(f"  {bar} {field}: {stats['coverage_pct']}% ({stats['present']}/{stats['present'] + stats['absent']})")
    lines.append("")

    t = report["timestamps"]
    lines.append("📅 Cobertura temporal")
    if t["has_timestamps"]:
        lines.append(f"  Primer evento: {t['first_event']}")
        lines.append(f"  Último evento: {t['last_event']}")
        lines.append(f"  Span: {t['span_days']} días")
    else:
        lines.append("  Sin timestamps")
    lines.append("")

    r = report["retention"]
    lines.append("🔄 Retención")
    lines.append(f"  Rotación configurada: {'Sí' if r['has_rotation'] else 'No'}")
    lines.append(f"  Tamaño actual: {r['current_size_mb']} MB (límite: {r['size_limit_mb']} MB)")
    if r["over_size_limit"]:
        lines.append("  ⚠️  ¡Excede límite recomendado!")
    lines.append("")

    gaps = report["gaps"]
    lines.append(f"🚨 Gaps detectados ({len(gaps)})")
    if gaps:
        for g in gaps:
            sev_icon = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢"}.get(g["severity"], "⚪")
            lines.append(f"  {sev_icon} [{g['severity']}] {g['id']}: {g['description']}")
    else:
        lines.append("  Ninguno detectado")
    lines.append("")

    lines.append(f"{'='*60}")
    lines.append(f"  VEREDICTO: {icon} Trazabilidad {v}")
    lines.append(f"{'='*60}")

    return "\n".join(lines)


def main() -> None:
    args = _parse_args()
    report = run_audit(args.log_dir)

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_text(report))

    verdict = report["verdict"]
    sys.exit(0 if verdict == "OK" else (1 if verdict == "PARCIAL" else 2))


if __name__ == "__main__":
    main()
