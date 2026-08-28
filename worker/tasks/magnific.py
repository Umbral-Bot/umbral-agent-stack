"""
Task: magnific.generate_variants — P2.2 Magnific 5 alternativas de imagen.

Generates image variants for a `Publicaciones` row via Magnific's REST API.
The editorial default is Nano Banana Pro Flash (also known as Nano Banana 2),
while Nano Banana Pro and the legacy Mystic/realism path remain explicit
overrides. The REST surface is the headless/API-key path documented as the
Worker fallback in docs/ops/magnific-editorial-setup-2026-06-06.md, distinct
from the interactive MCP OAuth path used by Rick/Cursor. Results are written
back per:

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
  are a no-op, except that `Selección imagen = Regenerar` on a ready/error row
  is consumed atomically as `Regeneración pedida` + `Pendiente` before a new
  run. `Regeneración pedida` itself remains eligible.
- Never touches `Visual asset URL`, `aprobado_contenido`,
  `autorizar_publicacion`, or any copy field. The only `Selección imagen`
  write is consuming the explicit `Regenerar` command back to `Pendiente`.
- Standardizes on exactly 5 variants (roadmap-named risk: "conteo 3 vs 5").
  A run that produces fewer than requested because of an upstream failure is
  reported as `Estado imagen = Error` with `imagen_error` set — never a false
  `Listo para selección` with a partial set.
- Proves Notion write access (writes the interim `Estado imagen = Generando`
  state) before spending any Magnific credits. If that write fails, aborts
  before calling Magnific at all.
- Never destructively clears `imagen_alt_*_url`. A failed run writes no image
  slots at all, preserving the prior set atomically. A complete production
  5/5 success overwrites all five; a smaller manual success overwrites only
  the slots it generated and never emits `url: null` for the remainder.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import yaml

from .. import config, notion_client

logger = logging.getLogger("worker.tasks.magnific")

MAGNIFIC_API_BASE_URL = "https://api.magnific.com"
MYSTIC_ENDPOINT = f"{MAGNIFIC_API_BASE_URL}/v1/ai/mystic"
NANO_BANANA_FLASH_ENDPOINT = (
    f"{MAGNIFIC_API_BASE_URL}/v1/ai/text-to-image/nano-banana-pro-flash"
)
NANO_BANANA_PRO_ENDPOINT = f"{MAGNIFIC_API_BASE_URL}/v1/ai/text-to-image/nano-banana-pro"

DEFAULT_VARIANT_COUNT = 5
# Umbral canonical Magnific aspect ratio = 4:3 and editorial resolution = 2K.
# These are the documented Nano Banana REST enums. Explicit Mystic requests
# are normalized to that legacy endpoint's `classic_4_3` / `2k` vocabulary.
DEFAULT_ASPECT_RATIO = "4:3"
DEFAULT_RESOLUTION = "2K"
DEFAULT_MODEL = "nano-banana-pro-flash"
MAX_PROMPT_CHARS = 3000

_SUBMIT_TIMEOUT_SEC = 30.0
_POLL_TIMEOUT_SEC = 20.0
_POLL_INTERVAL_SEC = 3.0
_MAX_POLL_ATTEMPTS = 40  # ~2 minutes per variant at the interval above
_MAX_HTTP_503_RETRIES = 2
_HTTP_503_RETRY_BASE_SEC = 1.0

# Estado imagen state machine (notion-publicaciones-v2-visual-gates-schema.md §2.2).
_IN_PROGRESS_STATES = {"Generando"}
_ALREADY_DONE_STATES = {"Listo para selección", "Seleccionada"}
_ELIGIBLE_STATES = {"", "No aplica", "Pendiente generación", "Error", "Regeneración pedida", None}
_REGENERABLE_STATES = {"Listo para selección", "Error"}

_ANTI_SLOP_SUFFIX = (
    "ilustración editorial isométrica no fotoreal; sin personas; sin rostros; "
    "sin logos ni lockup; sin letras incrustadas; SIN obra; SIN oficina técnica; "
    "SIN casco; SIN monitor fotoreal. Paleta turquesa/cian/menta sobre "
    "navy-carbón si el brief no indica otra."
)

_FLASH_MODEL_ALIASES = {
    "nano-banana-2",
    "nano-banana-2-flash",
    "imagen-nano-banana-2-flash",
    "nano-banana-pro-flash",
}
_PRO_MODEL_ALIASES = {"nano-banana-pro", "imagen-nano-banana-2"}
_MYSTIC_MODEL_ALIASES = {"mystic", "realism"}
_TEXT_TO_IMAGE_ASPECT_RATIOS = {
    "1:1",
    "2:3",
    "3:2",
    "4:3",
    "3:4",
    "5:4",
    "4:5",
    "16:9",
    "9:16",
    "21:9",
}
_TEXT_TO_IMAGE_RESOLUTIONS = {"1K", "2K", "4K"}
_MYSTIC_ASPECT_RATIO_ALIASES = {
    "1:1": "square_1_1",
    "4:3": "classic_4_3",
    "3:4": "traditional_3_4",
    "16:9": "widescreen_16_9",
    "9:16": "social_story_9_16",
    "3:2": "standard_3_2",
    "2:3": "portrait_2_3",
    "2:1": "horizontal_2_1",
    "1:2": "vertical_1_2",
    "5:4": "social_5_4",
    "4:5": "social_post_4_5",
}
_MYSTIC_ASPECT_RATIOS = {
    "square_1_1",
    "classic_4_3",
    "traditional_3_4",
    "widescreen_16_9",
    "social_story_9_16",
    "smartphone_horizontal_20_9",
    "smartphone_vertical_9_20",
    "standard_3_2",
    "portrait_2_3",
    "horizontal_2_1",
    "vertical_1_2",
    "social_5_4",
    "social_post_4_5",
}
_MYSTIC_RESOLUTIONS = {"1k", "2k", "4k"}


@dataclass(frozen=True)
class _GenerationTarget:
    model: str
    endpoint: str
    engine: str
    label: str
    mystic_model: Optional[str] = None


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
        "seleccion_imagen": get("Selección imagen"),
    }


def _parse_visual_brief(raw_brief: Any) -> Dict[str, Any]:
    """Parse a Visual brief as YAML without ever forwarding its raw keys.

    Publicaciones has historically accepted free-form text in this property,
    so malformed YAML and non-mapping values deliberately fall back to the
    row's Título + Premisa instead of becoming an error or a raw prompt.
    """
    text = str(raw_brief or "").strip()
    if not text:
        return {}
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()
    try:
        # BaseLoader is intentionally used instead of SafeLoader here: both
        # are non-executable loaders, but BaseLoader preserves scalars as
        # strings. PyYAML's YAML 1.1 resolver otherwise turns an unquoted
        # `aspect_ratio: 4:3` into the sexagesimal integer 243.
        parsed = yaml.load(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key).strip().lower(): value for key, value in parsed.items()}


def _brief_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {item}" for key, item in value.items() if str(item).strip()
        )
    text = str(value).strip()
    if text.lower() in {"null", "~"}:
        return ""
    return text


def _build_prompt(
    fields: Dict[str, Any],
    override_prompt: Optional[str],
    visual_brief: Optional[Dict[str, Any]] = None,
) -> str:
    if override_prompt and str(override_prompt).strip():
        # Preserve the established manual-override contract: an explicit
        # prompt is authoritative and does not receive the editorial suffix.
        return str(override_prompt).strip()[:MAX_PROMPT_CHARS]

    brief = visual_brief if visual_brief is not None else _parse_visual_brief(
        fields.get("visual_brief")
    )
    scene = _brief_text(brief.get("scene"))
    avoid = ""
    if scene:
        base = scene
        avoid = _brief_text(brief.get("avoid"))
    else:
        titulo = str(fields.get("titulo") or "").strip()
        premisa = str(fields.get("premisa") or "").strip()
        base = (
            f"Professional LinkedIn/blog hero for AEC/BIM audience. {titulo}. {premisa}"
        ).strip()

    if not base:
        base = "Editorial hero for an AEC/BIM audience."
    suffix = _ANTI_SLOP_SUFFIX.strip()
    # Keep `avoid` even when `scene` is very long. Cap pathological avoid
    # lists to one third of the API budget, then truncate only the scene/base.
    avoid_clause = ""
    if avoid:
        max_avoid_chars = max(2, (MAX_PROMPT_CHARS - len(suffix)) // 3)
        avoid_clause = f"Evitar: {avoid[:max_avoid_chars].rstrip()}."
    fixed_tail = " ".join(part for part in (avoid_clause, suffix) if part)
    base_budget = MAX_PROMPT_CHARS - len(fixed_tail) - 1
    base = base[:base_budget].rstrip()
    prompt = f"{base} {fixed_tail}".strip()
    return prompt[:MAX_PROMPT_CHARS]


def _normalize_model_alias(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _resolve_generation_target(value: Any) -> _GenerationTarget:
    alias = _normalize_model_alias(value or DEFAULT_MODEL)
    if alias in _FLASH_MODEL_ALIASES:
        return _GenerationTarget(
            model="nano-banana-pro-flash",
            endpoint=NANO_BANANA_FLASH_ENDPOINT,
            engine="flash",
            label="Nano Banana Pro Flash",
        )
    if alias in _PRO_MODEL_ALIASES:
        return _GenerationTarget(
            model="nano-banana-pro",
            endpoint=NANO_BANANA_PRO_ENDPOINT,
            engine="pro",
            label="Nano Banana Pro",
        )
    if alias in _MYSTIC_MODEL_ALIASES:
        return _GenerationTarget(
            model="realism",
            endpoint=MYSTIC_ENDPOINT,
            engine="mystic",
            label="Mystic",
            mystic_model="realism",
        )
    raise ValueError(
        "Unsupported Magnific model alias. Use Nano Banana 2/Flash, "
        "Nano Banana Pro, or explicit Mystic/realism."
    )


def _normalize_generation_params(
    target: _GenerationTarget, aspect_ratio: Any, resolution: Any
) -> tuple[str, str]:
    aspect = str(aspect_ratio or DEFAULT_ASPECT_RATIO).strip()
    resolved_resolution = str(resolution or DEFAULT_RESOLUTION).strip()
    if target.engine == "mystic":
        aspect = _MYSTIC_ASPECT_RATIO_ALIASES.get(aspect, aspect)
        resolved_resolution = resolved_resolution.lower()
        if aspect not in _MYSTIC_ASPECT_RATIOS:
            raise ValueError(f"Unsupported Mystic aspect_ratio: {aspect!r}")
        if resolved_resolution not in _MYSTIC_RESOLUTIONS:
            raise ValueError(
                f"Unsupported Mystic resolution: {resolved_resolution!r}"
            )
        return aspect, resolved_resolution

    if aspect == "classic_4_3":
        aspect = "4:3"
    resolved_resolution = resolved_resolution.upper()
    if aspect not in _TEXT_TO_IMAGE_ASPECT_RATIOS:
        raise ValueError(f"Unsupported Nano Banana aspect_ratio: {aspect!r}")
    if resolved_resolution not in _TEXT_TO_IMAGE_RESOLUTIONS:
        raise ValueError(f"Unsupported Nano Banana resolution: {resolved_resolution!r}")
    return aspect, resolved_resolution


def _config_value(
    input_data: Dict[str, Any], visual_brief: Dict[str, Any], key: str, default: Any
) -> Any:
    input_value = input_data.get(key)
    if input_value is not None and str(input_value).strip():
        return input_value
    brief_value = visual_brief.get(key)
    if _brief_text(brief_value):
        return brief_value
    return default


def _magnific_headers(*, include_content_type: bool = False) -> Dict[str, str]:
    api_key = (config.MAGNIFIC_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError(
            "MAGNIFIC_API_KEY not configured on server (VPS secrets / "
            "~/.config/openclaw/env) — see "
            "docs/ops/magnific-editorial-setup-2026-06-06.md and "
            "docs/ops/editorial-magnific-p22-poller-2026-07-23.md"
        )
    headers = {"x-magnific-api-key": api_key}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _safe_httpx_error_body(exc: httpx.HTTPStatusError) -> str:
    try:
        return _safe_error_text(exc.response.text)
    except Exception:
        return ""


def _safe_error_text(value: Any, limit: int = 300) -> str:
    """Keep diagnostics useful without persisting signed URLs or credentials."""
    text = " ".join(str(value or "").split())
    text = re.sub(r"https?://[^\s\"']+", "[REDACTED_URL]", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:Bearer|Basic)\s+\S+",
        "[REDACTED_AUTH]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:[\"']?[A-Z0-9_.-]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)"
        r"[A-Z0-9_.-]*[\"']?)\s*[:=]\s*"
        r"(?:\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)",
        "[REDACTED_CREDENTIAL]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:gh[pso]_|github_pat_|sk-|ntn_|secret_|ya29\.)[A-Za-z0-9._/-]+",
        "[REDACTED_TOKEN]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}(?:\.[A-Za-z0-9_-]{6,})?\b",
        "[REDACTED_TOKEN]",
        text,
    )
    return text[:limit]


def _request_with_503_retry(
    request_fn: Callable[[], httpx.Response],
    *,
    target: _GenerationTarget,
    operation: str,
) -> httpx.Response:
    """Run one Magnific request, retrying only the documented transient 503."""
    for attempt in range(_MAX_HTTP_503_RETRIES + 1):
        resp = request_fn()
        try:
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if (
                exc.response.status_code == 503
                and attempt < _MAX_HTTP_503_RETRIES
            ):
                time.sleep(_HTTP_503_RETRY_BASE_SEC * (2**attempt))
                continue
            raise RuntimeError(
                f"Magnific {target.label} {operation} error "
                f"{exc.response.status_code}: {_safe_httpx_error_body(exc)}"
            ) from exc
    raise AssertionError("unreachable")


def _submit_generation(
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    target: _GenerationTarget,
) -> str:
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    if target.engine == "flash":
        payload["use_google_search_tool"] = False
    elif target.engine == "mystic":
        payload["model"] = target.mystic_model or "realism"

    with httpx.Client(timeout=_SUBMIT_TIMEOUT_SEC) as client:
        resp = _request_with_503_retry(
            lambda: client.post(
                target.endpoint,
                headers=_magnific_headers(include_content_type=True),
                json=payload,
            ),
            target=target,
            operation="submit",
        )
        data = resp.json()
    task_id = ((data or {}).get("data") or {}).get("task_id")
    if not task_id:
        status = ((data or {}).get("data") or {}).get("status")
        raise RuntimeError(
            f"Magnific {target.label} submit response missing task_id (status={status!r})"
        )
    return str(task_id)


def _poll_generation(task_id: str, target: _GenerationTarget) -> str:
    url = f"{target.endpoint}/{task_id}"
    started = time.monotonic()
    for _attempt in range(_MAX_POLL_ATTEMPTS):
        with httpx.Client(timeout=_POLL_TIMEOUT_SEC) as client:
            resp = _request_with_503_retry(
                lambda: client.get(url, headers=_magnific_headers()),
                target=target,
                operation="poll",
            )
            data = resp.json()
        payload = (data or {}).get("data") or {}
        status = payload.get("status")
        if status == "COMPLETED":
            generated = payload.get("generated") or []
            if not isinstance(generated, list):
                raise RuntimeError(
                    f"Magnific {target.label} task {task_id} COMPLETED with invalid generated shape"
                )
            url_value = next(
                (u.strip() for u in generated if isinstance(u, str) and u.strip()),
                None,
            )
            if not url_value:
                raise RuntimeError(
                    f"Magnific {target.label} task {task_id} COMPLETED without a generated URL"
                )
            parsed_url = urlparse(url_value)
            hostname = (parsed_url.hostname or "").lower()
            if parsed_url.scheme.lower() not in {"http", "https"} or not hostname:
                raise RuntimeError(
                    f"Magnific {target.label} task {task_id} returned an invalid generated URL"
                )
            if hostname == "app.magnific.com" or hostname.endswith(".app.magnific.com"):
                # Mirrors the guard in scripts/editorial/sync_visual_asset_from_selection.py:
                # only direct/exportable URLs are acceptable, never the interactive app URL.
                raise RuntimeError(
                    f"Magnific {target.label} task {task_id} returned an app.magnific.com URL, "
                    "not a direct export"
                )
            return url_value
        if status == "FAILED":
            error = _safe_error_text(payload.get("error") or "upstream task failed", 200)
            raise RuntimeError(f"Magnific {target.label} task {task_id} FAILED: {error}")
        if status not in {"CREATED", "IN_PROGRESS"}:
            raise RuntimeError(
                f"Magnific {target.label} task {task_id} returned unknown status {status!r}"
            )
        time.sleep(_POLL_INTERVAL_SEC)
    elapsed = time.monotonic() - started
    raise RuntimeError(
        f"Magnific {target.label} task {task_id} did not complete within {elapsed:.0f}s "
        f"({_MAX_POLL_ATTEMPTS} attempts)"
    )


def _mystic_target(model: str = "realism") -> _GenerationTarget:
    return _GenerationTarget(
        model=model,
        endpoint=MYSTIC_ENDPOINT,
        engine="mystic",
        label="Mystic",
        mystic_model=model,
    )


def _submit_mystic(prompt: str, aspect_ratio: str, resolution: str, model: str) -> str:
    """Compatibility wrapper retained for legacy callers/tests."""
    return _submit_generation(prompt, aspect_ratio, resolution, _mystic_target(model))


def _poll_mystic(task_id: str) -> str:
    """Compatibility wrapper retained for legacy callers/tests."""
    return _poll_generation(task_id, _mystic_target())


def _generate_one_variant(
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    target: _GenerationTarget,
) -> str:
    task_id = _submit_generation(prompt, aspect_ratio, resolution, target)
    return _poll_generation(task_id, target)


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
            from `Visual brief.scene` + `avoid`, else `Título` + `Premisa`,
            plus the ADR-006 anti-slop suffix. Raw Visual brief YAML is never
            sent to the image model.
        aspect_ratio (str, optional): Magnific aspect_ratio enum value.
            Default "4:3" (Umbral canonical); explicit Mystic normalizes it
            to "classic_4_3".
        resolution (str, optional): Magnific resolution enum ("1K"/"2K"/"4K").
        model (str, optional): Nano Banana Flash/Pro alias, or explicit
            "mystic"/"realism". Default "nano-banana-pro-flash".

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
        raw_count = input_data["count"] if "count" in input_data else DEFAULT_VARIANT_COUNT
        count = int(raw_count)
    except (TypeError, ValueError):
        return {"ok": False, "error": "'count' must be an integer", "publicacion_page_id": page_id}
    if count < 1 or count > 5:
        return {"ok": False, "error": "'count' must be between 1 and 5", "publicacion_page_id": page_id}
    override_prompt = input_data.get("prompt")

    try:
        page = notion_client.get_page(page_id)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read Publicaciones page: {_safe_error_text(e)}",
            "publicacion_page_id": page_id,
        }

    fields = _read_publicacion_fields(page)
    estado = fields["estado_imagen"]
    regeneration_requested = (
        fields.get("seleccion_imagen") == "Regenerar" and estado in _REGENERABLE_STATES
    )

    if estado in _IN_PROGRESS_STATES:
        return {
            "ok": True,
            "skipped": True,
            "reason": "in_progress",
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }
    if estado in _ALREADY_DONE_STATES and not regeneration_requested:
        return {
            "ok": True,
            "skipped": True,
            "already_generated": True,
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }
    if estado not in _ELIGIBLE_STATES and not regeneration_requested:
        return {
            "ok": False,
            "error": f"estado_imagen_not_eligible: {estado!r}",
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    visual_brief = _parse_visual_brief(fields.get("visual_brief"))
    try:
        target = _resolve_generation_target(
            _config_value(input_data, visual_brief, "model", DEFAULT_MODEL)
        )
        aspect_ratio, resolution = _normalize_generation_params(
            target,
            _config_value(input_data, visual_brief, "aspect_ratio", DEFAULT_ASPECT_RATIO),
            _config_value(input_data, visual_brief, "resolution", DEFAULT_RESOLUTION),
        )
    except ValueError as e:
        return {
            "ok": False,
            "error": str(e),
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    prompt = _build_prompt(fields, override_prompt, visual_brief)
    if len(prompt) < 2:
        return {
            "ok": False,
            "error": "Magnific prompt must contain between 2 and 3000 characters",
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_generate": True,
            "count": count,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "model": target.model,
            "endpoint": target.endpoint,
            "use_google_search_tool": False if target.engine == "flash" else None,
            "regeneration_requested": regeneration_requested,
            "estado_imagen": estado,
            "publicacion_page_id": page_id,
        }

    try:
        _magnific_headers()  # raises early if MAGNIFIC_API_KEY missing — before any writes
    except RuntimeError as e:
        return {"ok": False, "error": str(e), "publicacion_page_id": page_id}

    if regeneration_requested:
        transition_props: Dict[str, Any] = {
            "Estado imagen": {"select": {"name": "Regeneración pedida"}},
            "Selección imagen": {"select": {"name": "Pendiente"}},
        }
        try:
            notion_client.update_page_properties(
                page_id_or_url=page_id, properties=transition_props
            )
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to consume 'Regenerar' request: {_safe_error_text(e)}",
                "publicacion_page_id": page_id,
            }

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
            "error": f"Failed to write interim 'Generando' state: {_safe_error_text(e)}",
            "publicacion_page_id": page_id,
        }

    urls: List[str] = []
    failure: Optional[str] = None
    for idx in range(1, count + 1):
        try:
            url = _generate_one_variant(prompt, aspect_ratio, resolution, target)
            urls.append(url)
            logger.info("Magnific variant %d/%d generated for page %s", idx, count, page_id[:8])
        except Exception as e:
            failure = f"alt_{idx}: {_safe_error_text(e, 200)}"
            logger.warning(
                "Magnific variant %d/%d failed for page %s: %s", idx, count, page_id[:8], failure
            )
            break

    if failure or len(urls) < count:
        # Preserve the prior image set atomically. A partial retry may have
        # produced paid URLs, but mixing them with older slots would make
        # imagen_cantidad/date lie and would overwrite reviewed alternatives.
        # Report the partial URLs to the caller, while Notion changes only to
        # Error metadata. A complete production 5/5 replaces all five below.
        error_props: Dict[str, Any] = {
            "Estado imagen": {"select": {"name": "Error"}},
            "imagen_error": {
                "rich_text": [
                    {"text": {"content": (failure or "incomplete_generation")[:2000]}}
                ]
            },
        }
        try:
            notion_client.update_page_properties(
                page_id_or_url=page_id, properties=error_props
            )
        except Exception as e:
            logger.warning(
                "Failed to write Error state for page %s: %s",
                page_id[:8],
                _safe_error_text(e),
            )
        return {
            "ok": False,
            "error": failure or "incomplete_generation",
            "generated": len(urls),
            "requested": count,
            "urls": urls,
            "publicacion_page_id": page_id,
        }

    props: Dict[str, Any] = {
        f"imagen_alt_{i}_url": {"url": u} for i, u in enumerate(urls, start=1)
    }
    props["imagen_cantidad"] = {"number": len(urls)}
    props["imagen_generada_at"] = {"date": {"start": _today_date()}}
    props["Estado imagen"] = {"select": {"name": "Listo para selección"}}
    # Never clear a prior slot. Production's complete 5/5 run naturally
    # overwrites all five; a smaller manual run must not erase the remainder.
    try:
        notion_client.update_page_properties(page_id_or_url=page_id, properties=props)
    except Exception as e:
        write_error = (
            f"Generated {len(urls)} variants but failed to write results: "
            f"{_safe_error_text(e)}"
        )
        # Do not strand the row in the interim `Generando` state forever.
        # Notion property updates are atomic, so this recovery write changes
        # only state/error metadata and never clears the prior image slots.
        recovery_props: Dict[str, Any] = {
            "Estado imagen": {"select": {"name": "Error"}},
            "imagen_error": {
                "rich_text": [{"text": {"content": write_error[:2000]}}]
            },
        }
        try:
            notion_client.update_page_properties(
                page_id_or_url=page_id, properties=recovery_props
            )
        except Exception as recovery_error:
            logger.warning(
                "Failed to recover final Notion write for page %s: %s",
                page_id[:8],
                _safe_error_text(recovery_error),
            )
        return {
            "ok": False,
            "error": write_error,
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
        "model": target.model,
        "endpoint": target.endpoint,
        "estado_imagen": "Listo para selección",
        "publicacion_page_id": page_id,
    }
