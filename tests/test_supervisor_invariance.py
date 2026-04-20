"""
Phase 5 supervisor invariance tests.

These tests prove that the passive supervisor registry/resolver introduced in
PR #234 does not affect envelopes, team routing, or TeamRouter dispatch.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

from dispatcher.health import SystemLevel
from dispatcher.intent_classifier import IntentResult, build_envelope, route_to_team
from dispatcher.queue import TaskQueue
from dispatcher.router import TeamRouter
from dispatcher.supervisor_resolution import load_supervisor_registry, resolve_supervisor
from dispatcher.team_config import get_team_capabilities

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")


def _make_health(vm_online: bool = True) -> MagicMock:
    health = MagicMock()
    health.vm_online = vm_online
    health.level = SystemLevel.NORMAL if vm_online else SystemLevel.PARTIAL
    return health


def _make_queue():
    return TaskQueue(fakeredis.FakeRedis(decode_responses=True))


def _improvement_envelope(task: str = "research.web") -> dict:
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "improvement",
        "task_type": "research",
        "task": task,
        "input": {"query": "phase 5 invariance"},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


def test_build_envelope_does_not_include_supervisor_fields():
    intent = IntentResult(intent="task", confidence="high")
    envelope = build_envelope(
        "revisa mejora continua y ooda",
        comment_id="comment-1234567890",
        intent=intent,
        team="improvement",
    )

    assert envelope["team"] == "improvement"
    assert "supervisor" not in envelope
    assert "supervisor_hint" not in envelope
    assert "supervisor_resolution" not in envelope

    metadata = envelope.get("metadata") or {}
    assert "supervisor" not in metadata
    assert "supervisor_hint" not in metadata
    assert "supervisor_resolution" not in metadata


def test_route_to_team_does_not_consult_supervisor_registry(monkeypatch):
    import dispatcher.supervisor_resolution as supervisor_resolution

    def fail_if_called(*args, **kwargs):
        raise AssertionError("route_to_team must not consult supervisor resolution")

    monkeypatch.setattr(supervisor_resolution, "load_supervisor_registry", fail_if_called)
    monkeypatch.setattr(supervisor_resolution, "resolve_supervisor", fail_if_called)

    assert route_to_team("revisa mejora continua y ooda") == "improvement"


def test_team_router_dispatch_does_not_consult_supervisor_resolver(monkeypatch):
    import dispatcher.supervisor_resolution as supervisor_resolution

    called = {"resolver": False}

    def fail_if_called(*args, **kwargs):
        called["resolver"] = True
        raise AssertionError("TeamRouter.dispatch must not consult supervisor resolution")

    monkeypatch.setattr(supervisor_resolution, "load_supervisor_registry", fail_if_called)
    monkeypatch.setattr(supervisor_resolution, "resolve_supervisor", fail_if_called)

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))

    result = router.dispatch(_improvement_envelope("research.web"))

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1
    assert called["resolver"] is False


def test_improvement_llm_task_still_routes_locally_when_vm_offline():
    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=False))

    result = router.dispatch(_improvement_envelope("research.web"))

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1
    assert queue.blocked_count() == 0


def test_improvement_vm_task_still_blocks_when_vm_offline():
    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=False))

    result = router.dispatch(_improvement_envelope("custom.vm.task"))

    assert result["action"] == "blocked"
    assert queue.pending_count() == 0
    assert queue.blocked_count() == 1
    assert "requires VM" in result["reason"]


def test_team_capabilities_keep_supervisor_as_metadata_only():
    teams = get_team_capabilities()
    improvement = teams["improvement"]

    assert improvement["supervisor"] == "Mejora Continua Supervisor"
    assert "supervisor_hint" not in improvement
    assert "supervisor_resolution" not in improvement
    assert "supervisor_target" not in improvement
    assert "target" not in improvement


def test_real_supervisors_registry_does_not_affect_dispatch_path():
    registry = load_supervisor_registry("config/supervisors.yaml")
    teams = get_team_capabilities()
    resolution = resolve_supervisor("improvement", teams_config=teams, registry=registry)

    assert resolution.resolution_status == "unresolved"
    assert resolution.reason == "status_design_only"
    assert resolution.fallback == "direct"
    assert resolution.should_block is False

    queue = _make_queue()
    router = TeamRouter(queue=queue, health=_make_health(vm_online=True))
    result = router.dispatch(_improvement_envelope("research.web"))

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"
    assert queue.pending_count() == 1


@pytest.mark.parametrize(
    "relative_path",
    [
        "dispatcher/service.py",
        "dispatcher/intent_classifier.py",
    ],
)
def test_runtime_files_do_not_import_supervisor_resolution(relative_path):
    """Phase 5 invariance: supervisor resolution must NOT be consumed by the
    service worker loop or the intent classifier. ``dispatcher/router.py`` is
    the designated integration point since the observability-only wiring
    slice and is covered by ``test_supervisor_runtime_observability_wiring``.
    """
    root = Path(__file__).resolve().parent.parent
    source = (root / relative_path).read_text(encoding="utf-8")

    assert "supervisor_resolution" not in source
