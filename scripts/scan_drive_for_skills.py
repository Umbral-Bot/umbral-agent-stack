#!/usr/bin/env python3
"""
scan_drive_for_skills.py — Scan Google Drive AI folder for potential OpenClaw skills.

Recursively walks G:\\Mi unidad\\AI\\IA Personalizadas\\ and reports:
  - Subdirectories with .md files
  - File count, total word count per folder
  - Suggested priority (ALTA/MEDIA/BAJA)
  - Potential skill name and domain

Outputs: reports/drive-skills-scan.md
"""

import argparse
import logging
import os
import sys
from pathlib import Path

LOG = logging.getLogger(__name__)

# Priority mapping based on David's professional profile
_PRIORITY_MAP: dict[str, str] = {
    "Consultor": "ALTA",
    "BIM Forum": "ALTA",
    "LLM-Mentor-Speckle-Dalux-PowerBI": "ALTA",
    "Linkedin": "MEDIA",
    "Linkedin 2": "MEDIA",
    "PowerFlow Coaching": "MEDIA",
    "Marca Personal": "MEDIA",
    "Scraping Dynamo": "MEDIA",
    "Docente 1": "MEDIA",
    "Docente 2": "MEDIA",
    "Docente 3": "MEDIA",
    "Docente 4": "MEDIA",
    "Autodesk": "BAJA",
    "Grasshopper": "BAJA",
    "Dalux": "BAJA",
    "Power BI": "BAJA",
    "Arquitectura y Robots": "BAJA",
    "Make LLMs 1": "META",
    "Make LLMs 2": "META",
    "Make LLMs 3": "META",
}

_DOMAIN_MAP: dict[str, str] = {
    "Consultor": "Consultoria BIM + IA",
    "BIM Forum": "ISO 19650 / Estandares BIM",
    "LLM-Mentor-Speckle-Dalux-PowerBI": "Speckle + Dalux + Power BI",
    "Linkedin": "Marketing LinkedIn",
    "Linkedin 2": "Marketing LinkedIn",
    "PowerFlow Coaching": "Marca personal / Coaching",
    "Marca Personal": "Branding personal",
    "Scraping Dynamo": "Dynamo scripting",
    "Docente 1": "Material docente",
    "Docente 2": "Material docente",
    "Docente 3": "Material docente",
    "Docente 4": "Material docente",
    "Autodesk": "Documentacion Autodesk",
    "Grasshopper": "Programacion visual",
    "Dalux": "Dalux AI Ready",
    "Power BI": "Power BI AI Ready",
    "Arquitectura y Robots": "Colaboracion humano-robot",
    "Make LLMs 1": "Meta: crear custom instructions",
    "Make LLMs 2": "Meta: crear custom instructions",
    "Make LLMs 3": "Meta: crear custom instructions",
}


def scan_folder(folder: Path) -> dict:
    """Scan a single folder and return stats."""
    md_files = list(folder.glob("*.md"))
    total_words = 0
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            total_words += len(text.split())
        except Exception:
            pass

    return {
        "name": folder.name,
        "md_count": len(md_files),
        "total_words": total_words,
        "priority": _PRIORITY_MAP.get(folder.name, "???"),
        "domain": _DOMAIN_MAP.get(folder.name, "Sin clasificar"),
    }


def generate_report(results: list[dict]) -> str:
    """Generate markdown report."""
    lines = [
        "# Drive Skills Scan Report",
        "",
        f"**Scanned:** `G:\\Mi unidad\\AI\\IA Personalizadas\\`",
        f"**Folders found:** {len(results)}",
        "",
        "## Summary",
        "",
        "| Carpeta | Archivos .md | Palabras | Prioridad | Dominio |",
        "|---------|:---:|---:|:---:|---------|",
    ]

    alta = []
    for r in sorted(results, key=lambda x: (
        {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "META": 3}.get(x["priority"], 9),
        x["name"],
    )):
        lines.append(
            f"| {r['name']} | {r['md_count']} | {r['total_words']:,} "
            f"| **{r['priority']}** | {r['domain']} |"
        )
        if r["priority"] == "ALTA":
            alta.append(r)

    lines.extend([
        "",
        "## Skills Prioritarios (ALTA)",
        "",
    ])

    for r in alta:
        lines.append(f"- **{r['name']}** - {r['domain']} ({r['md_count']} archivos, {r['total_words']:,} palabras)")

    lines.extend([
        "",
        "## Recomendaciones",
        "",
        "1. Crear skills para las 3 carpetas ALTA condensando a ~3000 palabras cada uno",
        "2. Las carpetas MEDIA pueden convertirse en skills en futuras iteraciones",
        "3. Las carpetas META contienen guias para crear instructions, utiles como referencia interna",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Google Drive for potential skills")
    parser.add_argument("--drive-path", default=r"G:\Mi unidad\AI\IA Personalizadas",
                        help="Path to scan")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    drive = Path(args.drive_path)
    if not drive.is_dir():
        LOG.error("Path not found: %s", drive)
        return 1

    results = []
    for child in sorted(drive.iterdir()):
        if child.is_dir():
            stats = scan_folder(child)
            if stats["md_count"] > 0:
                results.append(stats)
                LOG.info("  %s: %d files, %d words [%s]",
                         stats["name"], stats["md_count"],
                         stats["total_words"], stats["priority"])

    report = generate_report(results)

    if args.dry_run:
        print(report)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        out_dir = repo_root / "reports"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / "drive-skills-scan.md"
        out_file.write_text(report, encoding="utf-8")
        LOG.info("Report written to %s", out_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
