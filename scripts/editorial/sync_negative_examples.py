#!/usr/bin/env python3
"""CLI to materialize Shortlist `ejemplo_negativo=true` rows into a local
JSONL file consumable by rick-qa/generation (P2.5 — fila D, previously
AUSENTE).

Read-only against Notion: calls the existing `notion.read_database` Worker
task over HTTP, same as `scripts/editorial/magnific_generate_variants.py` —
no raw Notion API calls, no Notion writes at all (ADR-011 #1's write-monopoly
concern doesn't even apply here since this script never writes to Notion;
`ejemplo_negativo` itself is written by `worker/tasks/editorial_negative_capture.py`,
called by the dispatcher poller scan, not by this script).

This script closes the "captura pero no se consume" risk named in
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.5: it produces a
local, file-based store (JSONL, git-trackable, no new Notion DB) that
rick-qa/generation can load directly, plus a `find_similar_negatives` helper
that demonstrates the actual consult path (see --check-topic-key below).

Usage:
    export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx
    # Sync new negatives from Notion into the local file (idempotent — only
    # appends entries not already present, keyed by alternativa_id/page_id):
    python scripts/editorial/sync_negative_examples.py --dry-run
    python scripts/editorial/sync_negative_examples.py

    # Consult the local file (no Notion call at all) for a new candidate:
    python scripts/editorial/sync_negative_examples.py \\
        --check-topic-key "gobernanza en bim" --check-error-kind fuente_debil
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from client.worker_client import WorkerClient  # noqa: E402

DEFAULT_NEGATIVES_PATH = _REPO_ROOT / "evals" / "editorial" / "negative-examples-log.jsonl"


def normalize_topic_key(text: Optional[str]) -> str:
    """Normalize free text into a comparable topic key.

    Mirrors worker/tasks/editorial_dedupe.py's normalize_topic_key exactly
    (casefold + strip accents/punctuation + collapse whitespace) — kept as a
    separate local copy since scripts/ and worker/ are siloed in this repo
    (neither imports the other's package).
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped_accents.casefold()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(collapsed.split())


def _item_prop(item: Dict[str, Any], name: str) -> Any:
    props = item.get("properties") or {}
    return props.get(name)


def _item_text(item: Dict[str, Any], name: str) -> str:
    """Defensive against both the Worker's flattened shape (plain scalars)
    and raw Notion property dicts, same as dispatcher/notion_poller.py's
    _extract_item_text."""
    prop = _item_prop(item, name)
    if prop is None:
        return ""
    if isinstance(prop, str):
        return prop.strip()
    if not isinstance(prop, dict):
        return ""
    ptype = prop.get("type", "")
    if ptype == "rich_text":
        return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text", [])).strip()
    if ptype == "title":
        return "".join(rt.get("plain_text", "") for rt in prop.get("title", [])).strip()
    if ptype == "select":
        return ((prop.get("select") or {}).get("name") or "").strip()
    if ptype == "url":
        return (prop.get("url") or "").strip()
    return ""


def _item_checkbox(item: Dict[str, Any], name: str) -> bool:
    prop = _item_prop(item, name)
    if isinstance(prop, bool):
        return prop
    if isinstance(prop, str):
        return prop.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}
    if isinstance(prop, dict) and prop.get("type") == "checkbox":
        return bool(prop.get("checkbox"))
    return False


def _item_multi_select(item: Dict[str, Any], name: str) -> List[str]:
    prop = _item_prop(item, name)
    if isinstance(prop, list):
        return [str(v) for v in prop]
    if isinstance(prop, dict) and prop.get("type") == "multi_select":
        return [opt.get("name", "") for opt in prop.get("multi_select", [])]
    return []


def extract_negative_examples(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter Shortlist items down to captured negatives (`ejemplo_negativo`)
    and shape them into the JSONL record format this store persists."""
    records: List[Dict[str, Any]] = []
    for item in items:
        if not _item_checkbox(item, "ejemplo_negativo"):
            continue
        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        alternativa_id = _item_text(item, "alternativa_id") or page_id
        titulo = _item_text(item, "Título")
        topic_key_raw = _item_text(item, "topic_key") or titulo
        records.append(
            {
                "alternativa_id": alternativa_id,
                "page_id": page_id,
                "titulo": titulo,
                "topic_key": normalize_topic_key(topic_key_raw),
                "motivo_descarte": _item_text(item, "motivo_descarte"),
                "error_kind": _item_multi_select(item, "error_kind"),
                "fuente_pieza_url": _item_text(item, "fuente_pieza_url"),
            }
        )
    return records


def load_negative_examples(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _record_key(record: Dict[str, Any]) -> str:
    return record.get("alternativa_id") or record.get("page_id") or ""


def append_new_examples(path: Path, new_records: List[Dict[str, Any]]) -> int:
    """Append records not already present (deduped by alternativa_id/page_id).
    Returns the number of records actually appended."""
    existing_keys = {_record_key(r) for r in load_negative_examples(path)}
    to_append = [r for r in new_records if _record_key(r) and _record_key(r) not in existing_keys]
    if not to_append:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for record in to_append:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(to_append)


def find_similar_negatives(
    candidate_topic_key: str,
    candidate_error_kind: Optional[List[str]],
    examples: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return negatives that resemble a new candidate — the actual "does this
    repeat a known failure" consult path for rick-qa/generation.

    Two independent match signals, either sufficient on its own (same
    reasoning as worker/tasks/editorial_dedupe.py's find_backlog_match):
    - Normalized topic match against the negative's `topic_key`.
    - Any overlapping `error_kind` value.
    """
    normalized_candidate_topic = normalize_topic_key(candidate_topic_key)
    candidate_error_set = {e for e in (candidate_error_kind or []) if e}

    matches = []
    for example in examples:
        topic_match = bool(normalized_candidate_topic) and normalized_candidate_topic == example.get("topic_key")
        error_match = bool(candidate_error_set & set(example.get("error_kind") or []))
        if topic_match or error_match:
            matches.append(example)
    return matches


def _load_env_vars(env_path: Optional[str] = None) -> Dict[str, str]:
    env_vars: Dict[str, str] = {}
    path = env_path or os.path.expanduser("~/.config/openclaw/env")
    if not os.path.isfile(path):
        return env_vars
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def _resolve_worker_client() -> WorkerClient:
    url = os.environ.get("WORKER_URL", "").strip()
    token = os.environ.get("WORKER_TOKEN", "").strip()
    if not url or not token:
        env_vars = _load_env_vars()
        url = url or env_vars.get("WORKER_URL", "")
        token = token or env_vars.get("WORKER_TOKEN", "")
    if not url or not token:
        print("ERROR: WORKER_URL and WORKER_TOKEN required (env or ~/.config/openclaw/env)", file=sys.stderr)
        sys.exit(2)
    return WorkerClient(base_url=url, token=token, caller_id="script.sync_negative_examples")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Shortlist negative examples (ejemplo_negativo=true) to a local JSONL store (P2.5)"
    )
    parser.add_argument("--negatives-path", type=Path, default=DEFAULT_NEGATIVES_PATH)
    parser.add_argument(
        "--shortlist-ds-id",
        default=os.environ.get("NOTION_SHORTLIST_DS_ID", ""),
        help="Shortlist data source id/URL (default: $NOTION_SHORTLIST_DS_ID)",
    )
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be appended, without writing")
    parser.add_argument(
        "--check-topic-key",
        help="Consult the local store (no Notion call) for negatives resembling this topic",
    )
    parser.add_argument(
        "--check-error-kind",
        action="append",
        default=[],
        help="Additional error_kind value to match on with --check-topic-key (repeatable)",
    )
    args = parser.parse_args()

    if args.check_topic_key is not None or args.check_error_kind:
        examples = load_negative_examples(args.negatives_path)
        matches = find_similar_negatives(args.check_topic_key or "", args.check_error_kind, examples)
        if not matches:
            print(f"NO_SIMILAR_NEGATIVES topic_key={args.check_topic_key!r}")
            return 0
        print(f"SIMILAR_NEGATIVES_FOUND count={len(matches)}")
        for m in matches:
            print(json.dumps(m, ensure_ascii=False))
        return 0

    if not args.shortlist_ds_id:
        print("ERROR: --shortlist-ds-id or NOTION_SHORTLIST_DS_ID required", file=sys.stderr)
        return 2

    wc = _resolve_worker_client()
    try:
        response = wc.run(
            "notion.read_database",
            {"database_id_or_url": args.shortlist_ds_id, "max_items": args.max_items},
        )
    except Exception as e:
        print(f"ERROR: Worker call failed: {e}", file=sys.stderr)
        return 4

    result = response.get("result", response) if isinstance(response, dict) else response
    items = (result.get("items") if isinstance(result, dict) else None) or []
    negatives = extract_negative_examples(items)

    existing_keys = {_record_key(r) for r in load_negative_examples(args.negatives_path)}
    new_records = [r for r in negatives if _record_key(r) and _record_key(r) not in existing_keys]

    if args.dry_run:
        print(f"DRY_RUN scanned={len(items)} negatives_found={len(negatives)} new={len(new_records)}")
        for record in new_records:
            print(json.dumps(record, ensure_ascii=False))
        return 0

    appended = append_new_examples(args.negatives_path, negatives)
    print(f"SYNCED scanned={len(items)} negatives_found={len(negatives)} appended={appended} path={args.negatives_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
