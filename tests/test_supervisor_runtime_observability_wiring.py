"""
Phase 5 runtime slice: supervisor observability wiring tests.

These tests verify that ``TeamRouter.dispatch()`` wires the Phase 5 passive
foundation (ambiguity signal, supervisor resolution, observability events)
as a non-blocking, improvement-only, observability-only path.

Contract enforced:
- Dispatch behavior is unchanged for every team and every input.
- Only ``team == "improvement"`` triggers any supervisor work.
- Only ambiguous improvement tasks emit observability events.
- Any exception in the supervisor path is swallowed and dispatch continues.
- No OpenClaw, HTTP, or network imports are introduced in ``router.py``.
- The ``supervisor_hint`` envelope field remains absent.
- ``config/supervisors.yaml`` stays at ``design_only``.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_supervisor_runtime_observability_wiring.py -v
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

from dispatcher import ambiguity_signal as _ambiguity_signal_module
from dispatcher import supervisor_resolution as _supervisor_resolution_module
from dispatcher.health import SystemLevel
from dispatcher.intent_classifier import IntentResult, build_envelope
from dispatcher.queue import TaskQueue
from dispatcher.router import TeamRouter
from dispatcher.supervisor_resolution import (
    SupervisorResolution,
    load_supervisor_registry,
)
from dispatcher.team_config import get_team_capabilities

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")


# ── Fixtures / helpers ────────────────────────────────────────────


def _make_health(vm_online: bool = True) -> MagicMock:
    health = MagicMock()
    health.vm_online = vm_online
    health.level = SystemLevel.NORMAL if vm_online else SystemLevel.PARTIAL
    return health


def _make_queue() -> TaskQueue:
    return TaskQueue(fakeredis.FakeRedis(decode_responses=True))


def _improvement_envelope(
    *,
    task: str = "notion.add_comment",
    task_type: str = "general",
    text: str = "revisa la salud del sistema y dime que deberiamos mejorar",
) -> dict:
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "improvement",
        "task_type": task_type,
        "task": task,
        "input": {"text": text, "original_request": text},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


def _delivery_envelope() -> dict:
    """Envelope for a non-improvement team. ``marketing`` has no VM requirement
    and is covered by the existing dispatcher tests.
    """
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "notion.add_comment",
        "input": {"text": "mejora continua todo el marketing", "original_request": "x"},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


class _EventCapturingHandler:
    """Tiny logging handler that collects supervisor observability records."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def __call__(self, record) -> None:  # pragma: no cover - not a real handler
        raise NotImplementedError


def _install_event_sink(monkeypatch) -> list[dict]:
    """Monkeypatch ``TeamRouter._log_supervisor_event`` to capture raw events."""

    captured: list[dict] = []

    def _capture(self, event):
        try:
            captured.append(event.to_log_record())
        except Exception:  # pragma: no cover - defensive only
            captured.append({"error": "to_log_record_failed"})

    monkeypatch.setattr(TeamRouter, "_log_supervisor_event", _capture)
    return captured


# ── 1. Non-improvement team unchanged ─────────────────────────────


def test_non_improvement_team_does_not_trigger_supervisor_path(monkeypatch):
    """Non-improvement envelopes must never reach ambiguity detection or
    supervisor resolution. Dispatch result is identical to today.
    """

    def fail_if_called(*args, **kwargs):
        raise AssertionError("ambiguity detection must not run for non-improvement")

    def fail_if_resolved(*args, **kwargs):
        raise AssertionError("supervisor resolution must not run for non-improvement")

    monkeypatch.setattr(_ambiguity_signal_module, "detect_ambiguity_signal", fail_if_called)
    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", fail_if_resolved)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", fail_if_resolved
    )
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _delivery_envelope()
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "marketing"
    assert queue.pending_count() == 1
    assert captured == []


# ── 2. Concrete improvement task unchanged ────────────────────────


def test_concrete_improvement_task_does_not_resolve_supervisor(monkeypatch):
    """Explicit-handler improvement tasks must not trigger resolution. The
    ambiguity detector is consulted (for observability) but must return
    ``is_ambiguous=False`` because of the explicit handler, so no event is
    emitted and the resolver is never called.
    """

    def fail_if_resolved(*args, **kwargs):
        raise AssertionError("resolver must not run for concrete improvement task")

    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", fail_if_resolved)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", fail_if_resolved
    )
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _improvement_envelope(
        task="system.ooda_report",
        task_type="observability",
        text="corre el ooda report",
    )
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1
    assert captured == []


# ── 3. Ambiguous improvement task emits safe events ───────────────


def test_ambiguous_improvement_task_emits_safe_events(monkeypatch):
    """Ambiguous improvement task must produce both events and must not leak
    raw text. Dispatch result must remain unchanged.
    """

    detect_calls: list[tuple] = []
    resolve_calls: list[tuple] = []

    original_detect = _ambiguity_signal_module.detect_ambiguity_signal
    original_resolve = _supervisor_resolution_module.resolve_supervisor

    def _tracked_detect(*args, **kwargs):
        detect_calls.append((args, kwargs))
        return original_detect(*args, **kwargs)

    def _tracked_resolve(*args, **kwargs):
        resolve_calls.append((args, kwargs))
        return original_resolve(*args, **kwargs)

    monkeypatch.setattr(_ambiguity_signal_module, "detect_ambiguity_signal", _tracked_detect)
    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", _tracked_resolve)
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    raw_text = "revisa la salud del sistema y dime que deberiamos mejorar"
    envelope = _improvement_envelope(text=raw_text)
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1

    assert len(detect_calls) == 1
    assert len(resolve_calls) == 1

    event_types = [rec.get("event_type") for rec in captured]
    assert "supervisor.ambiguity_signal" in event_types
    assert "supervisor.resolution" in event_types
    for rec in captured:
        assert rec.get("team") == "improvement"
        assert rec.get("task_id") == envelope["task_id"]

    # No raw task text must leak into any event record.
    for rec in captured:
        import json as _json

        serialized = _json.dumps(rec, default=str)
        assert raw_text not in serialized
        assert envelope["input"]["text"] not in serialized

    resolution_records = [r for r in captured if r.get("event_type") == "supervisor.resolution"]
    assert resolution_records, "supervisor.resolution event must be emitted"
    for rec in resolution_records:
        fields = rec.get("fields") or {}
        assert fields.get("should_block") is False


# ── 4. Resolver exception does not block dispatch ────────────────


def test_resolver_exception_does_not_block_dispatch(monkeypatch):
    """A raising resolver must be caught. Dispatch result unchanged."""

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic resolver failure")

    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", _boom)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", lambda *a, **k: {}
    )
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    raw_text = "revisa la salud del sistema"
    envelope = _improvement_envelope(text=raw_text)
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1

    # Ambiguity event was emitted before the resolver raised; no resolution event.
    event_types = [rec.get("event_type") for rec in captured]
    assert "supervisor.ambiguity_signal" in event_types
    assert "supervisor.resolution" not in event_types

    # Still no raw text leakage even in the ambiguity event.
    import json as _json

    for rec in captured:
        serialized = _json.dumps(rec, default=str)
        assert raw_text not in serialized


# ── 5. Ambiguity detector exception does not block dispatch ───────


def test_ambiguity_detector_exception_does_not_block_dispatch(monkeypatch):
    """A raising ambiguity detector must be caught. Dispatch result unchanged."""

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic ambiguity failure")

    def fail_if_resolved(*args, **kwargs):
        raise AssertionError("resolver must not run when ambiguity detector fails")

    monkeypatch.setattr(_ambiguity_signal_module, "detect_ambiguity_signal", _boom)
    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", fail_if_resolved)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", fail_if_resolved
    )
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _improvement_envelope(text="revisa la salud del sistema")
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1
    assert captured == []


# ── 6. should_block=True is ignored defensively ───────────────────


def test_should_block_true_is_ignored_and_never_blocks_dispatch(monkeypatch):
    """Even if a synthetic resolver returns should_block=True, dispatch must
    continue unchanged. Observability captures the value for auditing, but
    routing is never affected.
    """

    def _fake_resolve(team, **kwargs):
        return SupervisorResolution(
            team=team,
            supervisor_label="Mejora Continua Supervisor",
            resolution_status="unresolved",
            target_type="openclaw_agent",
            target="improvement-supervisor",
            fallback="direct",
            fallback_used=True,
            should_block=True,  # synthetic: must NOT block routing
            reason="synthetic_should_block",
        )

    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", _fake_resolve)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", lambda *a, **k: {}
    )
    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _improvement_envelope(text="revisa la salud del sistema")
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1
    assert queue.blocked_count() == 0

    resolution_records = [r for r in captured if r.get("event_type") == "supervisor.resolution"]
    assert resolution_records, "resolution event must be emitted"
    fields = resolution_records[0].get("fields") or {}
    # Observability must reflect the synthetic should_block value...
    assert fields.get("should_block") is True
    # ...but routing itself still reached the enqueued path.


# ── 7. No supervisor_hint schema field introduced ─────────────────


def test_envelope_has_no_supervisor_hint_field():
    intent = IntentResult(intent="task", confidence="high")
    envelope = build_envelope(
        "revisa mejora continua y salud del sistema",
        comment_id="comment-0987654321",
        intent=intent,
        team="improvement",
    )

    assert "supervisor_hint" not in envelope
    metadata = envelope.get("metadata") or {}
    assert "supervisor_hint" not in metadata


def test_dispatch_does_not_require_supervisor_hint(monkeypatch):
    """Dispatch must not depend on a ``supervisor_hint`` field in the envelope."""

    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _improvement_envelope(text="revisa la salud del sistema")
    assert "supervisor_hint" not in envelope
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    # Router does not add ``supervisor_hint`` to the envelope.
    assert "supervisor_hint" not in envelope
    # Nothing about ``supervisor_hint`` should appear in emitted event records.
    import json as _json

    for rec in captured:
        serialized = _json.dumps(rec, default=str)
        assert "supervisor_hint" not in serialized


# ── 8. No OpenClaw / network imports in router.py ─────────────────


def test_router_does_not_import_openclaw_or_network_clients():
    """Supervisor observability wiring must not drag OpenClaw, HTTP, or
    webhook clients into the dispatcher router module. AST-level check — we
    accept the words appearing in docstrings or comments (they naturally show
    up when describing the safety contract) but reject any real import.
    """

    router_path = Path(__file__).resolve().parent.parent / "dispatcher" / "router.py"
    source = router_path.read_text(encoding="utf-8")

    tree = ast.parse(source)
    forbidden_roots = {
        "openclaw",
        "httpx",
        "requests",
        "urllib",
        "urllib3",
        "websocket",
        "websockets",
        "aiohttp",
        "socket",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden_roots, (
                    f"router.py must not import '{alias.name}' for supervisor wiring"
                )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            assert module not in forbidden_roots, (
                f"router.py must not import from '{node.module}' for supervisor wiring"
            )


# ── 9. Runtime config stays design_only ───────────────────────────


def test_supervisor_registry_stays_design_only_and_does_not_activate_dispatch(monkeypatch):
    """The on-disk registry must stay at ``design_only`` for improvement.
    Ambiguous improvement dispatch emits observability with
    ``reason=status_design_only`` and never blocks the task.
    """

    registry = load_supervisor_registry()
    improvement = registry.get("supervisors", {}).get("improvement") or {}
    assert improvement.get("status") == "design_only", (
        "improvement supervisor must remain design_only until explicit activation"
    )

    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    envelope = _improvement_envelope(text="revisa la salud del sistema")
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1

    resolution_records = [r for r in captured if r.get("event_type") == "supervisor.resolution"]
    assert resolution_records
    fields = resolution_records[0].get("fields") or {}
    assert fields.get("reason") == "status_design_only"
    assert fields.get("should_block") is False
    assert fields.get("fallback") == "direct"


# ── 10. Blocked improvement task is still unchanged, observability optional ─


def test_blocked_improvement_task_dispatch_is_unchanged(monkeypatch):
    """A VM-required improvement task with VM offline must still be blocked
    exactly as today. Supervisor observability runs *after* the block decision
    and cannot alter the dispatch outcome.
    """

    captured = _install_event_sink(monkeypatch)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=False))

    envelope = _improvement_envelope(
        task="custom.vm.task",
        task_type="general",
        text="revisa la salud del sistema",
    )
    result = router.dispatch(envelope)

    assert result["action"] == "blocked"
    assert queue.blocked_count() == 1
    assert queue.pending_count() == 0
    # Observability runs after the block decision; whether or not it emits,
    # routing is unchanged. Any emitted event must still be about the
    # improvement team and must not include raw text.
    import json as _json

    for rec in captured:
        assert rec.get("team") == "improvement"
        serialized = _json.dumps(rec, default=str)
        assert "revisa la salud del sistema" not in serialized
