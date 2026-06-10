"""Tests PIT-2b — contratos spawn/collect/kill del runner real (mock openclaw).

Cubren el ciclo completo de ``scripts/pit/pit_tournament_run.py`` sin binario
``openclaw`` ni VPS: la frontera subprocess (``OpenClawCli``) se reemplaza por
un fake que registra las llamadas y simula el trabajo de las lanes escribiendo
los lane result files en el vault (patrón D3.5b).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_runner_core as core
from scripts.pit import pit_tournament_run as run_mod
from scripts.pit.pit_tournament_run import (
    GATE_PHRASE,
    RUN_BLOCKED,
    RUN_FAIL,
    RUN_PARTIAL,
    RUN_PASS,
    RUN_PLAN_ONLY,
    SPAWN_BLOCKED_MARKER,
    OpenClawCli,
    RunBlocked,
    main,
    run_tournament,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SPEC = REPO_ROOT / "examples" / "pit-salud-mental-pilot.yaml"
EXAMPLE_LANES = REPO_ROOT / "examples" / "pit-salud-mental-pilot.lanes.yaml"
RUN_SH = REPO_ROOT / "scripts" / "pit" / "pit_tournament_run.sh"

PIT_ID = "pit-salud-mental-pilot"
LANE_IDS = ["lane-friccion", "lane-nudges", "lane-semaforo"]

_BASH = shutil.which("bash")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path) -> Path:
    """Vault scratch válido para pit_vault_check (README + pit/templates/archive)."""
    vault = tmp_path / "vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# scratch pit vault\n", encoding="utf-8")
    (vault / ".gitignore").write_text(".obsidian/workspace.json\n", encoding="utf-8")
    for template in core.TEMPLATES_DIR.iterdir():
        if template.is_file():
            shutil.copyfile(template, vault / "templates" / template.name)
    return vault


def _smoke_metrics(
    tmp_path: Path,
    *,
    verdict: str = "PIT_DRY_RUN_PASS",
    pit_id: str = PIT_ID,
    lane_count: int = 3,
    age_hours: float = 0.5,
) -> Path:
    """Evidencia de smoke PIT-2 fabricada (lo que deja pit_tournament_dry_run.sh)."""
    generated = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    path = tmp_path / "smoke-final-metrics.json"
    path.write_text(
        json.dumps(
            {
                "kind": "pit_dry_run_final_metrics",
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
    """openclaw.json mínimo con main explícito (como la VPS) + allowAgents D3."""
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
                            "subagents": {"allowAgents": ["rick-delivery", "rick-qa"]},
                        },
                        {"id": "rick-delivery", "workspace": "/home/rick/w"},
                    ],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _complete_lane(vault: Path, lane_id: str, *, factor: float = 0.8) -> None:
    """Simula el trabajo real de una lane: kpi_pack reproducible + announce.md."""
    core.lane_init(vault, PIT_ID, lane_id)
    core.iteration_close(
        vault,
        PIT_ID,
        lane_id,
        1,
        {
            "variable": "taps hasta completar el check-in",
            "statement": "Si bajo los taps, sube checkin_completion",
            "kpi_id": "checkin_completion",
            "validated": True,
        },
        [
            {
                "kpi_id": "checkin_completion",
                "unit": "%",
                "kpi_expected": 60,
                "kpi_achieved": 60 * factor,
                "direction": "increase",
                "weight": 2.0,
                "synthetic": True,
            }
        ],
        prototype_url=f"https://tunnel.invalid/mission-control/{PIT_ID}/{lane_id}",
        synthetic_personas={"used": True, "count": 3},
    )
    announce = core.lane_announce(vault, PIT_ID, lane_id, iteration=1)
    lane_root = vault / "pit" / PIT_ID / "lanes" / lane_id
    (lane_root / "announce.md").write_text(announce["announce"] + "\n", encoding="utf-8")


class FakeOpenClaw(OpenClawCli):
    """Fake del binario openclaw: registra llamadas y simula lanes en el vault."""

    def __init__(
        self,
        vault: Path,
        *,
        lanes_to_complete: list[str] | None = None,
        spawn_stdout: str = "PIT_SPAWN_FIRED 3",
        spawn_rc: int = 0,
        gateway_rc: int = 0,
        live_subagents: list[dict] | None = None,
    ) -> None:
        super().__init__("openclaw-fake", runner=self._fake_run)
        self.vault = vault
        self.lanes_to_complete = LANE_IDS if lanes_to_complete is None else lanes_to_complete
        self.spawn_stdout = spawn_stdout
        self.spawn_rc = spawn_rc
        self.gateway_rc = gateway_rc
        self.live_subagents = live_subagents if live_subagents is not None else [
            {"id": "task-1", "label": f"{PIT_ID}-lane-friccion"},
            {"id": "task-2", "label": "rick-delivery-unrelated"},
        ]
        self.calls: list[list[str]] = []

    def available(self) -> bool:  # el binario no existe en CI — el fake sí
        return True

    def _fake_run(self, argv, **kwargs):
        args = list(argv[1:])
        self.calls.append(args)
        stdout, rc = "", 0
        if args[:2] == ["gateway", "restart"]:
            rc = self.gateway_rc
        elif args[:2] == ["agent", "--agent"]:
            # Turno de main standalone: fan-out + yield. El "trabajo" de las
            # lanes se materializa como archivos en el vault (lane result files).
            for lane_id in self.lanes_to_complete:
                _complete_lane(self.vault, lane_id)
            stdout, rc = self.spawn_stdout, self.spawn_rc
        elif args[:2] == ["tasks", "list"]:
            stdout = json.dumps(self.live_subagents)
        elif args[:2] == ["subagents", "kill"]:
            rc = 0
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr="")

    # accesos cómodos para asserts
    def calls_starting(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]


def _run(tmp_path: Path, cli: FakeOpenClaw, vault: Path, **overrides):
    """run_tournament con defaults de test (timeouts cortos, paths tmp).

    Los defaults con side effects (smoke/config) solo se materializan si el
    test no los trae ya preparados — así un test puede fabricar variantes sin
    que el helper se las pise.
    """
    kwargs = {
        "gate": GATE_PHRASE,
        "vault_path": vault,
        "evidence_dir": tmp_path / "evidence",
        "workspaces_root": tmp_path / "workspaces",
        "collect_timeout_seconds": 1.0,
        "collect_poll_seconds": 0.01,
        "cli": cli,
    }
    kwargs.update(overrides)
    if "smoke_metrics_path" not in kwargs:
        kwargs["smoke_metrics_path"] = _smoke_metrics(tmp_path)
    if "openclaw_config" not in kwargs:
        kwargs["openclaw_config"] = _openclaw_config(tmp_path)
    return run_tournament(EXAMPLE_SPEC, EXAMPLE_LANES, **kwargs)


# ---------------------------------------------------------------------------
# Gates pre-spawn (abort = PIT_RUN_BLOCKED, sin llamadas openclaw)
# ---------------------------------------------------------------------------


class TestPreSpawnGates:
    def test_wrong_gate_phrase_blocks_before_anything(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        with pytest.raises(RunBlocked, match="gate phrase"):
            _run(tmp_path, cli, vault, gate="dale, arranca")
        assert cli.calls == []

    def test_missing_smoke_evidence_blocks(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        with pytest.raises(RunBlocked, match="smoke evidence not found"):
            _run(tmp_path, cli, vault, smoke_metrics_path=tmp_path / "nope.json")
        assert cli.calls == []

    def test_smoke_fail_verdict_blocks(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        smoke = _smoke_metrics(tmp_path, verdict="PIT_DRY_RUN_FAIL")
        with pytest.raises(RunBlocked, match="no spawn with red smoke"):
            _run(tmp_path, cli, vault, smoke_metrics_path=smoke)

    def test_smoke_pit_id_mismatch_blocks(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        smoke = _smoke_metrics(tmp_path, pit_id="pit-otro-torneo")
        with pytest.raises(RunBlocked, match="does not match spec"):
            _run(tmp_path, cli, vault, smoke_metrics_path=smoke)

    def test_smoke_lane_count_mismatch_blocks(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        smoke = _smoke_metrics(tmp_path, lane_count=2)
        with pytest.raises(RunBlocked, match="lane_count"):
            _run(tmp_path, cli, vault, smoke_metrics_path=smoke)

    def test_stale_smoke_blocks(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        smoke = _smoke_metrics(tmp_path, age_hours=30)
        with pytest.raises(RunBlocked, match="stale"):
            _run(tmp_path, cli, vault, smoke_metrics_path=smoke)
        # 0 = sin límite de edad — el mismo smoke viejo pasa el gate.
        metrics = _run(
            tmp_path, cli, vault, smoke_metrics_path=smoke, max_smoke_age_hours=0
        )
        assert metrics["verdict"] == RUN_PASS

    @pytest.mark.parametrize(
        "lanes_yaml, error_match",
        [
            ("lanes:\n  - lane_id: lane-aa\n    lane_focus: x\n", "count mismatch"),
            (
                "lanes:\n"
                "  - {lane_id: lane-aa, lane_focus: x}\n"
                "  - {lane_id: lane-aa, lane_focus: y}\n"
                "  - {lane_id: lane-cc, lane_focus: z}\n",
                "duplicate lane_id",
            ),
            (
                "lanes:\n"
                "  - {lane_id: 'lane-../etc', lane_focus: x}\n"
                "  - {lane_id: lane-bb, lane_focus: y}\n"
                "  - {lane_id: lane-cc, lane_focus: z}\n",
                "lane_id must match",
            ),
            (
                "lanes:\n"
                "  - {lane_id: lane-aa, lane_focus: x}\n"
                "  - {lane_id: lane-bb, lane_focus: ''}\n"
                "  - {lane_id: lane-cc, lane_focus: z}\n",
                "lane_focus is required",
            ),
        ],
    )
    def test_invalid_lanes_file_blocks(self, tmp_path, lanes_yaml, error_match):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        lanes_path = tmp_path / "lanes.yaml"
        lanes_path.write_text(lanes_yaml, encoding="utf-8")
        with pytest.raises(RunBlocked, match=error_match):
            run_tournament(
                EXAMPLE_SPEC,
                lanes_path,
                gate=GATE_PHRASE,
                vault_path=vault,
                evidence_dir=tmp_path / "evidence",
                smoke_metrics_path=_smoke_metrics(tmp_path),
                cli=cli,
            )

    def test_recycled_agent_id_blocks_and_config_untouched(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        config = _openclaw_config(tmp_path)
        loaded = json.loads(config.read_text(encoding="utf-8"))
        # Un efímero de un torneo anterior quedó registrado (no se recicla).
        loaded["agents"]["list"].append({"id": f"{PIT_ID}-lane-friccion"})
        config.write_text(json.dumps(loaded), encoding="utf-8")
        before = config.read_text(encoding="utf-8")
        with pytest.raises(RunBlocked, match="already registered"):
            _run(tmp_path, cli, vault, openclaw_config=config)
        assert config.read_text(encoding="utf-8") == before

    def test_main_exit_code_2_on_blocked(self, tmp_path):
        vault = _make_vault(tmp_path)
        rc = main(
            [
                str(EXAMPLE_SPEC),
                str(EXAMPLE_LANES),
                "--gate",
                "no es la frase",
                "--vault-path",
                str(vault),
                "--evidence-dir",
                str(tmp_path / "evidence"),
            ]
        )
        assert rc == 2


# ---------------------------------------------------------------------------
# Plan-only (validación post-merge VPS sin spawn)
# ---------------------------------------------------------------------------


class TestPlanOnly:
    def test_plan_only_renders_without_touching_runtime(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        metrics = _run(tmp_path, cli, vault, plan_only=True)

        assert metrics["verdict"] == RUN_PLAN_ONLY
        assert cli.calls == []  # ni registro, ni restart, ni spawn
        evidence = tmp_path / "evidence"
        assert (evidence / "spawn-prompt.md").is_file()
        assert (evidence / "agents.yaml").is_file()
        for lane_id in LANE_IDS:
            assert (evidence / "roles" / f"{lane_id}.ROLE.md").is_file()
        # El vault NO se toca en plan-only (ni spec/ ni lanes/).
        assert not (vault / "pit" / PIT_ID).exists()

    def test_plan_only_exit_code_0_via_main(self, tmp_path):
        vault = _make_vault(tmp_path)
        smoke = _smoke_metrics(tmp_path)
        rc = main(
            [
                str(EXAMPLE_SPEC),
                str(EXAMPLE_LANES),
                "--gate",
                GATE_PHRASE,
                "--vault-path",
                str(vault),
                "--evidence-dir",
                str(tmp_path / "evidence"),
                "--smoke-metrics",
                str(smoke),
                "--plan-only",
            ]
        )
        assert rc == 0

    def test_spawn_prompt_contract(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        _run(tmp_path, cli, vault, plan_only=True)
        prompt = (tmp_path / "evidence" / "spawn-prompt.md").read_text(encoding="utf-8")

        assert prompt.count("sessions_spawn(") == 3
        assert SPAWN_BLOCKED_MARKER in prompt  # G-D1b / ISSUE-001
        assert "PIT_SPAWN_FIRED 3" in prompt  # yield tras el fan-out
        for lane_id in LANE_IDS:
            assert f"{PIT_ID}-{lane_id}" in prompt  # agentId efímero por lane
            assert f"pit/{PIT_ID}/lanes/{lane_id}/announce.md" in prompt
        # Guardrails duros en el prompt del parent.
        assert "Magnific" in prompt and "URL pública" in prompt


# ---------------------------------------------------------------------------
# Ciclo completo: register → spawn → collect → kill → deregister
# ---------------------------------------------------------------------------


class TestFullRun:
    def test_all_lanes_complete_pass(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        config = _openclaw_config(tmp_path)
        metrics = _run(tmp_path, cli, vault, openclaw_config=config)

        assert metrics["verdict"] == RUN_PASS
        assert metrics["lanes_completed"] == 3
        for state in metrics["lane_results"]:
            assert state["lane_complete"] is True
            assert state["announce_file_present"] is True
            assert state["incomplete_reasons"] == []
            assert state["announce"].splitlines()[0].startswith("PROTOTYPE_URL=")

    def test_registration_lifecycle_round_trip(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        config = _openclaw_config(tmp_path)
        metrics = _run(tmp_path, cli, vault, openclaw_config=config)

        # Alta registrada en métricas + backup previo al patch.
        registered = metrics["registration"]["registered"]
        assert registered == [f"{PIT_ID}-{lane_id}" for lane_id in LANE_IDS]
        assert Path(metrics["registration"]["backup_path"]).is_file()
        backup = json.loads(
            Path(metrics["registration"]["backup_path"]).read_text(encoding="utf-8")
        )
        assert all(
            entry.get("id") not in registered for entry in backup["agents"]["list"]
        )

        # Workspaces efímeros con el ROLE como AGENTS.md.
        for agent_id in registered:
            role = tmp_path / "workspaces" / agent_id / "AGENTS.md"
            assert role.is_file()
            assert "agente **efímero**" in role.read_text(encoding="utf-8")

        # Al cierre: baja completa — config queda como antes (sin efímeros).
        final = json.loads(config.read_text(encoding="utf-8"))
        final_ids = [entry["id"] for entry in final["agents"]["list"]]
        assert final_ids == ["main", "rick-delivery"]
        main_allow = final["agents"]["list"][0]["subagents"]["allowAgents"]
        assert main_allow == ["rick-delivery", "rick-qa"]
        assert metrics["deregistration"]["entries_removed"] == 3
        # Restart de gateway en alta y en baja.
        assert len(cli.calls_starting("gateway", "restart")) == 2

    def test_spawn_call_targets_main_standalone(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        metrics = _run(tmp_path, cli, vault)

        spawn_calls = cli.calls_starting("agent", "--agent")
        assert len(spawn_calls) == 1
        assert spawn_calls[0][2] == "main"  # G-D1b: spawn parent main standalone
        assert metrics["spawn"]["returncode"] == 0
        assert metrics["spawn"]["fired_marker_seen"] is True
        assert metrics["spawn"]["blocked_issue_001"] is False
        assert Path(metrics["spawn"]["log_path"]).is_file()

    def test_kill_only_tournament_children(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        metrics = _run(tmp_path, cli, vault)

        kill_calls = cli.calls_starting("subagents", "kill")
        assert kill_calls == [["subagents", "kill", "task-1"]]  # nunca task-2 (ajena)
        assert metrics["kill"]["verdict"] == "ok"
        assert metrics["kill"]["killed"][0]["label"] == f"{PIT_ID}-lane-friccion"

    def test_agents_yaml_historical_record(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        metrics = _run(tmp_path, cli, vault)

        vault_agents = vault / "pit" / PIT_ID / "spec" / "agents.yaml"
        assert vault_agents.is_file()
        doc = yaml.safe_load(vault_agents.read_text(encoding="utf-8"))
        assert doc["pit_id"] == PIT_ID
        assert [a["lane_id"] for a in doc["agents"]] == LANE_IDS
        for agent in doc["agents"]:
            assert agent["status"] == "closed"
            assert agent["deregistered"] is True
            assert agent["killed_at"] is not None
            assert agent["scope"].startswith(f"pit/{PIT_ID}/lanes/")
        # Roles renderizados también quedan como histórico en el vault.
        assert (vault / "pit" / PIT_ID / "spec" / "agents" / "lane-friccion.ROLE.md").is_file()
        assert metrics["run_metrics_path"].endswith("run-metrics.json")

    def test_partial_when_one_lane_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault, lanes_to_complete=LANE_IDS[:2])
        metrics = _run(tmp_path, cli, vault)

        assert metrics["verdict"] == RUN_PARTIAL  # judge posible con >=2 completas
        assert metrics["lanes_completed"] == 2
        incomplete = metrics["lane_results"][2]
        assert incomplete["lane_id"] == "lane-semaforo"
        assert incomplete["lane_complete"] is False
        assert incomplete["incomplete_reasons"]
        # El cleanup corre igual con torneo parcial.
        assert metrics["deregistration"]["entries_removed"] == 3

    def test_fail_when_less_than_two_lanes(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault, lanes_to_complete=LANE_IDS[:1])
        metrics = _run(tmp_path, cli, vault)

        assert metrics["verdict"] == RUN_FAIL
        assert metrics["lanes_completed"] == 1

    def test_kpi_pack_without_announce_file_is_incomplete(self, tmp_path):
        """El lane result file es obligatorio: kpi_pack solo no completa la lane."""
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        metrics = _run(tmp_path, cli, vault)
        assert metrics["verdict"] == RUN_PASS  # sanity con announce.md

        vault2 = _make_vault(tmp_path / "second")

        class NoAnnounceFake(FakeOpenClaw):
            def _fake_run(self, argv, **kwargs):
                result = super()._fake_run(argv, **kwargs)
                if list(argv[1:3]) == ["agent", "--agent"]:
                    for lane_id in LANE_IDS:
                        announce = (
                            self.vault / "pit" / PIT_ID / "lanes" / lane_id / "announce.md"
                        )
                        announce.unlink(missing_ok=True)
                return result

        cli2 = NoAnnounceFake(vault2)
        metrics2 = _run(tmp_path / "second", cli2, vault2)
        assert metrics2["verdict"] == RUN_FAIL
        for state in metrics2["lane_results"]:
            assert state["lane_complete"] is False
            assert any("announce.md" in reason for reason in state["incomplete_reasons"])

    def test_spawn_blocked_issue_001_skips_collect_but_cleans_up(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(
            vault, lanes_to_complete=[], spawn_stdout=SPAWN_BLOCKED_MARKER
        )
        config = _openclaw_config(tmp_path)
        metrics = _run(tmp_path, cli, vault, openclaw_config=config)

        assert metrics["verdict"] == RUN_FAIL
        assert metrics["spawn"]["blocked_issue_001"] is True
        assert metrics["lane_results"] == []
        # Cleanup corre igual: baja de efímeros + allowAgents restaurado.
        final = json.loads(config.read_text(encoding="utf-8"))
        assert [entry["id"] for entry in final["agents"]["list"]] == [
            "main",
            "rick-delivery",
        ]

    def test_gateway_restart_failure_still_deregisters(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault, gateway_rc=1)
        config = _openclaw_config(tmp_path)
        with pytest.raises(RunBlocked, match="gateway restart failed"):
            _run(tmp_path, cli, vault, openclaw_config=config)

        # Aunque el restart post-alta falló, el finally desregistró los efímeros.
        final = json.loads(config.read_text(encoding="utf-8"))
        assert [entry["id"] for entry in final["agents"]["list"]] == [
            "main",
            "rick-delivery",
        ]
        assert cli.calls_starting("agent", "--agent") == []  # nunca se spawneó

    def test_allow_agents_wildcard_not_modified(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeOpenClaw(vault)
        config = _openclaw_config(tmp_path)
        loaded = json.loads(config.read_text(encoding="utf-8"))
        loaded["agents"]["list"][0]["subagents"]["allowAgents"] = ["*"]
        config.write_text(json.dumps(loaded), encoding="utf-8")

        metrics = _run(tmp_path, cli, vault, openclaw_config=config)
        assert metrics["registration"]["allow_agents_patched"] == "wildcard"
        final = json.loads(config.read_text(encoding="utf-8"))
        assert final["agents"]["list"][0]["subagents"]["allowAgents"] == ["*"]


@pytest.mark.skipif(_BASH is None, reason="bash not available")
class TestRunShellWrapper:
    def test_wrapper_plan_only(self, tmp_path):
        vault = _make_vault(tmp_path)
        smoke = _smoke_metrics(tmp_path)
        result = subprocess.run(
            [
                _BASH,
                str(RUN_SH),
                str(EXAMPLE_SPEC),
                str(EXAMPLE_LANES),
                "--gate",
                GATE_PHRASE,
                "--plan-only",
                "--vault-path",
                str(vault),
                "--evidence-dir",
                str(tmp_path / "evidence"),
                "--smoke-metrics",
                str(smoke),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert RUN_PLAN_ONLY in result.stdout
        assert (tmp_path / "evidence" / "run-metrics.json").is_file()

    def test_wrapper_blocked_without_smoke(self, tmp_path):
        vault = _make_vault(tmp_path)
        result = subprocess.run(
            [
                _BASH,
                str(RUN_SH),
                str(EXAMPLE_SPEC),
                str(EXAMPLE_LANES),
                "--gate",
                GATE_PHRASE,
                "--plan-only",
                "--vault-path",
                str(vault),
                "--evidence-dir",
                str(tmp_path / "evidence"),
                "--smoke-metrics",
                str(tmp_path / "missing.json"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 2
        assert RUN_BLOCKED in result.stdout
