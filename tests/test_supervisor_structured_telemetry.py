"""
Phase 6A tests: structured supervisor observability telemetry sink.

These tests verify the end-to-end path introduced by Phase 6A:

  ``TeamRouter.dispatch()``
      → ``_emit_supervisor_observability()``
      → ``_log_supervisor_event()``
      → ``OpsLogger.supervisor_event()``
      → ``ops_log.jsonl``

They assert that ambiguous improvement tasks produce structured JSONL records
in ops_log.jsonl with the stable ``SupervisorObservabilityEvent.to_log_record()``
shape, that non-improvement and concrete improvement tasks produce none, that
dispatch behavior is not altered, that sink failures are swallowed, that
``should_block=True`` is persisted for audit but never affects routing, and
that raw task text and sentinel patterns never reach the sink.

Run with:
    WORKER_TOKEN=test python -m pytest tests/test_supervisor_structured_telemetry.py -v
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

from dispatcher import router as router_module
from dispatcher import supervisor_resolution as _supervisor_resolution_module
from dispatcher.health import SystemLevel
from dispatcher.queue import TaskQueue
from dispatcher.router import TeamRouter
from dispatcher.supervisor_resolution import SupervisorResolution
from infra.ops_logger import OpsLogger

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")


RAW_AMBIGUOUS_TEXT = "revisa la salud del sistema y dime que deberiamos mejorar"
SENTINEL = "TEXTO_SENSIBLE_TELEMETRY_SENTINEL_2026"
FORBIDDEN_RAW_KEYS = ("text", "original_request", "prompt", "query", "question")


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def ops_logger_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OpsLogger:
    """Isolated OpsLogger whose log_dir lives under tmp_path.

    Patches the module-level ``_ops_log`` used by ``TeamRouter`` so the
    sink writes to ``tmp_path / ops_log.jsonl`` instead of the user-level
    ``~/.config/umbral/ops_log.jsonl``.
    """
    logger_instance = OpsLogger(log_dir=tmp_path)
    monkeypatch.setattr(router_module, "_ops_log", logger_instance)
    return logger_instance


@pytest.fixture
def team_router(ops_logger_tmp: OpsLogger) -> TeamRouter:
    queue = TaskQueue(fakeredis.FakeRedis(decode_responses=True))
    health = MagicMock()
    health.vm_online = True
    health.level = SystemLevel.NORMAL
    return TeamRouter(queue=queue, health=health)


def _improvement_envelope(
    *,
    task: str = "notion.add_comment",
    task_type: str = "general",
    text: str = RAW_AMBIGUOUS_TEXT,
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


def _delivery_envelope(text: str = "publica un post en LinkedIn sobre mejora continua") -> dict:
    return {
        "schema_version": "0.1",
        "task_id": str(uuid.uuid4()),
        "team": "marketing",
        "task_type": "writing",
        "task": "notion.add_comment",
        "input": {"text": text, "original_request": text},
        "trace_id": str(uuid.uuid4()),
        "status": "queued",
    }


def _supervisor_records(ops_logger: OpsLogger) -> list[dict]:
    """Return only records whose ``event`` starts with ``supervisor.``."""
    return [
        ev
        for ev in ops_logger.read_events(limit=10_000)
        if isinstance(ev.get("event"), str) and ev["event"].startswith("supervisor.")
    ]


# ── 1. Ambiguous improvement → structured records persisted ──────


def test_ambiguous_improvement_persists_structured_events(
    team_router: TeamRouter, ops_logger_tmp: OpsLogger
):
    envelope = _improvement_envelope()
    result = team_router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"

    records = _supervisor_records(ops_logger_tmp)
    event_types = [r.get("event_type") for r in records]
    assert "supervisor.ambiguity_signal" in event_types
    assert "supervisor.resolution" in event_types

    for rec in records:
        # Stable top-level schema required by monitoring.
        for key in ("event_type", "team", "task_id", "task_type", "outcome", "severity", "fields"):
            assert key in rec, f"missing key {key} in {rec['event_type']}"
        assert rec["team"] == "improvement"
        assert rec["task_id"] == envelope["task_id"]
        # OpsLogger always injects a timestamp.
        assert isinstance(rec.get("ts"), str) and rec["ts"]

    # Resolution field should_block must be False (registry design_only).
    resolution = next(r for r in records if r["event_type"] == "supervisor.resolution")
    assert resolution["fields"].get("should_block") is False


# ── 2. Non-improvement team → no structured records ────────────────


def test_non_improvement_team_persists_no_structured_events(
    team_router: TeamRouter, ops_logger_tmp: OpsLogger
):
    envelope = _delivery_envelope()
    result = team_router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "marketing"

    assert _supervisor_records(ops_logger_tmp) == []


# ── 3. Concrete improvement → no structured records ────────────────


def test_concrete_improvement_task_persists_no_structured_events(
    team_router: TeamRouter, ops_logger_tmp: OpsLogger
):
    envelope = _improvement_envelope(
        task="system.ooda_report",
        task_type="observability",
        text="corre el ooda report",
    )
    result = team_router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert result["team"] == "improvement"

    assert _supervisor_records(ops_logger_tmp) == []


# ── 4. Dispatch return value is semantically identical ─────────────


def test_dispatch_return_value_is_stable_with_and_without_sink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Stripping the structured sink must not alter the dispatch result."""
    envelope_a = _improvement_envelope()

    # Without sink (defensive fallback).
    monkeypatch.setattr(router_module, "_ops_log", None)
    queue_a = TaskQueue(fakeredis.FakeRedis(decode_responses=True))
    health_a = MagicMock()
    health_a.vm_online = True
    health_a.level = SystemLevel.NORMAL
    router_no_sink = TeamRouter(queue=queue_a, health=health_a)
    result_without = router_no_sink.dispatch(dict(envelope_a))

    # With sink.
    sink = OpsLogger(log_dir=tmp_path)
    monkeypatch.setattr(router_module, "_ops_log", sink)
    queue_b = TaskQueue(fakeredis.FakeRedis(decode_responses=True))
    health_b = MagicMock()
    health_b.vm_online = True
    health_b.level = SystemLevel.NORMAL
    router_with_sink = TeamRouter(queue=queue_b, health=health_b)
    result_with = router_with_sink.dispatch(dict(envelope_a))

    # Both must produce the same routing action / team / system_level. We
    # deliberately skip ``queue_stats`` because it reflects the isolated
    # fakeredis queue state, not supervisor behavior.
    for key in ("action", "team", "system_level"):
        assert result_without.get(key) == result_with.get(key), (
            f"dispatch return value diverged on '{key}': "
            f"no_sink={result_without.get(key)} with_sink={result_with.get(key)}"
        )


# ── 5. Sink failure does not block dispatch ────────────────────────


def test_sink_failure_does_not_block_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """If OpsLogger.supervisor_event raises, dispatch must still complete."""

    class _ExplodingOpsLogger:
        def supervisor_event(self, record):
            raise RuntimeError("synthetic sink failure")

    monkeypatch.setattr(router_module, "_ops_log", _ExplodingOpsLogger())

    queue = TaskQueue(fakeredis.FakeRedis(decode_responses=True))
    health = MagicMock()
    health.vm_online = True
    health.level = SystemLevel.NORMAL
    router = TeamRouter(queue=queue, health=health)

    envelope = _improvement_envelope()
    result = router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert queue.pending_count() == 1


# ── 6. should_block=True is persisted for audit, not acted upon ────


def test_should_block_true_is_persisted_but_not_enforced_on_dispatch(
    team_router: TeamRouter,
    ops_logger_tmp: OpsLogger,
    monkeypatch: pytest.MonkeyPatch,
):
    def _fake_resolve(team, **kwargs):
        return SupervisorResolution(
            team=team,
            supervisor_label="Mejora Continua Supervisor",
            resolution_status="unresolved",
            target_type="openclaw_agent",
            target="improvement-supervisor",
            fallback="direct",
            fallback_used=True,
            should_block=True,
            reason="synthetic_should_block",
        )

    monkeypatch.setattr(_supervisor_resolution_module, "resolve_supervisor", _fake_resolve)
    monkeypatch.setattr(
        _supervisor_resolution_module, "load_supervisor_registry", lambda *a, **k: {}
    )

    envelope = _improvement_envelope()
    result = team_router.dispatch(envelope)

    assert result["action"] == "enqueued"
    assert team_router.queue.pending_count() == 1
    assert team_router.queue.blocked_count() == 0

    records = _supervisor_records(ops_logger_tmp)
    resolution = next(r for r in records if r["event_type"] == "supervisor.resolution")
    assert resolution["fields"].get("should_block") is True


# ── 7. No raw text or sentinel leaks into structured events ────────


def test_structured_events_do_not_contain_raw_text_or_sentinel(
    team_router: TeamRouter, ops_logger_tmp: OpsLogger
):
    raw = f"{SENTINEL} {RAW_AMBIGUOUS_TEXT}"
    envelope = _improvement_envelope(text=raw)
    team_router.dispatch(envelope)

    records = _supervisor_records(ops_logger_tmp)
    assert records, "expected at least one structured supervisor event"

    for rec in records:
        blob = json.dumps(rec, default=str, ensure_ascii=False)
        assert SENTINEL not in blob, f"sentinel leaked in {rec['event_type']}"
        assert RAW_AMBIGUOUS_TEXT not in blob, f"raw text leaked in {rec['event_type']}"
        for key in FORBIDDEN_RAW_KEYS:
            assert key not in rec["fields"], f"raw key '{key}' leaked in fields"


# ── 8. Whitelist strictness: unknown keys are dropped ───────────────


def test_sink_drops_unknown_field_keys_and_non_supervisor_event_types(
    tmp_path: Path,
):
    sink = OpsLogger(log_dir=tmp_path)

    # Unknown keys must be dropped.
    sink.supervisor_event({
        "event_type": "supervisor.ambiguity_signal",
        "team": "improvement",
        "task_id": "t-1",
        "task_type": "general",
        "outcome": "ambiguous",
        "severity": "info",
        "fields": {
            "is_ambiguous": True,
            "reason": "positive_keyword_match",
            "text": "raw text should never be persisted",
            "original_request": "also never",
            "prompt": "also never",
            "some_other_key": "should be dropped",
        },
    })

    # Non-supervisor event_type must be rejected.
    sink.supervisor_event({
        "event_type": "task_completed",
        "team": "improvement",
        "fields": {"anything": "here"},
    })

    # Non-mapping payload must be rejected.
    sink.supervisor_event("not a dict")
    sink.supervisor_event(None)

    events = sink.read_events(limit=100)
    assert len(events) == 1
    ev = events[0]
    assert ev["event"] == "supervisor.ambiguity_signal"
    assert set(ev["fields"].keys()) == {"is_ambiguous", "reason"}
    blob = json.dumps(ev, default=str, ensure_ascii=False)
    assert "raw text" not in blob
    assert "also never" not in blob
    assert "should be dropped" not in blob


# ── 9. No forbidden imports in router or monitor script ────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "dispatcher/router.py",
        "scripts/monitor_supervisor_observability.py",
        "infra/ops_logger.py",
    ],
)
def test_forbidden_imports_absent(relative_path: str):
    import ast

    root = Path(__file__).resolve().parent.parent
    source = (root / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "openclaw",
        "httpx",
        "requests",
        "aiohttp",
        "socket",
        "websocket",
        "websockets",
    }
    # `urllib` is permitted only for stdlib usage elsewhere; guard network
    # clients explicitly. The listed names above already cover the concrete
    # HTTP/websocket risks the Phase 6A slice must avoid.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".")[0]
                assert root_name not in forbidden, (
                    f"{relative_path} must not import {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            assert module not in forbidden, (
                f"{relative_path} must not import from {node.module}"
            )


# ── 10. Config and OpenClaw registration invariants preserved ──────


def test_supervisors_yaml_still_design_only():
    from dispatcher.supervisor_resolution import load_supervisor_registry

    registry = load_supervisor_registry()
    improvement = registry.get("supervisors", {}).get("improvement") or {}
    assert improvement.get("status") == "design_only", (
        "Phase 6A must NOT change config/supervisors.yaml status"
    )


def test_openclaw_json_does_not_register_improvement_supervisor():
    """``improvement-supervisor`` must not be registered in openclaw.json."""
    root = Path(__file__).resolve().parent.parent
    openclaw_path = root / "openclaw.json"
    if not openclaw_path.exists():
        pytest.skip("openclaw.json not present in this checkout")
    payload = openclaw_path.read_text(encoding="utf-8")
    assert "improvement-supervisor" not in payload, (
        "improvement-supervisor must not appear in openclaw.json for Phase 6A"
    )
