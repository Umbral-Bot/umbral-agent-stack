#!/usr/bin/env python3
"""Copy imagen_alt_N_url → Visual asset URL when David selects Alt N in Notion.

One-off helper until Worker poller wires Selección imagen → Visual asset URL.
Does NOT touch aprobado_contenido or autorizar_publicacion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NOTION_VERSION = "2022-06-28"
DEFAULT_PAGE_ID = "34b5f443-fb5c-81dd-8338-cb0b46699250"
ALT_RE = re.compile(r"^Alt ([1-5])$")
ALT_URL_PROPS = {
    1: "imagen_alt_1_url",
    2: "imagen_alt_2_url",
    3: "imagen_alt_3_url",
    4: "imagen_alt_4_url",
    5: "imagen_alt_5_url",
}


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get_page(api_key: str, page_id: str) -> dict:
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(api_key),
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _patch_page(api_key: str, page_id: str, properties: dict) -> dict:
    body = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=body,
        headers=_headers(api_key),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _select_name(prop: dict | None) -> str | None:
    if not prop or prop.get("type") != "select":
        return None
    sel = prop.get("select")
    return sel.get("name") if sel else None


def _url_value(prop: dict | None) -> str | None:
    if not prop or prop.get("type") != "url":
        return None
    return prop.get("url")


def _checkbox(prop: dict | None) -> bool | None:
    if not prop or prop.get("type") != "checkbox":
        return None
    return prop.get("checkbox")


def _parse_alt(selection: str | None) -> int | None:
    if not selection:
        return None
    m = ALT_RE.match(selection.strip())
    return int(m.group(1)) if m else None


def _read_state(props: dict) -> dict[str, Any]:
    alts: dict[int, str | None] = {}
    for n, key in ALT_URL_PROPS.items():
        alts[n] = _url_value(props.get(key))
    return {
        "seleccion_imagen": _select_name(props.get("Selección imagen")),
        "estado_imagen": _select_name(props.get("Estado imagen")),
        "visual_asset_url": _url_value(props.get("Visual asset URL")),
        "imagen_cantidad": props.get("imagen_cantidad", {}).get("number"),
        "aprobado_contenido": _checkbox(props.get("aprobado_contenido")),
        "autorizar_publicacion": _checkbox(props.get("autorizar_publicacion")),
        "alt_urls": alts,
    }


def _valid_https(url: str | None) -> bool:
    return bool(url and url.startswith("https://") and "app.magnific.com" not in url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Visual asset URL from Selección imagen")
    parser.add_argument("--page-id", default=DEFAULT_PAGE_ID)
    parser.add_argument(
        "--set-selection",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="David's choice: also write Selección imagen = Alt N (human gate)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY required", file=sys.stderr)
        return 2

    page = _get_page(api_key, args.page_id)
    props = page["properties"]
    state = _read_state(props)

    print(json.dumps(state, indent=2, ensure_ascii=False))

    if args.report_only:
        return 0

    alt_num = args.set_selection or _parse_alt(state["seleccion_imagen"])
    if alt_num is None:
        print(
            "BLOCKED: Selección imagen not Alt 1-5. "
            "Pick in Notion or pass --set-selection N",
            file=sys.stderr,
        )
        return 3

    url_prop = ALT_URL_PROPS[alt_num]
    hero_url = state["alt_urls"].get(alt_num)
    if not _valid_https(hero_url):
        print(
            f"BLOCKED: {url_prop} missing or not direct HTTPS: {hero_url!r}",
            file=sys.stderr,
        )
        return 4

    patch: dict[str, Any] = {
        "Visual asset URL": {"url": hero_url},
        "Estado imagen": {"select": {"name": "Seleccionada"}},
    }
    if args.set_selection:
        patch["Selección imagen"] = {"select": {"name": f"Alt {alt_num}"}}

    if state["autorizar_publicacion"]:
        print("ERROR: autorizar_publicacion is true; refusing", file=sys.stderr)
        return 5

    if args.dry_run:
        print(f"DRY_RUN would patch: {list(patch)} hero={hero_url}")
        return 0

    before_auth = _checkbox(props.get("autorizar_publicacion"))
    _patch_page(api_key, args.page_id, patch)
    after = _get_page(api_key, args.page_id)
    after_auth = _checkbox(after["properties"].get("autorizar_publicacion"))
    if before_auth is not after_auth:
        raise RuntimeError("autorizar_publicacion changed unexpectedly")

    final = _read_state(after["properties"])
    print(f"SYNC_OK alt={alt_num} visual_asset_url={final['visual_asset_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
