"""Stage 10 publish-safety guard — assert all 6 gates before any LinkedIn POST.

Single chokepoint between the publishing pipeline and any real network
call to a publish target (LinkedIn first; future: X, Notion public, blog).
Every publisher MUST call :func:`assert_can_publish` BEFORE sanitising
payload / refreshing tokens / opening an HTTP client.

Contract (Hilo 6, S10)
----------------------
The 6 gates are evaluated by ``scripts.discovery.lib.gates`` (Hilo 4).
The reason codes below are emitted on block (stable order):

1. ``aprobado_contenido_missing``    — David checkbox `aprobado_contenido` False.
2. ``autorizar_publicacion_missing`` — David checkbox `autorizar_publicacion` False.
3. ``gate_invalidado_active``        — auto/comment-set invalidation flag True.
4. ``fuente_primaria_missing``       — `Fuente primaria` URL empty/unset.
5. ``plataforma_no_seleccionada``    — `Canal` not in {blog, linkedin, x, newsletter}.
6. ``contenido_duplicado``           — ``content_hash`` already in
                                        ``published_history`` (Hilo 3 dedup).

Dependencies (consumed APIs)
----------------------------
* ``scripts.discovery.lib.gates`` (Hilo 4):
    - ``gates.evaluate_gates(notion_page_dict: dict, dedup_check: Callable[[str], bool]) -> GatesStatus``
    - ``gates.can_publish(GatesStatus) -> tuple[bool, list[str]]``
* ``scripts.discovery.lib.dedup`` (Hilo 3):
    - ``dedup.is_duplicate(db_conn, content_hash) -> bool``
    - ``dedup.register_published(db_conn, content_hash, published_url, platform) -> None``

Both modules are imported lazily inside :func:`assert_can_publish` so this
file can be parsed and unit-tested in environments where Hilo 3 has not
yet landed (tests inject a fake ``dedup`` module via ``sys.modules``).

Behaviour
---------
* On pass    → emit ``publish_guard.pass`` to ops_log + return None.
* On block   → emit ``publish_guard.block`` to ops_log + raise
               :class:`PublishBlockedError` with the list of failing reason
               codes.

Cero side-effects beyond the structured log line.
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.discovery.lib.publish_flags import PublishFlags

__all__ = [
    "PublishBlockedError",
    "assert_can_publish",
    "REASON_CODES",
    "DEFAULT_OPS_LOG",
]

# Stable order matches ``gates._GATE_ORDER`` in Hilo 4.
REASON_CODES: tuple[str, ...] = (
    "aprobado_contenido_missing",
    "autorizar_publicacion_missing",
    "gate_invalidado_active",
    "fuente_primaria_missing",
    "plataforma_no_seleccionada",
    "contenido_duplicado",
)

DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"


class PublishBlockedError(Exception):
    """Raised when one or more publish gates fail.

    ``reasons`` is the ordered list of failing reason codes (subset of
    :data:`REASON_CODES`). ``page_id`` and ``content_hash`` are echoed back
    so callers can build operator-facing messages without re-deriving them.
    """

    def __init__(
        self,
        reasons: list[str],
        *,
        page_id: str = "",
        content_hash: str = "",
    ) -> None:
        self.reasons = list(reasons)
        self.page_id = page_id
        self.content_hash = content_hash
        msg = (
            f"publish blocked for page_id={page_id or '?'} "
            f"reasons={self.reasons}"
        )
        super().__init__(msg)


# --------------------------------------------------------------------------- #
# ops_log
# --------------------------------------------------------------------------- #

def _ops_log_path() -> Path:
    """Resolve ops_log path. Honours ``OPS_LOG_PATH`` env override (tests)."""
    override = os.environ.get("OPS_LOG_PATH", "").strip()
    return Path(override) if override else DEFAULT_OPS_LOG


def _emit_log(event: str, **fields: Any) -> None:
    """Append a single JSON line to ops_log. Best-effort; never raises."""
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    rec.update(fields)
    try:
        path = _ops_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        # ops_log is observability, not correctness. Never raise.
        pass


# --------------------------------------------------------------------------- #
# Lazy dependency loaders
# --------------------------------------------------------------------------- #

def _load_module(name: str) -> Any:
    """Import lazily. Honour ``sys.modules`` overrides (tests)."""
    if name in sys.modules:
        return sys.modules[name]
    return importlib.import_module(name)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def assert_can_publish(
    notion_page: dict[str, Any],
    content_hash: str,
    db_conn: sqlite3.Connection,
    flags: PublishFlags | None = None,
) -> None:
    """Raise :class:`PublishBlockedError` if any gate or runtime flag blocks publish.

    Parameters
    ----------
    notion_page
        Raw Notion page object (the one returned by ``GET /v1/pages/{id}``).
        ``properties`` is read by ``gates.evaluate_gates``.
    content_hash
        sha256 over canonical_url + normalized title + excerpt
        (see :func:`scripts.discovery.lib.dedup.compute_content_hash`).
        The hash is injected into the notion-page properties so the
        ``no_duplicado`` gate can be evaluated even when Notion does not
        store the hash yet.
    db_conn
        Open SQLite connection backing ``published_history``.
    flags
        Optional :class:`PublishFlags` snapshot. When supplied AND the
        flags would NOT allow a real publish, this function raises
        :class:`PublishBlockedError` with reasons drawn from
        :meth:`PublishFlags.block_reasons` BEFORE evaluating editorial
        gates or touching the DB. When omitted, behaviour is byte-identical
        to the pre-#405 version (legacy path, covered by
        ``test_publish_guard.py``).

    Side-effects
    ------------
    * Emits exactly one structured log line to ops_log per call:
      - ``publish_guard.runtime_block`` if runtime flags refuse publish.
      - ``publish_guard.pass`` on full success.
      - ``publish_guard.block`` if editorial gates fail.
    * Never writes to ``published_history`` (that is the publisher's job
      via :func:`dedup.register_published` AFTER the real POST succeeds).
    """
    page = dict(notion_page or {})
    page_id = page.get("id", "") or ""

    # Wave 2.A / #405 — runtime stop button.
    #
    # Semantics:
    #   * ``flags is None`` → legacy behaviour, byte-identical to pre-#405
    #     (verified by ``test_call_without_flags_preserves_legacy_behavior``).
    #   * ``flags`` explicit → fail-closed runtime policy. If the flags
    #     would NOT allow a real publish, we refuse here BEFORE evaluating
    #     editorial gates or touching the DB. We emit
    #     ``publish_guard.runtime_block`` and raise ``PublishBlockedError``
    #     with reason codes from :meth:`PublishFlags.block_reasons`.
    #
    # This makes the stop button an active block, not a passive marker.
    if flags is not None and not flags.allows_real_publish():
        runtime_reasons = flags.block_reasons()
        _emit_log(
            "publish_guard.runtime_block",
            page_id=page_id,
            content_hash=content_hash,
            reasons=list(runtime_reasons),
            publish_enabled=flags.publish_enabled,
            dry_run=flags.dry_run,
            max_posts=flags.max_posts,
            max_posts_per_day=flags.max_posts_per_day,
            cross_validation=flags.cross_validation_warnings(),
        )
        raise PublishBlockedError(
            list(runtime_reasons),
            page_id=page_id,
            content_hash=content_hash,
        )

    gates_mod = _load_module("scripts.discovery.lib.gates")
    dedup_mod = _load_module("scripts.discovery.lib.dedup")

    # Inject content_hash into properties so gates.evaluate_gates can read
    # it. Preserve any pre-existing properties dict to avoid clobbering
    # checkboxes / URLs the caller already populated.
    props = dict(page.get("properties") or {})
    if content_hash and not props.get("content_hash"):
        props["content_hash"] = content_hash
    page["properties"] = props

    def _is_dup(h: str) -> bool:
        return bool(dedup_mod.is_duplicate(db_conn, h))

    evaluated = gates_mod.evaluate_gates(page, _is_dup)
    ok, reasons = gates_mod.can_publish(evaluated)

    if ok:
        _emit_log(
            "publish_guard.pass",
            page_id=page_id,
            content_hash=content_hash,
            reasons=[],
        )
        return

    _emit_log(
        "publish_guard.block",
        page_id=page_id,
        content_hash=content_hash,
        reasons=list(reasons),
    )
    raise PublishBlockedError(
        list(reasons), page_id=page_id, content_hash=content_hash
    )
