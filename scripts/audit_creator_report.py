#!/usr/bin/env python3
"""
Audit Creator Report — ¿Quién hizo esta auditoría?

Escanea los documentos de auditoría del repo y reporta el creador/ejecutor
de cada uno, respondiendo a la pregunta: "¿quién hizo esta auditoría?".

Busca el campo '**Ejecutado por:**' o '**Autor:**' en los documentos de
docs/ y docs/audits/.

Uso:
  python scripts/audit_creator_report.py
  python scripts/audit_creator_report.py --dir docs/audits
  python scripts/audit_creator_report.py --format json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


_CREATOR_PATTERNS = [
    re.compile(r"\*\*Ejecutado\s+por:\*\*\s*(.+)"),
    re.compile(r"\*\*Autor:\*\*\s*(.+)"),
    re.compile(r"\*\*Agente:\*\*\s*(.+)"),
    re.compile(r"Ejecutada\s+v[ií]a\s+Remote-SSH\s+\(([^)]+)\)"),
    re.compile(r"Ejecutada.*?por\s+([A-Za-z0-9_-]+)"),
]

_DATE_PATTERN = re.compile(r"\*\*Fecha:\*\*\s*(.+)")

_AUDIT_KEYWORDS = ("audit", "auditoria", "auditoría", "verificación",
                   "vps-audit", "vm-audit")

_AUDIT_DIRS = ("audits",)


def _is_audit_doc(path: Path) -> bool:
    name_lower = path.name.lower()
    if any(kw in name_lower for kw in _AUDIT_KEYWORDS):
        return True
    # Any .md in a directory named "audits" is an audit doc
    return any(part in _AUDIT_DIRS for part in path.parts)


def _extract_creator(text: str) -> Optional[str]:
    for pattern in _CREATOR_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_date(text: str) -> Optional[str]:
    m = _DATE_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    return None


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "(sin título)"


def scan_dir(root: Path) -> List[Dict]:
    repo_root = root.parent
    results = []
    for md in sorted(root.rglob("*.md")):
        if not _is_audit_doc(md):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue

        creator = _extract_creator(text)
        date = _extract_date(text)
        title = _extract_title(text)

        try:
            rel_path = str(md.relative_to(repo_root))
        except ValueError:
            rel_path = str(md)

        results.append({
            "file": rel_path,
            "title": title,
            "date": date or "—",
            "creator": creator or "⚠️  sin datos",
        })
    return results


def _format_text(results: List[Dict], root: Path) -> str:
    lines = [
        "=" * 60,
        "  Umbral — Audit Creator Report",
        f"  Directorio: {root}",
        "=" * 60,
        "",
    ]
    if not results:
        lines.append("  No se encontraron documentos de auditoría.")
        return "\n".join(lines)

    for r in results:
        icon = "✅" if "sin datos" not in r["creator"] else "⚠️ "
        lines.append(f"{icon} {r['file']}")
        lines.append(f"   Título:         {r['title']}")
        lines.append(f"   Fecha:          {r['date']}")
        lines.append(f"   Ejecutado por:  {r['creator']}")
        lines.append("")

    lines.append("=" * 60)
    missing = sum(1 for r in results if "sin datos" in r["creator"])
    lines.append(f"  Total: {len(results)} auditorías  |  Sin creator: {missing}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="¿Quién hizo esta auditoría?")
    p.add_argument(
        "--dir",
        default=None,
        help="Directorio raíz a escanear (default: docs/ del repo)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato de salida",
    )
    args = p.parse_args()

    if args.dir:
        root = Path(args.dir).resolve()
    else:
        # Buscar la raíz del repo subiendo desde este script
        here = Path(__file__).resolve().parent
        repo_root = here.parent
        root = repo_root / "docs"

    if not root.exists():
        print(f"Error: directorio no encontrado: {root}", file=sys.stderr)
        sys.exit(1)

    results = scan_dir(root)

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(_format_text(results, root))

    missing = sum(1 for r in results if "sin datos" in r["creator"])
    sys.exit(1 if missing > 0 else 0)


if __name__ == "__main__":
    main()
