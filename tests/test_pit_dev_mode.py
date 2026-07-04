"""Tests PIT-DEV — spec v3, workspace curado, cierre dev, security, judges, runner.

Cubren el modo dev completo sin binario ``openclaw`` ni VPS ni red:

- ``PitSpecDev`` (pass/fail por campo) + detección/dispatch v3;
- ``pit_lane_workspace_init`` (tmpdir, git scratch repo);
- guard ``workspace/`` de ``pit_vault_check``;
- ``pit_dev_core``: verify_dev_lane (incl. re-run de tests), egress parse +
  consolidación, veredicto security, scorecards + ranking;
- denegación Magnific (tools.deny en registro + plantillas);
- ``pit_dev_run``: plan-only, gate, ciclo completo con fake openclaw
  (lanes → security → judges → kill/desregistro SIEMPRE).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_dev_core as dev_core
from scripts.pit import pit_dev_run as dev_run
from scripts.pit import pit_tournament_run as run_mod
from scripts.pit.pit_lane_workspace_init import init_workspace
from scripts.pit.pit_spec_validate import (
    PitSpecDev,
    is_dev_spec,
    load_dev_spec,
    validate_dev_file,
)
from scripts.pit.pit_spec_validate import main as validate_main
from scripts.pit.pit_tournament_run import (
    GATE_PHRASE,
    MAGNIFIC_DENY_TOOLS,
    OpenClawCli,
    RunBlocked,
    register_ephemeral_agents,
)
from scripts.pit.pit_vault_check import check_pit_vault

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DEV_SPEC = REPO_ROOT / "examples" / "pit" / "pit_spec.dev-mcp-ide.yaml"
ROLE_DEV_TEMPLATE = (
    REPO_ROOT / "openclaw" / "workspace-templates" / "pit-lane-agent" / "ROLE.template.dev.md"
)
SKILL_MD = (
    REPO_ROOT
    / "openclaw"
    / "workspace-templates"
    / "skills"
    / "product-innovation-tournament"
    / "SKILL.md"
)

PIT_ID = "pit-dev-test"
LANE_IDS = ["lane-alpha", "lane-beta"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dev_spec_dict(**overrides) -> dict:
    spec = {
        "schema_version": 3,
        "mode": "dev",
        "pit_id": PIT_ID,
        "title": "Torneo dev de prueba",
        "problem_statement": "Probar el modo dev end-to-end.",
        "deliverable_spec": "CLI que salude y tenga tests offline.",
        "repo_ref": "HEAD",
        "lane_count": 2,
        "iteration_count": 2,
        "budget_usd": 50,
        "judge_count": 2,
        "security_monitor": "required",
        "traceability": "required",
    }
    spec.update(overrides)
    return {k: v for k, v in spec.items() if v is not None}


def _write_spec(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "pit_spec.dev.yaml"
    path.write_text(yaml.safe_dump(_dev_spec_dict(**overrides)), encoding="utf-8")
    return path


def _write_lanes(tmp_path: Path, lane_ids: list[str] | None = None) -> Path:
    path = tmp_path / "lanes.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "lanes": [
                    {"lane_id": lane_id, "lane_focus": f"ángulo {lane_id}"}
                    for lane_id in (lane_ids or LANE_IDS)
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# scratch pit vault\n", encoding="utf-8")
    (vault / ".gitignore").write_text(".obsidian/workspace.json\n", encoding="utf-8")
    return vault


def _make_scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "scratch-repo"
    (repo / "worker" / "tasks").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "worker" / "app.py").write_text(
        '@app.get("/health")\n@app.post("/run")\n', encoding="utf-8"
    )
    (repo / "worker" / "tasks" / "ping.py").write_text("# ping\n", encoding="utf-8")
    (repo / "docs" / "intro.md").write_text("# docs\n", encoding="utf-8")
    (repo / ".env.example").write_text(
        "WORKER_TOKEN=CHANGE_ME_SECRET\n# NOTION_API_KEY=CHANGE_ME\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )
    return repo


def _lane_root(vault: Path, lane_id: str) -> Path:
    return vault / "pit" / PIT_ID / "lanes" / lane_id


def _write_test_report(
    vault: Path,
    lane_id: str,
    *,
    iteration: int = 1,
    exit_code: int = 0,
    command: list[str] | None = None,
    workdir: str = "deliverable",
) -> Path:
    report = {
        "schema_version": 1,
        "pit_id": PIT_ID,
        "lane_id": lane_id,
        "iteration": iteration,
        "command": command or [sys.executable, "-c", "pass"],
        "workdir": workdir,
        "exit_code": exit_code,
        "total": 3,
        "passed": 3 if exit_code == 0 else 2,
        "failed": 0 if exit_code == 0 else 1,
    }
    path = _lane_root(vault, lane_id) / "iterations" / str(iteration) / "test_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def _write_announce(
    vault: Path,
    lane_id: str,
    *,
    iteration: int = 1,
    self_assessment: str = "0.85",
    lines: list[str] | None = None,
) -> Path:
    if lines is None:
        lines = [
            f"DELIVERABLE_PATH=pit/{PIT_ID}/lanes/{lane_id}/deliverable/",
            f"TEST_REPORT=pit/{PIT_ID}/lanes/{lane_id}/iterations/{iteration}/test_report.json",
            f"SELF_ASSESSMENT={self_assessment}",
        ]
    path = _lane_root(vault, lane_id) / "announce.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_egress(vault: Path, lane_id: str, *, iteration: int = 1) -> Path:
    event = {
        "lane_id": lane_id,
        "iteration": iteration,
        "url_or_query": "https://modelcontextprotocol.io/docs",
        "purpose": "leer la spec MCP",
        "timestamp": "2026-07-03T12:00:00Z",
    }
    path = _lane_root(vault, lane_id) / "iterations" / str(iteration) / "egress.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return path


def _complete_dev_lane(vault: Path, lane_id: str) -> None:
    """Lane dev completa: deliverable + test_report válido + announce + egress."""
    deliverable = _lane_root(vault, lane_id) / "deliverable"
    deliverable.mkdir(parents=True, exist_ok=True)
    (deliverable / "main.py").write_text("print('hola')\n", encoding="utf-8")
    _write_test_report(vault, lane_id)
    _write_egress(vault, lane_id)
    _write_announce(vault, lane_id)


def _scorecard(lane_id: str, judge_id: str, *, score: float = 0.8) -> dict:
    return {
        "schema_version": 2,
        "pit_id": PIT_ID,
        "lane_id": lane_id,
        "judge_id": judge_id,
        "installed_clean": True,
        "ran": True,
        "own_tests_passed": True,
        "meets_functional_spec": True,
        # Hardening post pit-dev-ifc-viewer: true exige evidencia de input real.
        "functional_evidence": {
            "real_input_used": True,
            "input_description": "IFC real 2.4MB (hospital.ifc) — 128 elementos parseados, render OK",
        },
        "criteria": {
            "funcionalidad": score,
            "robustez": score,
            "dx": score,
            "docs": score,
            "testabilidad": score,
        },
    }


def _write_scorecard(vault: Path, lane_id: str, judge_id: str, *, score: float = 0.8) -> Path:
    path = vault / "pit" / PIT_ID / "judge" / "scorecards" / f"{judge_id}--{lane_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_scorecard(lane_id, judge_id, score=score)), encoding="utf-8")
    return path


def _write_security_verdict(vault: Path, lines: list[str]) -> Path:
    path = vault / "pit" / PIT_ID / "security" / "verdict.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
                            "subagents": {"allowAgents": []},
                        }
                    ],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Spec v3 (PitSpecDev) — pass/fail por campo, detección y dispatch CLI
# ---------------------------------------------------------------------------


class TestDevSpecValidate:
    def test_example_spec_passes(self):
        result = validate_dev_file(EXAMPLE_DEV_SPEC)
        assert result["status"] == "pass", result["errors"]
        assert result["spec"]["mode"] == "dev"
        assert result["spec"]["judge_count"] == 2
        assert result["spec"]["security_monitor"] == "required"

    def test_minimal_spec_passes_with_defaults(self, tmp_path):
        spec = load_dev_spec(_write_spec(tmp_path, judge_count=None))
        assert spec.judge_count == 2  # default
        assert spec.rubric_weights.as_dict() == {
            "funcionalidad": 1.0,
            "robustez": 1.0,
            "dx": 1.0,
            "docs": 1.0,
            "testabilidad": 1.0,
        }
        assert spec.budget_per_lane_usd == 25.0

    def test_is_dev_spec_detection(self):
        assert is_dev_spec({"schema_version": 3})
        assert is_dev_spec({"mode": "dev"})
        assert not is_dev_spec({"schema_version": 1, "mode": "product"})
        assert not is_dev_spec({"schema_version": 2, "broker_contract": {}})

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"deliverable_spec": None}, "deliverable_spec"),
            ({"repo_ref": None}, "repo_ref"),
            ({"security_monitor": None}, "security_monitor"),
            ({"security_monitor": "optional"}, "security_monitor"),
            ({"traceability": None}, "traceability"),
            ({"traceability": "no"}, "traceability"),
            ({"judge_count": 0}, "judge_count"),
            ({"judge_count": 6}, "judge_count"),
            ({"budget_usd": 0}, "budget_usd"),
            ({"lane_count": 1}, "lane_count"),
            ({"iteration_count": 1}, "iteration_count"),
            ({"pit_id": "X!"}, "pit_id"),
        ],
    )
    def test_field_failures_report_the_field(self, tmp_path, overrides, field):
        result = validate_dev_file(_write_spec(tmp_path, **overrides))
        assert result["status"] == "fail"
        assert any(field in error for error in result["errors"]), result["errors"]

    def test_rubric_weight_must_be_positive(self, tmp_path):
        result = validate_dev_file(
            _write_spec(tmp_path, rubric_weights={"funcionalidad": 0})
        )
        assert result["status"] == "fail"
        assert any("funcionalidad" in error for error in result["errors"])

    def test_visual_generation_is_forbidden_in_dev_spec(self, tmp_path):
        # Magnific fuera del spec de lanes: extra=forbid lo bloquea de raíz.
        result = validate_dev_file(
            _write_spec(tmp_path, visual_generation={"enabled": True})
        )
        assert result["status"] == "fail"
        assert any("visual_generation" in error for error in result["errors"])

    def test_cli_main_dispatches_dev_spec(self, tmp_path, capsys):
        spec_path = _write_spec(tmp_path)
        assert validate_main([str(spec_path)]) == 0
        out = capsys.readouterr().out
        assert "v3 dev" in out

    def test_cli_main_keeps_v1_path_intact(self, capsys):
        v1 = REPO_ROOT / "examples" / "pit-salud-mental-pilot.yaml"
        assert validate_main([str(v1)]) == 0
        out = capsys.readouterr().out
        assert "v3 dev" not in out and "v2 broker" not in out


# ---------------------------------------------------------------------------
# Workspace curado (FASE 2) — snapshot + CONTEXT_INDEX en tmpdir
# ---------------------------------------------------------------------------


class TestWorkspaceInit:
    def test_init_creates_snapshot_and_context_index(self, tmp_path):
        vault = _make_vault(tmp_path)
        repo = _make_scratch_repo(tmp_path)
        result = init_workspace(
            vault_path=vault,
            repo=repo,
            ref="HEAD",
            pit_id=PIT_ID,
            lane_id="lane-alpha",
            deliverable_spec="CLI de prueba",
        )
        workspace = Path(result["workspace"])
        assert (workspace / "snapshot" / "worker" / "app.py").is_file()
        assert result["snapshot_files"] >= 4
        index = (workspace / "CONTEXT_INDEX.md").read_text(encoding="utf-8")
        assert "GET /health" in index and "POST /run" in index
        assert "`ping`" in index  # task registrada
        assert "WORKER_TOKEN" in index and "NOTION_API_KEY" in index  # nombres
        assert "CHANGE_ME" not in index  # JAMÁS valores
        assert "CLI de prueba" in index  # deliverable_spec copiado
        # deliverable/ pre-creado FUERA del snapshot
        assert Path(result["deliverable_dir"]).is_dir()
        assert "snapshot" not in Path(result["deliverable_dir"]).parts

    def test_init_refuses_overwrite_without_force(self, tmp_path):
        vault = _make_vault(tmp_path)
        repo = _make_scratch_repo(tmp_path)
        kwargs = dict(
            vault_path=vault, repo=repo, ref="HEAD", pit_id=PIT_ID, lane_id="lane-alpha"
        )
        init_workspace(**kwargs)
        with pytest.raises(ValueError, match="already exists"):
            init_workspace(**kwargs)
        init_workspace(**kwargs, force=True)  # con --force reconstruye

    def test_init_rejects_unresolvable_ref(self, tmp_path):
        vault = _make_vault(tmp_path)
        repo = _make_scratch_repo(tmp_path)
        with pytest.raises(ValueError, match="not resolvable"):
            init_workspace(
                vault_path=vault, repo=repo, ref="no-such-tag",
                pit_id=PIT_ID, lane_id="lane-alpha",
            )

    def test_init_rejects_bad_lane_id(self, tmp_path):
        vault = _make_vault(tmp_path)
        repo = _make_scratch_repo(tmp_path)
        with pytest.raises(ValueError, match="lane_id"):
            init_workspace(
                vault_path=vault, repo=repo, ref="HEAD",
                pit_id=PIT_ID, lane_id="not-a-lane",
            )

    def test_vault_check_passes_with_valid_workspace(self, tmp_path):
        vault = _make_vault(tmp_path)
        repo = _make_scratch_repo(tmp_path)
        init_workspace(
            vault_path=vault, repo=repo, ref="HEAD", pit_id=PIT_ID, lane_id="lane-alpha"
        )
        result = check_pit_vault(vault)
        assert result["status"] == "pass", result["errors"]
        assert result["misplaced_workspaces"] == []


class TestVaultWorkspaceGuard:
    @pytest.mark.parametrize(
        "rel",
        ["workspace", f"pit/{PIT_ID}/workspace", f"pit/{PIT_ID}/judge/workspace"],
    )
    def test_misplaced_workspace_fails(self, tmp_path, rel):
        vault = _make_vault(tmp_path)
        (vault / rel).mkdir(parents=True)
        result = check_pit_vault(vault)
        assert result["status"] == "fail"
        assert any("workspace/ only allowed" in error for error in result["errors"])

    def test_nested_workspace_under_valid_one_is_fine(self, tmp_path):
        vault = _make_vault(tmp_path)
        nested = (
            vault / "pit" / PIT_ID / "lanes" / "lane-alpha" / "workspace"
            / "snapshot" / "sub" / "workspace"
        )
        nested.mkdir(parents=True)
        result = check_pit_vault(vault)
        assert result["status"] == "pass", result["errors"]


# ---------------------------------------------------------------------------
# Cierre de lane dev (regla de verdad §3) — verify_dev_lane
# ---------------------------------------------------------------------------


class TestVerifyDevLane:
    def test_complete_lane(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert state["lane_complete"], state["incomplete_reasons"]
        assert state["self_assessment"] == 0.85

    def test_missing_announce_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        (_lane_root(vault, "lane-alpha") / "announce.md").unlink()
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert not state["lane_complete"]
        assert any("announce" in reason for reason in state["incomplete_reasons"])

    def test_empty_deliverable_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        (_lane_root(vault, "lane-alpha") / "deliverable" / "main.py").unlink()
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert not state["lane_complete"]
        assert any("deliverable missing or empty" in r for r in state["incomplete_reasons"])

    def test_nonzero_exit_code_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        _write_test_report(vault, "lane-alpha", exit_code=1)
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert not state["lane_complete"]
        assert any("exit_code" in reason for reason in state["incomplete_reasons"])

    def test_self_assessment_out_of_range_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        _write_announce(vault, "lane-alpha", self_assessment="1.5")
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert not state["lane_complete"]

    def test_report_path_outside_lane_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        _write_announce(
            vault,
            "lane-alpha",
            lines=[
                f"DELIVERABLE_PATH=pit/{PIT_ID}/lanes/lane-alpha/deliverable/",
                f"TEST_REPORT=pit/{PIT_ID}/lanes/lane-beta/iterations/1/test_report.json",
                "SELF_ASSESSMENT=0.9",
            ],
        )
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha")
        assert not state["lane_complete"]
        assert any("must live under" in reason for reason in state["incomplete_reasons"])

    def test_re_run_tests_green(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha", re_run_tests=True)
        assert state["lane_complete"], state["incomplete_reasons"]
        assert state["re_run"]["ok"] and state["re_run"]["returncode"] == 0

    def test_re_run_tests_failing_command_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _complete_dev_lane(vault, "lane-alpha")
        _write_test_report(
            vault,
            "lane-alpha",
            command=[sys.executable, "-c", "import sys; sys.exit(1)"],
        )
        state = dev_core.verify_dev_lane(vault, PIT_ID, "lane-alpha", re_run_tests=True)
        assert not state["lane_complete"]
        assert any("re-run failed" in reason for reason in state["incomplete_reasons"])


# ---------------------------------------------------------------------------
# Egress (FASE 3) — parse + consolidación + veredicto security
# ---------------------------------------------------------------------------


class TestEgress:
    def test_parse_valid_lane_and_judge_events(self, tmp_path):
        path = tmp_path / "egress.jsonl"
        path.write_text(
            json.dumps(
                {
                    "lane_id": "lane-alpha",
                    "iteration": 1,
                    "url_or_query": "https://example.org",
                    "purpose": "docs",
                    "timestamp": "2026-07-03T00:00:00Z",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "judge_id": "judge-1",
                    "url_or_query": "pypi search mcp",
                    "purpose": "verificar dependencia",
                    "timestamp": "2026-07-03T01:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        events, errors = dev_core.parse_egress_file(path)
        assert errors == []
        assert len(events) == 2

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("{not json", "invalid JSON"),
            (json.dumps({"lane_id": "lane-alpha", "iteration": 1}), "missing/empty"),
            (
                json.dumps(
                    {
                        "url_or_query": "x",
                        "purpose": "y",
                        "timestamp": "z",
                    }
                ),
                "needs lane_id or judge_id",
            ),
            (
                json.dumps(
                    {
                        "lane_id": "lane-alpha",
                        "url_or_query": "x",
                        "purpose": "y",
                        "timestamp": "z",
                    }
                ),
                "integer iteration",
            ),
            (
                json.dumps(
                    {
                        "lane_id": "BAD LANE",
                        "iteration": 1,
                        "url_or_query": "x",
                        "purpose": "y",
                        "timestamp": "z",
                    }
                ),
                "invalid lane_id",
            ),
        ],
    )
    def test_parse_malformed_lines_report_errors(self, tmp_path, line, expected):
        path = tmp_path / "egress.jsonl"
        path.write_text(line + "\n", encoding="utf-8")
        events, errors = dev_core.parse_egress_file(path)
        assert events == []
        assert any(expected in error for error in errors), errors

    def test_consolidate_merges_lanes_and_judges(self, tmp_path):
        vault = _make_vault(tmp_path)
        for lane_id in LANE_IDS:
            _write_egress(vault, lane_id)
        judge_egress = vault / "pit" / PIT_ID / "judge" / "judge-1" / "egress.jsonl"
        judge_egress.parent.mkdir(parents=True)
        judge_egress.write_text(
            json.dumps(
                {
                    "judge_id": "judge-1",
                    "url_or_query": "https://example.org",
                    "purpose": "verificación",
                    "timestamp": "2026-07-03T02:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        report = dev_core.consolidate_egress(vault, PIT_ID, LANE_IDS, judge_ids=["judge-1"])
        assert report["events"] == 3
        ledger_lines = Path(report["ledger_path"]).read_text(encoding="utf-8").splitlines()
        assert len(ledger_lines) == 3
        assert all("source_file" in json.loads(line) for line in ledger_lines)

    def test_security_verdict_parse(self, tmp_path):
        vault = _make_vault(tmp_path)
        state = dev_core.security_verdict_state(vault, PIT_ID)
        assert not state["verdict_file_present"]
        _write_security_verdict(
            vault,
            [
                "lane-alpha: EGRESS_CLEAN",
                "lane-beta: EGRESS_FLAGGED(fetch no declarado; purpose vacío)",
            ],
        )
        state = dev_core.security_verdict_state(vault, PIT_ID)
        assert state["verdict_file_present"]
        assert state["lanes"]["lane-alpha"]["verdict"] == "EGRESS_CLEAN"
        assert state["lanes"]["lane-beta"]["verdict"] == "EGRESS_FLAGGED"
        assert state["lanes"]["lane-beta"]["reasons"] == [
            "fetch no declarado",
            "purpose vacío",
        ]


# ---------------------------------------------------------------------------
# Judges (FASE 4) — scorecard schema + ranking agregado
# ---------------------------------------------------------------------------


class TestScorecards:
    def test_valid_scorecard_passes(self, tmp_path):
        vault = _make_vault(tmp_path)
        method = dev_core.validate_scorecard(_scorecard("lane-alpha", "judge-1"), vault)
        assert method in ("jsonschema", "builtin-only")

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            ({"criteria": {"funcionalidad": 1.5, "robustez": 1, "dx": 1, "docs": 1, "testabilidad": 1}}, "within"),
            ({"judge_id": "not-a-judge"}, "judge_id"),
            ({"installed_clean": "yes"}, "installed_clean"),
        ],
    )
    def test_invalid_scorecard_raises(self, tmp_path, mutation, expected):
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        card.update(mutation)
        with pytest.raises(ValueError, match=expected):
            dev_core.validate_scorecard(card, vault)

    def test_missing_criteria_key_raises(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        del card["criteria"]["docs"]
        with pytest.raises(ValueError, match="docs"):
            dev_core.validate_scorecard(card, vault)

    # Hardening post pit-dev-ifc-viewer: jueces laxos — meets_functional_spec
    # true sin evidencia de input REAL invalida el scorecard.
    def test_meets_spec_true_without_evidence_raises(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        del card["functional_evidence"]
        with pytest.raises(ValueError, match="functional_evidence required"):
            dev_core.validate_scorecard(card, vault)

    def test_meets_spec_true_with_synthetic_input_raises(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        card["functional_evidence"]["real_input_used"] = False
        with pytest.raises(ValueError, match="real_input_used must be true"):
            dev_core.validate_scorecard(card, vault)

    def test_meets_spec_true_without_description_raises(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        card["functional_evidence"]["input_description"] = "   "
        with pytest.raises(ValueError, match="input_description required"):
            dev_core.validate_scorecard(card, vault)

    def test_meets_spec_false_needs_no_evidence(self, tmp_path):
        """Un scorecard honesto (spec no cumplido, solo fixture) sigue válido."""
        vault = _make_vault(tmp_path)
        card = _scorecard("lane-alpha", "judge-1")
        card["meets_functional_spec"] = False
        del card["functional_evidence"]
        method = dev_core.validate_scorecard(card, vault)
        assert method in ("jsonschema", "builtin-only")

    def test_collect_scorecards_separates_valid_from_invalid(self, tmp_path):
        vault = _make_vault(tmp_path)
        _write_scorecard(vault, "lane-alpha", "judge-1")
        _write_scorecard(vault, "lane-beta", "judge-1")
        bad = vault / "pit" / PIT_ID / "judge" / "scorecards" / "judge-2--lane-alpha.json"
        bad.write_text("{not json", encoding="utf-8")
        valid, errors = dev_core.collect_scorecards(vault, PIT_ID)
        assert len(valid) == 2
        assert len(errors) == 1

    def test_weighted_score_math(self):
        criteria = {
            "funcionalidad": 1.0,
            "robustez": 0.5,
            "dx": 0.0,
            "docs": 1.0,
            "testabilidad": 1.0,
        }
        weights = {"funcionalidad": 2.0, "robustez": 2.0, "dx": 1.0, "docs": 1.0, "testabilidad": 1.0}
        # (2*1 + 2*0.5 + 1*0 + 1*1 + 1*1) / 7 = 5/7
        assert dev_core.weighted_score(criteria, weights) == round(5 / 7, 4)

    def test_aggregate_ranking_orders_and_notes_do_not_decide(self):
        cards = [
            _scorecard("lane-alpha", "judge-1", score=0.9),
            _scorecard("lane-alpha", "judge-2", score=0.7),
            _scorecard("lane-beta", "judge-1", score=0.6),
            _scorecard("lane-beta", "judge-2", score=0.6),
        ]
        weights = {k: 1.0 for k in ("funcionalidad", "robustez", "dx", "docs", "testabilidad")}
        ranking = dev_core.aggregate_ranking(cards, weights)
        assert [item["lane_id"] for item in ranking] == ["lane-alpha", "lane-beta"]
        assert ranking[0]["rank"] == 1 and ranking[0]["mean_weighted_score"] == 0.8
        assert ranking[0]["judges"] == ["judge-1", "judge-2"]


# ---------------------------------------------------------------------------
# Magnific denial (FASE 6) — registro + plantillas (guard testeable)
# ---------------------------------------------------------------------------


class TestMagnificDenial:
    def test_register_adds_tools_deny_to_every_ephemeral(self, tmp_path):
        config_path = _openclaw_config(tmp_path)
        spec = load_dev_spec(_write_spec(tmp_path))
        lanes = [
            {"lane_id": lane_id, "agent_id": f"{PIT_ID}-{lane_id}", "role": "# r"}
            for lane_id in LANE_IDS
        ]
        register_ephemeral_agents(
            config_path, spec, lanes, workspaces_root=tmp_path / "ws"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        ephemerals = [
            entry
            for entry in config["agents"]["list"]
            if entry["id"].startswith(f"{PIT_ID}-")
        ]
        assert len(ephemerals) == 2
        for entry in ephemerals:
            assert entry["tools"]["deny"] == list(MAGNIFIC_DENY_TOOLS)

    def test_register_deny_coexists_with_tools_profile(self, tmp_path):
        config_path = _openclaw_config(tmp_path)
        spec = load_dev_spec(_write_spec(tmp_path))
        lanes = [{"lane_id": "lane-alpha", "agent_id": f"{PIT_ID}-lane-alpha", "role": "# r"}]
        register_ephemeral_agents(
            config_path,
            spec,
            lanes,
            workspaces_root=tmp_path / "ws",
            lane_tools_profile="minimal",
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = next(
            e for e in config["agents"]["list"] if e["id"] == f"{PIT_ID}-lane-alpha"
        )
        assert entry["tools"]["profile"] == "minimal"
        assert entry["tools"]["deny"] == list(MAGNIFIC_DENY_TOOLS)

    def test_all_role_templates_carry_the_prohibition(self):
        templates_dir = REPO_ROOT / "openclaw" / "workspace-templates" / "pit-lane-agent"
        for name in (
            "ROLE.template.md",
            "ROLE.template.broker.md",
            "ROLE.template.dev.md",
            "ROLE.security-monitor.md",
            "ROLE.judge-dev.md",
            "ROLE.traceability.md",
        ):
            text = (templates_dir / name).read_text(encoding="utf-8")
            assert "Magnific" in text and "PROHIBIDO" in text, name

    def test_skill_has_the_hard_stop(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "Magnific (CUALQUIER modo)" in text
        assert "`lane_blocked`" in text

    def test_rendered_dev_role_has_prohibition_and_no_leftovers(self, tmp_path):
        import re

        spec = load_dev_spec(_write_spec(tmp_path))
        role = dev_run.render_dev_role(
            spec, {"lane_id": "lane-alpha", "lane_focus": "foco"}
        )
        assert "Magnific PROHIBIDO" in role
        assert re.findall(r"{{[a-z_]+}}", role) == []


# ---------------------------------------------------------------------------
# Runner PIT-DEV — plan-only, gate, ciclo completo con fake openclaw
# ---------------------------------------------------------------------------


class FakeDevOpenClaw(OpenClawCli):
    """Fake del binario openclaw para el runner dev: simula lanes/security/judges."""

    def __init__(
        self,
        vault: Path,
        *,
        lanes_to_complete: list[str] | None = None,
        security_verdicts: list[str] | None = None,
        write_verdict: bool = True,
        scorecard_score: float = 0.8,
    ) -> None:
        super().__init__("openclaw-fake", runner=self._fake_run)
        self.vault = vault
        self.lanes_to_complete = LANE_IDS if lanes_to_complete is None else lanes_to_complete
        self.security_verdicts = security_verdicts
        self.write_verdict = write_verdict
        self.scorecard_score = scorecard_score
        self.calls: list[list[str]] = []
        self.stage_messages: dict[str, str] = {}

    def available(self) -> bool:
        return True

    def _fake_run(self, argv, **kwargs):
        args = list(argv[1:])
        self.calls.append(args)
        stdout, rc = "", 0
        if args[:2] == ["gateway", "restart"]:
            rc = 0
        elif args[:2] == ["agent", "--agent"]:
            message = args[4] if len(args) > 4 else ""
            if "fase lanes" in message:
                self.stage_messages["lanes"] = message
                for lane_id in self.lanes_to_complete:
                    _complete_dev_lane(self.vault, lane_id)
                stdout = f"PIT_SPAWN_FIRED {len(self.lanes_to_complete)}"
            elif "fase security" in message:
                self.stage_messages["security"] = message
                if self.write_verdict:
                    verdicts = self.security_verdicts or [
                        f"{lane_id}: EGRESS_CLEAN" for lane_id in LANE_IDS
                    ]
                    _write_security_verdict(self.vault, verdicts)
                stdout = "PIT_SPAWN_FIRED 1"
            elif "fase judges" in message:
                self.stage_messages["judges"] = message
                eligible = [
                    lane_id
                    for lane_id in LANE_IDS
                    if lane_id in message
                ]
                for judge_id in ("judge-1", "judge-2"):
                    for lane_id in eligible:
                        _write_scorecard(
                            self.vault, lane_id, judge_id, score=self.scorecard_score
                        )
                stdout = "PIT_SPAWN_FIRED 2"
            else:
                stdout = "PIT_SPAWN_FIRED 0"
        elif args[:2] == ["tasks", "list"]:
            stdout = json.dumps(
                [
                    {"id": "t1", "label": f"{PIT_ID}-lane-alpha"},
                    {"id": "t2", "label": f"{PIT_ID}-security"},
                    {"id": "t3", "label": f"{PIT_ID}-judge-1"},
                    {"id": "t4", "label": "rick-delivery-unrelated"},
                ]
            )
        elif args[:2] == ["subagents", "kill"]:
            rc = 0
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr="")


def _run_dev(tmp_path: Path, cli, vault: Path, **overrides):
    kwargs = {
        "gate": GATE_PHRASE,
        "repo": overrides.pop("repo", None) or _make_scratch_repo(tmp_path),
        "vault_path": vault,
        "evidence_dir": tmp_path / "evidence",
        "workspaces_root": tmp_path / "workspaces",
        "collect_timeout_seconds": 1.0,
        "collect_poll_seconds": 0.01,
        "security_timeout_seconds": 1.0,
        "judge_timeout_seconds": 1.0,
        "cli": cli,
    }
    kwargs.update(overrides)
    if "openclaw_config" not in kwargs:
        kwargs["openclaw_config"] = _openclaw_config(tmp_path)
    spec_path = kwargs.pop("spec_path", None) or _write_spec(tmp_path)
    lanes_path = kwargs.pop("lanes_path", None) or _write_lanes(tmp_path)
    return dev_run.run_dev_tournament(spec_path, lanes_path, **kwargs)


class TestDevRunner:
    def test_wrong_gate_blocks_before_anything(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(vault)
        with pytest.raises(RunBlocked, match="gate phrase"):
            _run_dev(tmp_path, cli, vault, gate="dale")
        assert cli.calls == []

    def test_plan_only_renders_all_roles_without_spawn(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(vault)
        metrics = _run_dev(tmp_path, cli, vault, plan_only=True)
        assert metrics["verdict"] == "PIT_RUN_PLAN_ONLY"
        assert cli.calls == []
        roles = {p.name for p in (tmp_path / "evidence" / "roles").iterdir()}
        assert roles == {
            "lane-alpha.ROLE.md",
            "lane-beta.ROLE.md",
            "security.ROLE.md",
            "judge-1.ROLE.md",
            "judge-2.ROLE.md",
        }

    def test_full_cycle_pass(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(vault)
        metrics = _run_dev(tmp_path, cli, vault)
        assert metrics["verdict"] == "PIT_RUN_PASS"
        assert metrics["lanes_completed"] == 2
        assert metrics["judge_gate"]["eligible"] == LANE_IDS
        assert metrics["judges"]["scorecards_valid"] == 4
        ranking_path = Path(metrics["judges"]["ranking_path"])
        assert ranking_path.is_file()
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        assert "NO decide" in ranking["note"]
        # spec + lanes.yaml persistidos en el vault (cadena de trazabilidad)
        assert (vault / "pit" / PIT_ID / "spec" / "pit_spec.yaml").is_file()
        assert (vault / "pit" / PIT_ID / "spec" / "lanes.yaml").is_file()
        # workspaces curados creados por lane
        for lane_id in LANE_IDS:
            assert (
                vault / "pit" / PIT_ID / "lanes" / lane_id / "workspace" / "CONTEXT_INDEX.md"
            ).is_file()
        # kill con prefijo del torneo COMPLETO (lanes + security + judges)
        killed = [k for k in metrics["kill"]["killed"]]
        assert {k["label"] for k in killed} == {
            f"{PIT_ID}-lane-alpha",
            f"{PIT_ID}-security",
            f"{PIT_ID}-judge-1",
        }
        # desregistro SIEMPRE — el config vuelve a quedar sin efímeros
        config = json.loads(
            (tmp_path / "openclaw.json").read_text(encoding="utf-8")
        )
        ids = {entry["id"] for entry in config["agents"]["list"]}
        assert ids == {"main"}
        assert metrics["deregistration"]["entries_removed"] == 5
        # token ledger (billing truth): el runner deja el ledger en el vault
        ledger = metrics["token_ledger"]
        assert ledger["ok"] is True
        ledger_path = Path(ledger["path"])
        assert ledger_path.is_file()
        assert ledger_path == vault / "pit" / PIT_ID / "metrics" / "token_ledger.yaml"

    def test_flagged_lane_excluded_from_judges_by_default(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(
            vault,
            security_verdicts=[
                "lane-alpha: EGRESS_CLEAN",
                "lane-beta: EGRESS_FLAGGED(fetch no declarado)",
            ],
        )
        metrics = _run_dev(tmp_path, cli, vault)
        assert metrics["judge_gate"]["eligible"] == ["lane-alpha"]
        assert metrics["judge_gate"]["flagged"] == ["lane-beta"]
        # <2 elegibles ⇒ judges no corren (fail-closed) ⇒ no PASS
        assert metrics["judges"] == {"ran": False}
        assert metrics["verdict"] == "PIT_RUN_PARTIAL"

    def test_flagged_lane_included_with_explicit_decision(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(
            vault,
            security_verdicts=[
                "lane-alpha: EGRESS_CLEAN",
                "lane-beta: EGRESS_FLAGGED(fetch no declarado)",
            ],
        )
        metrics = _run_dev(
            tmp_path, cli, vault,
            judge_flagged_lanes_reason="Rick: divergencia revisada, benigna",
        )
        assert sorted(metrics["judge_gate"]["eligible"]) == LANE_IDS
        decision = metrics["judge_gate"]["flagged_decision"]
        assert decision["included_flagged_lanes"] == ["lane-beta"]
        assert "Rick" in decision["reason"]
        assert metrics["verdict"] == "PIT_RUN_PASS"

    def test_missing_security_verdict_fails_closed(self, tmp_path):
        vault = _make_vault(tmp_path)
        cli = FakeDevOpenClaw(vault, write_verdict=False)
        metrics = _run_dev(tmp_path, cli, vault, security_timeout_seconds=0.05)
        assert metrics["judge_gate"]["eligible"] == []
        assert metrics["judge_gate"]["missing_verdict"] == LANE_IDS
        assert metrics["judges"] == {"ran": False}
        assert metrics["verdict"] == "PIT_RUN_PARTIAL"

    def test_dispatch_from_v1_runner_cli(self, tmp_path, capsys):
        # pit_tournament_run.main detecta el spec dev y delega (plan-only).
        vault = _make_vault(tmp_path)
        spec_path = _write_spec(tmp_path)
        lanes_path = _write_lanes(tmp_path)
        rc = run_mod.main(
            [
                str(spec_path),
                str(lanes_path),
                "--gate",
                GATE_PHRASE,
                "--plan-only",
                "--vault-path",
                str(vault),
                "--evidence-dir",
                str(tmp_path / "ev"),
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "delegating to pit_dev_run" in out
        assert "PIT_RUN_PLAN_ONLY" in out

    def test_traceability_phase_plan_only(self, tmp_path):
        vault = _make_vault(tmp_path)
        spec_path = _write_spec(tmp_path)
        metrics = dev_run.run_traceability_phase(
            spec_path,
            gate=GATE_PHRASE,
            vault_path=vault,
            evidence_dir=tmp_path / "ev",
            plan_only=True,
        )
        assert metrics["verdict"] == "PIT_RUN_PLAN_ONLY"
        assert (tmp_path / "ev" / "roles" / "traceability.ROLE.md").is_file()
