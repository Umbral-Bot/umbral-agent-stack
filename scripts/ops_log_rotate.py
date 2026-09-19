#!/usr/bin/env python3
"""
ops_log_rotate.py — Retención configurable del archivo ops_log.jsonl.

Lee el archivo JSONL, descarta eventos más antiguos que N días, y reescribe
el archivo solo con los eventos recientes.  Diseñado para ejecutarse desde
cron (p.ej. semanal).

Variables de entorno:
  UMBRAL_OPS_LOG_DIR            Directorio del log (default: ~/.config/umbral)
  UMBRAL_OPS_LOG_RETENTION_DAYS Días de retención (default: 90)

Uso:
  python scripts/ops_log_rotate.py
  UMBRAL_OPS_LOG_RETENTION_DAYS=30 python scripts/ops_log_rotate.py
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_LOG_DIR = Path.home() / ".config" / "umbral"
DEFAULT_LOG_FILE = "ops_log.jsonl"
DEFAULT_RETENTION_DAYS = 90


def rotate(log_path: Path, retention_days: int) -> dict[str, int]:
    """Filter *log_path* keeping only events within *retention_days*.

    Returns a dict with ``total``, ``kept``, and ``removed`` counts.
    """
    if not log_path.exists():
        return {"total": 0, "kept": 0, "removed": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    kept: list[str] = []
    total = 0

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_raw = ev.get("ts")
            if not ts_raw:
                kept.append(json.dumps(ev, default=str, ensure_ascii=False))
                continue
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                kept.append(json.dumps(ev, default=str, ensure_ascii=False))
                continue
            if ts >= cutoff:
                kept.append(json.dumps(ev, default=str, ensure_ascii=False))

    tmp_path = log_path.with_suffix(".jsonl.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        for entry in kept:
            f.write(entry + "\n")
    tmp_path.replace(log_path)

    return {"total": total, "kept": len(kept), "removed": total - len(kept)}


def rotate_con_cerrojo(log_path: Path, retention_days: int) -> dict[str, int]:
    """`rotate` bajo el mismo cerrojo que usan los monitores para añadir.

    Sin él, todo lo que se añada entre la lectura del archivo y el renombrado
    del temporal se va con el inodo viejo: el registro canónico pierde eventos
    en silencio, justo una vez por semana y sin dejar rastro de lo perdido.
    Los monitores lo toman en `umbral_ops_log` (scripts/vps/lib/umbral_alerting.sh).
    """
    lock_path = log_path.parent / "ops_log.lock"
    with open(lock_path, "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return rotate(log_path, retention_days)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def main() -> None:
    log_dir = Path(os.environ.get("UMBRAL_OPS_LOG_DIR", str(DEFAULT_LOG_DIR)))
    retention_days = int(os.environ.get("UMBRAL_OPS_LOG_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)))
    log_path = log_dir / DEFAULT_LOG_FILE

    if not log_path.exists():
        print(f"No log file found at {log_path}. Nothing to do.")
        sys.exit(0)

    stats = rotate_con_cerrojo(log_path, retention_days)
    print(
        f"Rotation complete: {stats['total']} total, "
        f"{stats['kept']} kept, {stats['removed']} removed "
        f"(retention={retention_days} days)"
    )


if __name__ == "__main__":
    main()
