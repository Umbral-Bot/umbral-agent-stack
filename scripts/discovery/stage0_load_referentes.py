"""Stage 0 — Load `👤 Referentes` from Notion → SQLite snapshot.

Read-only against Notion. Writes only to local SQLite at
``~/.cache/rick-discovery/state.sqlite`` (configurable via ``--sqlite``).

Filters:
- Excludes rows with `Confianza canales = DUPLICADO` or `Flags canales` ∋ DUP.
- Skips rows with `Flags canales` ∋ REQUIERE_VERIFICACION_MANUAL (pausado).

Channel fan-out (one row per channel per referente):
- rss      ← `RSS feed`
- web      ← `Web / Newsletter`
- youtube  ← `YouTube channel` (recorded; Stage 1 does not fetch)
- linkedin ← `LinkedIn activity feed` and/or `LinkedIn`
            (recorded; Stage 1 SKIPS — see policy in stage1).

CLI:
    python -m scripts.discovery.stage0_load_referentes \\
        --sqlite ~/.cache/rick-discovery/state.sqlite \\
        [--data-source-id <ds>] [--dry-run] [--limit N] \\
        [--referente-id <id>] [--verbose]

Env required:
    NOTION_API_KEY
    UMBRAL_DISCOVERY_REFERENTES_DS_ID  (or pass --data-source-id)
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scripts.discovery.lib.notion_read import (
    ReferenteRow,
    fan_out_channels,
    normalize_referente,
    query_data_source,
)

DEFAULT_SQLITE = Path("~/.cache/rick-discovery/state.sqlite").expanduser()
MIGRATION_PATH = Path(__file__).parent / "migrations" / "0001_referentes_signals.sql"

log = logging.getLogger("stage0_load_referentes")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def apply_migrations(conn: sqlite3.Connection, migration_path: Path = MIGRATION_PATH) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def open_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def filter_referentes(
    refs: Iterable[ReferenteRow],
    *,
    referente_id: str | None = None,
    limit: int | None = None,
) -> tuple[list[ReferenteRow], int, int, int]:
    """Return (kept, excluded, pausados, total)."""
    kept: list[ReferenteRow] = []
    excl = 0
    paus = 0
    total = 0
    for r in refs:
        total += 1
        if referente_id and r.referente_id != referente_id:
            continue
        if r.is_excluded:
            excl += 1
            log.info("skip excluded referente=%s nombre=%s", r.referente_id, r.nombre)
            continue
        if r.is_pausado:
            paus += 1
            log.info("skip pausado referente=%s nombre=%s", r.referente_id, r.nombre)
            continue
        kept.append(r)
        if limit is not None and len(kept) >= limit:
            break
    return kept, excl, paus, total


def upsert_snapshot(
    conn: sqlite3.Connection,
    *,
    referentes: Iterable[ReferenteRow],
    snapshot_at: str,
) -> dict[str, Any]:
    inserted = 0
    updated = 0
    by_canal: dict[str, int] = {}
    cur = conn.cursor()
    for ref in referentes:
        for canal_tipo, canal_url in fan_out_channels(ref):
            by_canal[canal_tipo] = by_canal.get(canal_tipo, 0) + 1
            cur.execute(
                """
                INSERT INTO referentes_snapshot
                    (referente_id, nombre, canal_tipo, canal_url, snapshot_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(referente_id, canal_tipo, canal_url)
                DO UPDATE SET snapshot_at = excluded.snapshot_at,
                              nombre = excluded.nombre
                """,
                (ref.referente_id, ref.nombre, canal_tipo, canal_url, snapshot_at),
            )
            if cur.rowcount == 1:
                # SQLite returns 1 for both insert and update via UPSERT — track via changes:
                inserted += 1
            else:
                updated += 1
    conn.commit()
    return {"inserted_or_updated": inserted, "updated": updated, "by_canal": by_canal}


def run(
    *,
    sqlite_path: Path,
    data_source_id: str,
    api_key: str,
    dry_run: bool = False,
    limit: int | None = None,
    referente_id: str | None = None,
) -> dict[str, Any]:
    pages = query_data_source(data_source_id=data_source_id, api_key=api_key)
    refs = [normalize_referente(p) for p in pages]
    kept, excl, paus, total = filter_referentes(refs, referente_id=referente_id, limit=limit)
    fan_out_total = sum(len(fan_out_channels(r)) for r in kept)
    by_canal: dict[str, int] = {}
    for r in kept:
        for canal_tipo, _ in fan_out_channels(r):
            by_canal[canal_tipo] = by_canal.get(canal_tipo, 0) + 1
    summary = {
        "total_in_notion": total,
        "activos_seleccionados": len(kept),
        "excluidos": excl,
        "pausados": paus,
        "channels_fan_out": fan_out_total,
        "by_canal": by_canal,
        "dry_run": dry_run,
    }
    if dry_run:
        return summary
    snapshot_at = _now_iso()
    conn = open_sqlite(sqlite_path)
    try:
        write = upsert_snapshot(conn, referentes=kept, snapshot_at=snapshot_at)
        summary["snapshot_at"] = snapshot_at
        summary["written"] = write
    finally:
        conn.close()
    return summary


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 0: load Referentes → SQLite")
    p.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    p.add_argument("--data-source-id", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--referente-id", default=None)
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        log.error("NOTION_API_KEY missing")
        return 2
    ds = args.data_source_id or os.environ.get("UMBRAL_DISCOVERY_REFERENTES_DS_ID")
    if not ds:
        log.error("data-source-id missing (--data-source-id or UMBRAL_DISCOVERY_REFERENTES_DS_ID)")
        return 2
    try:
        summary = run(
            sqlite_path=args.sqlite,
            data_source_id=ds,
            api_key=api_key,
            dry_run=args.dry_run,
            limit=args.limit,
            referente_id=args.referente_id,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("stage0 failed: %s", exc)
        return 1
    import json
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
