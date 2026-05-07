"""Stage 3 — Promoción a candidatos (local, dry-run first).

Reads pending items from ~/.cache/rick-discovery/state.sqlite (populated by
stage2_ingest.py), applies eligibility rules v1, and emits a JSON report.

Default mode: dry-run (no SQLite writes). Use --commit to actually mark
promovido_a_candidato_at on the eligible (post-limit) batch.

Eligibility rules v1 (all must hold):
  1. publicado_en parseable to UTC datetime (RFC822 or ISO 8601).
  2. age <= max-age-days from now UTC.
  3. titulo non-empty after strip.
  4. canal in {youtube, rss}.

Discarded items are classified with one of:
  fecha_invalida, fuera_ventana_90d, titulo_vacio, canal_no_elegible,
  ya_promovido (defensive — the SELECT base already filters).

Stage 3 is 100% local: no Notion, no network. Stage 4 will push to Notion.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable

ELIGIBLE_CHANNELS = frozenset({"youtube", "rss"})
DISCARD_REASONS = (
    "fecha_invalida",
    "fuera_ventana_90d",
    "titulo_vacio",
    "canal_no_elegible",
    "ya_promovido",
)
SAMPLE_LIMIT = 10
REQUIRED_COLUMNS = {
    "url_canonica",
    "referente_id",
    "referente_nombre",
    "canal",
    "titulo",
    "publicado_en",
    "promovido_a_candidato_at",
}


class Stage3Error(RuntimeError):
    """Fatal Stage 3 condition (drift, missing schema, etc)."""


@dataclass
class Item:
    url_canonica: str
    referente_id: str
    referente_nombre: str
    canal: str
    titulo: str | None
    publicado_en: str | None
    promovido_a_candidato_at: str | None


@dataclass
class Classified:
    item: Item
    eligible: bool
    reason: str | None = None
    pub_dt: datetime | None = None


@dataclass
class RunSummary:
    pending_total: int = 0
    eligible: int = 0
    promoted_this_run: int = 0
    discarded_total: int = 0
    discarded_by_reason: dict[str, int] = field(
        default_factory=lambda: {r: 0 for r in DISCARD_REASONS}
    )


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


def parse_pub_date(raw: str | None) -> datetime | None:
    """Parse RFC822 or ISO 8601 timestamp into a tz-aware UTC datetime.

    Naive inputs are assumed UTC. Returns None for invalid/empty input.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    # Try RFC822 first (feedparser style: "Wed, 29 Apr 2026 22:54:14 GMT").
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            return _to_utc(dt)
    except (TypeError, ValueError):
        pass
    # Try ISO 8601 (with optional trailing Z).
    iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(iso)
        return _to_utc(dt)
    except ValueError:
        return None


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def classify(item: Item, *, now: datetime, max_age_days: int) -> Classified:
    """Apply eligibility rules. Returns Classified with reason if discarded.

    Order of checks: ya_promovido > canal_no_elegible > titulo_vacio
    > fecha_invalida > fuera_ventana_90d. First failing rule wins; the rest
    are not evaluated.
    """
    if item.promovido_a_candidato_at:
        return Classified(item, eligible=False, reason="ya_promovido")
    if item.canal not in ELIGIBLE_CHANNELS:
        return Classified(item, eligible=False, reason="canal_no_elegible")
    if not (item.titulo or "").strip():
        return Classified(item, eligible=False, reason="titulo_vacio")
    pub_dt = parse_pub_date(item.publicado_en)
    if pub_dt is None:
        return Classified(item, eligible=False, reason="fecha_invalida")
    age_days = (now - pub_dt).total_seconds() / 86400.0
    if age_days > max_age_days:
        return Classified(item, eligible=False, reason="fuera_ventana_90d", pub_dt=pub_dt)
    return Classified(item, eligible=True, pub_dt=pub_dt)


# ---------------------------------------------------------------------------
# SQLite access
# ---------------------------------------------------------------------------


def open_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise Stage3Error(f"SQLite no existe: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def assert_schema(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(discovered_items)")}
    missing = REQUIRED_COLUMNS - cols
    if missing:
        raise Stage3Error(f"schema drift: faltan columnas {sorted(missing)}")


def select_pending(conn: sqlite3.Connection) -> list[Item]:
    rows = conn.execute(
        """
        SELECT url_canonica, referente_id, referente_nombre, canal,
               titulo, publicado_en, promovido_a_candidato_at
        FROM discovered_items
        WHERE promovido_a_candidato_at IS NULL
        """
    ).fetchall()
    return [
        Item(
            url_canonica=r["url_canonica"],
            referente_id=r["referente_id"],
            referente_nombre=r["referente_nombre"],
            canal=r["canal"],
            titulo=r["titulo"],
            publicado_en=r["publicado_en"],
            promovido_a_candidato_at=r["promovido_a_candidato_at"],
        )
        for r in rows
    ]


def count_promoted(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM discovered_items WHERE promovido_a_candidato_at IS NOT NULL"
    ).fetchone()[0]


def mark_promoted(
    conn: sqlite3.Connection, urls: Iterable[str], now_iso: str
) -> int:
    """UPDATE only NULL rows for the given urls. Returns rows mutated."""
    mutated = 0
    cur = conn.cursor()
    for url in urls:
        cur.execute(
            """
            UPDATE discovered_items
               SET promovido_a_candidato_at = ?
             WHERE url_canonica = ?
               AND promovido_a_candidato_at IS NULL
            """,
            (now_iso, url),
        )
        mutated += cur.rowcount
    conn.commit()
    return mutated


# ---------------------------------------------------------------------------
# Selection + reporting
# ---------------------------------------------------------------------------


def order_eligible(eligible: list[Classified]) -> list[Classified]:
    """Deterministic order: publicado_en DESC, url_canonica ASC."""
    return sorted(
        eligible,
        key=lambda c: (
            -(c.pub_dt.timestamp() if c.pub_dt else 0.0),
            c.item.url_canonica,
        ),
    )


def build_report(
    *,
    classifications: list[Classified],
    selected: list[Classified],
    mode: str,
    promoted_count: int,
    max_age_days: int,
    limit: int | None,
    started_at: str,
    finished_at: str,
    pending_total: int,
    now: datetime,
) -> dict:
    summary = RunSummary(pending_total=pending_total)
    for c in classifications:
        if c.eligible:
            summary.eligible += 1
        else:
            summary.discarded_total += 1
            if c.reason in summary.discarded_by_reason:
                summary.discarded_by_reason[c.reason] += 1
    summary.promoted_this_run = promoted_count

    candidates_sample = [
        {
            "url_canonica": c.item.url_canonica,
            "referente_nombre": c.item.referente_nombre,
            "canal": c.item.canal,
            "titulo": (c.item.titulo or "").strip(),
            "publicado_en_iso": c.pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            if c.pub_dt
            else None,
            "age_days": int((now - c.pub_dt).total_seconds() // 86400)
            if c.pub_dt
            else None,
        }
        for c in selected[:SAMPLE_LIMIT]
    ]

    discarded = [c for c in classifications if not c.eligible]
    discarded_sample = [
        {
            "url_canonica": c.item.url_canonica,
            "reason": c.reason,
            "age_days": int((now - c.pub_dt).total_seconds() // 86400)
            if c.pub_dt
            else None,
        }
        for c in discarded[:SAMPLE_LIMIT]
    ]

    consistent = (summary.eligible + summary.discarded_total) == summary.pending_total
    overall_pass = consistent and (
        promoted_count == 0 if mode == "dry-run" else promoted_count == len(selected)
    )

    return {
        "overall_pass": overall_pass,
        "run_started_at": started_at,
        "run_finished_at": finished_at,
        "mode": mode,
        "max_age_days": max_age_days,
        "limit": limit,
        "summary": {
            "pending_total": summary.pending_total,
            "eligible": summary.eligible,
            "promoted_this_run": summary.promoted_this_run,
            "discarded_total": summary.discarded_total,
            "discarded_by_reason": summary.discarded_by_reason,
        },
        "candidates_sample": candidates_sample,
        "discarded_sample": discarded_sample,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--max-age-days", type=int, default=90)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--commit", action="store_true",
                   help="Actually UPDATE promovido_a_candidato_at. Default is dry-run.")
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args(argv)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def run(args: argparse.Namespace) -> int:
    started = _now_utc()
    conn = open_sqlite(args.sqlite)
    try:
        assert_schema(conn)
        items = select_pending(conn)
        pending_total = len(items)
        classifications = [
            classify(it, now=started, max_age_days=args.max_age_days) for it in items
        ]
        eligible = [c for c in classifications if c.eligible]
        ordered = order_eligible(eligible)
        selected = ordered if args.limit is None else ordered[: args.limit]

        mode = "commit" if args.commit else "dry-run"
        promoted_count = 0
        if args.commit and selected:
            now_iso = _iso(_now_utc())
            promoted_count = mark_promoted(
                conn, (c.item.url_canonica for c in selected), now_iso
            )

        finished = _now_utc()
        report = build_report(
            classifications=classifications,
            selected=selected,
            mode=mode,
            promoted_count=promoted_count,
            max_age_days=args.max_age_days,
            limit=args.limit,
            started_at=_iso(started),
            finished_at=_iso(finished),
            pending_total=pending_total,
            now=started,
        )
    finally:
        conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.output}")
    print(f"mode={mode} pending={pending_total} eligible={report['summary']['eligible']} "
          f"promoted={promoted_count} overall_pass={report['overall_pass']}")
    return 0 if report["overall_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return run(args)
    except Stage3Error as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
