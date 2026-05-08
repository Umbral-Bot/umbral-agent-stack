"""Stage 8: hero image generator for Publicaciones drafts.

For each proposal that already has a Notion page (created by Stage 7) and
no image yet, this script:

1. Builds a visual prompt from the proposal's titular + ángulo + disciplinas.
2. Generates an image via Gemini (in-process, reuses
   ``worker.tasks.google_image.handle_google_image_generate``).
3. Saves the bytes locally under ``~/.cache/rick-discovery/images/``.
4. Uploads the file to Notion via the 2025-09-03 ``/file_uploads`` API
   (single-part flow).
5. Sets the page cover and inserts an ``image`` block at the top of the body.
6. Writes the Notion-hosted URL to the page's ``Visual asset URL`` property.
7. Updates ``proposals.image_status`` / ``image_url`` / ``image_prompt``.

Idempotency:
- Rows with ``image_status='ok'`` are skipped (unless ``--force-regenerate``).
- Rows with ``image_status='failed'`` are retried only after 24 h
  (column ``image_last_attempt_at`` epoch-seconds).

Cost guard:
- Static estimate per image (default $0.04, configurable via
  ``--max-cost-per-image``). The script exits non-zero before generating if
  ``estimate > max-cost-per-image``.

This is invoked manually for now — NO cron wiring.

Schema introspection (live, not hardcoded):
- DB Publicaciones data_source_id is configurable
  (``--publicaciones-ds-id``, default ``dc833f1f-07d9-49d0-82ec-fdfad1c808c4``).
- The script logs a warning if ``Visual asset URL`` is missing and falls back
  to cover + body block only (still a partial success).

Notion API limits respected:
- Rate-limit sleep ``0.34s`` between calls (~3 rps).
- File upload single-part path requires file ≤ 20 MB (Gemini PNGs are ≪).

Cero secrets en logs: tokens nunca se imprimen (sólo longitudes y prefijos).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DEFAULT_STATE_DB = Path.home() / ".cache" / "rick-discovery" / "state.sqlite"
DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"
DEFAULT_IMAGE_DIR = Path.home() / ".cache" / "rick-discovery" / "images"
DEFAULT_PUBLICACIONES_DS_ID = "dc833f1f-07d9-49d0-82ec-fdfad1c808c4"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
RATE_LIMIT_SLEEP_S = 0.34

DEFAULT_IMAGE_MODEL = "gemini-3-pro-image-preview"
DEFAULT_IMAGE_SIZE = "1536x1024"  # 3:2, suitable for Notion cover
DEFAULT_MAX_COST_PER_IMAGE_USD = 0.20
ESTIMATED_COST_PER_IMAGE_USD = 0.04  # gemini-3-pro-image-preview rough estimate

# Retry window for failed proposals.
RETRY_FAILED_AFTER_S = 24 * 3600

# Visual style guard rails for AEC / Umbral editorial.
PROMPT_STYLE_SUFFIX = (
    "Editorial illustration for an architecture-engineering-construction (AEC) "
    "publication. Minimalist, high contrast, clean composition, no text or "
    "captions, no embedded logos, no watermarks. Corporate Umbral palette: "
    "deep navy, warm off-white, accent ochre. Cinematic lighting, 3:2 frame."
)

VISUAL_ASSET_URL_PROP = "Visual asset URL"

logger = logging.getLogger("stage8")


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def log_event(event: str, **fields: Any) -> None:
    """Append a JSONL ops_log entry. Never raises."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    try:
        DEFAULT_OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# --------------------------------------------------------------------------
# State DB migration
# --------------------------------------------------------------------------

IMAGE_COLUMNS = {
    "image_status": "TEXT",
    "image_url": "TEXT",
    "image_prompt": "TEXT",
    "image_last_attempt_at": "INTEGER",
    "image_last_error": "TEXT",
}


def ensure_image_columns(db_path: Path) -> None:
    """Idempotent ``ALTER TABLE proposals ADD COLUMN`` for the image fields."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(proposals)").fetchall()
        if not rows:
            raise RuntimeError(
                f"Table 'proposals' missing in {db_path}. Run Stage 6 first."
            )
        existing = {r[1] for r in rows}
        for col, typ in IMAGE_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE proposals ADD COLUMN {col} {typ}")
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Proposal selection
# --------------------------------------------------------------------------

def read_candidate_proposals(
    db_path: Path,
    *,
    limit: int | None,
    force: bool,
) -> list[dict[str, Any]]:
    """Pull proposals eligible for image generation.

    Eligibility:
    - notion_page_id IS NOT NULL
    - image_status IS NULL, OR (status='failed' AND last_attempt_at older than
      RETRY_FAILED_AFTER_S), OR force=True.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if force:
            sql = (
                "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, "
                "       notion_page_id, image_status, image_last_attempt_at "
                "FROM proposals WHERE notion_page_id IS NOT NULL ORDER BY id ASC"
            )
            params: tuple[Any, ...] = ()
        else:
            now = int(time.time())
            sql = (
                "SELECT id, titular, hook, angulo, fuentes_urls, disciplinas, "
                "       notion_page_id, image_status, image_last_attempt_at "
                "FROM proposals "
                "WHERE notion_page_id IS NOT NULL "
                "  AND ( image_status IS NULL "
                "        OR (image_status = 'failed' "
                "            AND (image_last_attempt_at IS NULL "
                "                 OR image_last_attempt_at < ?)) ) "
                "ORDER BY id ASC"
            )
            params = (now - RETRY_FAILED_AFTER_S,)
        if limit is not None:
            sql += " LIMIT ?"
            params = params + (limit,)
        rows = list(conn.execute(sql, params))
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["fuentes_urls"] = json.loads(d.get("fuentes_urls") or "[]")
            d["disciplinas"] = json.loads(d.get("disciplinas") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def mark_image_ok(
    db_path: Path,
    proposal_id: int,
    *,
    image_url: str,
    image_prompt: str,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET image_status='ok', image_url=?, "
            "image_prompt=?, image_last_attempt_at=?, image_last_error=NULL "
            "WHERE id=?",
            (image_url, image_prompt, int(time.time()), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_image_failed(db_path: Path, proposal_id: int, error: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE proposals SET image_status='failed', "
            "image_last_attempt_at=?, image_last_error=? WHERE id=?",
            (int(time.time()), error[:500], proposal_id),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------

def build_image_prompt(proposal: dict[str, Any]) -> str:
    """Compose a visual prompt from the proposal fields."""
    titular = (proposal.get("titular") or "").strip()
    angulo = (proposal.get("angulo") or "").strip()
    disciplinas = proposal.get("disciplinas") or []
    if not titular:
        raise ValueError("proposal has no titular; cannot build prompt")
    parts = [f"Subject: {titular}."]
    if angulo:
        parts.append(f"Editorial angle: {angulo}.")
    if disciplinas:
        parts.append("Disciplines: " + ", ".join(disciplinas) + ".")
    parts.append(PROMPT_STYLE_SUFFIX)
    return " ".join(parts)


# --------------------------------------------------------------------------
# Cost guard
# --------------------------------------------------------------------------

def cost_guard(
    *,
    n_proposals: int,
    cost_per_image: float,
    max_per_image: float,
) -> None:
    """Abort if estimated unit cost exceeds the cap.

    The guard is per-image (not per-batch) because Stage 8 is invoked manually
    in small bursts. ``n_proposals`` is logged so operators can sanity-check
    the planned spend.
    """
    if cost_per_image > max_per_image:
        raise RuntimeError(
            f"Cost guard: estimated {cost_per_image:.4f} USD/image exceeds "
            f"--max-cost-per-image={max_per_image:.4f} (planned n={n_proposals})"
        )


# --------------------------------------------------------------------------
# Image generation (in-process Gemini via worker.tasks.google_image)
# --------------------------------------------------------------------------

def generate_image(
    prompt: str,
    *,
    output_dir: Path,
    proposal_id: int,
    model: str,
    size: str,
) -> Path:
    """Generate one image and return the local path.

    Imports the Worker handler lazily so unit tests that don't need network
    can stub it without touching the heavyweight import chain.
    """
    from worker.tasks.google_image import handle_google_image_generate

    output_dir.mkdir(parents=True, exist_ok=True)
    result = handle_google_image_generate({
        "prompt": prompt,
        "model": model,
        "size": size,
        "n": 1,
        "output_dir": str(output_dir),
        "filename_prefix": f"proposal-{proposal_id}",
    })
    images = result.get("images") or []
    if not images:
        raise RuntimeError("google.image.generate returned no images")
    return Path(images[0]["output_path"])


# --------------------------------------------------------------------------
# Notion client (minimal, with file_uploads single-part)
# --------------------------------------------------------------------------

class NotionClient:
    """Thin Notion wrapper. Single-part file upload only (≤ 20 MB)."""

    def __init__(self, token: str, *, timeout_s: float = 30.0) -> None:
        if not token:
            raise ValueError("NOTION_API_KEY not set")
        self._token = token
        self._client = httpx.Client(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout_s,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return "NotionClient(token=***)"

    def close(self) -> None:
        self._client.close()

    def get(self, path: str) -> dict[str, Any]:
        time.sleep(RATE_LIMIT_SLEEP_S)
        r = self._client.get(path)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        time.sleep(RATE_LIMIT_SLEEP_S)
        r = self._client.post(path, json=payload)
        r.raise_for_status()
        return r.json()

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        time.sleep(RATE_LIMIT_SLEEP_S)
        r = self._client.patch(path, json=payload)
        r.raise_for_status()
        return r.json()

    def upload_file(self, file_path: Path) -> dict[str, Any]:
        """Single-part file upload. Returns the file_upload object incl. id.

        The 2025-09-03 contract:
        1. POST /file_uploads → {id, upload_url, mode='single_part', ...}
        2. POST <upload_url> multipart with field 'file' → 200 + final object
           with status='uploaded'.
        """
        size = file_path.stat().st_size
        if size > 20 * 1024 * 1024:
            raise RuntimeError(
                f"File {file_path} is {size} bytes; single-part upload limit "
                "is 20 MB. Multi-part not implemented in Stage 8."
            )

        # Step 1 — create the file_upload object.
        meta = self.post(
            "/file_uploads",
            {
                "filename": file_path.name,
                "content_type": "image/png",
                "mode": "single_part",
            },
        )
        upload_url = meta.get("upload_url")
        upload_id = meta.get("id")
        if not upload_url or not upload_id:
            raise RuntimeError(f"file_uploads response missing fields: {meta}")

        # Step 2 — POST the binary to the signed upload_url.
        # Notion's upload endpoint expects multipart/form-data with the binary
        # under field name 'file'. Auth headers are still required.
        time.sleep(RATE_LIMIT_SLEEP_S)
        with open(file_path, "rb") as fh:
            files = {"file": (file_path.name, fh, "image/png")}
            # Use a raw httpx call (NOT self._client) to avoid the JSON
            # Content-Type default header.
            r = httpx.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Notion-Version": NOTION_VERSION,
                },
                files=files,
                timeout=120.0,
            )
        r.raise_for_status()
        return r.json()


# --------------------------------------------------------------------------
# Notion attach (cover + body block + Visual asset URL property)
# --------------------------------------------------------------------------

def attach_image_to_notion(
    client: NotionClient,
    *,
    page_id: str,
    file_path: Path,
    caption: str,
    schema_props: dict[str, str] | None,
) -> str:
    """Upload + set cover + insert image block + (optionally) set URL prop.

    Returns the Notion-hosted file URL (signed). If the schema lacks the
    ``Visual asset URL`` property, the URL is still returned but the property
    update is skipped (logged as a soft warning).
    """
    upload = client.upload_file(file_path)
    upload_id = upload["id"]

    # 1. Set page cover via PATCH /pages/{id}.
    client.patch(
        f"/pages/{page_id}",
        {
            "cover": {
                "type": "file_upload",
                "file_upload": {"id": upload_id},
            }
        },
    )

    # 2. Insert an image block at the top of the page body.
    image_block = {
        "object": "block",
        "type": "image",
        "image": {
            "type": "file_upload",
            "file_upload": {"id": upload_id},
            "caption": [
                {"type": "text", "text": {"content": caption[:2000]}}
            ],
        },
    }
    client.patch(
        f"/blocks/{page_id}/children",
        {"children": [image_block]},
    )

    # 3. Re-GET the page to recover the signed file URL Notion stored.
    page = client.get(f"/pages/{page_id}")
    cover = page.get("cover") or {}
    file_obj = cover.get("file") or cover.get("external") or {}
    notion_file_url = file_obj.get("url") or ""

    # 4. Set the Visual asset URL property if the schema supports it.
    if schema_props is not None and VISUAL_ASSET_URL_PROP in schema_props:
        if notion_file_url:
            client.patch(
                f"/pages/{page_id}",
                {
                    "properties": {
                        VISUAL_ASSET_URL_PROP: {"url": notion_file_url}
                    }
                },
            )
    elif schema_props is not None:
        logger.warning(
            "Schema gap: '%s' property missing from DB Publicaciones; "
            "page %s has cover+body image but no URL property set.",
            VISUAL_ASSET_URL_PROP,
            page_id,
        )

    return notion_file_url


# --------------------------------------------------------------------------
# Schema fetch
# --------------------------------------------------------------------------

def fetch_publicaciones_schema(
    client: NotionClient, ds_id: str
) -> dict[str, str]:
    ds = client.get(f"/data_sources/{ds_id}")
    return {
        name: (p.get("type") or "?")
        for name, p in (ds.get("properties") or {}).items()
    }


# --------------------------------------------------------------------------
# Per-proposal orchestration
# --------------------------------------------------------------------------

def process_proposal(
    client: NotionClient | None,
    *,
    db_path: Path,
    proposal: dict[str, Any],
    image_dir: Path,
    model: str,
    size: str,
    schema_props: dict[str, str] | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Generate, upload, attach, persist for a single proposal."""
    pid = int(proposal["id"])
    page_id = proposal["notion_page_id"]
    prompt = build_image_prompt(proposal)

    if dry_run:
        log_event(
            "stage8.dry_run",
            proposal_id=pid,
            page_id=page_id,
            prompt_chars=len(prompt),
        )
        return {"proposal_id": pid, "dry_run": True, "prompt": prompt}

    if client is None:
        raise RuntimeError("client is required when dry_run=False")

    try:
        local_path = generate_image(
            prompt,
            output_dir=image_dir,
            proposal_id=pid,
            model=model,
            size=size,
        )
        log_event(
            "stage8.image_generated",
            proposal_id=pid,
            local_path=str(local_path),
            size_bytes=local_path.stat().st_size,
            model=model,
        )

        notion_url = attach_image_to_notion(
            client,
            page_id=page_id,
            file_path=local_path,
            caption=(proposal.get("titular") or "")[:200],
            schema_props=schema_props,
        )
        log_event(
            "stage8.notion_attached",
            proposal_id=pid,
            page_id=page_id,
            url_chars=len(notion_url),
        )

        mark_image_ok(
            db_path,
            pid,
            image_url=notion_url,
            image_prompt=prompt,
        )
        log_event("stage8.proposal_done", proposal_id=pid, page_id=page_id)
        return {
            "proposal_id": pid,
            "page_id": page_id,
            "local_path": str(local_path),
            "notion_url": notion_url,
        }
    except Exception as exc:  # noqa: BLE001 — surface root cause to ops_log
        err = f"{type(exc).__name__}: {exc}"
        mark_image_failed(db_path, pid, err)
        log_event(
            "stage8.proposal_failed",
            proposal_id=pid,
            page_id=page_id,
            error=err[:500],
        )
        return {"proposal_id": pid, "page_id": page_id, "error": err}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _load_openclaw_env() -> None:
    """Best-effort load ~/.config/openclaw/env into os.environ (VPS only)."""
    env_file = Path.home() / ".config" / "openclaw" / "env"
    if not env_file.exists():
        return
    raw = env_file.read_text(encoding="utf-8", errors="ignore")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.removeprefix("export ").strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 8 — hero image generator")
    p.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    p.add_argument("--image-dir", default=str(DEFAULT_IMAGE_DIR))
    p.add_argument(
        "--publicaciones-ds-id", default=DEFAULT_PUBLICACIONES_DS_ID
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force-regenerate", action="store_true")
    p.add_argument("--model", default=DEFAULT_IMAGE_MODEL)
    p.add_argument("--size", default=DEFAULT_IMAGE_SIZE)
    p.add_argument(
        "--max-cost-per-image",
        type=float,
        default=DEFAULT_MAX_COST_PER_IMAGE_USD,
        help="Abort if estimated USD per image exceeds this cap.",
    )
    p.add_argument(
        "--cost-per-image",
        type=float,
        default=ESTIMATED_COST_PER_IMAGE_USD,
        help="Override the static cost estimate per image.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = _build_argparser().parse_args(argv)
    _load_openclaw_env()

    state_db = Path(args.state_db)
    image_dir = Path(args.image_dir)
    if not state_db.exists():
        print(f"state DB not found: {state_db}", file=sys.stderr)
        return 2

    ensure_image_columns(state_db)

    proposals = read_candidate_proposals(
        state_db, limit=args.limit, force=args.force_regenerate
    )
    if not proposals:
        print("No candidate proposals.")
        return 0

    cost_guard(
        n_proposals=len(proposals),
        cost_per_image=args.cost_per_image,
        max_per_image=args.max_cost_per_image,
    )

    log_event(
        "stage8.run_start",
        n_candidates=len(proposals),
        dry_run=args.dry_run,
        force=args.force_regenerate,
        model=args.model,
        cost_per_image_usd=args.cost_per_image,
    )

    schema_props: dict[str, str] | None = None
    client: NotionClient | None = None

    if not args.dry_run:
        token = os.environ.get("NOTION_API_KEY") or os.environ.get(
            "NOTION_TOKEN"
        )
        if not token:
            print("NOTION_API_KEY not set", file=sys.stderr)
            return 2
        client = NotionClient(token)
        try:
            schema_props = fetch_publicaciones_schema(
                client, args.publicaciones_ds_id
            )
            if VISUAL_ASSET_URL_PROP not in schema_props:
                logger.warning(
                    "DB Publicaciones lacks '%s' property — cover + body "
                    "block will still be set.",
                    VISUAL_ASSET_URL_PROP,
                )
        except httpx.HTTPError as exc:
            print(f"Failed to fetch DS schema: {exc}", file=sys.stderr)
            if client is not None:
                client.close()
            return 3

    n_ok = 0
    n_fail = 0
    try:
        for prop in proposals:
            res = process_proposal(
                client,
                db_path=state_db,
                proposal=prop,
                image_dir=image_dir,
                model=args.model,
                size=args.size,
                schema_props=schema_props,
                dry_run=args.dry_run,
            )
            if "error" in res:
                n_fail += 1
                print(
                    f"FAIL proposal_id={res['proposal_id']}: {res['error']}",
                    file=sys.stderr,
                )
            else:
                n_ok += 1
                if args.dry_run:
                    print(
                        f"DRY proposal_id={res['proposal_id']} "
                        f"prompt={res['prompt'][:120]}…"
                    )
                else:
                    print(
                        f"OK proposal_id={res['proposal_id']} "
                        f"page={res['page_id']} url={res['notion_url'][:80]}"
                    )
    finally:
        if client is not None:
            client.close()

    log_event("stage8.run_end", n_ok=n_ok, n_fail=n_fail)
    print(f"Done. ok={n_ok} fail={n_fail}")
    return 0 if n_fail == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
