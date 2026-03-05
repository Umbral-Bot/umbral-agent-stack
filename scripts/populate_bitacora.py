#!/usr/bin/env python3
"""
populate_bitacora.py — Poblar Bitácora Umbral Agent Stack en Notion.

Lee la historia del proyecto desde .agents/board.md y .agents/tasks/*.md
y genera entradas en la base de datos Bitácora de Notion.

Uso:
    python scripts/populate_bitacora.py [--dry-run] [--tasks-only] [--skip-inferred]

Variables de entorno requeridas:
    NOTION_API_KEY              Token de integración de Notion
    NOTION_BITACORA_DB_ID       ID de la DB Bitácora (default: 85f89758684744fb9f14076e7ba0930e)

Variables opcionales (para usar el Worker en lugar de la API directa):
    WORKER_URL                  URL base del Worker (ej: http://localhost:8088)
    WORKER_TOKEN                Token del Worker
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("populate_bitacora")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
BITACORA_DB_ID = os.environ.get("NOTION_BITACORA_DB_ID", "85f89758684744fb9f14076e7ba0930e")

AGENTS_DIR = Path(__file__).parent.parent / ".agents"
TASKS_DIR = AGENTS_DIR / "tasks"
BOARD_FILE = AGENTS_DIR / "board.md"

# Mapeo de assigned_to → Agente (Select de Notion)
AGENT_MAP: dict[str, str] = {
    "cursor": "Cursor",
    "cursor-agent-cloud": "Cursor",
    "cursor-agent-cloud-1": "Cursor",
    "cursor-agent-cloud-2": "Cursor",
    "cursor-agent-cloud-3": "Cursor",
    "cursor-agent-cloud-4": "Cursor",
    "cursor-agent-cloud-5": "Cursor",
    "cursor-agent-cloud-6": "Cursor",
    "cursor-agent-cloud-7": "Cursor",
    "cursor-agent-cloud-8": "Cursor",
    "cloud1": "Cursor",
    "cloud2": "Cursor",
    "cloud3": "Cursor",
    "cloud4": "Cursor",
    "cloud5": "Cursor",
    "cloud6": "Cursor",
    "cloud7": "Cursor",
    "cloud8": "Cursor",
    "codex": "Codex",
    "github-copilot": "Copilot",
    "copilot": "Copilot",
    "claude-code": "Claude",
    "claude": "Claude",
    "antigravity": "Antigravity",
    "manual": "Manual",
}

# Mapeo de round → Ronda (Select de Notion)
ROUND_MAP: dict[str | int, str] = {
    0: "Hackathon",
    1: "Hackathon",
    2: "Pre-R11",
    3: "Pre-R11",
    4: "Pre-R11",
    5: "Pre-R11",
    6: "Pre-R11",
    7: "Pre-R11",
    8: "Pre-R11",
    9: "Pre-R11",
    10: "Pre-R11",
    11: "R11",
    12: "R12",
    13: "R13",
    "hackathon": "Hackathon",
    "pre-r11": "Pre-R11",
    "r11": "R11",
    "r12": "R12",
    "r13": "R13",
    "ad-hoc": "Ad-hoc",
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class BitacoraEntry:
    titulo: str
    fecha: str
    ronda: str
    tipo: str
    detalle: str = ""
    referencia: str = ""
    agente: str = "Cursor"
    estado: str = "Completado"

    def to_dict(self) -> dict:
        return {
            "titulo": self.titulo,
            "fecha": self.fecha,
            "ronda": self.ronda,
            "tipo": self.tipo,
            "detalle": self.detalle,
            "referencia": self.referencia,
            "agente": self.agente,
            "estado": self.estado,
        }


# ---------------------------------------------------------------------------
# Hardcoded project history (minimum required entries from task spec)
# ---------------------------------------------------------------------------


HARDCODED_ENTRIES: list[BitacoraEntry] = [
    # ── Hackathon / Ronda 1 ───────────────────────────────────────────────
    BitacoraEntry(
        titulo="Hackathon base — Diagnóstico y arranque del stack",
        fecha="2026-03-04",
        ronda="Hackathon",
        tipo="Hito",
        detalle=(
            "Diagnóstico completo del stack, activación de infraestructura VPS, "
            "Notion API, Tailscale, dashboard y .env. Primer flujo e2e verificado: "
            "Enqueue → Dispatcher → Worker → Complete."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="Hackathon R1 — OpsLogger + research.web + SIM cron",
        fecha="2026-03-04",
        ronda="Hackathon",
        tipo="Hito",
        detalle=(
            "Activación de OpsLogger con persistencia Redis, handler research.web (Tavily), "
            "LLM connect (Gemini 2.5 Flash), SIM daily cron (3x/día). 9 tareas completadas."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="Hackathon R1 — Poller inteligente + clasificador de intents",
        fecha="2026-03-04",
        ronda="Hackathon",
        tipo="PR mergeado",
        detalle=(
            "Antigravity: intent classifier (question/task/instruction/echo), "
            "team routing por @mención, Notion Poller --once flag + health check. "
            "Claude Code: Notion Poller daemon (60s loop, PID, SIGTERM)."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Antigravity",
        estado="Completado",
    ),
    # ── Ronda 2 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R2 — Worker/Dispatcher supervisor + POST /enqueue",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #11: Worker/Dispatcher supervisor con auto-restart. "
            "PR #12: Notion Poller daemon + cron wrapper. "
            "PR #13: Poller --once flag + health check. "
            "PR #14: SIM report cron + tests. "
            "PR #15: POST /enqueue + GET /task/{id}/status API."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Copilot",
        estado="Completado",
    ),
    # ── Ronda 3 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R3 — Smart Notion Reply + Daily Digest + Composite handler",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #18: Smart Notion Reply Pipeline (research.web + llm.generate + notion.add_comment). "
            "PR #17: Daily Activity Digest (Redis → LLM → Notion, 22:00 cron). "
            "PR #16: Webhook Callback System (callback_url fire-and-forget + retry). "
            "PR #19: Composite Task Handler (research+LLM en un solo comando)."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Claude",
        estado="Completado",
    ),
    # ── Ronda 4 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R4 — Task History API + Make.com Webhook + Notion Result Poster",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #21: Task History API + Redis Pagination. "
            "PR #20: Make.com Webhook Integration — SIM Pipeline. "
            "PR #22: Notion Result Poster (smart reply + composite)."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Codex",
        estado="Completado",
    ),
    # ── Ronda 5 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R5 — Error Alerts + Team Workflows + Scheduled Tasks Manager",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #23: Error Alert System — notificaciones push de fallos. "
            "PR #24: Team Workflow Engine — flujos por equipo. "
            "PR #26: Scheduled Tasks Manager — tareas programadas via Notion. "
            "PR #25: E2E Validation Suite."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Codex",
        estado="Completado",
    ),
    # ── Ronda 6 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R6 — Multi-LLM Worker + Model Router (Gemini + OpenAI + Anthropic)",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #27: Multi-LLM Worker — OpenAI + Anthropic + Gemini con model routing. "
            "PR #28: Dispatcher Model Routing integrado al flujo real. "
            "PR #33: Quota Dashboard — reporte de uso en Notion. "
            "PR #29: Multi-Model E2E + Scheduled Tasks Validation."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Codex",
        estado="Completado",
    ),
    # ── Ronda 7 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R7 — Langfuse Tracing + OODA Report + Rate Limiting",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "PR #30: Langfuse Tracing — instrumentación de LLM calls. "
            "PR #32: OODA Report con Langfuse — reporte semanal. "
            "PR #34: Hardening Final — rate limiting (60 RPM) + sanitización + secrets audit. "
            "PR #31: E2E Integration Final — validación completa."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
        agente="Codex",
        estado="Completado",
    ),
    # ── Ronda 8 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R8 — Linear Webhooks + Provider Health Dashboard",
        fecha="2026-02-27",
        ronda="Pre-R11",
        tipo="PR mergeado",
        detalle=(
            "Linear webhooks integration: crear y actualizar issues desde el Worker. "
            "Provider Health Dashboard: monitoreo de salud de proveedores LLM. "
            "Multi-agent E2E validation completa."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Codex",
        estado="Completado",
    ),
    # ── Ronda 9 ──────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R9 — OpenClaw Skills — Figma, Notion, Windows",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="Skill creado",
        detalle=(
            "Cursor Cloud: OpenClaw Skills + Figma handler (get_file, get_node, export_image, "
            "add_comment, list_comments) + tests. "
            "Codex: Skills Notion y Windows documentados. "
            "Antigravity: Notion Dashboard Skills Sync. "
            "Claude: Skills Validation E2E."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    # ── Ronda 10 ─────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R10 — OpenClaw Skill Builder Pipeline + Personal Skills",
        fecha="2026-03-04",
        ronda="Pre-R11",
        tipo="Skill creado",
        detalle=(
            "Claude: OpenClaw Skill Builder Pipeline — generación automática de skills. "
            "Antigravity: Personal Skills from Google Drive — skills personalizados de David."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Claude",
        estado="Completado",
    ),
    # ── Ronda 11 ─────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R11 — Skills BIM/AEC — Revit, Dynamo, Rhino, Navisworks, ACC, KUKA",
        fecha="2026-03-04",
        ronda="R11",
        tipo="Skill creado",
        detalle=(
            "Cloud1 (PR #52): 6 skills BIM/AEC — Revit, Dynamo, Rhinoceros/Grasshopper, "
            "Navisworks, ACC (Autodesk Construction Cloud), KukaPRC/Robots."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pull/52",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R11 — Skills Cloud, AI, Automation, Content, Document Generation",
        fecha="2026-03-04",
        ronda="R11",
        tipo="Skill creado",
        detalle=(
            "Cloud2: Skills Automation/Lowcode. "
            "Cloud3: Skills Cloud, AI, Data. "
            "Cloud4: Skills Content, Marketing, Teaching. "
            "Cloud5: Skills Open Source Libraries. "
            "Cloud6: Skills Personal Drive. "
            "Cloud8: Skills Document Generation (Word, PDF, Presentation handlers)."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R11 — Pipeline Granola → Notion (transcripciones + compromisos)",
        fecha="2026-03-04",
        ronda="R11",
        tipo="Tarea creada",
        detalle=(
            "Cloud7: Arquitectura e implementación del pipeline Granola → Notion. "
            "Watcher en VM que detecta nuevas transcripciones Markdown y las envía "
            "al Worker para crear páginas en la Granola Inbox DB de Notion."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    # ── Ronda 12 ─────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R12 — Google Calendar + Gmail integration (tareas)",
        fecha="2026-03-04",
        ronda="R12",
        tipo="Tarea creada",
        detalle=(
            "Cloud1: Integración Google Calendar y Gmail — handlers para leer eventos, "
            "crear reuniones y gestionar correos desde el Worker."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R12 — Granola VM Service + BIM Skills IFC/Speckle",
        fecha="2026-03-04",
        ronda="R12",
        tipo="Tarea creada",
        detalle=(
            "Cloud2: Granola VM Service — servicio persistente en VM para procesamiento automático. "
            "Cloud3: Skills BIM — IFC (Open BIM) y Speckle (plataforma colaborativa AEC)."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R12 — Skills Audit + Pytest + RRSS Pipeline n8n",
        fecha="2026-03-04",
        ronda="R12",
        tipo="Tarea creada",
        detalle=(
            "Cloud4: Auditoría completa de skills con pytest — cobertura y validación. "
            "Cloud5: Pipeline RRSS con n8n — automatización de redes sociales."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    # ── Ronda 13 ─────────────────────────────────────────────────────────
    BitacoraEntry(
        titulo="R13 — Auditoría de trazabilidad y gobernanza",
        fecha="2026-03-04",
        ronda="R13",
        tipo="Documentación",
        detalle=(
            "Auditoría completa de trazabilidad del sistema: logs, eventos, decisiones. "
            "Definición de modelo de gobernanza inter-agentes y políticas de coordinación."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R13 — Governance Metrics Dashboard + Operational Runbook",
        fecha="2026-03-04",
        ronda="R13",
        tipo="Documentación",
        detalle=(
            "Dashboard de métricas de gobernanza del stack. "
            "Runbook operacional completo: procedimientos, escaladas, recuperación de fallos."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R13 — OpsLogger Audit Improvements",
        fecha="2026-03-04",
        ronda="R13",
        tipo="Hito",
        detalle=(
            "Mejoras al OpsLogger: auditoría más granular, correlación de eventos, "
            "métricas de calidad y trazabilidad completa de decisiones del sistema."
        ),
        referencia="https://github.com/Umbral-Bot/umbral-agent-stack",
        agente="Cursor",
        estado="Completado",
    ),
    BitacoraEntry(
        titulo="R13 — Bitácora Umbral Agent Stack — Poblamiento inicial",
        fecha="2026-03-05",
        ronda="R13",
        tipo="Documentación",
        detalle=(
            "Creación e implementación de la Bitácora — Umbral Agent Stack en Notion. "
            "Task notion.append_bitacora implementada en el Worker. "
            "Script populate_bitacora.py que genera entradas desde .agents/board.md y tasks/."
        ),
        referencia=(
            "https://github.com/Umbral-Bot/umbral-agent-stack/tree/feat/bitacora-populate"
        ),
        agente="Cursor",
        estado="Completado",
    ),
]


# ---------------------------------------------------------------------------
# Task file parser
# ---------------------------------------------------------------------------


def _parse_task_file(path: Path) -> Optional[BitacoraEntry]:
    """Parse a task YAML frontmatter and return a BitacoraEntry (or None)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Extract YAML frontmatter between --- delimiters
    if not text.startswith("---"):
        return None

    lines = text.split("\n")
    frontmatter_lines = []
    in_fm = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm and line.strip() == "---":
            break
        if in_fm:
            frontmatter_lines.append(line)

    if not frontmatter_lines:
        return None

    # Simple key: value parser (no nested YAML needed)
    fm: dict[str, str] = {}
    for line in frontmatter_lines:
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")

    task_id = fm.get("id", "")
    title = fm.get("title", "")
    assigned_to = fm.get("assigned_to", "cursor")
    round_raw = fm.get("round", "")
    status = fm.get("status", "")
    created = fm.get("created", "2026-03-04")
    pr_url = fm.get("pr", "")

    if not title:
        return None

    # Map round → Ronda
    try:
        round_int = int(round_raw)
        ronda = ROUND_MAP.get(round_int, "Ad-hoc")
    except (ValueError, TypeError):
        ronda = ROUND_MAP.get(round_raw.lower(), "Ad-hoc")

    # Map agente
    agente = AGENT_MAP.get(assigned_to.lower(), "Cursor")

    # Map status → estado
    estado_map = {
        "done": "Completado",
        "in_progress": "En curso",
        "blocked": "Bloqueado",
        "pending": "Pendiente",
    }
    estado = estado_map.get(status.lower(), "Completado")

    # Determine tipo
    if pr_url:
        tipo = "PR mergeado"
    elif "skill" in title.lower() or "skills" in title.lower():
        tipo = "Skill creado"
    elif any(w in title.lower() for w in ["diagnos", "audit", "runbook", "bitácora", "bitacora", "documentaci"]):
        tipo = "Documentación"
    elif any(w in title.lower() for w in ["fix", "bug", "hardening"]):
        tipo = "Bug fix"
    elif any(w in title.lower() for w in ["pipeline", "integr", "task", "handler"]):
        tipo = "Tarea creada"
    else:
        tipo = "Hito"

    referencia = pr_url or ""

    return BitacoraEntry(
        titulo=f"[{task_id}] {title}"[:200] if task_id else title[:200],
        fecha=created,
        ronda=ronda,
        tipo=tipo,
        detalle=f"Tarea {task_id}: {title}. Asignado a: {assigned_to}.",
        referencia=referencia,
        agente=agente,
        estado=estado,
    )


def load_inferred_entries() -> list[BitacoraEntry]:
    """Parse task files and generate BitacoraEntry objects."""
    entries: list[BitacoraEntry] = []
    task_files = sorted(TASKS_DIR.glob("*.md"))
    for path in task_files:
        entry = _parse_task_file(path)
        if entry:
            entries.append(entry)
    logger.info("Parsed %d entries from %d task files", len(entries), len(task_files))
    return entries


# ---------------------------------------------------------------------------
# Notion API direct insert
# ---------------------------------------------------------------------------


def _notion_headers() -> dict[str, str]:
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def insert_via_notion_api(entry: BitacoraEntry, db_id: str) -> dict:
    """Insert a single entry directly via Notion REST API."""
    properties: dict = {
        "Título": {"title": [{"text": {"content": entry.titulo[:2000]}}]},
        "Fecha": {"date": {"start": entry.fecha}},
        "Ronda": {"select": {"name": entry.ronda}},
        "Tipo": {"select": {"name": entry.tipo}},
    }
    if entry.detalle:
        properties["Detalle"] = {
            "rich_text": [{"type": "text", "text": {"content": entry.detalle[:2000]}}]
        }
    if entry.referencia:
        properties["Referencia"] = {"url": entry.referencia}
    if entry.agente:
        properties["Agente"] = {"select": {"name": entry.agente}}
    if entry.estado:
        properties["Estado"] = {"select": {"name": entry.estado}}

    payload = {"parent": {"database_id": db_id}, "properties": properties}

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=_notion_headers(),
            json=payload,
        )

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Notion API error ({resp.status_code}): {resp.text[:400]}"
        )
    data = resp.json()
    return {"page_id": data["id"], "url": data.get("url", "")}


# ---------------------------------------------------------------------------
# Worker API insert (optional)
# ---------------------------------------------------------------------------


def insert_via_worker(entry: BitacoraEntry, worker_url: str, worker_token: str) -> dict:
    """Insert a single entry via the Umbral Worker API."""
    payload = {
        "task": "notion.append_bitacora",
        "input": entry.to_dict(),
    }
    headers = {
        "Authorization": f"Bearer {worker_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{worker_url.rstrip('/')}/run",
            headers=headers,
            json=payload,
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Worker API error ({resp.status_code}): {resp.text[:400]}"
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_entries(skip_inferred: bool = False) -> list[BitacoraEntry]:
    """Build the full list of entries to insert."""
    entries = list(HARDCODED_ENTRIES)
    if not skip_inferred:
        inferred = load_inferred_entries()
        # Deduplicate by titulo (keep hardcoded ones, skip inferred duplicates)
        existing_titles = {e.titulo.lower() for e in entries}
        for e in inferred:
            if e.titulo.lower() not in existing_titles:
                entries.append(e)
                existing_titles.add(e.titulo.lower())
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Poblar la Bitácora Umbral Agent Stack en Notion"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar entradas sin escribir en Notion",
    )
    parser.add_argument(
        "--skip-inferred",
        action="store_true",
        help="Usar solo entradas hardcodeadas (no parsear .agents/tasks/)",
    )
    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="Usar solo entradas parseadas desde .agents/tasks/ (sin hardcodeadas)",
    )
    parser.add_argument(
        "--db-id",
        default=BITACORA_DB_ID,
        help=f"ID de la DB Bitácora (default: {BITACORA_DB_ID})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Segundos entre inserciones para respetar rate limits (default: 0.4)",
    )
    args = parser.parse_args()

    db_id = args.db_id
    worker_url = os.environ.get("WORKER_URL", "")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    use_worker = bool(worker_url and worker_token)

    # Build entries list
    if args.tasks_only:
        entries = load_inferred_entries()
    else:
        entries = build_entries(skip_inferred=args.skip_inferred)

    logger.info("Total entries to process: %d", len(entries))

    if args.dry_run:
        print(f"\n{'='*70}")
        print(f"DRY-RUN — {len(entries)} entradas (NO se escribirá en Notion)")
        print(f"DB ID: {db_id}")
        print(f"{'='*70}\n")
        for i, e in enumerate(entries, 1):
            print(f"[{i:02d}] {e.titulo}")
            print(f"     Fecha:     {e.fecha}")
            print(f"     Ronda:     {e.ronda}")
            print(f"     Tipo:      {e.tipo}")
            print(f"     Agente:    {e.agente}")
            print(f"     Estado:    {e.estado}")
            if e.detalle:
                print(f"     Detalle:   {e.detalle[:80]}...")
            if e.referencia:
                print(f"     Referencia:{e.referencia}")
            print()
        print(f"Total: {len(entries)} entradas generadas correctamente.")
        return

    # Validate credentials
    if not os.environ.get("NOTION_API_KEY") and not use_worker:
        logger.error("Se requiere NOTION_API_KEY (o WORKER_URL + WORKER_TOKEN)")
        sys.exit(1)

    # Insert entries
    ok = 0
    errors = 0
    for i, entry in enumerate(entries, 1):
        logger.info(
            "[%d/%d] Insertando: %s", i, len(entries), entry.titulo[:60]
        )
        try:
            if use_worker:
                result = insert_via_worker(entry, worker_url, worker_token)
            else:
                result = insert_via_notion_api(entry, db_id)
            logger.info("  ✓ page_id=%s", result.get("page_id", "?")[:8])
            ok += 1
        except Exception as exc:
            logger.error("  ✗ Error insertando '%s': %s", entry.titulo[:50], exc)
            errors += 1

        if i < len(entries):
            time.sleep(args.delay)

    print(f"\n{'='*50}")
    print(f"Completado: {ok} OK, {errors} errores de {len(entries)} entradas.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
