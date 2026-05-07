"""Stage 6: LLM combinator for AEC editorial proposals.

Reads top-N items from Stage 5 ranking (or, if ranking is not yet populated,
falls back to most-recently-promoted items) and asks an LLM to propose
3-5 publication ideas that combine ≥2 disciplines among
{BIM, automation, AI, low-code}.

Outputs a JSON list and persists each proposal as ``status='draft'`` into
``state.sqlite`` table ``proposals`` (created if missing).

LLM transport: OpenAI-compatible Chat Completions against the local OpenClaw
gateway at ``http://127.0.0.1:18789/v1/chat/completions``. Default model alias
is ``openclaw/main`` (routes to ``azure-openai-responses/gpt-5.4``).
A trivial mock-only mode is auto-engaged when ``--no-llm`` is set or when the
gateway is unreachable in dry-run mode.

Cache: SQLite at ``~/.cache/rick-discovery/llm_cache.sqlite`` keyed by
``sha256(model + '\\n' + prompt)`` with TTL 7 days. ``--force-refresh-cache``
bypasses hits.

Limits:
- Read-only against discovered_items.
- Hard cost guard: aborts before invoking LLM if estimated input tokens > 30k.
- Logs structured events to ``~/.config/umbral/ops_log.jsonl`` with
  prefix ``stage6.*``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_CACHE_DB = Path.home() / ".cache" / "rick-discovery" / "llm_cache.sqlite"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"
DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
DEFAULT_MODEL = "openclaw/main"
CACHE_TTL_S = 7 * 24 * 3600
COST_GUARD_MAX_INPUT_TOKENS = 30_000  # ~$0.10 max per call at gpt-5.4 rates
APPROX_CHARS_PER_TOKEN = 4

PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titular TEXT NOT NULL,
    hook TEXT,
    angulo TEXT,
    fuentes_urls TEXT NOT NULL,        -- JSON array
    disciplinas TEXT NOT NULL,         -- JSON array
    score REAL,
    ts INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    notion_page_id TEXT,
    last_error TEXT
)
"""


# ---------- Logging ----------

def log_event(event: str, **fields: Any) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    try:
        DEFAULT_OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------- State ----------

def ensure_proposals_table(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(PROPOSALS_DDL)
        conn.commit()
    finally:
        conn.close()


def read_stage5_output(db_path: Path, top_n: int) -> list[dict[str, Any]]:
    """Return top-N items by ranking_score; fallback to most-recently-promoted."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = list(conn.execute(
            "SELECT url_canonica, titulo, canal, referente_nombre, ranking_score, "
            "ranking_reason, contenido_html "
            "FROM discovered_items "
            "WHERE ranking_score IS NOT NULL "
            "ORDER BY ranking_score DESC LIMIT ?",
            (top_n,),
        ))
        if not rows:
            rows = list(conn.execute(
                "SELECT url_canonica, titulo, canal, referente_nombre, ranking_score, "
                "ranking_reason, contenido_html "
                "FROM discovered_items "
                "WHERE promovido_a_candidato_at IS NOT NULL "
                "ORDER BY promovido_a_candidato_at DESC LIMIT ?",
                (top_n,),
            ))
        return [dict(r) for r in rows]
    finally:
        conn.close()


def write_proposals_to_state(db_path: Path, proposals: list[dict[str, Any]]) -> list[int]:
    ensure_proposals_table(db_path)
    conn = sqlite3.connect(db_path)
    ids: list[int] = []
    try:
        ts = int(time.time())
        for p in proposals:
            cur = conn.execute(
                "INSERT INTO proposals "
                "(titular, hook, angulo, fuentes_urls, disciplinas, score, ts, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'draft')",
                (
                    p["titular"],
                    p.get("hook"),
                    p.get("angulo"),
                    json.dumps(p.get("fuentes_urls", []), ensure_ascii=False),
                    json.dumps(p.get("disciplinas", []), ensure_ascii=False),
                    float(p.get("score_relevancia") or p.get("score") or 0.0),
                    ts,
                ),
            )
            ids.append(int(cur.lastrowid))
        conn.commit()
    finally:
        conn.close()
    return ids


# ---------- Prompt ----------

SYSTEM_PROMPT = (
    "Eres un editor AEC senior. Recibes una lista de noticias recientes y "
    "propones 3-5 publicaciones combinando >=2 disciplinas entre "
    "{BIM, automatizacion, IA, low-code}. Cada propuesta debe ser ejecutable "
    "como post de LinkedIn o blog corto."
)


def build_prompt(items: list[dict[str, Any]]) -> str:
    """Build a deterministic user-message body that lists the items + JSON contract."""
    lines = ["Lista de noticias (input):", ""]
    for i, it in enumerate(items, 1):
        lines.append(
            f"[{i}] titulo={it.get('titulo') or ''!r} canal={it.get('canal') or ''} "
            f"referente={it.get('referente_nombre') or ''} url={it.get('url_canonica')}"
        )
        razon = it.get("ranking_reason")
        if razon:
            lines.append(f"    razon_ranking: {razon}")
    lines.extend([
        "",
        "Devuelve JSON puro (sin texto fuera del bloque) con la forma:",
        "{\"proposals\": [",
        "  {",
        "    \"titular\": str,",
        "    \"hook\": str (1-2 frases),",
        "    \"angulo\": str (por que importa AHORA),",
        "    \"fuentes_urls\": [str, ...] (subset de las urls de input, >=1),",
        "    \"disciplinas\": [str, ...] (>=2 de BIM/automatizacion/IA/low-code),",
        "    \"score_relevancia\": float (0-1)",
        "  }, ...",
        "]}",
        "Regla dura: 3 a 5 propuestas, cada una con disciplinas distintas combinadas.",
    ])
    return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


# ---------- Cache ----------

CACHE_DDL = (
    "CREATE TABLE IF NOT EXISTS llm_cache "
    "(key TEXT PRIMARY KEY, response TEXT NOT NULL, ts INTEGER NOT NULL)"
)


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode("utf-8")).hexdigest()


def cache_get(cache_db: Path, model: str, prompt: str, *, ttl_s: int = CACHE_TTL_S) -> str | None:
    cache_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_db)
    try:
        conn.execute(CACHE_DDL)
        key = _cache_key(model, prompt)
        row = conn.execute(
            "SELECT response, ts FROM llm_cache WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        if int(time.time()) - int(row[1]) > ttl_s:
            return None
        return row[0]
    finally:
        conn.close()


def cache_put(cache_db: Path, model: str, prompt: str, response: str) -> None:
    cache_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_db)
    try:
        conn.execute(CACHE_DDL)
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key, response, ts) VALUES (?, ?, ?)",
            (_cache_key(model, prompt), response, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- LLM call ----------

def llm_call(
    *,
    prompt: str,
    model: str,
    gateway_url: str,
    auth_token: str,
    timeout_s: float = 120.0,
) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    r = httpx.post(
        gateway_url,
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=timeout_s,
    )
    if r.status_code != 200:
        raise RuntimeError(f"LLM call failed: HTTP {r.status_code} body={r.text[:300]}")
    data = r.json()
    return data["choices"][0]["message"]["content"]


# ---------- Parse + validate ----------

def parse_proposals(llm_response: str) -> list[dict[str, Any]]:
    """Extract proposals from LLM response. Tolerates ```json fences."""
    text = llm_response.strip()
    if text.startswith("```"):
        # strip first fence line and trailing fence
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        log_event("stage6.parse.failed", reason="json_decode")
        return []
    raw = obj.get("proposals") if isinstance(obj, dict) else obj
    if not isinstance(raw, list):
        log_event("stage6.parse.failed", reason="proposals_not_list")
        return []
    out: list[dict[str, Any]] = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        titular = (p.get("titular") or "").strip()
        fuentes = p.get("fuentes_urls") or []
        if not titular or not isinstance(fuentes, list) or not fuentes:
            log_event("stage6.parse.skipped", titular=titular[:80], n_fuentes=len(fuentes) if isinstance(fuentes, list) else None)
            continue
        out.append({
            "titular": titular,
            "hook": (p.get("hook") or "").strip(),
            "angulo": (p.get("angulo") or "").strip(),
            "fuentes_urls": [str(u) for u in fuentes if u],
            "disciplinas": [str(d) for d in (p.get("disciplinas") or []) if d],
            "score_relevancia": p.get("score_relevancia"),
        })
    return out


# ---------- CLI ----------

def _gateway_token() -> str | None:
    try:
        cfg = json.loads((Path.home() / ".openclaw" / "openclaw.json").read_text())
        return cfg.get("gateway", {}).get("auth", {}).get("token")
    except (OSError, json.JSONDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 6 LLM combinator for AEC proposals.")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--output-json", default=None, help="Optional path to dump full proposals JSON.")
    p.add_argument("--dry-run", action="store_true",
                   help="Do not persist proposals to state.sqlite.")
    p.add_argument("--force-refresh-cache", action="store_true")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip LLM call; emit empty proposals (for plumbing tests).")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--cache-db", default=str(DEFAULT_CACHE_DB))
    args = p.parse_args(argv)

    state_db = Path(args.state_db)
    cache_db = Path(args.cache_db)

    items = read_stage5_output(state_db, args.top_n)
    log_event("stage6.input.loaded", n_items=len(items), top_n=args.top_n)
    if not items:
        print("no items to combinate (empty state)")
        return 0

    prompt = build_prompt(items)
    est_tokens = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(prompt)
    if est_tokens > COST_GUARD_MAX_INPUT_TOKENS:
        log_event("stage6.cost.aborted", est_tokens=est_tokens)
        print(f"ABORT: estimated {est_tokens} input tokens > guard {COST_GUARD_MAX_INPUT_TOKENS}",
              file=sys.stderr)
        return 3

    if args.no_llm:
        proposals: list[dict[str, Any]] = []
        log_event("stage6.llm.skipped", reason="no_llm_flag")
    else:
        cached = None if args.force_refresh_cache else cache_get(cache_db, args.model, prompt)
        if cached is not None:
            log_event("stage6.cache.hit", model=args.model)
            response_text = cached
        else:
            token = _gateway_token() or os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
            if not token:
                print("ERROR: no gateway token available", file=sys.stderr)
                return 2
            try:
                response_text = llm_call(
                    prompt=prompt,
                    model=args.model,
                    gateway_url=args.gateway_url,
                    auth_token=token,
                )
            except Exception as e:
                log_event("stage6.llm.failed", error=str(e)[:200])
                print(f"LLM call failed: {e}", file=sys.stderr)
                return 4
            cache_put(cache_db, args.model, prompt, response_text)
            log_event("stage6.cache.miss", model=args.model)
        proposals = parse_proposals(response_text)

    log_event("stage6.parse.ok", n_proposals=len(proposals))
    print(f"proposals_generated={len(proposals)}")

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps({"proposals": proposals, "n_input_items": len(items)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"output: {args.output_json}")

    if proposals and not args.dry_run:
        ids = write_proposals_to_state(state_db, proposals)
        log_event("stage6.persist.ok", ids=ids)
        print(f"persisted ids={ids}")
    elif args.dry_run:
        print("dry-run: skipping persist to state")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
