"""Stage 5 — Ranking determinístico de candidatos editoriales LinkedIn.

Ver `openclaw/workspace-agent-overrides/rick-linkedin-writer/SKILL.md` (Criterio 1)
y `INPUTS.md` / `OUTPUTS.md` para el contrato.

Sin LLM. Heurística pura. Validable bit-for-bit.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DEFAULT_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_CONFIG = Path("config/aec_keywords.yaml")
DEFAULT_REPORT_DIR = Path("reports")

EXIT_OK = 0
EXIT_DB_MISSING = 2
EXIT_CONFIG_BAD = 3
EXIT_WRITE_ERR = 4

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Config:
    weights: dict[str, float]
    recency_full_within_days: int
    recency_zero_after_days: int
    referente_canal_weights: dict[str, float]
    core_aec: tuple[str, ...]
    adyacente: tuple[str, ...]
    voz_david: tuple[str, ...]


def load_config(path: Path | str) -> Config:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    try:
        weights = {
            "w1_core_aec": float(raw["weights"]["w1_core_aec"]),
            "w2_adyacente": float(raw["weights"]["w2_adyacente"]),
            "w3_recency": float(raw["weights"]["w3_recency"]),
            "w4_referente": float(raw["weights"]["w4_referente"]),
        }
        recency = raw.get("recency", {})
        cfg = Config(
            weights=weights,
            recency_full_within_days=int(recency.get("full_bonus_within_days", 0)),
            recency_zero_after_days=int(recency.get("zero_bonus_after_days", 90)),
            referente_canal_weights={
                str(k): float(v) for k, v in raw["referente_canal_weights"].items()
            },
            core_aec=tuple(raw["buckets"]["core_aec"]),
            adyacente=tuple(raw["buckets"]["adyacente"]),
            voz_david=tuple(raw["buckets"].get("voz_david", [])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed config: {exc}") from exc
    return cfg


def _strip_accents(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    no_html = _TAG_RE.sub(" ", text)
    collapsed = _WS_RE.sub(" ", no_html)
    return _strip_accents(collapsed.lower()).strip()


def _compile_keyword_regex(keywords: tuple[str, ...]) -> re.Pattern[str]:
    if not keywords:
        return re.compile(r"(?!x)x")  # never matches
    parts = []
    for kw in keywords:
        norm = _strip_accents(kw.lower()).strip()
        # Escape and allow flexible whitespace between tokens.
        tokens = [re.escape(t) for t in norm.split()]
        body = r"\s+".join(tokens)
        parts.append(rf"\b{body}\b")
    return re.compile("|".join(parts))


def keyword_match(
    text: str, keywords: tuple[str, ...], *, _compiled: re.Pattern[str] | None = None
) -> tuple[list[str], int, float]:
    """Return (matched_keywords_unique_sorted, raw_count, normalized_in_0_1)."""
    if not text or not keywords:
        return ([], 0, 0.0)
    pattern = _compiled if _compiled is not None else _compile_keyword_regex(keywords)
    norm_text = _normalize_text(text)
    raw_matches = pattern.findall(norm_text)
    if not raw_matches:
        return ([], 0, 0.0)
    # Map matches back to canonical keyword strings.
    keyword_norm_map = {_strip_accents(kw.lower()).strip(): kw for kw in keywords}
    matched_canonical = sorted(
        {keyword_norm_map.get(_WS_RE.sub(" ", m).strip(), m) for m in raw_matches}
    )
    raw_count = len(raw_matches)
    normalized = min(1.0, raw_count / max(1, len(keywords)))
    return (matched_canonical, raw_count, normalized)


def recency_bonus(
    publicado_en: str | None,
    *,
    now: datetime,
    full_within_days: int,
    zero_after_days: int,
) -> tuple[int | None, float]:
    if not publicado_en:
        return (None, 0.0)
    try:
        s = publicado_en.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return (None, 0.0)
    delta = now - dt
    days_old = max(0, int(delta.total_seconds() // 86400))
    if zero_after_days <= full_within_days:
        return (days_old, 1.0 if days_old <= full_within_days else 0.0)
    if days_old <= full_within_days:
        return (days_old, 1.0)
    if days_old >= zero_after_days:
        return (days_old, 0.0)
    span = zero_after_days - full_within_days
    bonus = 1.0 - (days_old - full_within_days) / span
    return (days_old, max(0.0, min(1.0, bonus)))


def referente_priority(canal: str | None, weights: dict[str, float]) -> float:
    if not canal:
        return 0.0
    return float(weights.get(canal, 0.0))


def _round(x: float) -> float:
    return round(x, 6)


def score_item(
    *,
    titulo: str | None,
    contenido_html: str | None,
    publicado_en: str | None,
    canal: str | None,
    cfg: Config,
    now: datetime,
    core_re: re.Pattern[str],
    ady_re: re.Pattern[str],
) -> dict[str, Any]:
    text = " ".join([titulo or "", contenido_html or ""]).strip()
    core_matches, core_count, core_norm = keyword_match(text, cfg.core_aec, _compiled=core_re)
    ady_matches, ady_count, ady_norm = keyword_match(text, cfg.adyacente, _compiled=ady_re)
    days_old, rec_norm = recency_bonus(
        publicado_en,
        now=now,
        full_within_days=cfg.recency_full_within_days,
        zero_after_days=cfg.recency_zero_after_days,
    )
    ref_w = referente_priority(canal, cfg.referente_canal_weights)

    w = cfg.weights
    w_core = _round(w["w1_core_aec"] * core_norm)
    w_ady = _round(w["w2_adyacente"] * ady_norm)
    w_rec = _round(w["w3_recency"] * rec_norm)
    w_ref = _round(w["w4_referente"] * ref_w)
    total = _round(w_core + w_ady + w_rec + w_ref)

    return {
        "core_aec": {
            "matches": core_matches,
            "raw_count": core_count,
            "normalized": _round(core_norm),
            "weighted": w_core,
        },
        "adyacente": {
            "matches": ady_matches,
            "raw_count": ady_count,
            "normalized": _round(ady_norm),
            "weighted": w_ady,
        },
        "recency": {
            "days_old": days_old,
            "normalized": _round(rec_norm),
            "weighted": w_rec,
        },
        "referente": {
            "canal": canal,
            "weight_canal": _round(ref_w),
            "weighted": w_ref,
        },
        "total": total,
    }


def _ensure_columns(con: sqlite3.Connection) -> None:
    cur = con.execute("PRAGMA table_info(discovered_items)")
    existing = {row[1] for row in cur.fetchall()}
    for col, ddl in (
        ("ranking_score", "ALTER TABLE discovered_items ADD COLUMN ranking_score REAL"),
        ("ranking_reason", "ALTER TABLE discovered_items ADD COLUMN ranking_reason TEXT"),
        ("ranking_at", "ALTER TABLE discovered_items ADD COLUMN ranking_at TEXT"),
    ):
        if col not in existing:
            con.execute(ddl)
    con.commit()


def fetch_candidates(
    con: sqlite3.Connection, *, rerank: bool
) -> list[dict[str, Any]]:
    cur = con.execute("PRAGMA table_info(discovered_items)")
    existing = {row[1] for row in cur.fetchall()}
    where = "promovido_a_candidato_at IS NOT NULL"
    if not rerank and "ranking_score" in existing:
        where += " AND ranking_score IS NULL"
    sql = (
        "SELECT url_canonica, referente_id, referente_nombre, canal, titulo, "
        "publicado_en, contenido_html FROM discovered_items "
        f"WHERE {where} ORDER BY url_canonica"
    )
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def rank(
    candidates: list[dict[str, Any]], cfg: Config, *, now: datetime
) -> list[dict[str, Any]]:
    core_re = _compile_keyword_regex(cfg.core_aec)
    ady_re = _compile_keyword_regex(cfg.adyacente)
    ranked = []
    for c in candidates:
        breakdown = score_item(
            titulo=c.get("titulo"),
            contenido_html=c.get("contenido_html"),
            publicado_en=c.get("publicado_en"),
            canal=c.get("canal"),
            cfg=cfg,
            now=now,
            core_re=core_re,
            ady_re=ady_re,
        )
        ranked.append(
            {
                "url_canonica": c["url_canonica"],
                "referente_id": c.get("referente_id"),
                "referente_nombre": c.get("referente_nombre"),
                "canal": c.get("canal"),
                "titulo": c.get("titulo"),
                "publicado_en": c.get("publicado_en"),
                "ranking_score": breakdown["total"],
                "ranking_reason": breakdown,
            }
        )
    # Stable deterministic order: score desc, url asc.
    ranked.sort(key=lambda r: (-r["ranking_score"], r["url_canonica"]))
    return ranked


def build_report(
    ranked: list[dict[str, Any]],
    cfg: Config,
    *,
    mode: str,
    top_n: int,
    now: datetime,
) -> dict[str, Any]:
    scores = [r["ranking_score"] for r in ranked]
    scores_sorted = sorted(scores)
    if scores:
        median = (
            scores_sorted[len(scores) // 2]
            if len(scores) % 2 == 1
            else (scores_sorted[len(scores) // 2 - 1] + scores_sorted[len(scores) // 2]) / 2
        )
        smin, smax = min(scores), max(scores)
    else:
        median = smin = smax = 0.0
    items_top = []
    for idx, r in enumerate(ranked[:top_n], start=1):
        items_top.append({"rank": idx, **r})
    return {
        "stage": "stage5_rank_candidates",
        "version": "v0-deterministic",
        "timestamp_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "config": {
            "weights": cfg.weights,
            "buckets_loaded": {
                "core_aec_count": len(cfg.core_aec),
                "adyacente_count": len(cfg.adyacente),
                "voz_david_count": len(cfg.voz_david),
            },
        },
        "stats": {
            "candidates_total": len(ranked),
            "candidates_eligible": len(ranked),
            "candidates_skipped_no_text": sum(
                1 for r in ranked if not (r.get("titulo") or "")
            ),
            "score_min": _round(smin),
            "score_median": _round(median),
            "score_max": _round(smax),
        },
        "top_n": top_n,
        "items": items_top,
    }


def commit_to_db(con: sqlite3.Connection, ranked: list[dict[str, Any]], now: datetime) -> int:
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    written = 0
    for r in ranked:
        con.execute(
            "UPDATE discovered_items SET ranking_score = ?, ranking_reason = ?, "
            "ranking_at = ? WHERE url_canonica = ?",
            (
                r["ranking_score"],
                json.dumps(r["ranking_reason"], ensure_ascii=False, sort_keys=True),
                ts,
                r["url_canonica"],
            ),
        )
        written += 1
    con.commit()
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override now() for tests (ISO8601 UTC). Defaults to wall clock.",
    )
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"[stage5] SQLite not found: {args.db}", file=sys.stderr)
        return EXIT_DB_MISSING

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[stage5] {exc}", file=sys.stderr)
        return EXIT_CONFIG_BAD

    if args.now:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")).astimezone(timezone.utc)
    else:
        now = datetime.now(timezone.utc)

    con = sqlite3.connect(args.db)
    try:
        if args.commit:
            _ensure_columns(con)
        candidates = fetch_candidates(con, rerank=args.rerank)
        ranked = rank(candidates, cfg, now=now)
        mode = "commit" if args.commit else "dry-run"
        report = build_report(ranked, cfg, mode=mode, top_n=args.top_n, now=now)

        args.report_dir.mkdir(parents=True, exist_ok=True)
        ts_for_path = now.strftime("%Y%m%dT%H%M%SZ")
        out_path = args.report_dir / f"stage5-ranking-{ts_for_path}-{mode}.json"
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if args.commit:
            try:
                written = commit_to_db(con, ranked, now)
            except sqlite3.Error as exc:
                print(f"[stage5] write error: {exc}", file=sys.stderr)
                return EXIT_WRITE_ERR
            print(
                f"[stage5] mode=commit ranked={len(ranked)} written={written} "
                f"top_n={args.top_n} report={out_path}"
            )
        else:
            print(
                f"[stage5] mode=dry-run ranked={len(ranked)} top_n={args.top_n} "
                f"report={out_path}"
            )
    finally:
        con.close()

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
