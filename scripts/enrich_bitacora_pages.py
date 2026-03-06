#!/usr/bin/env python3
"""
Enriquece las páginas existentes de la Bitácora Umbral Agent Stack en Notion.

Para cada entrada de la base de datos:
  1. Extrae título y propiedades existentes
  2. Busca contexto en .agents/board.md, .agents/tasks/, y PRs de GitHub
  3. Genera contenido enriquecido: resumen ampliado, diagrama Mermaid, tabla
  4. Añade bloques a la página via notion_client.append_blocks_to_page

Uso:
    export NOTION_API_KEY=...
    export NOTION_BITACORA_DB_ID=<NOTION_BITACORA_DB_ID>
    python scripts/enrich_bitacora_pages.py [--dry-run]
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker import notion_client
from worker.notion_client import (
    _block_heading2,
    _block_heading3,
    _block_paragraph,
    _block_bulleted,
    _block_callout,
    _block_code,
    _block_divider,
    _block_table,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def require_bitacora_db_id() -> str:
    """Return the configured Bitacora database ID or abort with a clear message."""
    bitacora_db_id = os.environ.get("NOTION_BITACORA_DB_ID")
    if bitacora_db_id:
        return bitacora_db_id

    raise SystemExit(
        "NOTION_BITACORA_DB_ID no está configurada. Definí la variable de entorno antes de ejecutar este script."
    )


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_board() -> str:
    path = REPO_ROOT / ".agents" / "board.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_task_files() -> dict[str, str]:
    """Return {filename: content} for all task files."""
    tasks_dir = REPO_ROOT / ".agents" / "tasks"
    result = {}
    if tasks_dir.is_dir():
        for f in sorted(tasks_dir.glob("*.md")):
            result[f.name] = f.read_text(encoding="utf-8")
    return result


def get_pr_info(pr_number: int) -> dict[str, Any] | None:
    """Fetch PR info via gh CLI."""
    try:
        out = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "number,title,body,files,mergedAt,labels"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
        )
        if out.returncode == 0:
            return json.loads(out.stdout)
    except Exception as e:
        logger.warning("No se pudo obtener PR #%d: %s", pr_number, e)
    return None


def get_all_merged_prs() -> list[dict[str, Any]]:
    """Fetch all merged PRs."""
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--limit", "100",
             "--json", "number,title,body,files,mergedAt"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
        )
        if out.returncode == 0:
            return json.loads(out.stdout)
    except Exception as e:
        logger.warning("No se pudo obtener lista de PRs: %s", e)
    return []


def extract_page_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop_name in ("Name", "Nombre", "Título", "Title", "name", "title"):
        prop = props.get(prop_name)
        if prop and prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts)
    return ""


def extract_page_props(page: dict) -> dict[str, str]:
    """Extract key properties as strings."""
    props = page.get("properties", {})
    result: dict[str, str] = {}
    for key, val in props.items():
        ptype = val.get("type", "")
        if ptype == "title":
            result[key] = "".join(p.get("plain_text", "") for p in val.get("title", []))
        elif ptype == "rich_text":
            result[key] = "".join(p.get("plain_text", "") for p in val.get("rich_text", []))
        elif ptype == "select":
            sel = val.get("select")
            result[key] = sel.get("name", "") if sel else ""
        elif ptype == "multi_select":
            result[key] = ", ".join(s.get("name", "") for s in val.get("multi_select", []))
        elif ptype == "date":
            d = val.get("date")
            result[key] = d.get("start", "") if d else ""
        elif ptype == "number":
            result[key] = str(val.get("number", ""))
        elif ptype == "checkbox":
            result[key] = str(val.get("checkbox", False))
    return result


def find_matching_context(title: str, board: str, tasks: dict[str, str], prs: list[dict]) -> dict[str, Any]:
    """Find relevant context for a bitácora entry based on its title."""
    ctx: dict[str, Any] = {
        "board_section": "",
        "task_files": [],
        "pr_info": [],
        "round_number": None,
    }

    title_lower = title.lower()

    round_match = re.search(r'ronda\s*(\d+)', title_lower)
    if not round_match:
        round_match = re.search(r'r(\d+)', title_lower)
    if round_match:
        ctx["round_number"] = int(round_match.group(1))

    pr_match = re.search(r'pr\s*#?(\d+)', title_lower)
    pr_numbers_from_title = []
    if pr_match:
        pr_numbers_from_title.append(int(pr_match.group(1)))

    for line in board.split("\n"):
        line_lower = line.lower()
        if any(kw in line_lower for kw in _keywords_from_title(title)):
            if ctx["board_section"]:
                ctx["board_section"] += "\n"
            ctx["board_section"] += line

    round_tag = f"r{ctx['round_number']}" if ctx["round_number"] else None
    for fname, content in tasks.items():
        fname_lower = fname.lower()
        if round_tag and round_tag in fname_lower:
            ctx["task_files"].append({"name": fname, "content": content[:3000]})
        elif any(kw in fname_lower or kw in content[:500].lower() for kw in _keywords_from_title(title)):
            ctx["task_files"].append({"name": fname, "content": content[:3000]})

    for pr in prs:
        pr_title_lower = pr.get("title", "").lower()
        pr_body_lower = pr.get("body", "").lower()[:500]
        if pr["number"] in pr_numbers_from_title:
            ctx["pr_info"].append(pr)
        elif round_tag and round_tag in pr_title_lower:
            ctx["pr_info"].append(pr)
        elif any(kw in pr_title_lower or kw in pr_body_lower for kw in _keywords_from_title(title)):
            ctx["pr_info"].append(pr)

    return ctx


def _keywords_from_title(title: str) -> list[str]:
    stopwords = {
        "de", "del", "la", "el", "los", "las", "en", "con", "para", "por", "y", "o", "a",
        "un", "una", "es", "se", "que", "no", "al", "lo", "su", "más", "como", "todo",
        "ha", "fue", "son", "e", "—", "-", "+", "hito", "ronda", "pr", "#", ":", "feat",
        "the", "and", "of", "to", "in", "for", "on", "with", "from", "at"
    }
    words = re.findall(r'[a-záéíóúñü\d]+', title.lower())
    return [w for w in words if len(w) > 2 and w not in stopwords]


def generate_enrichment_blocks(title: str, props: dict[str, str], ctx: dict[str, Any]) -> list[dict]:
    """Generate Notion blocks to enrich a bitácora page."""
    blocks: list[dict] = []

    blocks.append(_block_divider())
    blocks.append(_block_callout("Contenido enriquecido — generado automáticamente por Rick", "🤖", "blue_background"))
    blocks.append(_block_divider())

    summary = _build_summary(title, props, ctx)
    blocks.append(_block_heading2("Resumen ampliado"))
    for para in summary:
        blocks.append(_block_paragraph(para))

    blocks.append(_block_divider())

    mermaid = _build_mermaid(title, props, ctx)
    if mermaid:
        blocks.append(_block_heading2("Diagrama"))
        blocks.append(_block_code(mermaid, "mermaid"))
        blocks.append(_block_divider())

    task_table = _build_task_table(ctx)
    if task_table:
        blocks.append(_block_heading2("Tareas relacionadas"))
        blocks.append(task_table)
        blocks.append(_block_divider())

    pr_table = _build_pr_table(ctx)
    if pr_table:
        blocks.append(_block_heading2("Pull Requests"))
        blocks.append(pr_table)
        blocks.append(_block_divider())

    files_list = _build_files_list(ctx)
    if files_list:
        blocks.append(_block_heading2("Archivos modificados"))
        for b in files_list:
            blocks.append(b)
        blocks.append(_block_divider())

    timeline = _build_timeline(title, props, ctx)
    if timeline:
        blocks.append(_block_heading2("Línea de tiempo"))
        blocks.append(_block_code(timeline, "mermaid"))
        blocks.append(_block_divider())

    return blocks


def _build_summary(title: str, props: dict[str, str], ctx: dict[str, Any]) -> list[str]:
    """Build 2-4 paragraph summary."""
    paragraphs = []

    detail = props.get("Detalle", "") or props.get("Descripción", "") or props.get("Description", "")
    category = props.get("Categoría", "") or props.get("Tipo", "") or props.get("Category", "")
    date = props.get("Fecha", "") or props.get("Date", "")
    round_num = ctx.get("round_number")

    if round_num:
        intro = f"Este hito corresponde a la Ronda {round_num} del desarrollo de Umbral Agent Stack."
    else:
        intro = "Este hito forma parte del desarrollo de Umbral Agent Stack."

    if category:
        intro += f" Categorizado como: {category}."
    if date:
        intro += f" Registrado el {date}."
    paragraphs.append(intro)

    if detail:
        paragraphs.append(detail)

    task_descriptions = []
    for tf in ctx.get("task_files", [])[:5]:
        content = tf["content"]
        obj_match = re.search(r'## Objetivo\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if obj_match:
            obj_text = obj_match.group(1).strip()[:300]
            task_descriptions.append(obj_text)

    if task_descriptions:
        ctx_para = "Contexto técnico: " + " ".join(task_descriptions[:2])
        paragraphs.append(ctx_para[:2000])

    agents = set()
    for tf in ctx.get("task_files", []):
        content = tf["content"]
        assigned = re.search(r'assigned_to:\s*(.+)', content)
        if assigned:
            agents.add(assigned.group(1).strip())

    if agents:
        agents_str = ", ".join(sorted(agents))
        impact = f"Agentes involucrados: {agents_str}. "
    else:
        impact = ""

    pr_count = len(ctx.get("pr_info", []))
    task_count = len(ctx.get("task_files", []))
    if pr_count or task_count:
        impact += f"Esta fase abarcó {task_count} tareas"
        if pr_count:
            impact += f" y {pr_count} pull requests"
        impact += ", contribuyendo al avance continuo del sistema de orquestación multi-agente."
    else:
        impact += "Contribuye al avance continuo del sistema de orquestación multi-agente."

    paragraphs.append(impact)

    return paragraphs


def _build_mermaid(title: str, props: dict[str, str], ctx: dict[str, Any]) -> str:
    """Build a Mermaid diagram based on entry type."""
    category = (props.get("Categoría", "") or props.get("Tipo", "") or "").lower()
    title_lower = title.lower()

    if any(kw in title_lower for kw in ["pipeline", "flujo", "workflow"]):
        return _mermaid_flowchart(title, ctx)
    elif any(kw in title_lower for kw in ["arquitectura", "infraestructura", "stack"]):
        return _mermaid_architecture(title, ctx)
    elif any(kw in title_lower for kw in ["skill", "handler", "task"]):
        return _mermaid_component(title, ctx)
    elif "pr" in category or "pr" in title_lower:
        return _mermaid_pr_flow(title, ctx)
    elif ctx.get("round_number"):
        return _mermaid_round_overview(title, ctx)
    else:
        return _mermaid_generic(title, ctx)


def _mermaid_flowchart(title: str, ctx: dict[str, Any]) -> str:
    keywords = _keywords_from_title(title)
    nodes = []
    for i, kw in enumerate(keywords[:6]):
        node_id = chr(65 + i)
        nodes.append(f"    {node_id}[{kw.capitalize()}]")

    if len(nodes) < 2:
        nodes = ["    A[Entrada]", "    B[Proceso]", "    C[Resultado]"]

    lines = ["flowchart LR"]
    lines.extend(nodes)
    for i in range(len(nodes) - 1):
        lines.append(f"    {chr(65+i)} --> {chr(66+i)}")
    return "\n".join(lines)


def _mermaid_architecture(title: str, ctx: dict[str, Any]) -> str:
    return """flowchart TD
    subgraph VPS["Control Plane (VPS)"]
        D[Dispatcher]
        R[(Redis)]
        CR[Crons]
    end
    subgraph VM["Execution Plane (VM)"]
        W[Worker API]
        N[Notion Client]
        LLM[LLM Providers]
    end
    D <--> R
    CR --> D
    D <--> W
    W --> N
    W --> LLM"""


def _mermaid_component(title: str, ctx: dict[str, Any]) -> str:
    task_names = []
    for tf in ctx.get("task_files", [])[:6]:
        content = tf["content"]
        t_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if t_match:
            name = t_match.group(1).strip()[:40]
            task_names.append(name)

    if not task_names:
        task_names = [title[:40]]

    lines = ["flowchart TD"]
    lines.append(f'    W["Worker API"]')
    for i, name in enumerate(task_names[:6]):
        safe_name = name.replace('"', "'")
        lines.append(f'    T{i}["{safe_name}"]')
        lines.append(f"    W --> T{i}")
    return "\n".join(lines)


def _mermaid_pr_flow(title: str, ctx: dict[str, Any]) -> str:
    return """flowchart LR
    A[Feature Branch] --> B[Pull Request]
    B --> C[Code Review]
    C --> D[Merge a Main]
    D --> E[Deploy VPS]"""


def _mermaid_round_overview(title: str, ctx: dict[str, Any]) -> str:
    round_num = ctx.get("round_number", "?")
    task_count = len(ctx.get("task_files", []))
    pr_count = len(ctx.get("pr_info", []))

    agents = set()
    for tf in ctx.get("task_files", []):
        assigned = re.search(r'assigned_to:\s*(.+)', tf["content"])
        if assigned:
            agents.add(assigned.group(1).strip())

    lines = [f'flowchart TD']
    lines.append(f'    R["Ronda {round_num}"]')
    lines.append(f'    T["{task_count} Tareas"]')
    lines.append(f'    P["{pr_count} PRs"]')
    lines.append(f'    R --> T')
    lines.append(f'    R --> P')

    for i, agent in enumerate(sorted(agents)[:5]):
        safe = agent.replace('"', "'")
        lines.append(f'    A{i}["{safe}"]')
        lines.append(f'    T --> A{i}')

    lines.append(f'    T --> D["Deploy"]')
    lines.append(f'    P --> D')
    return "\n".join(lines)


def _mermaid_generic(title: str, ctx: dict[str, Any]) -> str:
    keywords = _keywords_from_title(title)[:4]
    if not keywords:
        keywords = ["inicio", "desarrollo", "resultado"]

    lines = ["flowchart LR"]
    for i, kw in enumerate(keywords):
        node_id = chr(65 + i)
        lines.append(f'    {node_id}["{kw.capitalize()}"]')
    for i in range(len(keywords) - 1):
        lines.append(f"    {chr(65+i)} --> {chr(66+i)}")
    return "\n".join(lines)


def _build_task_table(ctx: dict[str, Any]) -> dict | None:
    """Build a Notion table block with task info."""
    task_files = ctx.get("task_files", [])
    if not task_files:
        return None

    headers = ["Tarea", "Asignado", "Estado"]
    rows = []
    for tf in task_files[:15]:
        content = tf["content"]
        t_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        a_match = re.search(r'assigned_to:\s*(.+)', content)
        s_match = re.search(r'status:\s*(.+)', content)
        title_val = t_match.group(1).strip() if t_match else tf["name"]
        assigned = a_match.group(1).strip() if a_match else "—"
        status = s_match.group(1).strip() if s_match else "—"
        rows.append([title_val[:60], assigned, status])

    if not rows:
        return None

    return _block_table(headers, rows)


def _build_pr_table(ctx: dict[str, Any]) -> dict | None:
    """Build a Notion table block with PR info."""
    prs = ctx.get("pr_info", [])
    if not prs:
        return None

    headers = ["PR", "Título", "Fecha merge"]
    rows = []
    seen = set()
    for pr in prs[:10]:
        num = pr.get("number", 0)
        if num in seen:
            continue
        seen.add(num)
        title_val = pr.get("title", "")[:60]
        merged = pr.get("mergedAt", "")[:10]
        rows.append([f"#{num}", title_val, merged])

    if not rows:
        return None
    return _block_table(headers, rows)


def _build_files_list(ctx: dict[str, Any]) -> list[dict]:
    """Build a bullet list of modified files from PRs."""
    all_files: list[str] = []
    seen = set()
    for pr in ctx.get("pr_info", []):
        for f in pr.get("files", []):
            fpath = f.get("path", "")
            if fpath and fpath not in seen:
                seen.add(fpath)
                adds = f.get("additions", 0)
                dels = f.get("deletions", 0)
                all_files.append(f"{fpath} (+{adds}/-{dels})")

    if not all_files:
        return []

    blocks = []
    for fp in all_files[:20]:
        blocks.append(_block_bulleted(fp))
    return blocks


def _build_timeline(title: str, props: dict[str, str], ctx: dict[str, Any]) -> str:
    """Build a Mermaid timeline diagram."""
    round_num = ctx.get("round_number")
    if not round_num:
        return ""

    events = []
    for tf in ctx.get("task_files", [])[:5]:
        content = tf["content"]
        t_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if t_match:
            name = t_match.group(1).strip()[:50]
            events.append(name)

    if len(events) < 2:
        return ""

    lines = ["timeline"]
    lines.append(f"    title Ronda {round_num}")
    for ev in events:
        safe = ev.replace('"', "'").replace(":", " -")
        lines.append(f"    {safe}")
    return "\n".join(lines)


def enrich_page(page: dict, board: str, tasks: dict[str, str], prs: list[dict], dry_run: bool = False) -> bool:
    """Enrich a single bitácora page. Returns True if blocks were appended."""
    page_id = page["id"]
    title = extract_page_title(page)
    props = extract_page_props(page)

    if not title:
        logger.warning("Página %s sin título, omitiendo", page_id[:8])
        return False

    logger.info("Procesando: %s (%s)", title[:60], page_id[:8])

    ctx = find_matching_context(title, board, tasks, prs)
    blocks = generate_enrichment_blocks(title, props, ctx)

    if not blocks:
        logger.info("  Sin bloques generados para: %s", title[:60])
        return False

    logger.info("  Generados %d bloques para: %s", len(blocks), title[:60])

    if dry_run:
        logger.info("  [DRY-RUN] No se envía a Notion")
        return True

    try:
        result = notion_client.append_blocks_to_page(page_id, blocks)
        logger.info("  Bloques añadidos: %d", result.get("blocks_appended", 0))
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.error("  Error al enriquecer %s: %s", page_id[:8], e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Enriquece páginas de la Bitácora en Notion")
    parser.add_argument("--dry-run", action="store_true", help="No enviar a Notion, solo generar")
    parser.add_argument("--limit", type=int, default=0, help="Limitar número de páginas a procesar")
    parser.add_argument("--page-id", type=str, help="Procesar solo una página específica")
    args = parser.parse_args()

    if not os.environ.get("NOTION_API_KEY"):
        logger.error("NOTION_API_KEY no está configurada")
        sys.exit(1)

    logger.info("Cargando contexto del repositorio...")
    board = load_board()
    tasks = load_task_files()
    logger.info("  Board: %d caracteres", len(board))
    logger.info("  Task files: %d archivos", len(tasks))

    logger.info("Cargando PRs de GitHub...")
    prs = get_all_merged_prs()
    logger.info("  PRs mergeados: %d", len(prs))

    bitacora_db_id = require_bitacora_db_id()
    logger.info("Consultando base de datos Bitácora (%s)...", bitacora_db_id[:8])
    pages = notion_client.query_database(bitacora_db_id)
    logger.info("  Páginas encontradas: %d", len(pages))

    if args.page_id:
        pages = [p for p in pages if p["id"].replace("-", "") == args.page_id.replace("-", "")]
        if not pages:
            logger.error("Página %s no encontrada en la Bitácora", args.page_id)
            sys.exit(1)

    if args.limit:
        pages = pages[:args.limit]

    enriched = 0
    errors = 0
    for page in pages:
        try:
            if enrich_page(page, board, tasks, prs, dry_run=args.dry_run):
                enriched += 1
        except Exception as e:
            logger.error("Error procesando página %s: %s", page.get("id", "?")[:8], e)
            errors += 1

    logger.info("=== Resumen ===")
    logger.info("Total páginas: %d", len(pages))
    logger.info("Enriquecidas: %d", enriched)
    logger.info("Errores: %d", errors)


if __name__ == "__main__":
    main()
