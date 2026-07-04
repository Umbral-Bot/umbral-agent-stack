#!/usr/bin/env python3
"""PIT-DEV — runner del torneo developer product (spawn real de efímeros).

Runner del modo ``dev`` (pit_spec v3): tras el gate literal de David
(``ok, arranca``) prepara el workspace curado por lane, spawnea las lanes dev,
colecta sus cierres verificables (DELIVERABLE_PATH / TEST_REPORT /
SELF_ASSESSMENT), consolida el egress declarado, spawnea el security monitor
(veredicto EGRESS_CLEAN|EGRESS_FLAGGED por lane), spawnea los jueces
ejecutores SOLO sobre lanes limpias (las flaggeadas requieren decisión
explícita), agrega el ranking — que NO decide — y SIEMPRE mata y desregistra
los efímeros al cierre.

Reusa las fronteras existentes de ``pit_tournament_run.py`` (OpenClawCli,
register/deregister, kill por label, patrón D3.5b de lane result files) y las
primitivas de ``pit_dev_core.py``. Los modos v1 producto y v2 broker quedan
intactos: ``pit_tournament_run.main`` delega acá cuando detecta un spec dev,
igual que delega al broker con un spec v2.

Fases (``--phase full``, default)::

    gate literal → dev preflight (spec v3 + vault) → workspace init × lane
      → render roles (lanes + security + judges [+ traceability])
      → [--plan-only: artefactos sin registro ni spawn]
      → register + spawn lanes → collect dev (announce + deliverable + tests)
      → consolidar egress → spawn security → veredicto por lane
      → [gate pre-judge: flagged fuera salvo --judge-flagged-lanes "<motivo>"]
      → spawn judges → scorecards válidos + ranking agregado
      → kill + desregistro SIEMPRE (finally) → run-metrics.json

``--phase traceability`` (post-outcome/deck, separado): spawnea SOLO el agente
de trazabilidad, espera ``pit/<pit_id>/traceability/report.md`` y registra el
veredicto TRACE_COMPLETE | TRACE_GAPS.

Gates David explícitos (SKILL §PIT-DEV): (1) ``ok, arranca``; (2) aprobación
pre-judge si security flaggeó; (3) winner (el ranking NO decide); (4) cualquier
acción externa (Drive/Telegram) — fuera de este runner.

Contrato: ``docs/ops/pit-dev-mode-vision-2026-07-03.md``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.pit import pit_dev_core as dev_core
    from scripts.pit.pit_lane_workspace_init import init_workspace
    from scripts.pit.pit_spec_validate import PitSpecDev, load_dev_spec
    from scripts.pit.pit_tournament_run import (
        GATE_PHRASE,
        RUN_BLOCKED,
        RUN_FAIL,
        RUN_PARTIAL,
        RUN_PASS,
        RUN_PLAN_ONLY,
        SPAWN_BLOCKED_MARKER,
        SPAWN_FIRED_MARKER,
        OpenClawCli,
        RunBlocked,
        deregister_ephemeral_agents,
        kill_tournament_subagents,
        load_lanes,
        register_ephemeral_agents,
        write_generated_artifacts,
    )
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_dev_core as dev_core
    from scripts.pit.pit_lane_workspace_init import init_workspace
    from scripts.pit.pit_spec_validate import PitSpecDev, load_dev_spec
    from scripts.pit.pit_tournament_run import (
        GATE_PHRASE,
        RUN_BLOCKED,
        RUN_FAIL,
        RUN_PARTIAL,
        RUN_PASS,
        RUN_PLAN_ONLY,
        SPAWN_BLOCKED_MARKER,
        SPAWN_FIRED_MARKER,
        OpenClawCli,
        RunBlocked,
        deregister_ephemeral_agents,
        kill_tournament_subagents,
        load_lanes,
        register_ephemeral_agents,
        write_generated_artifacts,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_ROOT = REPO_ROOT / "openclaw" / "workspace-templates" / "pit-lane-agent"
ROLE_DEV_TEMPLATE = _TEMPLATES_ROOT / "ROLE.template.dev.md"
ROLE_SECURITY_TEMPLATE = _TEMPLATES_ROOT / "ROLE.security-monitor.md"
ROLE_JUDGE_TEMPLATE = _TEMPLATES_ROOT / "ROLE.judge-dev.md"
ROLE_TRACE_TEMPLATE = _TEMPLATES_ROOT / "ROLE.traceability.md"

DEFAULT_VAULT_PATH = Path.home() / "umbral-pit-vault"
DEFAULT_EVIDENCE_ROOT = Path.home() / ".coord-ag-evidence" / "pit-dev-run"
DEFAULT_OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_WORKSPACES_ROOT = Path.home() / ".openclaw" / "workspaces"

DEFAULT_LANE_TIMEOUT_SECONDS = 3600
DEFAULT_SPAWN_TIMEOUT_SECONDS = 900
DEFAULT_COLLECT_TIMEOUT_SECONDS = 7200
DEFAULT_COLLECT_POLL_SECONDS = 30
DEFAULT_SECURITY_TIMEOUT_SECONDS = 1800
DEFAULT_JUDGE_TIMEOUT_SECONDS = 3600


def _log(message: str) -> None:
    print(f"[pit-dev-run] {message}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Render de roles (plantillas canónicas del repo — nunca instancias editadas)
# ---------------------------------------------------------------------------


def _render(template_path: Path, replacements: dict[str, str]) -> str:
    template = template_path.read_text(encoding="utf-8")
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    leftover = sorted(set(re.findall(r"{{[a-z_]+}}", rendered)))
    if leftover:
        raise RunBlocked(
            f"ROLE template placeholders left unrendered in {template_path.name}: {leftover}"
        )
    return rendered


def render_dev_role(spec: PitSpecDev, lane: dict[str, str]) -> str:
    return _render(
        ROLE_DEV_TEMPLATE,
        {
            "{{pit_id}}": spec.pit_id,
            "{{title}}": spec.title,
            "{{problem_statement}}": spec.problem_statement,
            "{{deliverable_spec}}": spec.deliverable_spec,
            "{{lane_id}}": lane["lane_id"],
            "{{lane_focus}}": lane["lane_focus"],
            "{{iteration_count}}": str(spec.iteration_count),
            "{{budget_lane_usd}}": f"{spec.budget_per_lane_usd:.2f}",
        },
    )


def render_security_role(spec: PitSpecDev, lane_ids: list[str]) -> str:
    return _render(
        ROLE_SECURITY_TEMPLATE,
        {
            "{{pit_id}}": spec.pit_id,
            "{{title}}": spec.title,
            "{{lane_ids}}": ", ".join(lane_ids),
        },
    )


def render_judge_role(spec: PitSpecDev, judge_id: str, lane_ids: list[str]) -> str:
    weights = ", ".join(
        f"{k}={v}" for k, v in spec.rubric_weights.as_dict().items()
    )
    return _render(
        ROLE_JUDGE_TEMPLATE,
        {
            "{{pit_id}}": spec.pit_id,
            "{{title}}": spec.title,
            "{{deliverable_spec}}": spec.deliverable_spec,
            "{{judge_id}}": judge_id,
            "{{lane_ids}}": ", ".join(lane_ids),
            "{{rubric_weights}}": weights,
        },
    )


def render_trace_role(spec: PitSpecDev) -> str:
    return _render(
        ROLE_TRACE_TEMPLATE,
        {"{{pit_id}}": spec.pit_id, "{{title}}": spec.title},
    )


def build_dev_agents_yaml(
    spec: PitSpecDev,
    ephemerals: list[dict[str, str]],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Histórico de qué efímeros existieron (lanes + security + judges + trace)."""
    return {
        "schema_version": 1,
        "pit_id": spec.pit_id,
        "mode": "dev",
        "created_at": created_at,
        "spawn_parent": "main",
        "generated_by": "scripts/pit/pit_dev_run.py (PIT-DEV)",
        "agents": [
            {
                "lane_id": item["lane_id"],
                "agent_id": item["agent_id"],
                "kind": item["kind"],
                "lane_focus": item.get("lane_focus", ""),
                "created_at": created_at,
                "scope": item["scope"],
                "status": "generated",
                "killed_at": None,
                "deregistered": False,
            }
            for item in ephemerals
        ],
    }


# ---------------------------------------------------------------------------
# Task bodies + fan-out prompts (main standalone, G-D1b — patrón D3.5b)
# ---------------------------------------------------------------------------


def _dev_lane_task_body(spec: PitSpecDev, lane: dict[str, str], vault: Path) -> str:
    announce_rel = f"pit/{spec.pit_id}/lanes/{lane['lane_id']}/announce.md"
    return (
        f"{lane['role']}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}` — todos los paths `pit/...` cuelgan de ahí.\n"
        f"- Write scope: `PIT_VAULT_WRITE_SCOPE=pit` — escribís SOLO bajo "
        f"`pit/{spec.pit_id}/lanes/{lane['lane_id']}/`.\n"
        f"- Tu workspace curado YA está inicializado: leé "
        f"`pit/{spec.pit_id}/lanes/{lane['lane_id']}/workspace/CONTEXT_INDEX.md` primero.\n"
        f"- Lane result file (patrón D3.5b): al cerrar escribí las 3 líneas literales "
        f"(DELIVERABLE_PATH= / TEST_REPORT= / SELF_ASSESSMENT=) en `{announce_rel}` y "
        "terminá la sesión. Sin ese archivo + test_report verificable, tu lane cuenta "
        "como lane_incomplete.\n"
    )


def _security_task_body(spec: PitSpecDev, role: str, vault: Path) -> str:
    return (
        f"{role}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}`.\n"
        f"- El ledger mecánico ya está consolidado en "
        f"`pit/{spec.pit_id}/security/egress_ledger.jsonl` — verificalo y contrastalo.\n"
        f"- Tu salida obligatoria: `pit/{spec.pit_id}/security/verdict.md` con UNA "
        "línea literal por lane (EGRESS_CLEAN o EGRESS_FLAGGED(<motivos>)) y tu "
        f"análisis en `pit/{spec.pit_id}/security/egress_log.md`. Después terminá "
        "la sesión.\n"
    )


def _judge_task_body(
    spec: PitSpecDev, judge: dict[str, str], eligible_lanes: list[str], vault: Path
) -> str:
    return (
        f"{judge['role']}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}`.\n"
        f"- Lanes ELEGIBLES para evaluar (security-cleared): {', '.join(eligible_lanes)}. "
        "NO evalúes ninguna otra.\n"
        f"- Un scorecard POR lane elegible en "
        f"`pit/{spec.pit_id}/judge/scorecards/{judge['lane_id']}--<lane_id>.json` "
        "válido contra `templates/judge-scorecard.schema.json`. Después terminá la sesión.\n"
    )


def _trace_task_body(spec: PitSpecDev, role: str, vault: Path) -> str:
    return (
        f"{role}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}` (exportá PIT_VAULT_PATH si hace falta).\n"
        f"- Tu salida obligatoria: `pit/{spec.pit_id}/traceability/report.md` "
        "(el verificador la escribe) + announce final con la línea literal "
        "`TRACE_VERDICT=...`. Después terminá la sesión.\n"
    )


def build_fanout_prompt(
    stage: str,
    pit_id: str,
    spawns: list[dict[str, Any]],
) -> str:
    """Mensaje a ``main`` standalone: fan-out ``sessions_spawn`` × N + yield."""
    blocks: list[str] = [
        f"[PIT-DEV] Torneo {pit_id} — fase {stage}: spawn de {len(spawns)} efímero(s).",
        "",
        "Pre-condición G-D1b / ISSUE-001: si `sessions_spawn` NO está en tu tool set "
        f"(sesión nested), NO intentes spawnear: respondé literalmente `{SPAWN_BLOCKED_MARKER}` "
        "y terminá tu turno.",
        "",
        "Disparar los spawns EN ESTE MISMO TURNO (fan-out paralelo):",
        "",
    ]
    for spawn in spawns:
        blocks.append(
            f"sessions_spawn({json.dumps(spawn, ensure_ascii=False, indent=2)})"
        )
        blocks.append("")
    blocks.extend(
        [
            "Tras disparar los spawns, respondé literalmente "
            f"`{SPAWN_FIRED_MARKER} {len(spawns)}` y terminá tu turno (yield). "
            "NO esperes los announces en tu transcript: el collect se verifica "
            "contra el pit-vault (result files), patrón D3.5b.",
            "",
            "Guardrails: no merges, no publiques, no toques Notion, Magnific "
            "PROHIBIDO en todos los modos (ni invocarlo ni pedirlo — regla dura "
            "FASE 6), nunca URL pública.",
        ]
    )
    return "\n".join(blocks)


def _spawn_stage(
    cli: OpenClawCli,
    *,
    stage: str,
    pit_id: str,
    spawns: list[dict[str, Any]],
    evidence: Path,
    spawn_timeout_seconds: float,
) -> dict[str, Any]:
    """Dispara un fan-out vía main standalone y persiste el log de la fase."""
    prompt = build_fanout_prompt(stage, pit_id, spawns)
    (evidence / f"spawn-prompt-{stage}.md").write_text(prompt, encoding="utf-8")
    try:
        result = cli.agent_message("main", prompt, timeout=spawn_timeout_seconds)
        returncode: int | None = result.returncode
        output = (result.stdout or "") + (result.stderr or "")
    except Exception as exc:  # subprocess.TimeoutExpired y afines
        returncode = None
        output = f"SPAWN ERROR after {spawn_timeout_seconds}s: {exc}"
    (evidence / f"openclaw-spawn-{stage}.log").write_text(output, encoding="utf-8")
    return {
        "stage": stage,
        "returncode": returncode,
        "blocked_issue_001": SPAWN_BLOCKED_MARKER in output,
        "fired_marker_seen": SPAWN_FIRED_MARKER in output,
        "ok": returncode == 0 and SPAWN_BLOCKED_MARKER not in output,
        "log_path": str(evidence / f"openclaw-spawn-{stage}.log"),
    }


def _poll_until(
    condition: Callable[[], bool],
    *,
    timeout_seconds: float,
    poll_seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    deadline = clock() + timeout_seconds
    while True:
        if condition():
            return True
        if clock() >= deadline:
            return False
        sleep(poll_seconds)


# ---------------------------------------------------------------------------
# Collects por fase (vault como fuente de verdad)
# ---------------------------------------------------------------------------


def collect_dev_lanes(
    vault: Path,
    pit_id: str,
    lanes: list[dict[str, str]],
    *,
    re_run_tests: bool,
    timeout_seconds: float,
    poll_seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Espera el cierre verificable de todas las lanes dev (regla de verdad §3)."""
    deadline = clock() + timeout_seconds
    states: dict[str, dict[str, Any]] = {}
    pending = [lane["lane_id"] for lane in lanes]
    while True:
        for lane_id in list(pending):
            state = dev_core.verify_dev_lane(
                vault, pit_id, lane_id, re_run_tests=re_run_tests
            )
            states[lane_id] = state
            if state["lane_complete"]:
                pending.remove(lane_id)
                _log(
                    f"collect: {lane_id} lane_complete "
                    f"self_assessment={state.get('self_assessment')}"
                )
        if not pending or clock() >= deadline:
            break
        sleep(poll_seconds)
    for lane_id in pending:
        _log(f"collect: {lane_id} INCOMPLETE — {states[lane_id]['incomplete_reasons'][:3]}")
    return [states[lane["lane_id"]] for lane in lanes]


def _judge_ids(spec: PitSpecDev) -> list[str]:
    return [f"judge-{index}" for index in range(1, spec.judge_count + 1)]


def _expected_scorecards(judges: list[str], eligible: list[str]) -> set[tuple[str, str]]:
    return {(judge_id, lane_id) for judge_id in judges for lane_id in eligible}


# ---------------------------------------------------------------------------
# Run end-to-end (--phase full)
# ---------------------------------------------------------------------------


def run_dev_tournament(
    spec_path: Path,
    lanes_path: Path,
    *,
    gate: str,
    repo: Path | None = None,
    vault_path: Path | None = None,
    evidence_dir: Path | None = None,
    openclaw_config: Path | None = None,
    workspaces_root: Path | None = None,
    lane_model: str | None = None,
    lane_tools_profile: str | None = None,
    lane_timeout_seconds: int = DEFAULT_LANE_TIMEOUT_SECONDS,
    spawn_timeout_seconds: float = DEFAULT_SPAWN_TIMEOUT_SECONDS,
    collect_timeout_seconds: float = DEFAULT_COLLECT_TIMEOUT_SECONDS,
    collect_poll_seconds: float = DEFAULT_COLLECT_POLL_SECONDS,
    security_timeout_seconds: float = DEFAULT_SECURITY_TIMEOUT_SECONDS,
    judge_timeout_seconds: float = DEFAULT_JUDGE_TIMEOUT_SECONDS,
    re_run_tests: bool = False,
    judge_flagged_lanes_reason: str | None = None,
    plan_only: bool = False,
    force_workspace: bool = False,
    skip_gateway_restart: bool = False,
    cli: OpenClawCli | None = None,
) -> dict[str, Any]:
    """Orquesta el torneo PIT-DEV end-to-end y persiste run-metrics.json."""
    started_at = _utcnow().isoformat()

    # Gate David (1) — frase literal, sin variantes.
    if gate != GATE_PHRASE:
        raise RunBlocked(
            f"gate phrase mismatch: PIT-DEV requires the literal phrase "
            f"{GATE_PHRASE!r} from David (got {gate!r})"
        )

    spec = load_dev_spec(spec_path)
    lanes = load_lanes(lanes_path, spec)
    vault = (vault_path or Path(os.environ.get("PIT_VAULT_PATH") or DEFAULT_VAULT_PATH)).expanduser()
    evidence = (evidence_dir or DEFAULT_EVIDENCE_ROOT / spec.pit_id).expanduser()
    evidence.mkdir(parents=True, exist_ok=True)
    config_path = (
        openclaw_config
        or Path(os.environ.get("OPENCLAW_CONFIG_PATH") or DEFAULT_OPENCLAW_CONFIG)
    ).expanduser()
    repo = (repo or REPO_ROOT).expanduser()
    cli = cli or OpenClawCli(os.environ.get("OPENCLAW_BIN", "openclaw"))

    previous_scope = os.environ.get("PIT_VAULT_WRITE_SCOPE")
    os.environ["PIT_VAULT_WRITE_SCOPE"] = "pit"
    try:
        # 1. Preflight dev — spec v3 + vault (fail-closed).
        preflight = dev_core.dev_preflight(spec_path, vault, require_write_scope=True)
        _log(f"preflight: {preflight['verdict']}")
        if not preflight["ok"]:
            raise RunBlocked(f"dev preflight failed: {preflight['errors']}")

        lane_ids = [lane["lane_id"] for lane in lanes]
        judges = _judge_ids(spec)

        # 2. Render de TODOS los efímeros del torneo.
        ephemerals: list[dict[str, Any]] = []
        for lane in lanes:
            lane["role"] = render_dev_role(spec, lane)
            lane["kind"] = "lane"
            lane["scope"] = f"pit/{spec.pit_id}/lanes/{lane['lane_id']}/"
            ephemerals.append(lane)
        security = {
            "lane_id": "security",
            "lane_focus": "egress audit (no compite)",
            "agent_id": f"{spec.pit_id}-security",
            "role": render_security_role(spec, lane_ids),
            "kind": "security",
            "scope": f"pit/{spec.pit_id}/security/",
        }
        ephemerals.append(security)
        judge_items: list[dict[str, Any]] = []
        for judge_id in judges:
            judge = {
                "lane_id": judge_id,
                "lane_focus": "juez ejecutor (post-cierre de lanes)",
                "agent_id": f"{spec.pit_id}-{judge_id}",
                "role": render_judge_role(spec, judge_id, lane_ids),
                "kind": "judge",
                "scope": f"pit/{spec.pit_id}/judge/{judge_id}/",
            }
            judge_items.append(judge)
            ephemerals.append(judge)

        agents_doc = build_dev_agents_yaml(spec, ephemerals, created_at=started_at)

        metrics: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pit_dev_run_metrics",
            "generated_by": "scripts/pit/pit_dev_run.py (PIT-DEV)",
            "started_at": started_at,
            "pit_id": spec.pit_id,
            "mode": "dev",
            "spec_path": str(spec_path),
            "lanes_path": str(lanes_path),
            "vault_path": str(vault),
            "repo": str(repo),
            "repo_ref": spec.repo_ref,
            "lane_count": spec.lane_count,
            "iteration_count": spec.iteration_count,
            "judge_count": spec.judge_count,
            "preflight_verdict": preflight["verdict"],
            "budget": preflight["budget"],
            "gate_phrase_ok": True,
            "plan_only": plan_only,
            "lanes": [
                {
                    "lane_id": lane["lane_id"],
                    "agent_id": lane["agent_id"],
                    "lane_focus": lane["lane_focus"],
                }
                for lane in lanes
            ],
            "constraints": {
                "magnific": "denied_for_all_ephemerals_all_modes",
                "public_url": False,
                "snapshot_over_live_main": True,
                "spawn_parent": "main (standalone, G-D1b)",
            },
        }

        if plan_only:
            write_generated_artifacts(spec, ephemerals, agents_doc, vault=None, out_dir=evidence)
            metrics["verdict"] = RUN_PLAN_ONLY
            _log("plan-only: roles + agents.yaml renderizados; sin workspace/registro/spawn")
            _write_metrics(evidence, metrics)
            return metrics

        if not cli.available():
            raise RunBlocked(
                f"openclaw binary not found ({cli.bin_path}) — set OPENCLAW_BIN or run on the VPS"
            )

        # 3. Persistir spec + lanes.yaml en el vault (cadena de trazabilidad).
        spec_dir = vault / "pit" / spec.pit_id / "spec"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "pit_spec.yaml").write_text(
            Path(spec_path).read_text(encoding="utf-8"), encoding="utf-8"
        )
        (spec_dir / "lanes.yaml").write_text(
            Path(lanes_path).read_text(encoding="utf-8"), encoding="utf-8"
        )

        # 4. Workspace curado por lane (snapshot + CONTEXT_INDEX).
        workspace_reports: list[dict[str, Any]] = []
        for lane in lanes:
            report = init_workspace(
                vault_path=vault,
                repo=repo,
                ref=spec.repo_ref,
                pit_id=spec.pit_id,
                lane_id=lane["lane_id"],
                deliverable_spec=spec.deliverable_spec,
                force=force_workspace,
            )
            workspace_reports.append(report)
            _log(
                f"workspace: {lane['lane_id']} snapshot {report['snapshot_files']} files "
                f"@ {report['commit_sha'][:12]}"
            )
        metrics["workspaces"] = workspace_reports

        artifact_paths = write_generated_artifacts(
            spec, ephemerals, agents_doc, vault=vault, out_dir=evidence
        )
        metrics["artifacts"] = artifact_paths

        # 5. Registro de TODOS los efímeros (lanes + security + judges).
        registration = register_ephemeral_agents(
            config_path,
            spec,
            ephemerals,
            workspaces_root=(workspaces_root or DEFAULT_WORKSPACES_ROOT).expanduser(),
            lane_model=lane_model,
            lane_tools_profile=lane_tools_profile,
        )
        metrics["registration"] = registration
        for agent in agents_doc["agents"]:
            agent["status"] = "registered"

        lane_states: list[dict[str, Any]] = []
        try:
            if not skip_gateway_restart:
                restart = cli.gateway_restart()
                metrics["registration"]["gateway_restart_rc"] = restart.returncode
                if restart.returncode != 0:
                    raise RunBlocked(
                        "gateway restart failed after registration — config backup at "
                        f"{registration['backup_path']}"
                    )

            # 6. FASE LANES — fan-out + collect verificable.
            lane_spawns = [
                {
                    "runtime": "subagent",
                    "agentId": lane["agent_id"],
                    "label": lane["agent_id"],
                    "timeoutSeconds": lane_timeout_seconds,
                    "task": _dev_lane_task_body(spec, lane, vault),
                }
                for lane in lanes
            ]
            spawn_report = _spawn_stage(
                cli,
                stage="lanes",
                pit_id=spec.pit_id,
                spawns=lane_spawns,
                evidence=evidence,
                spawn_timeout_seconds=spawn_timeout_seconds,
            )
            metrics["spawn_lanes"] = spawn_report
            if not spawn_report["ok"]:
                _log("spawn lanes failed/blocked — skipping collect and later phases")
            else:
                for agent in agents_doc["agents"]:
                    if agent["kind"] == "lane":
                        agent["status"] = "spawned"
                lane_states = collect_dev_lanes(
                    vault,
                    spec.pit_id,
                    lanes,
                    re_run_tests=re_run_tests,
                    timeout_seconds=collect_timeout_seconds,
                    poll_seconds=collect_poll_seconds,
                )
            metrics["lane_results"] = lane_states
            complete_lanes = [
                state["lane_id"] for state in lane_states if state.get("lane_complete")
            ]
            metrics["lanes_completed"] = len(complete_lanes)

            # 7. FASE SECURITY — consolidación mecánica + veredicto del agente.
            security_report: dict[str, Any] = {"ran": False}
            if spawn_report["ok"]:
                consolidation = dev_core.consolidate_egress(
                    vault, spec.pit_id, lane_ids
                )
                metrics["egress_consolidation"] = consolidation
                security_spawn = _spawn_stage(
                    cli,
                    stage="security",
                    pit_id=spec.pit_id,
                    spawns=[
                        {
                            "runtime": "subagent",
                            "agentId": security["agent_id"],
                            "label": security["agent_id"],
                            "timeoutSeconds": int(security_timeout_seconds),
                            "task": _security_task_body(spec, security["role"], vault),
                        }
                    ],
                    evidence=evidence,
                    spawn_timeout_seconds=spawn_timeout_seconds,
                )
                security_report = {"ran": True, "spawn": security_spawn}
                if security_spawn["ok"]:
                    for agent in agents_doc["agents"]:
                        if agent["kind"] == "security":
                            agent["status"] = "spawned"
                    _poll_until(
                        lambda: dev_core.security_verdict_state(vault, spec.pit_id)[
                            "verdict_file_present"
                        ],
                        timeout_seconds=security_timeout_seconds,
                        poll_seconds=collect_poll_seconds,
                    )
                verdict_state = dev_core.security_verdict_state(vault, spec.pit_id)
                security_report["verdict_state"] = verdict_state
            metrics["security"] = security_report

            # 8. Gate pre-judge (Gate David 2): flagged fuera salvo decisión
            # explícita; sin verdict.md no hay judge (fail-closed).
            verdict_lanes = (
                security_report.get("verdict_state", {}).get("lanes", {})
                if security_report.get("ran")
                else {}
            )
            eligible: list[str] = []
            flagged: list[str] = []
            missing_verdict: list[str] = []
            for lane_id in complete_lanes:
                lane_verdict = verdict_lanes.get(lane_id, {}).get("verdict")
                if lane_verdict == dev_core.SECURITY_CLEAN:
                    eligible.append(lane_id)
                elif lane_verdict == dev_core.SECURITY_FLAGGED:
                    flagged.append(lane_id)
                else:
                    missing_verdict.append(lane_id)
            judge_flagged_decision = None
            if flagged and judge_flagged_lanes_reason:
                # Decisión explícita de Rick (+ gate David si es grave): las
                # lanes flaggeadas entran al judge y la razón queda registrada.
                judge_flagged_decision = {
                    "included_flagged_lanes": flagged,
                    "reason": judge_flagged_lanes_reason,
                }
                eligible.extend(flagged)
            metrics["judge_gate"] = {
                "eligible": eligible,
                "flagged": flagged,
                "missing_verdict": missing_verdict,
                "flagged_decision": judge_flagged_decision,
            }

            # 9. FASE JUDGES — solo con >=2 lanes elegibles (paralelo v1).
            judges_report: dict[str, Any] = {"ran": False}
            if len(eligible) >= 2:
                judge_spawns = [
                    {
                        "runtime": "subagent",
                        "agentId": judge["agent_id"],
                        "label": judge["agent_id"],
                        "timeoutSeconds": int(judge_timeout_seconds),
                        "task": _judge_task_body(spec, judge, eligible, vault),
                    }
                    for judge in judge_items
                ]
                judge_spawn = _spawn_stage(
                    cli,
                    stage="judges",
                    pit_id=spec.pit_id,
                    spawns=judge_spawns,
                    evidence=evidence,
                    spawn_timeout_seconds=spawn_timeout_seconds,
                )
                judges_report = {"ran": True, "spawn": judge_spawn}
                if judge_spawn["ok"]:
                    for agent in agents_doc["agents"]:
                        if agent["kind"] == "judge":
                            agent["status"] = "spawned"
                    expected = _expected_scorecards(judges, eligible)

                    def _scorecards_done() -> bool:
                        valid, _errors = dev_core.collect_scorecards(vault, spec.pit_id)
                        seen = {(card["judge_id"], card["lane_id"]) for card in valid}
                        return expected.issubset(seen)

                    _poll_until(
                        _scorecards_done,
                        timeout_seconds=judge_timeout_seconds,
                        poll_seconds=collect_poll_seconds,
                    )
                valid_cards, card_errors = dev_core.collect_scorecards(vault, spec.pit_id)
                ranking = dev_core.aggregate_ranking(
                    valid_cards, spec.rubric_weights.as_dict()
                )
                ranking_path = vault / "pit" / spec.pit_id / "judge" / "ranking.json"
                ranking_path.parent.mkdir(parents=True, exist_ok=True)
                ranking_path.write_text(
                    json.dumps(
                        {
                            "pit_id": spec.pit_id,
                            "note": "El ranking NO decide: Rick consolida y David da el gate de winner.",
                            "rubric_weights": spec.rubric_weights.as_dict(),
                            "ranking": ranking,
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                judges_report.update(
                    {
                        "scorecards_valid": len(valid_cards),
                        "scorecards_invalid": card_errors,
                        "ranking": ranking,
                        "ranking_path": str(ranking_path),
                    }
                )
            else:
                _log(
                    f"judges: skipped — {len(eligible)} eligible lane(s) (<2); "
                    "flagged/missing verdict lanes need explicit decision"
                )
            metrics["judges"] = judges_report
        finally:
            # 10. Kill + desregistro SIEMPRE — todos los efímeros del torneo
            # (prefijo <pit_id>- cubre lanes + security + judges).
            killed_at = _utcnow().isoformat()
            kill_report = kill_tournament_subagents(
                cli, spec.pit_id, label_prefix=f"{spec.pit_id}-"
            )
            metrics["kill"] = kill_report
            try:
                dereg = deregister_ephemeral_agents(
                    config_path, [item["agent_id"] for item in ephemerals]
                )
                if not skip_gateway_restart:
                    dereg["gateway_restart_rc"] = cli.gateway_restart().returncode
                metrics["deregistration"] = dereg
                deregistered = True
            except Exception as exc:  # visible en métricas; nunca enmascara el run
                metrics["deregistration"] = {"error": str(exc)}
                deregistered = False
            for agent in agents_doc["agents"]:
                agent["killed_at"] = killed_at
                agent["deregistered"] = deregistered
                agent["status"] = "closed"
            write_generated_artifacts(spec, ephemerals, agents_doc, vault=vault, out_dir=evidence)

        metrics["verdict"] = _dev_verdict(metrics)
        _write_metrics(evidence, metrics)
        return metrics
    finally:
        if previous_scope is None:
            os.environ.pop("PIT_VAULT_WRITE_SCOPE", None)
        else:
            os.environ["PIT_VAULT_WRITE_SCOPE"] = previous_scope


def _dev_verdict(metrics: dict[str, Any]) -> str:
    """PASS = pipeline completo verde; PARTIAL = judge posible; FAIL = <2 lanes."""
    spawn_ok = bool(metrics.get("spawn_lanes", {}).get("ok"))
    lane_states = metrics.get("lane_results", [])
    complete = sum(1 for state in lane_states if state.get("lane_complete"))
    if not spawn_ok:
        return RUN_FAIL
    all_lanes_complete = bool(lane_states) and complete == len(lane_states)
    security_ok = bool(
        metrics.get("security", {})
        .get("verdict_state", {})
        .get("verdict_file_present")
    )
    judges = metrics.get("judges", {})
    judges_ok = bool(judges.get("ran")) and judges.get("scorecards_valid", 0) > 0
    if all_lanes_complete and security_ok and judges_ok:
        return RUN_PASS
    if complete >= 2:
        return RUN_PARTIAL
    return RUN_FAIL


# ---------------------------------------------------------------------------
# --phase traceability (post-outcome/deck)
# ---------------------------------------------------------------------------


def run_traceability_phase(
    spec_path: Path,
    *,
    gate: str,
    vault_path: Path | None = None,
    evidence_dir: Path | None = None,
    openclaw_config: Path | None = None,
    workspaces_root: Path | None = None,
    spawn_timeout_seconds: float = DEFAULT_SPAWN_TIMEOUT_SECONDS,
    trace_timeout_seconds: float = DEFAULT_SECURITY_TIMEOUT_SECONDS,
    collect_poll_seconds: float = DEFAULT_COLLECT_POLL_SECONDS,
    plan_only: bool = False,
    skip_gateway_restart: bool = False,
    cli: OpenClawCli | None = None,
) -> dict[str, Any]:
    """Spawnea SOLO el agente de trazabilidad (post-outcome) y colecta su report."""
    started_at = _utcnow().isoformat()
    if gate != GATE_PHRASE:
        raise RunBlocked(
            f"gate phrase mismatch: traceability phase requires the literal phrase "
            f"{GATE_PHRASE!r} (got {gate!r})"
        )
    spec = load_dev_spec(spec_path)
    vault = (vault_path or Path(os.environ.get("PIT_VAULT_PATH") or DEFAULT_VAULT_PATH)).expanduser()
    evidence = (
        (evidence_dir or DEFAULT_EVIDENCE_ROOT / spec.pit_id).expanduser()
    )
    evidence.mkdir(parents=True, exist_ok=True)
    config_path = (
        openclaw_config
        or Path(os.environ.get("OPENCLAW_CONFIG_PATH") or DEFAULT_OPENCLAW_CONFIG)
    ).expanduser()
    cli = cli or OpenClawCli(os.environ.get("OPENCLAW_BIN", "openclaw"))

    trace = {
        "lane_id": "traceability",
        "lane_focus": "verificación de cadena post-torneo",
        "agent_id": f"{spec.pit_id}-traceability",
        "role": render_trace_role(spec),
        "kind": "traceability",
        "scope": f"pit/{spec.pit_id}/traceability/",
    }
    agents_doc = build_dev_agents_yaml(spec, [trace], created_at=started_at)
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "kind": "pit_dev_trace_metrics",
        "generated_by": "scripts/pit/pit_dev_run.py (--phase traceability)",
        "started_at": started_at,
        "pit_id": spec.pit_id,
        "phase": "traceability",
        "plan_only": plan_only,
    }

    if plan_only:
        write_generated_artifacts(spec, [trace], agents_doc, vault=None, out_dir=evidence)
        metrics["verdict"] = RUN_PLAN_ONLY
        _write_metrics(evidence, metrics)
        return metrics

    if not cli.available():
        raise RunBlocked(
            f"openclaw binary not found ({cli.bin_path}) — set OPENCLAW_BIN or run on the VPS"
        )

    registration = register_ephemeral_agents(
        config_path,
        spec,
        [trace],
        workspaces_root=(workspaces_root or DEFAULT_WORKSPACES_ROOT).expanduser(),
    )
    metrics["registration"] = registration
    try:
        if not skip_gateway_restart:
            restart = cli.gateway_restart()
            metrics["registration"]["gateway_restart_rc"] = restart.returncode
            if restart.returncode != 0:
                raise RunBlocked("gateway restart failed after registration")
        spawn_report = _spawn_stage(
            cli,
            stage="traceability",
            pit_id=spec.pit_id,
            spawns=[
                {
                    "runtime": "subagent",
                    "agentId": trace["agent_id"],
                    "label": trace["agent_id"],
                    "timeoutSeconds": int(trace_timeout_seconds),
                    "task": _trace_task_body(spec, trace["role"], vault),
                }
            ],
            evidence=evidence,
            spawn_timeout_seconds=spawn_timeout_seconds,
        )
        metrics["spawn_traceability"] = spawn_report
        report_path = vault / "pit" / spec.pit_id / "traceability" / "report.md"
        if spawn_report["ok"]:
            _poll_until(
                report_path.is_file,
                timeout_seconds=trace_timeout_seconds,
                poll_seconds=collect_poll_seconds,
            )
        metrics["report_present"] = report_path.is_file()
        # Veredicto autoritativo: el runner corre el verificador él mismo.
        try:
            from scripts.pit.pit_traceability_check import check_traceability

            trace_result = check_traceability(vault, spec.pit_id)
            metrics["trace_verdict"] = trace_result["verdict"]
            metrics["trace_gaps"] = trace_result["gaps"]
        except ValueError as exc:
            metrics["trace_verdict"] = f"UNAVAILABLE ({exc})"
    finally:
        kill_report = kill_tournament_subagents(
            cli, spec.pit_id, label_prefix=f"{spec.pit_id}-traceability"
        )
        metrics["kill"] = kill_report
        try:
            dereg = deregister_ephemeral_agents(config_path, [trace["agent_id"]])
            if not skip_gateway_restart:
                dereg["gateway_restart_rc"] = cli.gateway_restart().returncode
            metrics["deregistration"] = dereg
        except Exception as exc:
            metrics["deregistration"] = {"error": str(exc)}

    metrics["verdict"] = (
        RUN_PASS
        if metrics.get("report_present") and str(metrics.get("trace_verdict", "")).startswith("TRACE_")
        else RUN_FAIL
    )
    _write_metrics(evidence, metrics)
    return metrics


def _write_metrics(evidence: Path, metrics: dict[str, Any]) -> None:
    metrics["finished_at"] = _utcnow().isoformat()
    metrics_path = evidence / "run-metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metrics["run_metrics_path"] = str(metrics_path)
    _log(f"run-metrics: {metrics_path}")
    _log(f"verdict: {metrics['verdict']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PIT-DEV — runner del torneo developer product (spec v3)."
    )
    parser.add_argument("spec_path", type=Path, help="Path al pit_spec v3 (mode: dev).")
    parser.add_argument(
        "lanes_path",
        type=Path,
        nargs="?",
        default=None,
        help="Lanes file YAML (lanes: [{lane_id, lane_focus}, ...]). "
        "Obligatorio en --phase full; ignorado en --phase traceability.",
    )
    parser.add_argument("--gate", required=True,
                        help=f"Frase literal del gate David ({GATE_PHRASE!r}).")
    parser.add_argument("--phase", choices=("full", "traceability"), default="full",
                        help="full = lanes+security+judges; traceability = post-outcome.")
    parser.add_argument("--repo", type=Path, default=None,
                        help="Checkout del repo a snapshotear (default: este repo).")
    parser.add_argument("--vault-path", type=Path, default=None)
    parser.add_argument("--evidence-dir", type=Path, default=None)
    parser.add_argument("--openclaw-config", type=Path, default=None)
    parser.add_argument("--workspaces-root", type=Path, default=None)
    parser.add_argument("--lane-model", default=None)
    parser.add_argument("--lane-tools-profile", default=None)
    parser.add_argument("--lane-timeout-seconds", type=int, default=DEFAULT_LANE_TIMEOUT_SECONDS)
    parser.add_argument("--spawn-timeout-seconds", type=float, default=DEFAULT_SPAWN_TIMEOUT_SECONDS)
    parser.add_argument("--collect-timeout-seconds", type=float, default=DEFAULT_COLLECT_TIMEOUT_SECONDS)
    parser.add_argument("--collect-poll-seconds", type=float, default=DEFAULT_COLLECT_POLL_SECONDS)
    parser.add_argument("--security-timeout-seconds", type=float, default=DEFAULT_SECURITY_TIMEOUT_SECONDS)
    parser.add_argument("--judge-timeout-seconds", type=float, default=DEFAULT_JUDGE_TIMEOUT_SECONDS)
    parser.add_argument("--re-run-tests", action="store_true",
                        help="El collect re-ejecuta el comando declarado del test_report.")
    parser.add_argument("--judge-flagged-lanes", default=None, metavar="REASON",
                        help="Decisión explícita (Rick, + gate David si es grave) para "
                        "incluir lanes EGRESS_FLAGGED en el judge; el motivo queda registrado.")
    parser.add_argument("--plan-only", action="store_true",
                        help="Renderiza plan (roles + agents.yaml) sin registro ni spawn.")
    parser.add_argument("--force-workspace", action="store_true",
                        help="Reconstruir snapshots de workspace existentes.")
    parser.add_argument("--skip-gateway-restart", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.phase == "traceability":
            metrics = run_traceability_phase(
                args.spec_path,
                gate=args.gate,
                vault_path=args.vault_path,
                evidence_dir=args.evidence_dir,
                openclaw_config=args.openclaw_config,
                workspaces_root=args.workspaces_root,
                spawn_timeout_seconds=args.spawn_timeout_seconds,
                trace_timeout_seconds=args.security_timeout_seconds,
                collect_poll_seconds=args.collect_poll_seconds,
                plan_only=args.plan_only,
                skip_gateway_restart=args.skip_gateway_restart,
            )
        else:
            if args.lanes_path is None:
                raise RunBlocked("lanes_path is required for --phase full")
            metrics = run_dev_tournament(
                args.spec_path,
                args.lanes_path,
                gate=args.gate,
                repo=args.repo,
                vault_path=args.vault_path,
                evidence_dir=args.evidence_dir,
                openclaw_config=args.openclaw_config,
                workspaces_root=args.workspaces_root,
                lane_model=args.lane_model,
                lane_tools_profile=args.lane_tools_profile,
                lane_timeout_seconds=args.lane_timeout_seconds,
                spawn_timeout_seconds=args.spawn_timeout_seconds,
                collect_timeout_seconds=args.collect_timeout_seconds,
                collect_poll_seconds=args.collect_poll_seconds,
                security_timeout_seconds=args.security_timeout_seconds,
                judge_timeout_seconds=args.judge_timeout_seconds,
                re_run_tests=args.re_run_tests,
                judge_flagged_lanes_reason=args.judge_flagged_lanes,
                plan_only=args.plan_only,
                force_workspace=args.force_workspace,
                skip_gateway_restart=args.skip_gateway_restart,
            )
    except RunBlocked as exc:
        _log(f"BLOCKED: {exc}")
        _log(f"verdict: {RUN_BLOCKED}")
        return 2
    except Exception as exc:  # error inesperado — visible, sin medio-correr
        _log(f"ERROR: {exc}")
        _log(f"verdict: {RUN_BLOCKED}")
        return 2

    if metrics["verdict"] in (RUN_PASS, RUN_PLAN_ONLY):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
