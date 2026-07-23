#!/usr/bin/env python3
"""Apply canonical editorial copy to a Notion Publicaciones page (gates untouched)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from scripts.editorial.editorial_model_guard import (  # noqa: E402
    EditorialModelError,
    editorial_model_status_message,
    verify_openclaw_agent_model,
)
from scripts.editorial.validate_editorial_copy import (  # noqa: E402
    validate_publication_payload,
)

NOTION_VERSION = "2022-06-28"
DEFAULT_COPY_DIR = _REPO_ROOT / "evals" / "editorial"

# Notion's documented per-property rich_text limits: each object's
# text.content maxes at 2000 chars, and the array itself maxes at 100 items.
# P2.3 (docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.F): a
# ~350-500+ word Copy Blog fits comfortably under this, but the guard exists
# so a future, much longer body fails loudly instead of silently overflowing
# the property — see build_copy_blog_body_blocks / build_worker_copy_payload
# for the two documented escape hatches.
_NOTION_RICH_TEXT_MAX_ITEMS = 100
_BODY_MARKER_PREFIX = "Copy Blog (V2 canonical body)"


class RichTextOverflowError(RuntimeError):
    """Content needs more rich_text chunks than Notion's property array allows."""


def _chunks(text: str, size: int = 1900, *, guard_property_limit: bool = False) -> list[dict]:
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    chunks = [{"type": "text", "text": {"content": text[i : i + size]}} for i in range(0, len(text), size)]
    if guard_property_limit and len(chunks) > _NOTION_RICH_TEXT_MAX_ITEMS:
        raise RichTextOverflowError(
            f"{len(text)} chars split into {len(chunks)} rich_text chunks, over "
            f"Notion's {_NOTION_RICH_TEXT_MAX_ITEMS}-item property limit; use "
            "--write-body (page body blocks) and/or --emit-worker-payload instead "
            "of the Copy Blog property for this content"
        )
    return chunks


def _paragraph_blocks(text: str) -> list[dict]:
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return [
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _chunks(p, size=1900)}}
        for p in paragraphs
    ]


def build_copy_blog_body_blocks(text: str, marker: str) -> list[dict]:
    """V2 escape hatch #1 — write the long-form body as page blocks.

    Bypasses the ``Copy Blog`` *property* rich_text limit entirely, since page
    body blocks have no comparable per-page cap (see
    docs/ops/notion-blog-linkedin-v3-content-model.md §Limitation and
    ADR-010 §Negativas). Prefixing with ``marker`` (a callout block) makes a
    re-run idempotent: callers should skip appending when the marker is
    already present among the page's existing children.
    """
    blocks: list[dict] = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": marker}}],
                "icon": {"type": "emoji", "emoji": "\U0001F5D2"},
            },
        },
        {"object": "block", "type": "divider", "divider": {}},
    ]
    blocks.extend(_paragraph_blocks(text))
    return blocks


def build_worker_copy_payload(payload: dict, page_id: str) -> dict:
    """V2 escape hatch #2 — an explicit ``payload`` for the Worker task.

    ``worker/tasks/editorial_publish.py`` already accepts an explicit
    ``payload`` dict as an alternative to reading Notion properties
    (``_build_payload_from_notion``); feeding it ``body_markdown`` directly
    means the publish step never re-reads ``Copy Blog`` back through the
    rich_text property, so the property's size limit cannot truncate it.

    This is a **partial** payload (copy step only): slug/title/tags/excerpt
    belong to the blog-metadata step, not this copy script, and must be
    merged in by the caller before invoking
    ``handle_web_publish_editorial_post``. Gates are hardcoded false here as
    defense in depth — only David flips them, in Notion.
    """
    return {
        "notion_page_id": page_id,
        "trace_id": payload.get("trace_id"),
        "body_markdown": payload["copy_blog"].strip(),
        "slug": str(payload.get("slug") or ""),
        "title": str(payload.get("title") or ""),
        "excerpt": str(payload.get("excerpt") or ""),
        "autorizar_publicacion": False,
        "aprobado_contenido": False,
        "_note": (
            "Partial payload (copy step only). Merge slug/title/tags/excerpt "
            "from the blog metadata step before calling "
            "worker.tasks.editorial_publish.handle_web_publish_editorial_post "
            "with this dict as 'payload'. Gates are intentionally false; only "
            "David flips them in Notion."
        ),
    }


def _notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get_page(api_key: str, page_id: str) -> dict:
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_notion_headers(api_key),
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _patch_page(api_key: str, page_id: str, properties: dict) -> dict:
    body = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=body,
        headers=_notion_headers(api_key),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _list_block_children(api_key: str, block_id: str) -> list[dict]:
    results: list[dict] = []
    cursor: str | None = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        req = urllib.request.Request(url, headers=_notion_headers(api_key))
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def _append_block_children(api_key: str, block_id: str, blocks: list[dict]) -> None:
    for i in range(0, len(blocks), 100):
        chunk = blocks[i : i + 100]
        body = json.dumps({"children": chunk}).encode()
        req = urllib.request.Request(
            f"https://api.notion.com/v1/blocks/{block_id}/children",
            data=body,
            headers=_notion_headers(api_key),
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            json.load(resp)


def _block_plain_text(block: dict) -> str:
    btype = block.get("type")
    content = block.get(btype) if btype else None
    if not isinstance(content, dict):
        return ""
    rich_text = content.get("rich_text", [])
    if not isinstance(rich_text, list):
        return ""
    return "".join(
        rt.get("plain_text") or (rt.get("text") or {}).get("content", "") for rt in rich_text
    )


def body_marker_present(children: list[dict], marker: str) -> bool:
    return any(marker in _block_plain_text(b) for b in children)


def load_publication_copy(publication_id: str, copy_dir: Path) -> dict:
    path = copy_dir / f"{publication_id.lower()}-final-copy.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Copy file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_properties(payload: dict) -> dict:
    props: dict = {
        "Copy LinkedIn": {"rich_text": _chunks(payload["copy_linkedin"].strip(), guard_property_limit=True)},
        "Copy Blog": {"rich_text": _chunks(payload["copy_blog"].strip(), guard_property_limit=True)},
        "Copy X": {"rich_text": _chunks(payload["copy_x"].strip(), guard_property_limit=True)},
    }
    if payload.get("copy_linkedin_empresa"):
        props["Copy LinkedIn empresa"] = {
            "rich_text": _chunks(payload["copy_linkedin_empresa"].strip(), guard_property_limit=True)
        }
    if payload.get("trace_id"):
        props["trace_id"] = {"rich_text": _chunks(payload["trace_id"])}
    if payload.get("comentarios_revision"):
        props["Comentarios revisión"] = {
            "rich_text": _chunks(payload["comentarios_revision"].strip())
        }
    return props


def assert_gates_unchanged(before: dict, after: dict) -> None:
    for gate in ("aprobado_contenido", "autorizar_publicacion", "gate_invalidado"):
        if gate not in before:
            continue
        b = before[gate].get("checkbox")
        a = after[gate].get("checkbox")
        if b is not a:
            raise RuntimeError(f"Gate {gate} changed {b} -> {a}; aborting")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply editorial copy to Notion")
    parser.add_argument("--publication-id", default="CAND-001")
    parser.add_argument("--page-id", help="Override Notion page ID")
    parser.add_argument("--copy-dir", type=Path, default=DEFAULT_COPY_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verify-openclaw",
        type=Path,
        default=Path.home() / ".openclaw" / "openclaw.json",
        help="Verify rick-communication-director uses GPT-5.5",
    )
    parser.add_argument("--skip-model-verify", action="store_true")
    parser.add_argument(
        "--write-body",
        action="store_true",
        help=(
            "Also append the long Copy Blog text as page body blocks (V2 escape "
            "hatch #1 for the rich_text property limit; idempotent per page via "
            "a trace_id marker block, see build_copy_blog_body_blocks)"
        ),
    )
    parser.add_argument(
        "--force-body-append",
        action="store_true",
        help="With --write-body: append even if the marker block is already present",
    )
    parser.add_argument(
        "--emit-worker-payload",
        type=Path,
        help=(
            "Write a partial explicit-payload JSON (V2 escape hatch #2: full "
            "body_markdown, bypasses the Copy Blog property entirely) for "
            "worker/tasks/editorial_publish.py's 'payload' input"
        ),
    )
    args = parser.parse_args()

    payload = load_publication_copy(args.publication_id, args.copy_dir)
    page_id = args.page_id or payload.get("notion_page_id")
    if not page_id:
        print("ERROR: notion_page_id required", file=sys.stderr)
        return 2

    validation = validate_publication_payload(payload)
    print("VALIDATION_OK" if validation.ok else "VALIDATION_FAIL")
    for w in validation.warnings:
        print(f"  warn: {w}")
    if not validation.ok:
        for e in validation.errors:
            print(f"  error: {e}", file=sys.stderr)
        return 1

    if not args.skip_model_verify:
        try:
            if args.verify_openclaw.is_file():
                info = verify_openclaw_agent_model(
                    args.verify_openclaw, "rick-communication-director"
                )
                print(f"MODEL_VERIFY_OK agent={info['agent_id']} model={info['model_primary']}")
            else:
                print(f"MODEL_VERIFY_SKIP: {args.verify_openclaw} not found (local dev)")
                print(editorial_model_status_message())
        except EditorialModelError as exc:
            print(f"MODEL_VERIFY_FAIL: {exc}", file=sys.stderr)
            return 3

    try:
        properties = build_properties(payload)
    except RichTextOverflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5

    marker = f"{_BODY_MARKER_PREFIX} — trace_id: {payload.get('trace_id') or args.publication_id}"
    body_blocks = build_copy_blog_body_blocks(payload["copy_blog"].strip(), marker) if args.write_body else []

    if args.emit_worker_payload:
        worker_payload = build_worker_copy_payload(payload, page_id)
        args.emit_worker_payload.parent.mkdir(parents=True, exist_ok=True)
        args.emit_worker_payload.write_text(
            json.dumps(worker_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"WORKER_PAYLOAD_WRITTEN path={args.emit_worker_payload}")

    if args.dry_run:
        print(f"DRY_RUN page_id={page_id} props={list(properties)}")
        if args.write_body:
            print(
                f"DRY_RUN write_body blocks={len(body_blocks)} marker={marker!r} "
                "(idempotency vs existing page blocks not checked in dry-run, no Notion call)"
            )
        print("VALIDATION_OK gates=unchanged (dry-run, no Notion call)")
        return 0

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY required for Notion write", file=sys.stderr)
        return 2

    before = _get_page(api_key, page_id)
    props_before = before["properties"]
    for gate in ("aprobado_contenido", "autorizar_publicacion"):
        if props_before.get(gate, {}).get("checkbox"):
            print(f"ERROR: {gate} is true; refusing to overwrite copy", file=sys.stderr)
            return 4

    after = _patch_page(api_key, page_id, properties)
    assert_gates_unchanged(props_before, after["properties"])
    print(f"APPLIED page_id={page_id} trace_id={payload.get('trace_id')}")
    print("gates unchanged: aprobado_contenido=false autorizar_publicacion=false")

    if args.write_body:
        existing_children = _list_block_children(api_key, page_id)
        if not args.force_body_append and body_marker_present(existing_children, marker):
            print(f"BODY_SKIP_ALREADY_PRESENT marker={marker!r}")
        else:
            _append_block_children(api_key, page_id, body_blocks)
            print(f"BODY_APPENDED blocks={len(body_blocks)} marker={marker!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
