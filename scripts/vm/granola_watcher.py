"""
Granola Watcher — Monitorea carpeta de exports y envía al Worker.

Corre en la VM Windows. Detecta archivos .md nuevos en GRANOLA_EXPORT_DIR,
los parsea para extraer metadata, y los envía al Worker via POST /run
con la tarea granola.process_transcript.

Modos:
    python granola_watcher.py          # Modo continuo (watchdog)
    python granola_watcher.py --once   # Procesa pendientes y sale

Variables de entorno (acepta prefijo GRANOLA_ o sin prefijo):
    GRANOLA_EXPORT_DIR        Carpeta a monitorear (requerida)
    GRANOLA_PROCESSED_DIR     Destino post-procesado (default: EXPORT_DIR/processed)
    GRANOLA_WORKER_URL        URL del Worker (default: http://localhost:8088)
    GRANOLA_WORKER_TOKEN      Token de autenticación del Worker (requerida)
    GRANOLA_POLL_INTERVAL     Segundos entre checks (default: 5)
    GRANOLA_LOG_FILE          Ruta del log file (default: C:\\Granola\\watcher.log)
"""

import argparse
import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests

from scripts.vm.granola_watcher_env_loader import load_env

_ENV_PATH = os.environ.get("GRANOLA_ENV_FILE", r"C:\Granola\.env")
load_env(_ENV_PATH)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2


def _setup_logging() -> logging.Logger:
    """Configure logging to stdout and optionally to a file."""
    _logger = logging.getLogger("granola_watcher")
    if _logger.handlers:
        return _logger
    _logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(fmt)
    _logger.addHandler(stdout_handler)

    log_file = os.environ.get("GRANOLA_LOG_FILE", r"C:\Granola\watcher.log")
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(fmt)
        _logger.addHandler(file_handler)
    except OSError:
        _logger.debug("Could not open log file %s; using stdout only", log_file)

    return _logger


logger = _setup_logging()


def _get_poll_interval() -> int:
    raw = os.environ.get("GRANOLA_POLL_INTERVAL", "5")
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def parse_granola_markdown(text: str, filename: str = "") -> dict[str, Any]:
    """Parse a Granola-exported markdown file into structured data."""
    lines = text.strip().splitlines()

    title = filename.replace(".md", "").strip()
    date_str = ""
    attendees: list[str] = []
    action_items: list[dict[str, str]] = []
    metadata: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current_section = "_preamble"
    sections[current_section] = []

    def _normalize_metadata_key(label: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")

    for line in lines:
        stripped = line.strip()

        # Title from first H1
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            continue

        if stripped.startswith("# ") and title == filename.replace(".md", "").strip():
            title = stripped[2:].strip()
            continue

        # Metadata fields
        date_match = re.match(
            r"\*\*(?:Date|Fecha)\s*:\*\*\s*(.+)", stripped, re.IGNORECASE
        )
        if date_match:
            date_str = date_match.group(1).strip()
            continue

        att_match = re.match(
            r"\*\*(?:Attendees|Participants|Participantes|Asistentes)\s*:\*\*\s*(.+)",
            stripped,
            re.IGNORECASE,
        )
        if att_match:
            attendees = [a.strip() for a in att_match.group(1).split(",") if a.strip()]
            continue

        metadata_match = re.match(r"\*\*(.+?)\s*:\*\*\s*(.+)", stripped)
        if metadata_match:
            label = metadata_match.group(1).strip()
            value = metadata_match.group(2).strip()
            metadata[_normalize_metadata_key(label)] = value
            continue

        bullet_metadata_match = re.match(r"-\s*\*\*(.+?)\s*:\*\*\s*(.+)", stripped)
        if bullet_metadata_match:
            label = bullet_metadata_match.group(1).strip()
            value = bullet_metadata_match.group(2).strip()
            metadata[_normalize_metadata_key(label)] = value
            continue

        # Section headers
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            sections.setdefault(current_section, [])
            continue

        sections.setdefault(current_section, [])
        sections[current_section].append(line)

    # Extract action items from the "action items" section
    ai_section = sections.get("action items", [])
    for line in ai_section:
        m = re.match(r"[-*]\s*\[[ x]?\]\s*(.+)", line.strip())
        if m:
            item_text = m.group(1).strip()
            assignee = ""
            due = ""
            # Try to parse "(Person, YYYY-MM-DD)" at the end
            paren = re.search(r"\(([^)]+)\)\s*$", item_text)
            if paren:
                parts = [p.strip() for p in paren.group(1).split(",")]
                for p in parts:
                    if re.match(r"\d{4}-\d{2}-\d{2}", p):
                        due = p
                    else:
                        assignee = p
                item_text = item_text[: paren.start()].strip()
            action_items.append(
                {"text": item_text, "assignee": assignee, "due": due}
            )

    notes_parts = sections.get("notes", sections.get("notas", []))
    transcript_parts = sections.get("transcript", sections.get("transcripción", []))

    # If no specific sections, use everything as content
    if not notes_parts and not transcript_parts:
        all_content = []
        for sec_name, sec_lines in sections.items():
            if sec_name not in ("action items",):
                all_content.extend(sec_lines)
        notes_parts = all_content

    content = "\n".join(notes_parts).strip()
    transcript = "\n".join(transcript_parts).strip()

    full_content = content
    if transcript:
        full_content = f"{content}\n\n---\n\n## Transcripción\n\n{transcript}" if content else transcript

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    return {
        "title": title or "Reunión sin título",
        "content": full_content or "(sin contenido)",
        "date": date_str,
        "attendees": attendees,
        "action_items": action_items,
        "source": "granola",
        "metadata": metadata,
        "granola_document_id": metadata.get("granola_document_id", ""),
        "source_updated_at": metadata.get("updated_at", ""),
        "source_url": metadata.get("source_url", ""),
    }


# ---------------------------------------------------------------------------
# Worker client
# ---------------------------------------------------------------------------

def send_to_worker(
    worker_url: str, worker_token: str, task: str, input_data: dict[str, Any]
) -> dict[str, Any]:
    """POST a task to the Worker API with retry + exponential backoff."""
    url = f"{worker_url.rstrip('/')}/run"
    headers = {"Authorization": f"Bearer {worker_token}", "Content-Type": "application/json"}
    payload = {"task": task, "input": input_data}

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as exc:
            last_exc = exc
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Connection error (attempt %d/%d), retrying in %ds: %s",
                attempt, MAX_RETRIES, wait, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)
        except requests.exceptions.RequestException:
            raise

    raise requests.exceptions.ConnectionError(
        f"Failed after {MAX_RETRIES} retries"
    ) from last_exc


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

def process_file(filepath: Path, worker_url: str, worker_token: str, processed_dir: Path) -> bool:
    """Process a single markdown file: parse, send to worker, move to processed."""
    logger.info("Processing: %s", filepath.name)

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Failed to read %s: %s", filepath, e)
        return False

    if len(text.strip()) < 10:
        logger.warning("Skipping %s: too short (%d chars)", filepath.name, len(text))
        return False

    parsed = parse_granola_markdown(text, filepath.name)
    logger.info(
        "Parsed: title=%r, date=%s, attendees=%d, action_items=%d",
        parsed["title"],
        parsed["date"],
        len(parsed["attendees"]),
        len(parsed["action_items"]),
    )

    try:
        result = send_to_worker(worker_url, worker_token, "granola.process_transcript", parsed)
        logger.info("Worker response: %s", result)
    except requests.exceptions.RequestException as e:
        logger.error("Worker request failed for %s: %s", filepath.name, e)
        return False

    # Move to processed
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / filepath.name
    if dest.exists():
        stem = filepath.stem
        dest = processed_dir / f"{stem}_{int(time.time())}{filepath.suffix}"
    try:
        shutil.move(str(filepath), str(dest))
        logger.info("Moved to: %s", dest)
    except Exception as e:
        logger.error("Failed to move %s: %s", filepath, e)

    return True


def scan_and_process(export_dir: Path, worker_url: str, worker_token: str, processed_dir: Path) -> int:
    """Scan export_dir for unprocessed .md files and process them."""
    md_files = sorted(export_dir.glob("*.md"))
    processed = 0
    for f in md_files:
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        if process_file(f, worker_url, worker_token, processed_dir):
            processed += 1
    return processed


# ---------------------------------------------------------------------------
# Watcher modes
# ---------------------------------------------------------------------------

def run_once(export_dir: Path, worker_url: str, worker_token: str, processed_dir: Path) -> None:
    """Process all pending files and exit."""
    count = scan_and_process(export_dir, worker_url, worker_token, processed_dir)
    logger.info("One-shot complete: %d files processed", count)


def run_polling(export_dir: Path, worker_url: str, worker_token: str, processed_dir: Path) -> None:
    """Poll the export directory continuously."""
    interval = _get_poll_interval()
    logger.info("Polling mode: watching %s every %ds", export_dir, interval)
    try:
        while True:
            scan_and_process(export_dir, worker_url, worker_token, processed_dir)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Watcher stopped by user")


def run_watchdog(export_dir: Path, worker_url: str, worker_token: str, processed_dir: Path) -> None:
    """Use watchdog for filesystem events (preferred on Windows)."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.warning("watchdog not installed; falling back to polling mode")
        run_polling(export_dir, worker_url, worker_token, processed_dir)
        return

    class GranolaHandler(FileSystemEventHandler):
        def on_created(self, event):  # type: ignore[override]
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() == ".md" and not path.name.startswith((".", "_")):
                time.sleep(1)  # wait for write to finish
                process_file(path, worker_url, worker_token, processed_dir)

    observer = Observer()
    observer.schedule(GranolaHandler(), str(export_dir), recursive=False)
    observer.start()
    logger.info("Watchdog mode: watching %s", export_dir)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    logger.info("Watcher stopped")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _env(key: str, *fallback_keys: str, default: str = "") -> str:
    """Read env var with fallback keys for backward compat (GRANOLA_* → legacy)."""
    val = os.environ.get(key, "")
    if val:
        return val
    for fb in fallback_keys:
        val = os.environ.get(fb, "")
        if val:
            return val
    return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Granola Export Watcher")
    parser.add_argument("--once", action="store_true", help="Process pending files and exit")
    parser.add_argument("--poll", action="store_true", help="Use polling instead of watchdog")
    args = parser.parse_args()

    export_dir_str = _env("GRANOLA_EXPORT_DIR")
    if not export_dir_str:
        logger.error("GRANOLA_EXPORT_DIR not set")
        sys.exit(1)

    export_dir = Path(export_dir_str)
    if not export_dir.is_dir():
        logger.error("GRANOLA_EXPORT_DIR does not exist: %s", export_dir)
        sys.exit(1)

    processed_dir = Path(
        _env("GRANOLA_PROCESSED_DIR", default=str(export_dir / "processed"))
    )
    worker_url = _env("GRANOLA_WORKER_URL", "WORKER_URL", default="http://localhost:8088")
    worker_token = _env("GRANOLA_WORKER_TOKEN", "WORKER_TOKEN")
    if not worker_token:
        logger.error("GRANOLA_WORKER_TOKEN / WORKER_TOKEN not set")
        sys.exit(1)

    count = scan_and_process(export_dir, worker_url, worker_token, processed_dir)
    if count:
        logger.info("Initial scan: processed %d files", count)

    if args.once:
        return

    if args.poll:
        run_polling(export_dir, worker_url, worker_token, processed_dir)
    else:
        run_watchdog(export_dir, worker_url, worker_token, processed_dir)


if __name__ == "__main__":
    main()
