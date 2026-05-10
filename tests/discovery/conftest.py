"""Shared fixtures for discovery-pipeline tests (Hilo 6 / S10).

Provides:
* ``isolate_ops_log`` (autouse) — redirects ops_log writes to a tmp file
  via the ``OPS_LOG_PATH`` env var so tests never touch
  ``~/.config/umbral/ops_log.jsonl``.
* ``install_fake_gates`` (factory) — registers a stub ``gates`` module
  inside ``sys.modules`` so :func:`publish_guard.assert_can_publish` calls
  the fake instead of Hilo 4's real implementation.
* ``install_fake_dedup`` (factory) — same idea for Hilo 3's dedup module.
* Convenience fixtures: ``fake_gates_pass_all``, ``fake_gates_only_dup``,
  ``fake_dedup_no_duplicates``, ``fake_dedup_always_duplicate``.

The fakes mimic the exact API surface the guard depends on:

* ``gates.evaluate_gates(notion_page_dict, dedup_check) -> object`` whose
  attributes match :class:`scripts.discovery.lib.gates.GatesStatus`.
* ``gates.can_publish(status) -> tuple[bool, list[str]]`` returning the
  H4 reason codes in stable order.
* ``dedup.is_duplicate(db_conn, content_hash) -> bool``
* ``dedup.register_published(db_conn, content_hash, published_url, platform) -> None``
* ``dedup.compute_content_hash(canonical_url, title, excerpt) -> str``
"""

from __future__ import annotations

import hashlib
import re
import sys
import types
from pathlib import Path
from typing import Callable

import pytest

# H4 reason codes — must match scripts/discovery/lib/gates.py exactly.
GATE_REASON_CODES: tuple[str, ...] = (
    "aprobado_contenido_missing",
    "autorizar_publicacion_missing",
    "gate_invalidado_active",
    "fuente_primaria_missing",
    "plataforma_no_seleccionada",
    "contenido_duplicado",
)


@pytest.fixture(autouse=True)
def isolate_ops_log(tmp_path, monkeypatch):
    """Redirect publish_guard ops_log writes to a per-test tmp file."""
    log_path = tmp_path / "ops_log.jsonl"
    monkeypatch.setenv("OPS_LOG_PATH", str(log_path))
    return log_path


def _make_gates_status(
    *,
    aprobado_contenido: bool = True,
    autorizar_publicacion: bool = True,
    gate_invalidado: bool = False,
    fuente_primaria_ok: bool = True,
    plataforma_seleccionada: bool = True,
    no_duplicado: bool = True,
):
    """Build a duck-typed GatesStatus equivalent (attrs only)."""
    ns = types.SimpleNamespace(
        aprobado_contenido=aprobado_contenido,
        autorizar_publicacion=autorizar_publicacion,
        gate_invalidado=gate_invalidado,
        fuente_primaria_ok=fuente_primaria_ok,
        plataforma_seleccionada=plataforma_seleccionada,
        no_duplicado=no_duplicado,
    )
    return ns


def _can_publish(status) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not status.aprobado_contenido:
        reasons.append("aprobado_contenido_missing")
    if not status.autorizar_publicacion:
        reasons.append("autorizar_publicacion_missing")
    if status.gate_invalidado:
        reasons.append("gate_invalidado_active")
    if not status.fuente_primaria_ok:
        reasons.append("fuente_primaria_missing")
    if not status.plataforma_seleccionada:
        reasons.append("plataforma_no_seleccionada")
    if not status.no_duplicado:
        reasons.append("contenido_duplicado")
    return (not reasons, reasons)


@pytest.fixture
def install_fake_gates(monkeypatch):
    """Factory: install a fake ``scripts.discovery.lib.gates`` module.

    Usage:
        install_fake_gates(evaluate=my_evaluate_callable)

    where ``my_evaluate_callable(notion_page, dedup_check)`` returns either
    a SimpleNamespace built via :func:`_make_gates_status` or a dict that
    will be passed through ``_make_gates_status(**dict)``.
    """

    def _factory(evaluate: Callable):
        mod = types.ModuleType("scripts.discovery.lib.gates")

        def _evaluate(notion_page, dedup_check):
            result = evaluate(notion_page, dedup_check)
            if isinstance(result, dict):
                return _make_gates_status(**result)
            return result

        mod.evaluate_gates = _evaluate
        mod.can_publish = _can_publish
        monkeypatch.setitem(sys.modules, "scripts.discovery.lib.gates", mod)
        return mod

    return _factory


@pytest.fixture
def fake_gates_pass_all(install_fake_gates):
    """All 6 gates pass (assuming dedup_check returns False)."""

    def _evaluate(notion_page, dedup_check):
        # Honour dedup so dup-blocking tests can still flip no_duplicado.
        props = (notion_page or {}).get("properties") or {}
        h = props.get("content_hash") or ""
        is_dup = bool(dedup_check(h)) if h else False
        return _make_gates_status(no_duplicado=not is_dup)

    install_fake_gates(_evaluate)


@pytest.fixture
def fake_gates_only_dup(install_fake_gates):
    """All Notion gates pass; ``no_duplicado`` driven by dedup callable."""
    return install_fake_gates  # caller composes


@pytest.fixture
def install_fake_dedup(monkeypatch):
    """Factory: install a fake ``scripts.discovery.lib.dedup`` module."""

    _ws = re.compile(r"\s+")

    def _normalize(s: str) -> str:
        if s is None:
            return ""
        if not isinstance(s, str):
            s = str(s)
        return _ws.sub(" ", s.strip().lower())

    def _compute_hash(canonical_url: str, title: str, excerpt: str) -> str:
        s = f"{(canonical_url or '').strip()}\n{_normalize(title)}\n{_normalize(excerpt)}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _factory(*, is_duplicate=lambda db, h: False, register=None):
        mod = types.ModuleType("scripts.discovery.lib.dedup")
        mod.is_duplicate = is_duplicate
        mod.compute_content_hash = _compute_hash
        mod.normalize_text = _normalize
        register_calls: list[tuple] = []

        def _register(db_conn, content_hash, published_url, platform):
            if register is not None:
                register(db_conn, content_hash, published_url, platform)
            register_calls.append(
                (content_hash, published_url, platform)
            )

        mod.register_published = _register
        mod._register_calls = register_calls  # noqa: SLF001 (test-only)
        monkeypatch.setitem(sys.modules, "scripts.discovery.lib.dedup", mod)
        return mod

    return _factory


@pytest.fixture
def fake_dedup_no_duplicates(install_fake_dedup):
    return install_fake_dedup(is_duplicate=lambda db, h: False)


@pytest.fixture
def fake_dedup_always_duplicate(install_fake_dedup):
    return install_fake_dedup(is_duplicate=lambda db, h: True)


@pytest.fixture
def fresh_state_db(tmp_path) -> Path:
    """Empty SQLite file path. Tests open/close their own connections."""
    return tmp_path / "state.sqlite"
