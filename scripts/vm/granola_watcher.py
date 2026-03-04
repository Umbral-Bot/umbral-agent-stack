"""
Granola Watcher — Monitorea carpeta de exports y envía al Worker.

Corre en la VM Windows. Detecta archivos .md nuevos en GRANOLA_EXPORT_DIR,
parsea metadata (título, fecha, participantes, action items), y llama al
Worker con task granola.process_transcript.

Requisitos:
    pip install watchdog httpx

Variables de entorno:
    GRANOLA_EXPORT_DIR   — carpeta a monitorear (default: C:\\Users\\rick\\Documents\\Granola)
    GRANOLA_PROCESSED_DIR — carpeta destino (default: {EXPORT_DIR}\\processed)
    WORKER_URL           — URL del Worker (default: http://localhost:8088)
    WORKER_TOKEN         — Bearer token del Worker
"""

import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("granola_watcher.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("granola_watcher")

EXPORT_DIR = Path(os.environ.get("GRANOLA_EXPORT_DIR", r"C:\Users\rick\Documents\Granola"))
PROCESSED_DIR = Path(os.environ.get("GRANOLA_PROCESSED_DIR", str(EXPORT_DIR / "processed")))
WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8088")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
POLL_INTERVAL = int(os.environ.get("GRANOLA_POLL_INTERVAL", "10"))


def parse_markdown_transcript(content: str) -> dict:
    """Extract structured data from a Granola-style markdown export."""
    result: dict = {
        "title": "",
        "date": "",
        "attendees": [],
        "action_items": [],
        "content": content,
    }

    lines = content.strip().split("\n")

    # Title: first H1
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            result["title"] = stripped[2:].strip()
            break

    if not result["title"] and lines:
        result["title"] = lines[0].strip()[:100]

    # Date: look for ISO dates or common patterns
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    for line in lines[:20]:
        m = date_pattern.search(line)
        if m:
            result["date"] = m.group(1)
            break

    if not result["date"]:
        result["date"] = datetime.now().strftime("%Y-%m-%d")

    # Attendees: lines after "Participantes", "Attendees", or "Asistentes" heading
    attendee_section = False
    attendee_patterns = re.compile(r"^#{1,3}\s*(participantes|attendees|asistentes|participants)", re.IGNORECASE)
    for line in lines:
        stripped = line.strip()
        if attendee_patterns.match(stripped):
            attendee_section = True
            continue
        if attendee_section:
            if stripped.startswith("#") or (not stripped and result["attendees"]):
                attendee_section = False
                continue
            person = re.sub(r"^[-*]\s*", "", stripped).strip()
            if person:
                result["attendees"].append(person)

    # Action items: lines with "- [ ]" or "- [x]" or after "Action Items" heading
    action_section = False
    action_heading = re.compile(r"^#{1,3}\s*(action\s*items|compromisos|tareas|next\s*steps|pr[oó]ximos\s*pasos)", re.IGNORECASE)
    for line in lines:
        stripped = line.strip()
        if action_heading.match(stripped):
            action_section = True
            continue

        # Checkbox-style items anywhere
        checkbox = re.match(r"^-\s*\[[ x]\]\s*(.+)", stripped, re.IGNORECASE)
        if checkbox:
            result["action_items"].append(checkbox.group(1).strip())
            continue

        if action_section:
            if stripped.startswith("#") or (not stripped and result["action_items"]):
                action_section = False
                continue
            item = re.sub(r"^[-*]\s*", "", stripped).strip()
            if item:
                result["action_items"].append(item)

    return result


def send_to_worker(parsed: dict) -> dict | None:
    """POST parsed transcript to Worker API."""
    url = f"{WORKER_URL}/run"
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "task": "granola.process_transcript",
        "input": parsed,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            logger.info("Worker response: %s", data)
            return data
        else:
            logger.error("Worker returned %d: %s", resp.status_code, resp.text[:500])
            return None
    except Exception as exc:
        logger.error("Failed to reach Worker: %s", exc)
        return None


def process_file(filepath: Path) -> bool:
    """Read, parse, send to worker, and move to processed."""
    logger.info("Processing: %s", filepath.name)
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error("Cannot read %s: %s", filepath, exc)
        return False

    if len(content.strip()) < 20:
        logger.warning("File too short, skipping: %s", filepath.name)
        return False

    parsed = parse_markdown_transcript(content)
    if not parsed["title"]:
        parsed["title"] = filepath.stem

    logger.info(
        "Parsed: title=%s, date=%s, attendees=%d, action_items=%d",
        parsed["title"], parsed["date"], len(parsed["attendees"]), len(parsed["action_items"]),
    )

    result = send_to_worker(parsed)
    if result is None:
        logger.error("Worker call failed for %s — file NOT moved", filepath.name)
        return False

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / filepath.name
    if dest.exists():
        stem = filepath.stem
        dest = PROCESSED_DIR / f"{stem}_{int(time.time())}{filepath.suffix}"
    shutil.move(str(filepath), str(dest))
    logger.info("Moved to processed: %s", dest.name)
    return True


def run_polling_loop():
    """Fallback: poll directory every POLL_INTERVAL seconds."""
    logger.info("Starting polling mode (interval=%ds) on %s", POLL_INTERVAL, EXPORT_DIR)
    seen: set[str] = set()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for f in EXPORT_DIR.glob("*.md"):
        seen.add(f.name)

    while True:
        try:
            for f in sorted(EXPORT_DIR.glob("*.md")):
                if f.name not in seen:
                    seen.add(f.name)
                    process_file(f)
        except Exception as exc:
            logger.error("Poll error: %s", exc)
        time.sleep(POLL_INTERVAL)


def run_watchdog():
    """Primary: use watchdog for real-time FS events."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        logger.warning("watchdog not installed, falling back to polling")
        run_polling_loop()
        return

    class GranolaHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() == ".md":
                time.sleep(1)
                process_file(path)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(GranolaHandler(), str(EXPORT_DIR), recursive=False)
    observer.start()
    logger.info("Watchdog monitoring: %s", EXPORT_DIR)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    if not WORKER_TOKEN:
        logger.error("WORKER_TOKEN not set — exiting")
        sys.exit(1)

    mode = os.environ.get("GRANOLA_WATCHER_MODE", "watchdog")
    if mode == "polling":
        run_polling_loop()
    else:
        run_watchdog()
