"""Pure gate evaluation library for S9→S10 publish contract.

Zero HTTP, zero Notion writes, zero side effects. Operates on already-parsed
dicts plus an injected dedup callable. Intended to be used by S10
(``stage10_*``) before any platform publish call.

Public API:

* :class:`GatesStatus` — pydantic snapshot of the 6 mandatory gates.
* :func:`evaluate_gates` — build a :class:`GatesStatus` from a Notion-shaped
  dict + dedup callable.
* :func:`can_publish` — collapse a :class:`GatesStatus` into
  ``(allowed, reasons)``; safe-by-default (any unset gate blocks).

Reason codes (stable, ordered):

1. ``aprobado_contenido_missing``
2. ``autorizar_publicacion_missing``
3. ``gate_invalidado_active``
4. ``fuente_primaria_missing``
5. ``plataforma_no_seleccionada``
6. ``contenido_duplicado``
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field


# Stable order of the 6 contract gates. Used by :func:`can_publish` to keep
# reasons deterministic so callers and tests can rely on ordering.
_GATE_ORDER: tuple[tuple[str, str], ...] = (
    ("aprobado_contenido", "aprobado_contenido_missing"),
    ("autorizar_publicacion", "autorizar_publicacion_missing"),
    ("gate_invalidado", "gate_invalidado_active"),  # inverted: must be False
    ("fuente_primaria_ok", "fuente_primaria_missing"),
    ("plataforma_seleccionada", "plataforma_no_seleccionada"),
    ("no_duplicado", "contenido_duplicado"),
)

_VALID_CHANNELS: frozenset[str] = frozenset({"blog", "linkedin", "x", "newsletter"})


class GatesStatus(BaseModel):
    """Snapshot of the 6 mandatory S9→S10 gates.

    All fields default to a safe-blocking value. ``gate_invalidado`` is the
    only inverted gate: ``True`` means the gate is *invalidated* and publish
    is blocked.
    """

    aprobado_contenido: bool = Field(
        default=False,
        description="David human gate 1: content approved for the channel.",
    )
    autorizar_publicacion: bool = Field(
        default=False,
        description="David human gate 2: publishing authorized.",
    )
    gate_invalidado: bool = Field(
        default=False,
        description=(
            "Inverted gate. True means a human comment or auto-invalidation "
            "(duplicate / source-down) reset the approvals. Blocks publish."
        ),
    )
    fuente_primaria_ok: bool = Field(
        default=False,
        description="Primary source URL present and (caller-asserted) reachable.",
    )
    plataforma_seleccionada: bool = Field(
        default=False,
        description="Canal field is one of the supported platforms.",
    )
    no_duplicado: bool = Field(
        default=False,
        description="Dedup callable confirmed content_hash is not already published.",
    )


def _coerce_checkbox(value: object) -> bool:
    """Best-effort checkbox parsing for Notion-shaped dicts.

    Accepts bare bools, Notion property dicts (``{"checkbox": bool}``) and
    ``None``. Anything else returns ``False`` (safe-blocking).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and "checkbox" in value:
        return bool(value["checkbox"])
    return False


def _coerce_url(value: object) -> str:
    """Best-effort URL extraction.

    Accepts bare strings, Notion property dicts (``{"url": str | None}``)
    and ``None``. Returns empty string when not present.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict) and "url" in value:
        url = value.get("url")
        return url.strip() if isinstance(url, str) else ""
    return ""


def _coerce_select(value: object) -> str:
    """Best-effort select parsing. Returns option name or empty string."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "select" in value and isinstance(value["select"], dict):
            return str(value["select"].get("name") or "")
        if "name" in value:
            return str(value.get("name") or "")
    return ""


def _coerce_text(value: object) -> str:
    """Best-effort plain-text extraction (rich_text or bare str)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        rt = value.get("rich_text")
        if isinstance(rt, list):
            parts = []
            for item in rt:
                if isinstance(item, dict):
                    plain = item.get("plain_text")
                    if isinstance(plain, str):
                        parts.append(plain)
            return "".join(parts)
    return ""


def evaluate_gates(
    notion_page_dict: dict,
    dedup_check: Callable[[str], bool],
) -> GatesStatus:
    """Build a :class:`GatesStatus` from an already-parsed Notion-shaped dict.

    Parameters
    ----------
    notion_page_dict
        A flat dict keyed by Notion property names. Values may be either
        Notion-shaped property dicts (``{"checkbox": bool}``,
        ``{"url": str}``…) or already-coerced primitives. Both layouts are
        accepted so callers can use the cheap path or the raw API path.
    dedup_check
        Callable that returns ``True`` when the given ``content_hash`` is a
        duplicate of an already-published piece. In production this is
        ``lib.dedup.is_duplicate``. Tests inject a stub. When the page has
        no ``content_hash`` the dedup callable is **not** invoked and
        ``no_duplicado`` is left ``False`` (safe-blocking).

    Returns
    -------
    GatesStatus
        Defaults to all-blocking on missing data; never raises on shape.
    """
    props = notion_page_dict.get("properties", notion_page_dict)
    if not isinstance(props, dict):
        props = {}

    aprobado = _coerce_checkbox(props.get("aprobado_contenido"))
    autorizar = _coerce_checkbox(props.get("autorizar_publicacion"))
    invalidado = _coerce_checkbox(props.get("gate_invalidado"))

    fuente_primaria = _coerce_url(props.get("Fuente primaria"))
    fuente_ok = bool(fuente_primaria)

    canal = _coerce_select(props.get("Canal"))
    plataforma_ok = canal in _VALID_CHANNELS

    content_hash = _coerce_text(props.get("content_hash")).strip()
    if content_hash:
        try:
            is_dup = bool(dedup_check(content_hash))
        except Exception:
            # Dedup failures must NOT silently approve. Treat as duplicate.
            is_dup = True
        no_dup = not is_dup
    else:
        # Missing content_hash → cannot prove non-duplication → block.
        no_dup = False

    return GatesStatus(
        aprobado_contenido=aprobado,
        autorizar_publicacion=autorizar,
        gate_invalidado=invalidado,
        fuente_primaria_ok=fuente_ok,
        plataforma_seleccionada=plataforma_ok,
        no_duplicado=no_dup,
    )


def can_publish(gates: GatesStatus) -> tuple[bool, list[str]]:
    """Collapse a :class:`GatesStatus` into ``(allowed, reasons)``.

    Returns ``(True, [])`` when all 6 gates pass. Otherwise returns
    ``(False, [reason_codes])`` in the stable order defined by
    :data:`_GATE_ORDER`.
    """
    reasons: list[str] = []
    for field, code in _GATE_ORDER:
        value = getattr(gates, field)
        if field == "gate_invalidado":
            # Inverted gate.
            if value:
                reasons.append(code)
        else:
            if not value:
                reasons.append(code)
    return (not reasons, reasons)


__all__ = ["GatesStatus", "evaluate_gates", "can_publish"]
