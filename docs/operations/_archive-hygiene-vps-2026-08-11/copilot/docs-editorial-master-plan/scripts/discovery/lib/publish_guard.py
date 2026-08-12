"""Stage 10 publish-safety guard — assert all 6 gates before any LinkedIn POST.

This module is the single chokepoint between the publishing pipeline and any
real network call to a publish target (LinkedIn first; future: X, Notion
public, blog). Every publisher MUST call :func:`assert_can_publish` BEFORE
sanitising payload / refreshing tokens / opening an HTTP client.

Contract (Hilo 6, S10)
----------------------
6 gates evaluated by ``scripts.discovery.lib.gates`` (Hilo 4 — see
``docs/editorial-pipeline/notion-schema.md``):

1. ``aprobado_contenido``    — David approved content (Notion checkbox).
2. ``aprobado_imagen``       — David approved image (Notion checkbox).
3. ``aprobado_voz``          — Voice match score ≥ threshold (Notion checkbox).
4. ``aprobado_fuente``       — Source verification passed (Notion checkbox).
5. ``validacion_humana``     — Final human go-ahead (Notion checkbox).
6. ``no_duplicado``          — ``content_hash`` not in ``published_history``
                                (Hilo 3 ``dedup.is_duplicate``).

Dependencies (consumed APIs)
----------------------------
* ``scripts.discovery.lib.gates``  — Hilo 4 contract:
    - ``gates.evaluate_gates(notion_page: dict, is_duplicate: Callable[[str], bool]) -> dict[str, bool]``
    - ``gates.can_publish(evaluated: dict[str, bool]) -> tuple[bool, list[str]]``
    The list returned by ``can_publish`` is the names of the gates that
    *failed* (reasons to block).
* ``scripts.discovery.lib.dedup``  — Hilo 3 (already merged):
    - ``dedup.is_duplicate(db_conn, content_hash) -> bool``
    - ``dedup.register_published(db_conn, content_hash, published_url, platform) -> None``

Both modules are imported lazily inside :func:`assert_can_publish` so this
file can be parsed and unit-tested in environments where Hilo 4 has not yet
landed (tests inject a fake ``gates`` module via ``sys.modules``).

Behaviour
---------
* On pass    → emit ``publish_guard.pass`` to ops_log + return None.
* On block   → emit ``publish_guard.block`` to ops_log + raise
               :class:`PublishBlockedError` with the list of failing gate
               names. ``content_hash`` is never logged truncated; ``page_id``
               and timestamps are always included.

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

__all__ = [
    "PublishBlockedError",
    "assert_can_publish",
    "GATE_NAMES",
    "DEFAULT_OPS_LOG",
]

# The 6 canonical gate names (master plan §3). Order matters for stable
# reason-list output. ``no_duplicado`` is appended last because it is the
# only auto-evaluated gate (the other 5 are Notion checkboxes set by David).
GATE_NAMES: tuple[str, ...] = (
    "aprobado_contenido",
    "aprobado_imagen",
    "aprobado_voz",
    "aprobado_fuente",
    "validacion_humana",
    "no_duplicado",
)

DEFAULT_OPS_LOG = Path.home() / ".config" / "umbral" / "ops_log.jsonl"


class PublishBlockedError(Exception):
    """Raised when one or more publish gates fail.

    ``reasons`` is the ordered list of failing gate names (subset of
    :data:`GATE_NAMES`). ``page_id`` and ``content_hash`` are echoed back
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

def _load_gates() -> Any:
    """Import the ``gates`` module lazily.

    Allows tests to inject a fake module via ``sys.modules`` and lets this
    file load cleanly even when Hilo 4 has not yet merged.
    """
    name = "scripts.discovery.lib.gates"
    if name in sys.modules:
        return sys.modules[name]
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:  # pragma: no cover — exercised in CI
        raise ModuleNotFoundError(
            "scripts.discovery.lib.gates is required by publish_guard "
            "(Hilo 4 dependency). Tests must inject a fake module via "
            "sys.modules['scripts.discovery.lib.gates'] = <fake>."
        ) from exc


def _load_dedup() -> Any:
    """Import the ``dedup`` module lazily."""
    name = "scripts.discovery.lib.dedup"
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
) -> None:
    """Raise :class:`PublishBlockedError` if any of the 6 gates fail.

    Parameters
    ----------
    notion_page
        Raw Notion page object (the one returned by ``GET /v1/pages/{id}``).
        ``properties`` is read by ``gates.evaluate_gates``.
    content_hash
        sha256 over canonical_url + normalized title + excerpt
        (see :func:`scripts.discovery.lib.dedup.compute_content_hash`).
        Empty string is treated as "no hash" → ``no_duplicado`` evaluates
        to ``False`` and the publish is blocked.
    db_conn
        Open SQLite connection backing ``published_history``.

    Side-effects
    ------------
    * Emits exactly one structured log line to ops_log:
      ``publish_guard.pass`` on success, ``publish_guard.block`` on failure.
    * Never writes to ``published_history`` (that is the publisher's job
      via :func:`dedup.register_published` AFTER the real POST succeeds).
    """
    page_id = (notion_page or {}).get("id", "") or ""
    gates_mod = _load_gates()
    dedup_mod = _load_dedup()

    # Closure: Hilo 4 contract receives a single-arg callable.
    def _is_dup(h: str) -> bool:
        return bool(dedup_mod.is_duplicate(db_conn, h))

    evaluated = gates_mod.evaluate_gates(notion_page or {}, _is_dup)
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
