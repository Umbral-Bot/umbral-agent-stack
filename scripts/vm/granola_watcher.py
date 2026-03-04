"""
Granola Watcher — Monitorea carpeta de exports de Granola en la VM Windows.

Detecta archivos .md nuevos en GRANOLA_EXPORT_DIR, parsea metadata y
transcripción, y los envía al Worker via POST /run con task
"granola.process_transcript".  Archivos procesados se mueven a
GRANOLA_PROCESSED_DIR (default: EXPORT_DIR/processed/).

Variables de entorno:
    GRANOLA_EXPORT_DIR     Carpeta a monitorear (requerida).
    GRANOLA_PROCESSED_DIR  Carpeta destino post-proceso (default: EXPORT_DIR/processed).
    WORKER_URL             URL del Worker HTTP (requerida).
    WORKER_TOKEN           Bearer token de autenticación (requerida).
    GRANOLA_POLL_INTERVAL  Segundos entre escaneos (default: 30).

Uso:
    python scripts/vm/granola_watcher.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests  # type: ignore[no-redef]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("granola_watcher")

POLL_INTERVAL = int(os.environ.get("GRANOLA_POLL_INTERVAL", "30"))


def _get_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        logger.error("Variable de entorno %s no configurada", name)
        sys.exit(1)
    return val


def parse_markdown(text: str, filename: str) -> dict[str, Any]:
    """Extract metadata and content from a Granola markdown export.

    Heuristics:
    - First ``# heading`` becomes the title.
    - Date extracted from filename pattern ``YYYY-MM-DD`` or from content.
    - Lines matching action-item patterns are collected.
    - Attendees extracted from lines starting with "Participantes:" or similar.
    """
    lines = text.split("\n")
    title: str | None = None
    attendees: list[str] = []
    action_items: list[str] = []
    date: str | None = None

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if date_match:
        date = date_match.group(1)

    in_action_section = False

    for line in lines:
        stripped = line.strip()

        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue

        if re.match(r"^#{1,3}\s+.*(?:action|tareas|compromisos|pendientes|to.?do)", stripped, re.IGNORECASE):
            in_action_section = True
            continue

        if in_action_section and re.match(r"^#{1,3}\s+", stripped):
            in_action_section = False

        if in_action_section and re.match(r"^[-*]\s+", stripped):
            item = re.sub(r"^[-*]\s+", "", stripped)
            if item:
                action_items.append(item)
            continue

        if not in_action_section and re.match(r"^[-*]\s+\[.\]\s+", stripped):
            item = re.sub(r"^[-*]\s+\[.\]\s+", "", stripped)
            if item:
                action_items.append(item)
            continue

        attendee_match = re.match(
            r"^(?:participantes?|attendees?|asistentes?)\s*:\s*(.+)",
            stripped,
            re.IGNORECASE,
        )
        if attendee_match:
            raw = attendee_match.group(1)
            attendees = [a.strip() for a in re.split(r"[,;]", raw) if a.strip()]
            continue

        if not date:
            inline_date = re.search(r"(?:fecha|date)\s*:\s*(\d{4}-\d{2}-\d{2})", stripped, re.IGNORECASE)
            if inline_date:
                date = inline_date.group(1)

    if not title:
        stem = Path(filename).stem
        title = re.sub(r"\d{4}-\d{2}-\d{2}[_-]?", "", stem).replace("_", " ").replace("-", " ").strip()
        if not title:
            title = stem

    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "title": title,
        "content": text,
        "date": date,
        "attendees": attendees,
        "action_items": action_items,
    }


def send_to_worker(payload: dict[str, Any], worker_url: str, token: str) -> dict[str, Any]:
    """POST /run with task granola.process_transcript."""
    url = f"{worker_url.rstrip('/')}/run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "task": "granola.process_transcript",
        "input": payload,
    }

    logger.info("Enviando transcripción '%s' al Worker (%s)", payload.get("title"), url)
    resp = requests.post(url, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    logger.info("Worker respondió: ok=%s", result.get("ok"))
    return result


def process_file(filepath: Path, processed_dir: Path, worker_url: str, token: str) -> bool:
    """Read, parse, send and move a single markdown file.  Returns True on success."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.error("No se pudo leer %s: %s", filepath, exc)
        return False

    if not text.strip():
        logger.warning("Archivo vacío, ignorando: %s", filepath.name)
        return False

    payload = parse_markdown(text, filepath.name)

    try:
        send_to_worker(payload, worker_url, token)
    except Exception as exc:
        logger.error("Error enviando %s al Worker: %s", filepath.name, exc)
        return False

    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / filepath.name
    counter = 1
    while dest.exists():
        dest = processed_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
        counter += 1

    try:
        shutil.move(str(filepath), str(dest))
        logger.info("Movido a processed: %s", dest.name)
    except OSError as exc:
        logger.warning("No se pudo mover %s: %s", filepath.name, exc)

    return True


def scan_directory(export_dir: Path, processed_dir: Path, worker_url: str, token: str) -> int:
    """Scan for new .md files and process them.  Returns count of processed files."""
    md_files = sorted(export_dir.glob("*.md"))
    processed = 0
    for f in md_files:
        if f.is_file() and process_file(f, processed_dir, worker_url, token):
            processed += 1
    return processed


def main() -> None:
    export_dir_str = _get_env("GRANOLA_EXPORT_DIR")
    worker_url = _get_env("WORKER_URL")
    token = _get_env("WORKER_TOKEN")

    export_dir = Path(export_dir_str)
    processed_dir_str = os.environ.get("GRANOLA_PROCESSED_DIR", "").strip()
    processed_dir = Path(processed_dir_str) if processed_dir_str else export_dir / "processed"

    if not export_dir.exists():
        logger.info("Creando carpeta de export: %s", export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

    processed_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Granola Watcher iniciado — dir=%s, processed=%s, poll=%ds",
        export_dir, processed_dir, POLL_INTERVAL,
    )

    try:
        while True:
            n = scan_directory(export_dir, processed_dir, worker_url, token)
            if n:
                logger.info("Procesados %d archivos en este ciclo", n)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Watcher detenido por el usuario")


if __name__ == "__main__":
    main()
