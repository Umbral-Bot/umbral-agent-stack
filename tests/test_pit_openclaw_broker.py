"""Tests P10 — runner OpenClaw broker-real (``scripts/pit/pit_broker_run.py``).

Cubren el bridge broker sin binario ``openclaw`` ni Worker: la frontera
subprocess (``OpenClawCli``) se reemplaza por un fake que, en el turno de
``main`` standalone, materializa el cierre broker de cada lane en el vault
(``broker_result.json`` + ``announce.md``), igual que harían los agentes
efímeros tras despachar su ``copilot_cli.run``.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.pit import pit_runner_core as core
from scripts.pit import pit_broker_run as brk
from scripts.pit.pit_broker_run import (
    BROKER_RUN_BLOCKED,
    BROKER_RUN_FAIL,
    BROKER_RUN_PARTIAL,
    BROKER_RUN_PASS,
    BROKER_RUN_PLAN_ONLY,
    GATE_PHRASE,
    OpenClawCli,
    RunBlocked,
    _broker_payload,
    _broker_verdict_for,
    _seed_fake_broker_lane,
    build_broker_lanes,
    build_broker_spawn_prompt,
    exit_code_for,
    load_lane_enrichment,
    main,
    render_broker_role,
    run_broker_tournament,
)
from scripts.pit.pit_spec_validate import load_broker_spec, validate_broker_file

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "examples" / "pit" / "pit_spec.openclaw-broker-v1.yaml"
LANES_PATH = REPO_ROOT / "examples" / "pit" / "pit-openclaw-broker-v1.lanes.yaml"

PIT_ID = "pit-openclaw-broker-v1"
LANE_IDS = ["lane-foundry-tools", "lane-codex-depth", "lane-cost-mini"]


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# scratch pit vault\n", encoding="utf-8")
    (vault / ".gitignore").write_text(".obsidian/workspace.json\n", encoding="utf-8")
    return vault


def _smoke_metrics(
    tmp_path: Path,
    *,
    verdict: str = "PIT_DRY_RUN_PASS",
    pit_id: str = PIT_ID,
    lane_count: int = 3,
    age_hours: float = 0.5,
) -> Path:
    generated = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    path = tmp_path / "smoke-final-metrics.json"
    path.write_text(
        json.dumps(
            {
                "kind": "pit_broker_dry_run_final_metrics",
                "verdict": verdict,
                "pit_id": pit_id,
                "lane_count": lane_count,
                "generated_at": generated.isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return path


def _openclaw_config(tmp_path: Path) -> Path:
    path = tmp_path / "openclaw.json"
    path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {"subagents": {"maxSpawnDepth": 2}},
                    "list": [
                        {
                            "id": "main",
                            "workspace": "/home/rick/.openclaw/workspace",
                            "subagents": {"allowAgents": ["rick-delivery"]},
                        }
                    ],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _spec_and_lanes():
    spec = load_broker_spec(SPEC_PATH)
    enrichment = load_lane_enrichment(LANES_PATH)
    lanes = build_broker_lanes(spec, enrichment=enrichment, batch_id=f"{spec.pit_id}-broker")
    return spec, lanes


class FakeOpenClaw(OpenClawCli):
    """Fake del binario openclaw para el ciclo broker (register→spawn→collect→kill)."""

    def __init__(
        self,
        vault: Path,
        lanes: list[dict],
        *,
        lanes_to_complete: list[str] | None = None,
        spawn_stdout: str = "PIT_SPAWN_FIRED 3",
        spawn_rc: int = 0,
        gateway_rc: int = 0,
    ) -> None:
        super().__init__("openclaw-fake", runner=self._fake_run)
        self.vault = vault
        self.lanes = lanes
        self.lanes_to_complete = (
            LANE_IDS if lanes_to_complete is None else lanes_to_complete
        )
        self.spawn_stdout = spawn_stdout
        self.spawn_rc = spawn_rc
        self.gateway_rc = gateway_rc
        self.live_subagents = [{"id": "task-1", "label": f"{PIT_ID}-lane-foundry-tools"}]
        self.calls: list[list[str]] = []

    def available(self) -> bool:
        return True

    def _fake_run(self, argv, **kwargs):
        args = list(argv[1:])
        self.calls.append(args)
        stdout, rc = "", 0
        if args[:2] == ["gateway", "restart"]:
            rc = self.gateway_rc
        elif args[:2] == ["agent", "--agent"]:
            for lane in self.lanes:
                if lane["lane_id"] in self.lanes_to_complete:
                    _seed_fake_broker_lane(self.vault, PIT_ID, lane)
            stdout, rc = self.spawn_stdout, self.spawn_rc
        elif args[:2] == ["tasks", "list"]:
            stdout = json.dumps(self.live_subagents)
        elif args[:2] == ["subagents", "kill"]:
            rc = 0
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr="")

    def calls_starting(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]


def _run(tmp_path: Path, cli: FakeOpenClaw, vault: Path, **overrides):
    kwargs = {
        "gate": GATE_PHRASE,
        "vault_path": vault,
        "evidence_dir": tmp_path / "evidence",
        "workspaces_root": tmp_path / "workspaces",
        "collect_timeout_seconds": 1.0,
        "collect_poll_seconds": 0.01,
        "cli": cli,
        "lanes_path": LANES_PATH,
    }
    kwargs.update(overrides)
    if "smoke_metrics_path" not in kwargs:
        kwargs["smoke_metrics_path"] = _smoke_metrics(tmp_path)
    if "openclaw_config" not in kwargs:
        kwargs["openclaw_config"] = _openclaw_config(tmp_path)
    return run_broker_tournament(SPEC_PATH, **kwargs)


# ---------------------------------------------------------------------------
# Spec / validator
# ---------------------------------------------------------------------------


def test_broker_spec_validates_with_orchestration():
    result = validate_broker_file(SPEC_PATH)
    assert result["status"] == "pass", result["errors"]
    assert result["schema_version"] == 2
    spec = load_broker_spec(SPEC_PATH)
    assert spec.pit_id == PIT_ID
    assert spec.openclaw_orchestration is not None
    assert spec.openclaw_orchestration.enabled is True
    assert spec.openclaw_orchestration.spawn_from == "main_standalone"
    assert spec.openclaw_orchestration.collect_mode == "broker_announce"


# ---------------------------------------------------------------------------
# Lane materialization + payload + role + spawn prompt
# ---------------------------------------------------------------------------


def test_build_broker_lanes_identity():
    spec, lanes = _spec_and_lanes()
    assert [lane["lane_id"] for lane in lanes] == LANE_IDS
    for lane in lanes:
        assert lane["agent_id"] == f"{PIT_ID}-{lane['lane_id']}"
        assert lane["batch_id"] == f"{PIT_ID}-broker"
        assert lane["max_iterations"] == 1
        assert lane["lane_focus"]


def test_build_broker_lanes_rejects_quote_in_focus():
    spec = load_broker_spec(SPEC_PATH)
    bad = {LANE_IDS[0]: {"lane_focus": 'has "quote" inside'}}
    with pytest.raises(RunBlocked, match="quotes or newlines"):
        build_broker_lanes(spec, enrichment=bad, batch_id="x-broker")


def test_broker_payload_canonical_contract():
    spec, lanes = _spec_and_lanes()
    payload = _broker_payload(spec, lanes[0])
    assert payload["reasoning_effort"] == lanes[0]["reasoning_effort"]
    assert "reasoning_effort" not in payload.get("metadata", {})
    assert payload["dry_run"] is False
    assert payload["prompt"] == lanes[0]["lane_focus"]
    assert payload["repo_path"] == spec.repo_path
    meta = payload["metadata"]
    assert meta["pit_id"] == PIT_ID
    assert meta["lane_id"] == lanes[0]["lane_id"]
    assert meta["agent_id"] == lanes[0]["agent_id"]
    assert meta["batch_id"] == lanes[0]["batch_id"]
    assert meta["iteration"] == 1


def test_render_broker_role_no_leftover_placeholders():
    spec, lanes = _spec_and_lanes()
    role = render_broker_role(spec, lanes[0], worker_url="http://127.0.0.1:8088")
    import re

    leftover = re.findall(r"{{[a-z_]+}}", role)
    assert leftover == [], f"unfilled placeholders: {leftover}"
    assert lanes[0]["lane_id"] in role
    assert PIT_ID in role


def test_spawn_prompt_dispatch_contract():
    spec, lanes = _spec_and_lanes()
    for lane in lanes:
        lane["role"] = render_broker_role(spec, lane, worker_url="http://127.0.0.1:8088")
    prompt = build_broker_spawn_prompt(
        spec, lanes, worker_url="http://127.0.0.1:8088",
        vault=Path("/home/rick/umbral-pit-vault"), lane_timeout_seconds=1800,
    )
    assert "worker-call copilot_cli.run" in prompt
    assert "PIT_SPAWN_FIRED 3" in prompt
    assert "sessions_spawn(" in prompt
    for lane in lanes:
        assert lane["agent_id"] in prompt
    # canonical payload embedded (nested JSON -> quotes are backslash-escaped):
    # assert the field names + values survive rather than exact quoting.
    assert "dry_run" in prompt and "false" in prompt
    assert "reasoning_effort" in prompt
    assert "iteration" in prompt
    assert PIT_ID in prompt
    assert "WORKER_TOKEN" in prompt  # guardrail mention, never the value


# ---------------------------------------------------------------------------
# Verdict + exit code units
# ---------------------------------------------------------------------------


def _state(lane_id: str, complete: bool) -> dict:
    return {"lane_id": lane_id, "broker_complete": complete}


def test_broker_verdict_for():
    three = [_state(l, True) for l in LANE_IDS]
    assert _broker_verdict_for(three, spawn_ok=True) == BROKER_RUN_PASS
    assert _broker_verdict_for(three, spawn_ok=False) == BROKER_RUN_FAIL
    two = [_state(LANE_IDS[0], True), _state(LANE_IDS[1], True), _state(LANE_IDS[2], False)]
    assert _broker_verdict_for(two, spawn_ok=True) == BROKER_RUN_PARTIAL
    one = [_state(LANE_IDS[0], True), _state(LANE_IDS[1], False), _state(LANE_IDS[2], False)]
    assert _broker_verdict_for(one, spawn_ok=True) == BROKER_RUN_FAIL


def test_exit_code_for():
    assert exit_code_for(BROKER_RUN_PASS) == 0
    assert exit_code_for(BROKER_RUN_PLAN_ONLY) == 0
    assert exit_code_for(BROKER_RUN_BLOCKED) == 2
    assert exit_code_for(BROKER_RUN_PARTIAL) == 1
    assert exit_code_for(BROKER_RUN_FAIL) == 1


# ---------------------------------------------------------------------------
# Smoke (no OpenClaw / no Worker)
# ---------------------------------------------------------------------------


def test_smoke_pass(tmp_path: Path):
    metrics = brk.run_broker_smoke(
        SPEC_PATH,
        lanes_path=LANES_PATH,
        vault_path=tmp_path / "scratch",
        evidence_dir=tmp_path / "ev",
    )
    assert metrics["verdict"] == "PIT_DRY_RUN_PASS"
    final = (tmp_path / "ev" / "final-metrics.json")
    assert final.is_file()
    data = json.loads(final.read_text(encoding="utf-8"))
    assert data["verdict"] == "PIT_DRY_RUN_PASS"
    assert data["pit_id"] == PIT_ID
    assert data["lane_count"] == 3


def test_main_smoke(tmp_path: Path):
    rc = main([str(SPEC_PATH), str(LANES_PATH), "--smoke", "--evidence-dir", str(tmp_path / "ev")])
    assert rc == 0


# ---------------------------------------------------------------------------
# Plan-only (gate NOT required) vs real spawn (gate required)
# ---------------------------------------------------------------------------


def test_plan_only_no_gate_required(tmp_path: Path):
    vault = _make_vault(tmp_path)
    cli = FakeOpenClaw(vault, [])
    metrics = _run(tmp_path, cli, vault, gate="", plan_only=True)
    assert metrics["verdict"] == BROKER_RUN_PLAN_ONLY
    assert metrics["plan_only"] is True
    # plan-only renders artifacts but never registers/spawns/kills
    assert "registration" not in metrics
    assert "kill" not in metrics
    assert cli.calls == []
    evidence = tmp_path / "evidence"
    assert (evidence / "spawn-prompt.md").is_file()
    assert (evidence / "agents.yaml").is_file()
    assert (evidence / "run-metrics.json").is_file()


def test_real_spawn_requires_gate(tmp_path: Path):
    vault = _make_vault(tmp_path)
    cli = FakeOpenClaw(vault, [])
    with pytest.raises(RunBlocked, match="gate phrase"):
        _run(tmp_path, cli, vault, gate="", plan_only=False)


def test_real_spawn_all_lanes_pass(tmp_path: Path):
    vault = _make_vault(tmp_path)
    spec, lanes = _spec_and_lanes()
    cli = FakeOpenClaw(vault, lanes)
    metrics = _run(tmp_path, cli, vault)
    assert metrics["verdict"] == BROKER_RUN_PASS
    assert metrics["lanes_completed"] == 3
    # lifecycle: register + spawn + kill + deregister
    assert metrics["registration"]["registered"] == [lane["agent_id"] for lane in lanes]
    assert cli.calls_starting("agent", "--agent")
    assert cli.calls_starting("tasks", "list")
    assert "deregistration" in metrics


def test_real_spawn_partial(tmp_path: Path):
    vault = _make_vault(tmp_path)
    spec, lanes = _spec_and_lanes()
    cli = FakeOpenClaw(vault, lanes, lanes_to_complete=LANE_IDS[:2])
    metrics = _run(tmp_path, cli, vault)
    assert metrics["verdict"] == BROKER_RUN_PARTIAL
    assert metrics["lanes_completed"] == 2


def test_real_spawn_incomplete_fails(tmp_path: Path):
    vault = _make_vault(tmp_path)
    spec, lanes = _spec_and_lanes()
    cli = FakeOpenClaw(vault, lanes, lanes_to_complete=[])
    metrics = _run(tmp_path, cli, vault)
    assert metrics["verdict"] == BROKER_RUN_FAIL
    assert metrics["lanes_completed"] == 0


def test_real_spawn_red_smoke_blocks(tmp_path: Path):
    vault = _make_vault(tmp_path)
    spec, lanes = _spec_and_lanes()
    cli = FakeOpenClaw(vault, lanes)
    with pytest.raises(RunBlocked, match="smoke verdict"):
        _run(
            tmp_path, cli, vault,
            smoke_metrics_path=_smoke_metrics(tmp_path, verdict="PIT_DRY_RUN_FAIL"),
        )


def test_deregister_always_runs_even_if_spawn_fails(tmp_path: Path):
    vault = _make_vault(tmp_path)
    spec, lanes = _spec_and_lanes()
    cli = FakeOpenClaw(vault, lanes, spawn_rc=1)
    metrics = _run(tmp_path, cli, vault)
    assert metrics["verdict"] == BROKER_RUN_FAIL
    # even on spawn failure the ephemerals are killed + deregistered
    assert "kill" in metrics
    assert "deregistration" in metrics
