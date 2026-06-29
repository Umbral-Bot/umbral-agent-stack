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


def _chunks(text: str, size: int = 1900) -> list[dict]:
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    return [{"type": "text", "text": {"content": text[i : i + size]}} for i in range(0, len(text), size)]


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


def load_publication_copy(publication_id: str, copy_dir: Path) -> dict:
    path = copy_dir / f"{publication_id.lower()}-final-copy.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Copy file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_properties(payload: dict) -> dict:
    props: dict = {
        "Copy LinkedIn": {"rich_text": _chunks(payload["copy_linkedin"].strip())},
        "Copy Blog": {"rich_text": _chunks(payload["copy_blog"].strip())},
        "Copy X": {"rich_text": _chunks(payload["copy_x"].strip())},
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

    properties = build_properties(payload)

    if args.dry_run:
        print(f"DRY_RUN page_id={page_id} props={list(properties)}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
