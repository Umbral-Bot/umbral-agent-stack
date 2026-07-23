"""
Task: magnific.generate_variants — P2.2 Magnific 5 alternativas de imagen.

Generates image variants for a `Publicaciones` row via Magnific's Mystic REST
API (https://docs.magnific.com/api-reference/mystic/post-mystic — Magnific's
REST surface is the headless/API-key path documented as the Worker fallback
in docs/ops/magnific-editorial-setup-2026-06-06.md, distinct from the
interactive MCP OAuth path used by Rick/Cursor), and writes the resulting
URLs back, per:

    docs/ops/editorial-norte-hitl-contract-2026-07-22.md §5.G
    docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md P2.2
    docs/ops/notion-publicaciones-v2-visual-gates-schema.md §2 (Estado imagen
      state machine, property names/types)
    docs/adr/ADR-006-capa-visual-editorial.md (anti-AI-slop rule)

Contract (do not weaken):
- Notion writes are Worker/core's exclusive job (ADR-011 #1). The dispatcher
  poller only decides which `Publicaciones` rows to ask this handler to
  (re-)evaluate; it never writes to Notion itself.
- Fail-closed: re-fetches the Publicaciones page itself and only acts on the
  live `Estado imagen` value — never trusts a caller-supplied snapshot.
- Idempotent: rows already `Generando` (another run in flight) or
  `Listo para selección` / `Seleccionada` (already produced / already chosen)
  are a no-op. `Regeneración pedida` is treated as an explicit request and is
  eligible.
- Never touches `Selección imagen`, `Visual asset URL`, `aprobado_contenido`,
  `autorizar_publicacion`, or any copy field — those belong to David
  (`Selección imagen`), `scripts/editorial/sync_visual_asset_from_selection.py`
  (`Visual asset URL`), or other packages entirely.
- Standardizes on exactly 5 variants (roadmap-named risk: "conteo 3 vs 5").
  A run that produces fewer than requested because of an upstream failure is
  reported as `Estado imagen = Error` with `imagen_error` set — never a false
  `Listo para selección` with a partial set.
- Proves Notion write access (writes the interim `Estado imagen = Generando`
  state) before spending any Magnific credits. If that write fails, aborts
  before calling Magnific at all.
- Never destructively clears `imagen_alt_*_url` slots this run did not
  itself (re)populate: a prior attempt may have already produced valid,
  credit-paid URLs before failing partway through, and a subsequent retry
  that also fails must not erase them. Only a full success (every requested
  variant generated) overwrites/clears the complete set.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .. import config, notion_client

logger = logging.getLogger("worker.tasks.magnific")

MAGNIFIC_API_BASE_URL = "https://api.magnific.com"
MYSTIC_ENDPOINT = f"{MAGNIFIC_API_BASE_URL}/v1/ai/mystic"

DEFAULT_VARIANT_COUNT = 5
# Umbral canonical Magnific aspect ratio = 4:3 (docs/ops/umbral-bim-magnific-visual-style-v1.md).
# "classic_4_3" is Magnific's documented aspect_ratio enum value for 4:3.
DEFAULT_ASPECT_RATIO = "classic_4_3"
DEFAULT_RESOLUTION = "2k"
DEFAULT_MODEL = "realism"

_SUBMIT_TIMEOUT_SEC = 30.0
_POLL_TIMEOUT_SEC = 20.0
_POLL_INTERVAL_SEC = 3.0
_MAX_POLL_ATTEMPTS = 40  # ~2 minutes per variant at the interval above

# Estado imagen state machine (notion-publicaciones-v2-visual-gates-schema.md §2.2).
_IN_PROGRESS_STATES = {"Generando"}
_ALREADY_DONE_STATES = {"Listo para selección", "Seleccionada"}
_ELIGIBLE_STATES = {"", "No aplica", "Pendiente generación", "Error", "Regeneración pedida", None}

_ANTI_SLOP_SUFFIX = (
    "Sobrio, técnico, anti-hype. Sin personas foto-real generadas por AI, sin "
    "rostros reconocibles, sin logos ni marcas de terceros. Contexto AECO real "
    "(obra, oficina técnica, modelos BIM en pantalla), nada de stock genérico "
    "corporativo. Composición clara para feed LinkedIn / hero de blog. Sin "
    "texto incrustado generado por el modelo."
)


def _flatten_prop(prop: Any) -> Any:
    """Flatten a single raw Notion property value (as returned by get_page)."""
    if not isinstance(prop, dict):
        return None
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "url":
        return prop.get("url")
    if ptype == "select":
        return (prop.get("select") or {}).get("name")
    if ptype == "number":
        return prop.get("number")
    return None


def _read_publicacion_fields(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get("properties") or {}

    def get(name: str) -> Any:
        return _flatten_prop(props.get(name))

    return {
        "titulo": get("Título"),
        "premisa": get("Premisa"),
        "visual_brief": get("Visual brief"),
        "estado_imagen": get("Estado imagen"),
    }


def _build_prompt(fields: Dict[str, Any], override_prompt: Optional[str]) -> str:
    if override_prompt and str(override_prompt).strip():
        return str(override_prompt).strip()
    brief = str(fields.get("visual_brief") or "").strip()
    if brief:
        base = brief
    else:
        titulo = str(fields.get("titulo") or "").strip()
        premisa = str(fields.get("premisa") or "").strip()
        base = f"Professional LinkedIn/blog hero for AEC/BIM audience. {titulo}. {premisa}".strip()
    return f"{base} {_ANTI_SLOP_SUFFIX}".strip()


def _magnific_headers() -> Dict[str, str]:
    api_key = (config.MAGNIFIC_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError(
            "MAGNIFIC_API_KEY not configured on server (VPS secrets / "
            "~/.config/openclaw/env) — see "
            "docs/ops/magnific-editorial-setup-2026-06-06.md and "
            "docs/ops/editorial-magnific-p22-poller-2026-07-23.md"
        )
    return {"x-magnific-api-key": api_key, "Content-Type": "application/json"}


def _safe_httpx_error_body(exc: httpx.HTTPStatusError) -> str:
    try:
        return exc.response.text[:300]
    except Exception:
        return ""


def _submit_mystic(prompt: str, aspect_ratio: str, resolution: str, model: str) -> str:
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "model": model,
    }
    with httpx.Client(timeout=_SUBMIT_TIMEOUT_SEC) as client:
        try:
            resp = client.post(MYSTIC_ENDPOINT, headers=_magnific_headers(), json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Magnific Mystic submit error {exc.response.status_code}: {_safe_httpx_error_body(exc)}"
            )
        data = resp.json()
    task_id = ((data or {}).get("data") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Magnific Mystic submit response missing task_id: {str(data)[:300]}")
    return str(task_id)


def _poll_mystic(task_id: str) -> str:
    url = f"{MYSTIC_ENDPOINT}/{task_id}"
    started = time.monotonic()
    for _attempt in range(_MAX_POLL_ATTEMPTS):
        with httpx.Client(timeout=_POLL_TIMEOUT_SEC) as client:
            try:
                resp = client.get(url, headers=_magnific_headers())
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Magnific Mystic poll error {exc.response.status_code}: {_safe_httpx_error_body(exc)}"
                )
            data = resp.json()
        payload = (data or {}).get("data") or {}
        status = payload.get("status")
        if status == "COMPLETED":
            generated = payload.get("generated") or []
            url_value = next((u for u in generated if isinstance(u, str) and u.strip()), None)
            if not url_value:
                raise RuntimeError(f"Magnific Mystic task {task_id} COMPLETED without a generated URL")
            if "app.magnific.com" in url_value:
                # Mirrors the guard in scripts/editorial/sync_visual_asset_from_selection.py:
                # only direct/exportable URLs are acceptable, never the interactive app URL.
                raise RuntimeError(
                    f"Magnific Mystic task {task_id} returned an app.magnific.com URL, not a direct export"
                )
            return url_value
        if status == "FAILED":
            raise RuntimeError(f"Magnific Mystic task {task_id} FAILED: {str(payload)[:300]}")
        time.sleep(_POLL_INTERVAL_SEC)
    elapsed = time.monotonic() - started
    raise RuntimeError(
        f"Magnific Mystic task {task_id} did not complete within {elapsed:.0f}s "
        f"({_MAX_POLL_ATTEMPTS} attempts)"
    )


def _generate_one_variant(prompt: str, aspect_ratio: str, resolution: str, model: str) -> str:
    task_id = _submit_mystic(prompt, aspect_ratio, resolution, model)
    return _poll_mystic(task_id)


def _today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def handle_magnific_generate_variants(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate image variants for one Publicaciones row and write the results.

    Input:
        publicacion_page_id (str, required): Notion page id (or URL) of the
            Publicaciones row to evaluate.
        dry_run (bool, optional): if True, verify eligibility and return the
            prompt/params that would be used, without calling Magnific or
            writing to Notion.
        count (int, optional): variants to generate, 1-5. Default 5 (the
            contract count — see roadmap risk "conteo 3 vs 5"). Lower values
            exist for manual/testing use, not for production scans.
        prompt (str, optional): explicit prompt override. Default: derived
            from `Visual brief`, else `Título` + `Premisa`, plus the ADR-006
            anti-slop suffix.
        aspect_ratio (str, optional): Magnific aspect_ratio enum value.
            Default "classic_4_3" (Umbral canonical 4:3).
        resolution (str, optional): Magnific resolution enum ("1k"/"2k"/"4k").
        model (str, optional): Magnific Mystic model enum.

    Returns:
        {"ok": bool, "generated": int, "requested": int, "urls": [...],
         "estado_imagen": str|None, "publicacion_page_id": str,
         "error": str|None, "skipped": bool|None, ...}
    """
    page_id = str(input_data.get("publicacion_page_id") or "").strip()
    if not page_id:
        return {"ok": False, "error": "'publicacion_page_id' is required"}

    dry_run = bool(input_data.get("dry_run", False))
    try:
        count = int(input_data.get("count") or DEFAULT_VARIANT_COUNT)
    except (TypeError, ValueError):
        return {"ok": False, "error": "'count' must be an integer", "publicacion_page_id": page_id}
    if count < 1 or count > 5:
        return {"ok": False, "error": "'count' must be between 1 and 5", "publicacion_page_id": page_id}
    aspect_ratio = str(input_data.get("aspect_ratio") or DEFAULT_ASPECT_RATIO)
    resolution = str(input_data.get("resolution") or DEFAULT_RESOLUTION)
    model = str(input_data.get("model") or DEFAULT_MODEL)
    override_prompt = input_data.get("prompt")

    try:
        page = notion_client.get_page(page_id)
    except Exception as e:
        return {"ok": False, "error": f"Failed to read Publicaciones page: {e}", "publicacion_page_id": page_id}

    fields = _read_publicacion_fields(page)
    estado = fields["estado_imagen"]

    if estado in _IN_PROGRESS_STATES:
        return {
            "ok": True,
            "skipped": True,
            "reason": "in_progress",
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }
    if estado in _ALREADY_DONE_STATES:
        return {
            "ok": True,
            "skipped": True,
            "already_generated": True,
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }
    if estado not in _ELIGIBLE_STATES:
        return {
            "ok": False,
            "error": f"estado_imagen_not_eligible: {estado!r}",
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    prompt = _build_prompt(fields, override_prompt)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_generate": True,
            "count": count,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "model": model,
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    try:
        _magnific_headers()  # raises early if MAGNIFIC_API_KEY missing — before any writes
    except RuntimeError as e:
        return {"ok": False, "error": str(e), "publicacion_page_id": page_id}

    # Prove Notion write access before spending Magnific credits. Deliberately
    # does NOT clear imagen_alt_*_url here: a prior attempt may have already
    # produced (credit-paid) valid URLs before failing partway through, and a
    # subsequent automatic retry that also fails must not destroy them. See
    # the failure branch below for how existing slots are preserved.
    interim_props: Dict[str, Any] = {
        "Estado imagen": {"select": {"name": "Generando"}},
        "imagen_error": {"rich_text": []},
    }
    try:
        notion_client.update_page_properties(page_id_or_url=page_id, properties=interim_props)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to write interim 'Generando' state: {e}",
            "publicacion_page_id": page_id,
        }

    urls: List[str] = []
    failure: Optional[str] = None
    for idx in range(1, count + 1):
        try:
            url = _generate_one_variant(prompt, aspect_ratio, resolution, model)
            urls.append(url)
            logger.info("Magnific variant %d/%d generated for page %s", idx, count, page_id[:8])
        except Exception as e:
            failure = f"alt_{idx}: {str(e)[:200]}"
            logger.warning(
                "Magnific variant %d/%d failed for page %s: %s", idx, count, page_id[:8], failure
            )
            break

    props: Dict[str, Any] = {f"imagen_alt_{i}_url": {"url": u} for i, u in enumerate(urls, start=1)}
    props["imagen_cantidad"] = {"number": len(urls)}
    props["imagen_generada_at"] = {"date": {"start": _today_date()}}

    if failure or len(urls) < count:
        props["Estado imagen"] = {"select": {"name": "Error"}}
        props["imagen_error"] = {"rich_text": [{"text": {"content": (failure or "incomplete_generation")[:2000]}}]}
        try:
            notion_client.update_page_properties(page_id_or_url=page_id, properties=props)
        except Exception:
            logger.warning("Failed to write Error state for page %s", page_id[:8], exc_info=True)
        return {
            "ok": False,
            "error": failure or "incomplete_generation",
            "generated": len(urls),
            "requested": count,
            "urls": urls,
            "publicacion_page_id": page_id,
        }

    props["Estado imagen"] = {"select": {"name": "Listo para selección"}}
    # A full successful batch supersedes everything: clear any higher-numbered
    # slots left over from a previous run with a larger `count` (only matters
    # when count < 5, e.g. a manual override — the default production count
    # is always 5, filling every slot).
    for i in range(count + 1, 6):
        props[f"imagen_alt_{i}_url"] = {"url": None}
    try:
        notion_client.update_page_properties(page_id_or_url=page_id, properties=props)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Generated {len(urls)} variants but failed to write results: {e}",
            "generated": len(urls),
            "requested": count,
            "urls": urls,
            "publicacion_page_id": page_id,
        }

    logger.info("Magnific: %d/%d variants written for page %s", len(urls), count, page_id[:8])
    return {
        "ok": True,
        "generated": len(urls),
        "requested": count,
        "urls": urls,
        "estado_imagen": "Listo para selección",
        "publicacion_page_id": page_id,
    }
