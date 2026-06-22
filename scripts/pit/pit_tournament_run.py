#!/usr/bin/env python3
"""PIT-2b — spawn real de agentes efímeros OpenClaw (post-smoke PIT_DRY_RUN_PASS).

Runner del torneo PIT real sobre la VPS: tras el gate literal de David
(``ok, arranca``) y el smoke PIT-2 en verde, genera los agentes efímeros del
torneo (docs/ops/pit-ephemeral-agent-generator.md), los registra en OpenClaw,
dispara el fan-out ``sessions_spawn`` × N desde ``main`` standalone (G-D1b) y
colecta el cierre de cada lane contra el pit-vault. Al terminar — pase lo que
pase — mata los hijos vivos y desregistra los efímeros, dejando
``agents.yaml`` como histórico.

Patrón D3.5b (PRs #472/#473): ``sessions_spawn`` × N + yield + lane result
files. El parent NO espera announces en su transcript: cada lane persiste su
announce final en ``pit/<pit_id>/lanes/<lane_id>/announce.md`` y el collect
verifica el vault con ``pit_runner_core.lane_announce`` (la misma
implementación que la task Worker ``pit.lane_announce``) — ``lane_complete``
obligatorio, paralelo a docs/79 §4.1.

Orden de fases::

    gate literal → smoke gate (PIT_DRY_RUN_PASS) → preflight (pit.preflight)
      → generate (ROLE render + agents.yaml) → register (openclaw.json)
      → spawn (openclaw agent --agent main) → collect (vault) → kill +
      deregister (finally) → run-metrics.json

Veredictos (``run-metrics.json.verdict``):

- ``PIT_RUN_PASS`` — todas las lanes ``lane_complete`` (exit 0).
- ``PIT_RUN_PARTIAL`` — ≥2 lanes completas (judge posible) pero no todas (exit 1).
- ``PIT_RUN_FAIL`` — <2 lanes completas (exit 1).
- ``PIT_RUN_BLOCKED`` — gate/smoke/preflight/registro fallaron ANTES del spawn (exit 2).
- ``PIT_RUN_PLAN_ONLY`` — ``--plan-only``: plan renderizado, sin registro ni spawn (exit 0).

Guardrails duros: NO Magnific directo (broker Rick), NO URL pública, write
scope por lane, budget kill switch sigue stub (enforcement PIT-3).

Uso (vía ``scripts/pit/pit_tournament_run.sh``)::

    bash scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> \
        --gate "ok, arranca"            # spawn real (VPS)
    bash scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> \
        --gate "ok, arranca" --plan-only  # validación post-merge sin spawn
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

try:
    from scripts.pit import pit_runner_core as core
    from scripts.pit.pit_dry_run import (
        DEFAULT_EVIDENCE_ROOT as DRY_RUN_EVIDENCE_ROOT,
        DRY_RUN_PASS,
    )
    from scripts.pit.pit_spec_validate import PitSpec, is_broker_spec, load_spec
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_runner_core as core
    from scripts.pit.pit_dry_run import (
        DEFAULT_EVIDENCE_ROOT as DRY_RUN_EVIDENCE_ROOT,
        DRY_RUN_PASS,
    )
    from scripts.pit.pit_spec_validate import PitSpec, is_broker_spec, load_spec

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE_TEMPLATE_PATH = (
    REPO_ROOT / "openclaw" / "workspace-templates" / "pit-lane-agent" / "ROLE.template.md"
)

GATE_PHRASE = "ok, arranca"

RUN_PASS = "PIT_RUN_PASS"
RUN_PARTIAL = "PIT_RUN_PARTIAL"
RUN_FAIL = "PIT_RUN_FAIL"
RUN_BLOCKED = "PIT_RUN_BLOCKED"
RUN_PLAN_ONLY = "PIT_RUN_PLAN_ONLY"

# Marker literal que main debe responder si sessions_spawn no está en su tool
# set (sesión nested — ISSUE-001 / G-D1b). El runner lo detecta y NO colecta.
SPAWN_BLOCKED_MARKER = "PIT_SPAWN_BLOCKED_ISSUE_001"
SPAWN_FIRED_MARKER = "PIT_SPAWN_FIRED"

DEFAULT_VAULT_PATH = Path.home() / "umbral-pit-vault"
DEFAULT_EVIDENCE_ROOT = Path.home() / ".coord-ag-evidence" / "pit-run"
DEFAULT_OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_WORKSPACES_ROOT = Path.home() / ".openclaw" / "workspaces"

DEFAULT_LANE_TIMEOUT_SECONDS = 1800
DEFAULT_COLLECT_TIMEOUT_SECONDS = 3600
DEFAULT_COLLECT_POLL_SECONDS = 30
DEFAULT_SPAWN_TIMEOUT_SECONDS = 900
DEFAULT_MAX_SMOKE_AGE_HOURS = 24.0

ANNOUNCE_FILE_NAME = "announce.md"


class RunBlocked(Exception):
    """Abort pre-spawn: gate, smoke, preflight, lanes o registro inválidos."""


def _log(message: str) -> None:
    print(f"[pit-run] {message}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# OpenClaw CLI boundary (mockable en tests)
# ---------------------------------------------------------------------------


class OpenClawCli:
    """Frontera subprocess → binario ``openclaw`` (G-D1b: spawn vía main).

    Toda interacción con el runtime OpenClaw pasa por acá, así los tests de
    contrato inyectan un fake sin necesitar el binario ni una VPS.
    """

    def __init__(
        self,
        bin_path: str = "openclaw",
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        self.bin_path = bin_path
        self._runner = runner or subprocess.run

    def available(self) -> bool:
        return shutil.which(self.bin_path) is not None

    def run(self, args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess:
        return self._runner(
            [self.bin_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def gateway_restart(self) -> subprocess.CompletedProcess:
        return self.run(["gateway", "restart"], timeout=120)

    def agent_message(
        self, agent_id: str, message: str, *, timeout: float
    ) -> subprocess.CompletedProcess:
        return self.run(["agent", "--agent", agent_id, "-m", message], timeout=timeout)

    def tasks_list_subagents(self) -> subprocess.CompletedProcess:
        return self.run(["tasks", "list", "--runtime", "subagent", "--json"], timeout=120)

    def subagent_kill(self, task_id: str) -> subprocess.CompletedProcess:
        return self.run(["subagents", "kill", task_id], timeout=120)


# ---------------------------------------------------------------------------
# Lanes file (identidades derivadas por Rick — generador §2.1)
# ---------------------------------------------------------------------------


def load_lanes(lanes_path: Path, spec: PitSpec) -> list[dict[str, str]]:
    """Carga lanes.yaml: ``lanes: [{lane_id, lane_focus}, ...]``.

    Las identidades (slug = ángulo de exploración) las deriva Rick por torneo;
    el runner solo valida: count == spec.lane_count, ids únicos y válidos.
    """
    if not lanes_path.is_file():
        raise RunBlocked(f"lanes file not found: {lanes_path}")
    raw = yaml.safe_load(lanes_path.read_text(encoding="utf-8"))
    lanes_raw = raw.get("lanes") if isinstance(raw, dict) else None
    if not isinstance(lanes_raw, list) or not lanes_raw:
        raise RunBlocked("lanes file must contain a non-empty 'lanes:' list")
    if len(lanes_raw) != spec.lane_count:
        raise RunBlocked(
            f"lanes count mismatch: spec.lane_count={spec.lane_count}, "
            f"lanes file has {len(lanes_raw)}"
        )
    lanes: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(lanes_raw):
        if not isinstance(item, dict):
            raise RunBlocked(f"lanes[{index}] must be an object with lane_id/lane_focus")
        lane_id = (item.get("lane_id") or "").strip()
        if not core.LANE_ID_RE.fullmatch(lane_id):
            raise RunBlocked(
                f"lanes[{index}].lane_id must match {core.LANE_ID_RE.pattern} (got {lane_id!r})"
            )
        if lane_id in seen:
            raise RunBlocked(f"duplicate lane_id in lanes file: {lane_id}")
        seen.add(lane_id)
        lane_focus = (item.get("lane_focus") or "").strip()
        if not lane_focus:
            raise RunBlocked(f"lanes[{index}].lane_focus is required (ángulo de exploración)")
        lanes.append(
            {
                "lane_id": lane_id,
                "lane_focus": lane_focus,
                # Identidad efímera 1:1 con el torneo (generador §1): nunca se
                # recicla entre torneos porque lleva el pit_id en el id.
                "agent_id": f"{spec.pit_id}-{lane_id}",
            }
        )
    return lanes


# ---------------------------------------------------------------------------
# Smoke gate — abort si el dry-run PIT-2 no quedó en PASS
# ---------------------------------------------------------------------------


def check_smoke_gate(
    spec: PitSpec,
    *,
    smoke_metrics_path: Path | None = None,
    max_age_hours: float = DEFAULT_MAX_SMOKE_AGE_HOURS,
) -> dict[str, Any]:
    """Gate post-smoke: exige PIT_DRY_RUN_PASS fresco para el MISMO pit_id.

    Smoke rojo o ausente ⇒ no spawn (SKILL §Smoke runner PIT-2: "smoke rojo ⇒
    STOP"). El veredicto se lee de la evidencia que dejó
    ``pit_tournament_dry_run.sh``.
    """
    metrics_path = smoke_metrics_path or (
        DRY_RUN_EVIDENCE_ROOT / spec.pit_id / "final-metrics.json"
    )
    if not metrics_path.is_file():
        raise RunBlocked(
            f"smoke evidence not found: {metrics_path} — "
            "run scripts/pit/pit_tournament_dry_run.sh first"
        )
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunBlocked(f"smoke evidence is not valid JSON ({metrics_path}): {exc}") from exc

    verdict = metrics.get("verdict")
    if verdict != DRY_RUN_PASS:
        raise RunBlocked(
            f"smoke verdict is {verdict!r}, required {DRY_RUN_PASS} — no spawn with red smoke"
        )
    if metrics.get("pit_id") != spec.pit_id:
        raise RunBlocked(
            f"smoke evidence pit_id {metrics.get('pit_id')!r} does not match spec "
            f"pit_id {spec.pit_id!r}"
        )
    if metrics.get("lane_count") != spec.lane_count:
        raise RunBlocked(
            f"smoke evidence lane_count {metrics.get('lane_count')!r} does not match "
            f"spec lane_count {spec.lane_count!r} — re-run the smoke for this spec"
        )

    age_hours: float | None = None
    generated_at = metrics.get("generated_at")
    if isinstance(generated_at, str):
        try:
            generated = datetime.fromisoformat(generated_at)
        except ValueError:
            generated = None
        if generated is not None:
            age_hours = (_utcnow() - generated).total_seconds() / 3600.0
            if max_age_hours > 0 and age_hours > max_age_hours:
                raise RunBlocked(
                    f"smoke evidence is stale ({age_hours:.1f}h > {max_age_hours}h) — "
                    "re-run scripts/pit/pit_tournament_dry_run.sh"
                )
    return {
        "metrics_path": str(metrics_path),
        "verdict": verdict,
        "generated_at": generated_at,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
    }


# ---------------------------------------------------------------------------
# Generate — render de ROLE.template.md + agents.yaml (generador §2-§3)
# ---------------------------------------------------------------------------


def _kpi_table(spec: PitSpec) -> str:
    lines = [
        "| kpi_id | nombre | unidad | objetivo | dirección | peso |",
        "|---|---|---|---|---|---|",
    ]
    for kpi in spec.kpi_definitions:
        lines.append(
            f"| {kpi.kpi_id} | {kpi.name} | {kpi.unit} | {kpi.kpi_expected} "
            f"| {kpi.direction} | {kpi.weight} |"
        )
    return "\n".join(lines)


def render_role(spec: PitSpec, lane: dict[str, str]) -> str:
    """Instancia ROLE.template.md con las variables del spec (generador §3)."""
    template = ROLE_TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{pit_id}}": spec.pit_id,
        "{{title}}": spec.title,
        "{{problem_statement}}": spec.problem_statement,
        "{{lane_id}}": lane["lane_id"],
        "{{lane_focus}}": lane["lane_focus"],
        "{{iteration_count}}": str(spec.iteration_count),
        "{{budget_lane_usd}}": f"{spec.budget_per_lane_usd:.2f}",
        "{{research_profile}}": spec.research_profile,
        "{{prototype_output}}": spec.prototype_output,
        "{{kpi_table}}": _kpi_table(spec),
        "{{hypothesis_seed}}": spec.hypothesis_seed or "(sin semilla — derivá del research)",
        "{{visual_enabled}}": str(spec.visual_generation.enabled).lower(),
        "{{visual_aspect_ratio}}": spec.visual_generation.aspect_ratio,
        "{{synthetic_enabled}}": str(spec.synthetic_personas.enabled).lower(),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    leftover = sorted(set(re.findall(r"{{[a-z_]+}}", rendered)))
    if leftover:
        raise RunBlocked(f"ROLE template placeholders left unrendered: {leftover}")
    return rendered


def build_agents_yaml(
    spec: PitSpec, lanes: list[dict[str, str]], *, created_at: str
) -> dict[str, Any]:
    """Registro de qué efímeros existieron (generador §2.5) — evidencia histórica."""
    return {
        "schema_version": 1,
        "pit_id": spec.pit_id,
        "created_at": created_at,
        "spawn_parent": "main",
        "generated_by": "scripts/pit/pit_tournament_run.py (PIT-2b)",
        "agents": [
            {
                "lane_id": lane["lane_id"],
                "agent_id": lane["agent_id"],
                "lane_focus": lane["lane_focus"],
                "created_at": created_at,
                "scope": f"pit/{spec.pit_id}/lanes/{lane['lane_id']}/",
                "status": "generated",
                "killed_at": None,
                "deregistered": False,
            }
            for lane in lanes
        ],
    }


def write_generated_artifacts(
    spec: PitSpec,
    lanes: list[dict[str, str]],
    agents_doc: dict[str, Any],
    *,
    vault: Path | None,
    out_dir: Path,
) -> dict[str, str]:
    """Escribe agents.yaml + roles renderizados en evidencia (y vault si aplica)."""
    roles_dir = out_dir / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for lane in lanes:
        role_path = roles_dir / f"{lane['lane_id']}.ROLE.md"
        role_path.write_text(lane["role"], encoding="utf-8")
        paths[lane["lane_id"]] = str(role_path)

    agents_yaml = yaml.safe_dump(agents_doc, allow_unicode=True, sort_keys=False)
    (out_dir / "agents.yaml").write_text(agents_yaml, encoding="utf-8")
    paths["agents_yaml"] = str(out_dir / "agents.yaml")

    if vault is not None:
        # pit/<pit_id>/spec/ es write del parent (Rick/runner), no de lanes.
        spec_dir = vault / "pit" / spec.pit_id / "spec"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "agents.yaml").write_text(agents_yaml, encoding="utf-8")
        paths["agents_yaml_vault"] = str(spec_dir / "agents.yaml")
        vault_roles = spec_dir / "agents"
        vault_roles.mkdir(parents=True, exist_ok=True)
        for lane in lanes:
            (vault_roles / f"{lane['lane_id']}.ROLE.md").write_text(
                lane["role"], encoding="utf-8"
            )
    return paths


# ---------------------------------------------------------------------------
# Register / deregister — agents.list de openclaw.json + allowAgents de main
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp-pit")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def register_ephemeral_agents(
    config_path: Path,
    spec: PitSpec,
    lanes: list[dict[str, str]],
    *,
    workspaces_root: Path,
    lane_model: str | None = None,
    lane_tools_profile: str | None = None,
    spawn_parent: str = "main",
) -> dict[str, Any]:
    """Alta de efímeros en ``agents.list`` + allowAgents del spawn parent.

    Mismo mecanismo documentado del stack (alta tipo ``openclaw agents add`` /
    baja vía edición de ``openclaw.json`` + restart — ver task VPS
    2026-05-05-003). Backup previo SIEMPRE; escritura atómica; el workspace de
    cada efímero recibe su ROLE renderizado como ``AGENTS.md``.
    """
    if not config_path.is_file():
        raise RunBlocked(f"openclaw config not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    agents_cfg = config.setdefault("agents", {})
    agents_list = agents_cfg.setdefault("list", [])
    if not isinstance(agents_list, list):
        raise RunBlocked("openclaw config agents.list is not a list")

    existing_ids = {entry.get("id") for entry in agents_list if isinstance(entry, dict)}
    clashes = [lane["agent_id"] for lane in lanes if lane["agent_id"] in existing_ids]
    if clashes:
        # No se reciclan agentes entre torneos ni se pisa un registro vivo.
        raise RunBlocked(f"ephemeral agent ids already registered: {clashes}")

    backup_path = config_path.with_name(config_path.name + f".bak-{spec.pit_id}")
    shutil.copyfile(config_path, backup_path)

    workspaces: dict[str, str] = {}
    for lane in lanes:
        workspace = workspaces_root / lane["agent_id"]
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "AGENTS.md").write_text(lane["role"], encoding="utf-8")
        workspaces[lane["agent_id"]] = str(workspace)
        entry: dict[str, Any] = {
            "id": lane["agent_id"],
            "name": f"PIT lane {lane['lane_id']} ({spec.pit_id})",
            "workspace": str(workspace),
            # Efímeros no spawnean a nadie (maxSpawnDepth los deja en depth 1).
            "subagents": {"allowAgents": []},
        }
        if lane_model:
            entry["model"] = lane_model
        if lane_tools_profile:
            entry["tools"] = {"profile": lane_tools_profile}
        agents_list.append(entry)

    # El spawn parent (main) debe poder spawnear los efímeros: allowAgents.
    allow_agents_patched = "absent"
    parent_entry = next(
        (
            entry
            for entry in agents_list
            if isinstance(entry, dict) and entry.get("id") == spawn_parent
        ),
        None,
    )
    if parent_entry is not None:
        allow = parent_entry.setdefault("subagents", {}).setdefault("allowAgents", [])
        if "*" in allow:
            allow_agents_patched = "wildcard"
        else:
            allow.extend(lane["agent_id"] for lane in lanes)
            allow_agents_patched = "parent-entry"
    else:
        defaults_sub = agents_cfg.get("defaults", {}).get("subagents", {})
        default_allow = defaults_sub.get("allowAgents")
        if isinstance(default_allow, list):
            if "*" in default_allow:
                allow_agents_patched = "wildcard-defaults"
            else:
                default_allow.extend(lane["agent_id"] for lane in lanes)
                allow_agents_patched = "defaults"

    _atomic_write_json(config_path, config)
    return {
        "backup_path": str(backup_path),
        "registered": [lane["agent_id"] for lane in lanes],
        "allow_agents_patched": allow_agents_patched,
        "workspaces": workspaces,
    }


def deregister_ephemeral_agents(
    config_path: Path,
    agent_ids: list[str],
    *,
    spawn_parent: str = "main",
) -> dict[str, Any]:
    """Baja del registro OpenClaw (agents.list + allowAgents). Workspaces quedan
    en disco como forense; los artefactos del torneo viven en el vault."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    agents_cfg = config.get("agents", {})
    agents_list = agents_cfg.get("list", [])
    ids = set(agent_ids)

    before = len(agents_list)
    agents_cfg["list"] = [
        entry
        for entry in agents_list
        if not (isinstance(entry, dict) and entry.get("id") in ids)
    ]
    removed = before - len(agents_cfg["list"])

    for entry in agents_cfg["list"]:
        if isinstance(entry, dict) and entry.get("id") == spawn_parent:
            allow = entry.get("subagents", {}).get("allowAgents")
            if isinstance(allow, list):
                entry["subagents"]["allowAgents"] = [a for a in allow if a not in ids]
    defaults_allow = agents_cfg.get("defaults", {}).get("subagents", {}).get("allowAgents")
    if isinstance(defaults_allow, list):
        agents_cfg["defaults"]["subagents"]["allowAgents"] = [
            a for a in defaults_allow if a not in ids
        ]

    _atomic_write_json(config_path, config)
    return {"deregistered": sorted(ids), "entries_removed": removed}


# ---------------------------------------------------------------------------
# Spawn — prompt de orquestación para main standalone (G-D1b)
# ---------------------------------------------------------------------------


def _lane_task_body(spec: PitSpec, lane: dict[str, str], vault: Path) -> str:
    """Task body del sessions_spawn: ROLE + wiring runtime (vault + announce file)."""
    announce_rel = f"pit/{spec.pit_id}/lanes/{lane['lane_id']}/{ANNOUNCE_FILE_NAME}"
    return (
        f"{lane['role']}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}` — todos los paths `pit/...` de arriba cuelgan de ahí.\n"
        f"- Write scope: `PIT_VAULT_WRITE_SCOPE=pit` — escribís SOLO bajo `pit/{spec.pit_id}/lanes/{lane['lane_id']}/`.\n"
        "- Cada cierre de iteración pasa por la task Worker `pit.iteration_close` (kpi_pack + kanban); "
        "tu announce se verifica con `pit.lane_announce` contra el vault.\n"
        f"- Lane result file (patrón D3.5b): al cerrar tu ÚLTIMA iteración escribí las 3 líneas literales "
        f"(PROTOTYPE_URL= / KPI_PACK= / FULFILLMENT=) en `{announce_rel}` y terminá la sesión. "
        "Sin ese archivo + kpi_pack verificable, tu lane cuenta como lane_incomplete.\n"
    )


def build_spawn_prompt(
    spec: PitSpec,
    lanes: list[dict[str, str]],
    *,
    vault: Path,
    lane_timeout_seconds: int,
) -> str:
    """Mensaje a ``main`` standalone: fan-out sessions_spawn × N en un turno + yield."""
    blocks: list[str] = [
        f"[PIT-2b] Torneo de producto {spec.pit_id} — spawn de {len(lanes)} lanes efímeras.",
        "",
        "Pre-condición G-D1b / ISSUE-001: si `sessions_spawn` NO está en tu tool set "
        f"(sesión nested), NO intentes spawnear: respondé literalmente `{SPAWN_BLOCKED_MARKER}` "
        "y terminá tu turno.",
        "",
        "Disparar los N spawns EN ESTE MISMO TURNO (fan-out paralelo), uno por lane:",
        "",
    ]
    for lane in lanes:
        spawn_call = {
            "runtime": "subagent",
            "agentId": lane["agent_id"],
            "label": lane["agent_id"],
            "timeoutSeconds": lane_timeout_seconds,
            "task": _lane_task_body(spec, lane, vault),
        }
        blocks.append(f"sessions_spawn({json.dumps(spawn_call, ensure_ascii=False, indent=2)})")
        blocks.append("")
    blocks.extend(
        [
            "Tras disparar los N spawns, respondé literalmente "
            f"`{SPAWN_FIRED_MARKER} {len(lanes)}` y terminá tu turno (yield). "
            "NO esperes los announces en tu transcript: el collect del torneo se "
            "verifica contra el pit-vault (lane result files), patrón D3.5b.",
            "",
            "Guardrails: no merges, no publiques, no toques Notion, no llames "
            "Magnific (las lanes lo piden vía Rick broker), nunca URL pública.",
        ]
    )
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Collect — vault como fuente de verdad (pit.lane_announce + announce.md)
# ---------------------------------------------------------------------------


def _collect_lane_state(vault: Path, pit_id: str, lane_id: str) -> dict[str, Any]:
    """Estado actual de una lane: announce.md (señal de cierre) + verificación vault."""
    announce_file = vault / "pit" / pit_id / "lanes" / lane_id / ANNOUNCE_FILE_NAME
    state: dict[str, Any] = {
        "lane_id": lane_id,
        "announce_file_present": announce_file.is_file(),
        "lane_complete": False,
        "incomplete_reasons": [],
    }
    try:
        # Misma implementación que la task Worker pit.lane_announce (regla de
        # verdad del SKILL §Cierre): kpi_pack válido + fulfillment reproducible.
        announce = core.lane_announce(vault, pit_id, lane_id)
    except ValueError as exc:
        state["incomplete_reasons"] = [str(exc)]
        return state
    state.update(
        {
            "iteration": announce["iteration"],
            "fulfillment": announce["fulfillment"],
            "kpi_pack": announce["kpi_pack"],
            "prototype_url": announce["prototype_url"],
            "announce": announce["announce"],
            "incomplete_reasons": list(announce["incomplete_reasons"]),
        }
    )
    if not state["announce_file_present"]:
        state["incomplete_reasons"].append(
            f"missing lane result file {ANNOUNCE_FILE_NAME} (lane did not declare close)"
        )
    state["lane_complete"] = announce["lane_complete"] and state["announce_file_present"]
    return state


def collect_lanes(
    vault: Path,
    pit_id: str,
    lanes: list[dict[str, str]],
    *,
    timeout_seconds: float,
    poll_seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Espera el cierre de todas las lanes contra el vault (yield del parent).

    lane_complete obligatorio: announce.md presente + kpi_pack reproducible.
    Devuelve el estado final por lane (completas o no) al completar o vencer
    el timeout.
    """
    deadline = clock() + timeout_seconds
    states: dict[str, dict[str, Any]] = {}
    pending = [lane["lane_id"] for lane in lanes]
    while True:
        for lane_id in list(pending):
            state = _collect_lane_state(vault, pit_id, lane_id)
            states[lane_id] = state
            if state["lane_complete"]:
                pending.remove(lane_id)
                _log(
                    f"collect: {lane_id} lane_complete fulfillment={state.get('fulfillment')}"
                )
        if not pending or clock() >= deadline:
            break
        sleep(poll_seconds)
    for lane_id in pending:
        _log(
            f"collect: {lane_id} INCOMPLETE — {states[lane_id]['incomplete_reasons']}"
        )
    return [states[lane["lane_id"]] for lane in lanes]


# ---------------------------------------------------------------------------
# Kill — solo hijos del torneo (label = agent_id efímero, lleva el pit_id)
# ---------------------------------------------------------------------------


def kill_tournament_subagents(cli: OpenClawCli, pit_id: str) -> dict[str, Any]:
    """Mata los subagentes vivos del torneo (nunca hijos ajenos al pit_id)."""
    listing = cli.tasks_list_subagents()
    if listing.returncode != 0:
        return {
            "verdict": "list_failed",
            "detail": (listing.stderr or listing.stdout or "").strip()[:500],
            "killed": [],
        }
    try:
        tasks = json.loads(listing.stdout or "[]")
    except json.JSONDecodeError:
        return {"verdict": "list_unparseable", "killed": []}

    prefix = f"{pit_id}-lane-"
    killed: list[dict[str, Any]] = []
    for task in tasks if isinstance(tasks, list) else []:
        if not isinstance(task, dict):
            continue
        label = str(task.get("label") or "")
        task_id = str(task.get("id") or "")
        if not task_id or not label.startswith(prefix):
            continue
        result = cli.subagent_kill(task_id)
        killed.append(
            {"task_id": task_id, "label": label, "returncode": result.returncode}
        )
    return {"verdict": "ok", "killed": killed}


# ---------------------------------------------------------------------------
# Run end-to-end
# ---------------------------------------------------------------------------


def _verdict_for(lane_states: list[dict[str, Any]], spawn_ok: bool) -> str:
    complete = sum(1 for state in lane_states if state.get("lane_complete"))
    if not spawn_ok:
        return RUN_FAIL
    if lane_states and complete == len(lane_states):
        return RUN_PASS
    # Judge solo con >=2 lanes completas (SKILL §Cierre, paralelo docs/79 §4.1).
    if complete >= 2:
        return RUN_PARTIAL
    return RUN_FAIL


def run_tournament(
    spec_path: Path,
    lanes_path: Path,
    *,
    gate: str,
    vault_path: Path | None = None,
    evidence_dir: Path | None = None,
    smoke_metrics_path: Path | None = None,
    max_smoke_age_hours: float = DEFAULT_MAX_SMOKE_AGE_HOURS,
    openclaw_config: Path | None = None,
    workspaces_root: Path | None = None,
    lane_model: str | None = None,
    lane_tools_profile: str | None = None,
    lane_timeout_seconds: int = DEFAULT_LANE_TIMEOUT_SECONDS,
    spawn_timeout_seconds: float = DEFAULT_SPAWN_TIMEOUT_SECONDS,
    collect_timeout_seconds: float = DEFAULT_COLLECT_TIMEOUT_SECONDS,
    collect_poll_seconds: float = DEFAULT_COLLECT_POLL_SECONDS,
    plan_only: bool = False,
    skip_gateway_restart: bool = False,
    cli: OpenClawCli | None = None,
) -> dict[str, Any]:
    """Orquesta el torneo PIT real end-to-end y persiste run-metrics.json."""
    started_at = _utcnow().isoformat()

    # Gate David — frase literal, sin variantes (SKILL §Fase de confirmación).
    if gate != GATE_PHRASE:
        raise RunBlocked(
            f"gate phrase mismatch: spawn real requires the literal phrase "
            f"{GATE_PHRASE!r} from David (got {gate!r})"
        )

    spec = load_spec(spec_path)
    lanes = load_lanes(lanes_path, spec)
    vault = (vault_path or Path(os.environ.get("PIT_VAULT_PATH") or DEFAULT_VAULT_PATH)).expanduser()
    evidence = (evidence_dir or DEFAULT_EVIDENCE_ROOT / spec.pit_id).expanduser()
    evidence.mkdir(parents=True, exist_ok=True)
    config_path = (
        openclaw_config
        or Path(os.environ.get("OPENCLAW_CONFIG_PATH") or DEFAULT_OPENCLAW_CONFIG)
    ).expanduser()
    cli = cli or OpenClawCli(os.environ.get("OPENCLAW_BIN", "openclaw"))

    # 1. Smoke gate — PIT_DRY_RUN_PASS o no hay torneo.
    smoke = check_smoke_gate(
        spec, smoke_metrics_path=smoke_metrics_path, max_age_hours=max_smoke_age_hours
    )
    _log(f"smoke gate: {smoke['verdict']} ({smoke['metrics_path']})")

    # 2. Preflight real contra el vault prod (misma impl que task pit.preflight).
    previous_scope = os.environ.get("PIT_VAULT_WRITE_SCOPE")
    os.environ["PIT_VAULT_WRITE_SCOPE"] = "pit"
    try:
        preflight = core.preflight(spec_path, vault, require_write_scope=True)
        _log(f"preflight: {preflight['verdict']}")
        if not preflight["ok"]:
            raise RunBlocked(f"preflight failed: {preflight['errors']}")

        for lane in lanes:
            lane["role"] = render_role(spec, lane)

        agents_doc = build_agents_yaml(spec, lanes, created_at=started_at)
        spawn_prompt = build_spawn_prompt(
            spec, lanes, vault=vault, lane_timeout_seconds=lane_timeout_seconds
        )
        (evidence / "spawn-prompt.md").write_text(spawn_prompt, encoding="utf-8")

        metrics: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pit_run_metrics",
            "generated_by": "scripts/pit/pit_tournament_run.py (PIT-2b)",
            "started_at": started_at,
            "pit_id": spec.pit_id,
            "spec_path": str(spec_path),
            "lanes_path": str(lanes_path),
            "vault_path": str(vault),
            "lane_count": spec.lane_count,
            "iteration_count": spec.iteration_count,
            "smoke_gate": smoke,
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
                "magnific_direct": False,
                "public_url": False,
                "spawn_parent": "main (standalone, G-D1b)",
            },
        }

        if plan_only:
            write_generated_artifacts(
                spec, lanes, agents_doc, vault=None, out_dir=evidence
            )
            metrics["verdict"] = RUN_PLAN_ONLY
            _log("plan-only: roles + agents.yaml + spawn-prompt renderizados; sin registro ni spawn")
            _write_metrics(evidence, metrics)
            return metrics

        if not cli.available():
            raise RunBlocked(
                f"openclaw binary not found ({cli.bin_path}) — set OPENCLAW_BIN or run on the VPS"
            )

        artifact_paths = write_generated_artifacts(
            spec, lanes, agents_doc, vault=vault, out_dir=evidence
        )
        metrics["artifacts"] = artifact_paths

        # 3. Registro de efímeros (alta en openclaw.json + restart gateway).
        registration = register_ephemeral_agents(
            config_path,
            spec,
            lanes,
            workspaces_root=(workspaces_root or DEFAULT_WORKSPACES_ROOT).expanduser(),
            lane_model=lane_model,
            lane_tools_profile=lane_tools_profile,
        )
        metrics["registration"] = registration
        for agent in agents_doc["agents"]:
            agent["status"] = "registered"

        spawn_ok = False
        lane_states: list[dict[str, Any]] = []
        try:
            # Desde acá los efímeros existen en el registro: cualquier salida
            # (éxito, restart roto, timeout) pasa por el cleanup del finally.
            if not skip_gateway_restart:
                restart = cli.gateway_restart()
                metrics["registration"]["gateway_restart_rc"] = restart.returncode
                if restart.returncode != 0:
                    raise RunBlocked(
                        "gateway restart failed after registration — config backup at "
                        f"{registration['backup_path']}"
                    )

            # 4. Spawn vía main standalone (G-D1b): sessions_spawn × N + yield.
            _log(f"spawn: openclaw agent --agent main ({len(lanes)} lanes)")
            try:
                spawn_result = cli.agent_message(
                    "main", spawn_prompt, timeout=spawn_timeout_seconds
                )
                spawn_rc: int | None = spawn_result.returncode
                spawn_output = (spawn_result.stdout or "") + (spawn_result.stderr or "")
            except subprocess.TimeoutExpired as exc:
                spawn_rc = None
                spawn_output = f"TIMEOUT after {spawn_timeout_seconds}s: {exc}"
            (evidence / "openclaw-spawn.log").write_text(spawn_output, encoding="utf-8")
            metrics["spawn"] = {
                "returncode": spawn_rc,
                "blocked_issue_001": SPAWN_BLOCKED_MARKER in spawn_output,
                "fired_marker_seen": SPAWN_FIRED_MARKER in spawn_output,
                "log_path": str(evidence / "openclaw-spawn.log"),
            }
            if spawn_rc != 0:
                _log("spawn: openclaw agent failed (rc != 0 / timeout) — skipping collect")
            elif SPAWN_BLOCKED_MARKER in spawn_output:
                _log("spawn: blocked by ISSUE-001 (nested session, no sessions_spawn)")
            else:
                spawn_ok = True
                for agent in agents_doc["agents"]:
                    agent["status"] = "spawned"
                # 5. Collect contra el vault (lane result files).
                lane_states = collect_lanes(
                    vault,
                    spec.pit_id,
                    lanes,
                    timeout_seconds=collect_timeout_seconds,
                    poll_seconds=collect_poll_seconds,
                )
        finally:
            # 6. Kill + desregistro SIEMPRE (aunque collect/spawn hayan fallado).
            killed_at = _utcnow().isoformat()
            kill_report = kill_tournament_subagents(cli, spec.pit_id)
            metrics["kill"] = kill_report
            try:
                dereg = deregister_ephemeral_agents(
                    config_path, [lane["agent_id"] for lane in lanes]
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
            # agents.yaml final = histórico de qué existió (generador §2.7).
            write_generated_artifacts(spec, lanes, agents_doc, vault=vault, out_dir=evidence)

        metrics["lane_results"] = lane_states
        metrics["lanes_completed"] = sum(1 for s in lane_states if s.get("lane_complete"))
        metrics["verdict"] = _verdict_for(lane_states, spawn_ok)
        _write_metrics(evidence, metrics)
        return metrics
    finally:
        if previous_scope is None:
            os.environ.pop("PIT_VAULT_WRITE_SCOPE", None)
        else:
            os.environ["PIT_VAULT_WRITE_SCOPE"] = previous_scope


def _write_metrics(evidence: Path, metrics: dict[str, Any]) -> None:
    metrics["finished_at"] = _utcnow().isoformat()
    metrics_path = evidence / "run-metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metrics["run_metrics_path"] = str(metrics_path)
    _log(f"run-metrics: {metrics_path}")
    _log(f"verdict: {metrics['verdict']}")


def _is_broker_spec_file(path: Path) -> bool:
    """True si el pit_spec en disco es v2/broker (schema_version 2 o broker_contract)."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return False
    return isinstance(raw, dict) and is_broker_spec(raw)


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    # Dispatch broker (pit_spec v2 / P10): si el primer positional es un spec
    # broker, delega el run COMPLETO a pit_broker_run sin tocar el camino v1 de
    # producto (su parser queda intacto y maneja todos los flags broker-only).
    if (
        raw_args
        and not raw_args[0].startswith("-")
        and _is_broker_spec_file(Path(raw_args[0]))
    ):
        from scripts.pit import pit_broker_run

        _log("broker spec detected -> delegating to pit_broker_run (P10)")
        return pit_broker_run.main(raw_args)

    parser = argparse.ArgumentParser(
        description="PIT-2b — spawn real de agentes efímeros OpenClaw (post-smoke)."
    )
    parser.add_argument("spec_path", type=Path, help="Path al pit_spec YAML/JSON validado.")
    parser.add_argument(
        "lanes_path",
        type=Path,
        help="Lanes file YAML (lanes: [{lane_id, lane_focus}, ...]) derivado por Rick.",
    )
    parser.add_argument(
        "--gate",
        required=True,
        help=f"Frase literal del gate David ({GATE_PHRASE!r}). Sin ella no hay spawn.",
    )
    parser.add_argument("--vault-path", type=Path, default=None,
                        help="pit-vault real (default: $PIT_VAULT_PATH o ~/umbral-pit-vault).")
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="Evidencia (default: ~/.coord-ag-evidence/pit-run/<pit_id>).")
    parser.add_argument("--smoke-metrics", type=Path, default=None,
                        help="final-metrics.json del dry-run (default: evidencia estándar PIT-2).")
    parser.add_argument("--max-smoke-age-hours", type=float, default=DEFAULT_MAX_SMOKE_AGE_HOURS,
                        help="Edad máxima del smoke PASS (0 = sin límite).")
    parser.add_argument("--openclaw-config", type=Path, default=None,
                        help="openclaw.json (default: $OPENCLAW_CONFIG_PATH o ~/.openclaw/openclaw.json).")
    parser.add_argument("--workspaces-root", type=Path, default=None,
                        help="Raíz de workspaces efímeros (default: ~/.openclaw/workspaces).")
    parser.add_argument("--lane-model", default=None,
                        help="Model override para los agentes efímeros (opcional).")
    parser.add_argument("--lane-tools-profile", default=None,
                        help="tools.profile mínimo para los efímeros (lo fija Copilot-VPS).")
    parser.add_argument("--lane-timeout-seconds", type=int, default=DEFAULT_LANE_TIMEOUT_SECONDS)
    parser.add_argument("--spawn-timeout-seconds", type=float, default=DEFAULT_SPAWN_TIMEOUT_SECONDS)
    parser.add_argument("--collect-timeout-seconds", type=float, default=DEFAULT_COLLECT_TIMEOUT_SECONDS)
    parser.add_argument("--collect-poll-seconds", type=float, default=DEFAULT_COLLECT_POLL_SECONDS)
    parser.add_argument("--plan-only", action="store_true",
                        help="Renderiza plan (roles + agents.yaml + prompt) sin registrar ni spawnear.")
    parser.add_argument("--skip-gateway-restart", action="store_true",
                        help="No reiniciar el gateway tras alta/baja (operador lo hace a mano).")
    args = parser.parse_args(argv)

    try:
        metrics = run_tournament(
            args.spec_path,
            args.lanes_path,
            gate=args.gate,
            vault_path=args.vault_path,
            evidence_dir=args.evidence_dir,
            smoke_metrics_path=args.smoke_metrics,
            max_smoke_age_hours=args.max_smoke_age_hours,
            openclaw_config=args.openclaw_config,
            workspaces_root=args.workspaces_root,
            lane_model=args.lane_model,
            lane_tools_profile=args.lane_tools_profile,
            lane_timeout_seconds=args.lane_timeout_seconds,
            spawn_timeout_seconds=args.spawn_timeout_seconds,
            collect_timeout_seconds=args.collect_timeout_seconds,
            collect_poll_seconds=args.collect_poll_seconds,
            plan_only=args.plan_only,
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
