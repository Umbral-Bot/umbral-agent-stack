#!/usr/bin/env python3
"""P10 — OpenClaw broker-real tournament runner (pit_spec v2).

Cierra el gap PIT-2b ↔ P9
(docs/ops/pit-broker-real-pass-handoff-20260622.md §4): P9 probó el broker con
POSTs directos al Worker (``openclaw_total=0``, sin agentes); P10 orquesta
agentes EFÍMEROS OpenClaw ``<pit_id>-lane-*`` donde cada lane despacha UNA
``copilot_cli.run`` al Worker (contrato broker P4). Cada sesión efímera deja sus
tokens en ``~/.openclaw/agents/<pit_id>-lane-*/sessions.json`` →
``openclaw_total>0`` en el ledger (scripts/pit/pit_collect_tokens.py).

Este es el camino v2 (``schema_version: 2`` / broker spec). El runner v1 de
producto (scripts/pit/pit_tournament_run.run_tournament) queda INTACTO: el
dispatcher ``pit_tournament_run.main`` enruta acá cuando el spec es broker
(pit_spec_validate.is_broker_spec). Reusa los boundaries OpenClaw del runner v1
(register / deregister / kill / OpenClawCli) para no duplicar el ciclo de vida.

Veredictos (``run-metrics.json.verdict``):

- ``P10_OPENCLAW_BROKER_RUN_PASS`` — todas las lanes broker_complete (exit 0).
- ``P10_OPENCLAW_BROKER_PARTIAL`` — ≥2 lanes completas pero no todas.
- ``P10_OPENCLAW_BROKER_FAIL`` — <2 lanes completas / spawn no disparó.
- ``P10_OPENCLAW_BROKER_BLOCKED`` — gate/smoke/preflight/registro fallaron pre-spawn.
- ``P10_OPENCLAW_BROKER_PLAN_OK`` — ``--plan-only``: artefactos renderizados, sin
  registro ni spawn.

Gate David (spawn real): frase literal ``ok, arranca`` (igual que PIT-2b). El
``--plan-only`` NO la exige (divergencia deliberada y segura vs. v1): plan-only es
render + validación pura, nunca registra ni spawnea, así que no necesita
autorización de spawn. El spawn real SIEMPRE exige la frase.

Uso (vía scripts/pit/pit_openclaw_broker_run.sh o directo)::

    python scripts/pit/pit_broker_run.py <spec.yaml> [<lanes.yaml>] --plan-only
    python scripts/pit/pit_broker_run.py <spec.yaml> [<lanes.yaml>] \
        --gate "ok, arranca"            # spawn real (VPS, ventana autorizada)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

try:
    from scripts.pit import pit_runner_core as core
    from scripts.pit import pit_tournament_run as v1
    from scripts.pit.pit_dry_run import (
        DEFAULT_EVIDENCE_ROOT as DRY_RUN_EVIDENCE_ROOT,
        DRY_RUN_FAIL,
        DRY_RUN_PASS,
    )
    from scripts.pit.pit_spec_validate import (
        BrokerLane,
        PitSpecV2,
        is_broker_spec,
        load_broker_spec,
        validate_broker_file,
    )
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_runner_core as core
    from scripts.pit import pit_tournament_run as v1
    from scripts.pit.pit_dry_run import (
        DEFAULT_EVIDENCE_ROOT as DRY_RUN_EVIDENCE_ROOT,
        DRY_RUN_FAIL,
        DRY_RUN_PASS,
    )
    from scripts.pit.pit_spec_validate import (
        BrokerLane,
        PitSpecV2,
        is_broker_spec,
        load_broker_spec,
        validate_broker_file,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
BROKER_ROLE_TEMPLATE_PATH = (
    REPO_ROOT
    / "openclaw"
    / "workspace-templates"
    / "pit-lane-agent"
    / "ROLE.template.broker.md"
)

# Reusa el gate/marcadores/boundaries del runner v1 (misma semántica de spawn).
GATE_PHRASE = v1.GATE_PHRASE
SPAWN_BLOCKED_MARKER = v1.SPAWN_BLOCKED_MARKER
SPAWN_FIRED_MARKER = v1.SPAWN_FIRED_MARKER
ANNOUNCE_FILE_NAME = v1.ANNOUNCE_FILE_NAME
RunBlocked = v1.RunBlocked
OpenClawCli = v1.OpenClawCli

DEFAULT_WORKER_URL = "http://127.0.0.1:8088"
BROKER_RESULT_FILE_NAME = "broker_result.json"

BROKER_RUN_PASS = "P10_OPENCLAW_BROKER_RUN_PASS"
BROKER_RUN_PARTIAL = "P10_OPENCLAW_BROKER_PARTIAL"
BROKER_RUN_FAIL = "P10_OPENCLAW_BROKER_FAIL"
BROKER_RUN_BLOCKED = "P10_OPENCLAW_BROKER_BLOCKED"
BROKER_RUN_PLAN_ONLY = "P10_OPENCLAW_BROKER_PLAN_OK"

DEFAULT_VAULT_PATH = v1.DEFAULT_VAULT_PATH
DEFAULT_EVIDENCE_ROOT = Path.home() / ".coord-ag-evidence" / "pit-openclaw-broker"
DEFAULT_OPENCLAW_CONFIG = v1.DEFAULT_OPENCLAW_CONFIG
DEFAULT_WORKSPACES_ROOT = v1.DEFAULT_WORKSPACES_ROOT

DEFAULT_LANE_TIMEOUT_SECONDS = v1.DEFAULT_LANE_TIMEOUT_SECONDS
DEFAULT_COLLECT_TIMEOUT_SECONDS = v1.DEFAULT_COLLECT_TIMEOUT_SECONDS
DEFAULT_COLLECT_POLL_SECONDS = v1.DEFAULT_COLLECT_POLL_SECONDS
DEFAULT_SPAWN_TIMEOUT_SECONDS = v1.DEFAULT_SPAWN_TIMEOUT_SECONDS
DEFAULT_MAX_SMOKE_AGE_HOURS = v1.DEFAULT_MAX_SMOKE_AGE_HOURS

_PLACEHOLDER_RE = re.compile(r"{{[a-z_]+}}")


def _log(message: str) -> None:
    print(f"[pit-broker] {message}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Spec dispatch — peek schema_version y enrutar v1/v2
# ---------------------------------------------------------------------------


def load_pit_spec(path: Path) -> tuple[str, Any]:
    """Peek a pit_spec file and route to the right schema.

    Returns ``("broker", PitSpecV2)`` for v2 broker specs, or ``("product",
    None)`` for v1 product specs (the caller loads v1 via
    ``pit_tournament_run.load_spec``). Keeps the schema decision in one place so
    both entrypoints (this module and ``pit_tournament_run.main``) agree.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RunBlocked(f"pit_spec is not a mapping: {path}")
    if is_broker_spec(raw):
        return "broker", load_broker_spec(Path(path))
    return "product", None


# ---------------------------------------------------------------------------
# Lanes — del spec v2 (+ enriquecimiento lane_focus opcional)
# ---------------------------------------------------------------------------


def load_lane_enrichment(lanes_path: Path | None) -> dict[str, dict[str, Any]]:
    """Optional ``lanes.yaml`` enrichment: per-lane ``lane_focus`` (the prompt).

    Format mirrors v1 (``lanes: [{lane_id, lane_focus}, ...]``) but every field
    is optional for broker mode — when absent a deterministic read-only focus is
    derived from the lane mission.
    """
    if lanes_path is None:
        return {}
    data = yaml.safe_load(Path(lanes_path).read_text(encoding="utf-8")) or {}
    items = data.get("lanes") if isinstance(data, dict) else data
    out: dict[str, dict[str, Any]] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        lane_id = str(item.get("lane_id") or "").strip()
        if lane_id:
            out[lane_id] = item
    return out


def _default_lane_focus(spec: PitSpecV2, lane: BrokerLane) -> str:
    return (
        f"Read-only {lane.mission} probe via the copilot_cli broker for "
        f"{lane.lane_id} on {spec.pit_id}: summarize the repository purpose and "
        "cite the most relevant files. Do not modify anything."
    )


def build_broker_lanes(
    spec: PitSpecV2,
    *,
    enrichment: dict[str, dict[str, Any]],
    batch_id: str,
) -> list[dict[str, Any]]:
    """Materialize lane dicts (id/model/effort/mission/focus/agent_id/batch_id).

    ``lane_id`` is re-checked against the stricter ``core.LANE_ID_RE`` (the
    validator only enforces the loose PIT regex) because it becomes the agent id
    and the vault path segment — same guard the v1 runner relies on.
    """
    lanes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for lane in spec.lanes:
        lane_id = lane.lane_id
        if not core.LANE_ID_RE.match(lane_id):
            raise RunBlocked(
                f"lane_id {lane_id!r} must match {core.LANE_ID_RE.pattern} "
                "(it becomes the agent id + vault path segment)"
            )
        if lane_id in seen:
            raise RunBlocked(f"duplicate lane_id in spec: {lane_id}")
        seen.add(lane_id)
        enr = enrichment.get(lane_id, {})
        lane_focus = str(enr.get("lane_focus") or _default_lane_focus(spec, lane)).strip()
        if not lane_focus:
            raise RunBlocked(f"lanes[{lane_id}].lane_focus resolved empty")
        if '"' in lane_focus or "\n" in lane_focus:
            # lane_focus se embebe como string JSON en el ROLE/spawn-prompt.
            raise RunBlocked(
                f"lane_focus for {lane_id} must not contain quotes or newlines "
                "(it is embedded into the broker JSON payload)"
            )
        lanes.append(
            {
                "lane_id": lane_id,
                "model": lane.model,
                "reasoning_effort": lane.reasoning_effort,
                "mission": lane.mission,
                "max_iterations": lane.max_iterations,
                "lane_focus": lane_focus,
                # Identidad efímera 1:1 con el torneo (lleva el pit_id): nunca se
                # recicla entre torneos.
                "agent_id": f"{spec.pit_id}-{lane_id}",
                "batch_id": batch_id,
            }
        )
    return lanes


# ---------------------------------------------------------------------------
# Smoke gate — exige el dry-run broker en PIT_DRY_RUN_PASS para este pit_id
# ---------------------------------------------------------------------------


def check_broker_smoke_gate(
    spec: PitSpecV2,
    *,
    smoke_metrics_path: Path | None = None,
    max_age_hours: float = DEFAULT_MAX_SMOKE_AGE_HOURS,
) -> dict[str, Any]:
    """Gate post-smoke: PIT_DRY_RUN_PASS fresco para el MISMO pit_id + lane_count.

    Paralelo a ``pit_tournament_run.check_smoke_gate`` pero leyendo
    ``lane_count`` de ``len(spec.lanes)`` (PitSpecV2 no tiene atributos de
    producto). Smoke rojo o ausente ⇒ no spawn.
    """
    metrics_path = smoke_metrics_path or (
        DRY_RUN_EVIDENCE_ROOT / spec.pit_id / "final-metrics.json"
    )
    if not metrics_path.is_file():
        raise RunBlocked(
            f"smoke evidence not found: {metrics_path} — "
            "run scripts/pit/pit_broker_dry_run.sh first"
        )
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunBlocked(
            f"smoke evidence is not valid JSON ({metrics_path}): {exc}"
        ) from exc

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
    lane_count = len(spec.lanes)
    if metrics.get("lane_count") != lane_count:
        raise RunBlocked(
            f"smoke evidence lane_count {metrics.get('lane_count')!r} does not match "
            f"spec lane_count {lane_count!r} — re-run the broker smoke for this spec"
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
                    "re-run scripts/pit/pit_broker_dry_run.sh"
                )
    return {
        "metrics_path": str(metrics_path),
        "verdict": verdict,
        "generated_at": generated_at,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
    }


# ---------------------------------------------------------------------------
# Render ROLE broker + agents.yaml
# ---------------------------------------------------------------------------


def render_broker_role(
    spec: PitSpecV2, lane: dict[str, Any], *, worker_url: str
) -> str:
    """Instancia ROLE.template.broker.md con las variables del spec/lane."""
    template = BROKER_ROLE_TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{lane_id}}": lane["lane_id"],
        "{{pit_id}}": spec.pit_id,
        "{{title}}": spec.title or spec.pit_id,
        "{{model}}": lane["model"],
        "{{reasoning_effort}}": lane["reasoning_effort"],
        "{{mission}}": lane["mission"],
        "{{lane_focus}}": lane["lane_focus"],
        "{{max_iterations}}": str(lane["max_iterations"]),
        "{{worker_url}}": worker_url,
        "{{repo_path}}": spec.repo_path,
        "{{batch_id}}": lane["batch_id"],
        "{{agent_id}}": lane["agent_id"],
        "{{budget_usd_total}}": f"{spec.budget_usd_total:.2f}",
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    leftover = sorted(set(_PLACEHOLDER_RE.findall(rendered)))
    if leftover:
        raise RunBlocked(
            f"broker ROLE template placeholders left unrendered: {leftover}"
        )
    return rendered


def build_broker_agents_yaml(
    spec: PitSpecV2, lanes: list[dict[str, Any]], *, created_at: str
) -> dict[str, Any]:
    """Registro histórico de qué efímeros broker existieron (evidencia)."""
    return {
        "schema_version": 1,
        "mode": "broker",
        "pit_id": spec.pit_id,
        "created_at": created_at,
        "spawn_parent": "main",
        "generated_by": "scripts/pit/pit_broker_run.py (P10)",
        "agents": [
            {
                "lane_id": lane["lane_id"],
                "agent_id": lane["agent_id"],
                "model": lane["model"],
                "reasoning_effort": lane["reasoning_effort"],
                "mission": lane["mission"],
                "batch_id": lane["batch_id"],
                "created_at": created_at,
                "scope": f"pit/{spec.pit_id}/lanes/{lane['lane_id']}/",
                "status": "generated",
                "killed_at": None,
                "deregistered": False,
            }
            for lane in lanes
        ],
    }


# ---------------------------------------------------------------------------
# Spawn — prompt de orquestación para main standalone (G-D1b), modo broker
# ---------------------------------------------------------------------------


def _broker_payload(spec: PitSpecV2, lane: dict[str, Any]) -> dict[str, Any]:
    """Cuerpo canónico P4 del ``copilot_cli.run`` que despacha la lane."""
    return {
        "mission": lane["mission"],
        "model": lane["model"],
        "reasoning_effort": lane["reasoning_effort"],
        "prompt": lane["lane_focus"],
        "repo_path": spec.repo_path,
        "dry_run": False,
        "metadata": {
            "batch_id": lane["batch_id"],
            "agent_id": lane["agent_id"],
            "pit_id": spec.pit_id,
            "lane_id": lane["lane_id"],
            "iteration": 1,
        },
    }


def _broker_lane_task_body(
    spec: PitSpecV2, lane: dict[str, Any], *, worker_url: str, vault: Path
) -> str:
    """Task body del sessions_spawn: ROLE + wiring broker (worker-call + cierre)."""
    lane_dir = f"pit/{spec.pit_id}/lanes/{lane['lane_id']}"
    announce_rel = f"{lane_dir}/{ANNOUNCE_FILE_NAME}"
    result_rel = f"{lane_dir}/{BROKER_RESULT_FILE_NAME}"
    result_abs = f"{vault}/{result_rel}"
    payload_json = json.dumps(_broker_payload(spec, lane), ensure_ascii=False)
    bash = (
        "worker-call copilot_cli.run "
        + repr(payload_json)
        + f" > '{result_abs}'"
    )
    return (
        f"{lane['role']}\n\n"
        "## Wiring runtime (no negociable)\n\n"
        f"- pit-vault (raíz absoluta): `{vault}` — todos los paths `pit/...` cuelgan de ahí.\n"
        f"- Write scope: SOLO bajo `{lane_dir}/`.\n"
        "- Despachá EXACTAMENTE UNA vez (sin reintentos) la task broker contra el "
        f"Worker en `{worker_url}` usando el wrapper `worker-call` (toma "
        "`WORKER_URL`/`WORKER_TOKEN` de tu entorno; NUNCA los imprimas ni los "
        "pongas en el payload):\n\n"
        f"```bash\n{bash}\n```\n\n"
        f"- Guardá la respuesta JSON íntegra (redactada de secretos) en `{result_rel}`.\n"
        f"- Cerrá tu lane escribiendo en `{announce_rel}` las 3 líneas literales "
        "`BROKER_EXECUTED=` / `BROKER_EXIT=` / `BROKER_AUDIT_ID=` (ver tu ROLE). "
        f"Sin `{BROKER_RESULT_FILE_NAME}` + `BROKER_EXECUTED=true` + `BROKER_EXIT=0`, "
        "tu lane cuenta como lane_incomplete.\n"
    )


def build_broker_spawn_prompt(
    spec: PitSpecV2,
    lanes: list[dict[str, Any]],
    *,
    worker_url: str,
    vault: Path,
    lane_timeout_seconds: int,
) -> str:
    """Mensaje a ``main`` standalone: fan-out sessions_spawn × N broker + yield."""
    blocks: list[str] = [
        f"[P10-broker] Torneo broker {spec.pit_id} — spawn de {len(lanes)} lanes "
        "efímeras (cada una despacha UNA copilot_cli.run al Worker).",
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
            "task": _broker_lane_task_body(
                spec, lane, worker_url=worker_url, vault=vault
            ),
        }
        blocks.append(
            f"sessions_spawn({json.dumps(spawn_call, ensure_ascii=False, indent=2)})"
        )
        blocks.append("")
    blocks.extend(
        [
            "Tras disparar los N spawns, respondé literalmente "
            f"`{SPAWN_FIRED_MARKER} {len(lanes)}` y terminá tu turno (yield). "
            "NO esperes los announces en tu transcript: el collect del torneo se "
            "verifica contra el pit-vault (broker_result.json + announce.md).",
            "",
            "Guardrails: no merges, no publiques, no toques Notion, una sola "
            "copilot_cli.run por lane (sin reintentos), nunca imprimas WORKER_TOKEN.",
        ]
    )
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Collect — vault como fuente de verdad (broker_result.json + announce.md)
# ---------------------------------------------------------------------------


def _parse_broker_announce(text: str) -> dict[str, str]:
    """Extrae las 3 líneas literales BROKER_* del announce.md."""
    keys = ("BROKER_EXECUTED", "BROKER_EXIT", "BROKER_AUDIT_ID")
    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for key in keys:
            if line.startswith(key + "="):
                out[key] = line[len(key) + 1 :].strip()
    return out


def _collect_broker_lane_state(
    vault: Path, pit_id: str, lane: dict[str, Any]
) -> dict[str, Any]:
    """Estado de una lane broker: announce.md (BROKER_*) + broker_result.json."""
    lane_id = lane["lane_id"]
    lane_dir = vault / "pit" / pit_id / "lanes" / lane_id
    announce_file = lane_dir / ANNOUNCE_FILE_NAME
    result_file = lane_dir / BROKER_RESULT_FILE_NAME
    reasons: list[str] = []
    executed = False
    exit_code: int | None = None
    audit_id: str | None = None

    if announce_file.is_file():
        parsed = _parse_broker_announce(announce_file.read_text(encoding="utf-8"))
        executed = parsed.get("BROKER_EXECUTED", "").lower() == "true"
        raw_exit = parsed.get("BROKER_EXIT")
        if raw_exit in (None, ""):
            reasons.append("BROKER_EXIT missing")
        else:
            try:
                exit_code = int(raw_exit)
            except ValueError:
                reasons.append(f"BROKER_EXIT not an int: {raw_exit!r}")
        audit_id = parsed.get("BROKER_AUDIT_ID") or None
        if not executed:
            reasons.append("BROKER_EXECUTED != true")
        if exit_code is not None and exit_code != 0:
            reasons.append(f"BROKER_EXIT != 0 ({exit_code})")
    else:
        reasons.append(f"missing lane result file {ANNOUNCE_FILE_NAME}")
    if not result_file.is_file():
        reasons.append(f"missing {BROKER_RESULT_FILE_NAME} (broker dispatch not persisted)")

    broker_complete = (
        announce_file.is_file()
        and result_file.is_file()
        and executed
        and exit_code == 0
    )
    return {
        "lane_id": lane_id,
        "agent_id": lane["agent_id"],
        "announce_file_present": announce_file.is_file(),
        "broker_result_present": result_file.is_file(),
        "broker_executed": executed,
        "broker_exit": exit_code,
        "broker_audit_id": audit_id,
        "broker_complete": broker_complete,
        "incomplete_reasons": reasons,
    }


def collect_broker_lanes(
    vault: Path,
    pit_id: str,
    lanes: list[dict[str, Any]],
    *,
    timeout_seconds: float,
    poll_seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Espera el cierre broker de todas las lanes contra el vault (yield parent)."""
    deadline = clock() + timeout_seconds
    states: dict[str, dict[str, Any]] = {}
    pending = [lane["lane_id"] for lane in lanes]
    while True:
        for lane in lanes:
            lane_id = lane["lane_id"]
            if lane_id not in pending:
                continue
            state = _collect_broker_lane_state(vault, pit_id, lane)
            states[lane_id] = state
            if state["broker_complete"]:
                pending.remove(lane_id)
                _log(
                    f"collect: {lane_id} broker_complete "
                    f"audit={state.get('broker_audit_id')}"
                )
        if not pending or clock() >= deadline:
            break
        sleep(poll_seconds)
    for lane_id in pending:
        _log(f"collect: {lane_id} INCOMPLETE — {states[lane_id]['incomplete_reasons']}")
    return [states[lane["lane_id"]] for lane in lanes]


def _broker_verdict_for(lane_states: list[dict[str, Any]], spawn_ok: bool) -> str:
    complete = sum(1 for state in lane_states if state.get("broker_complete"))
    if not spawn_ok:
        return BROKER_RUN_FAIL
    if lane_states and complete == len(lane_states):
        return BROKER_RUN_PASS
    if complete >= 2:
        return BROKER_RUN_PARTIAL
    return BROKER_RUN_FAIL


# ---------------------------------------------------------------------------
# Smoke (dry-run) — sin OpenClaw ni Worker: simula los announces broker y
# ejercita el collect en un vault scratch. Deja final-metrics.json
# PIT_DRY_RUN_PASS que consume check_broker_smoke_gate antes del spawn real.
# ---------------------------------------------------------------------------


def _bootstrap_scratch_vault(vault: Path) -> None:
    """Vault scratch mínimo que satisface core.check_pit_vault (pit/templates/archive)."""
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True, exist_ok=True)
    readme = vault / "README.md"
    if not readme.exists():
        readme.write_text(
            "# umbral-pit-vault (scratch broker dry-run)\n\n"
            "Vault efímero de scripts/pit/pit_broker_run.py --smoke (P10). No es el "
            "pit-vault real de la VPS; puede borrarse.\n",
            encoding="utf-8",
        )
    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            ".obsidian/workspace.json\n.obsidian/workspaces.json\n", encoding="utf-8"
        )


def _seed_fake_broker_lane(vault: Path, pit_id: str, lane: dict[str, Any]) -> None:
    """Escribe announce.md (BROKER_* OK) + broker_result.json fake para el smoke."""
    lane_dir = vault / "pit" / pit_id / "lanes" / lane["lane_id"]
    lane_dir.mkdir(parents=True, exist_ok=True)
    audit_id = f"dryrun-{lane['lane_id']}"[:32]
    fake_result = {
        "dry_run": True,
        "task": "copilot_cli.run",
        "ok": True,
        "would_run": True,
        "decision": "dry_run",
        "exit_code": 0,
        "mission_run_id": audit_id,
        "batch_id": lane["batch_id"],
        "metadata": {
            "pit_id": pit_id,
            "lane_id": lane["lane_id"],
            "agent_id": lane["agent_id"],
            "iteration": 1,
        },
    }
    (lane_dir / BROKER_RESULT_FILE_NAME).write_text(
        json.dumps(fake_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (lane_dir / ANNOUNCE_FILE_NAME).write_text(
        f"BROKER_EXECUTED=true\nBROKER_EXIT=0\nBROKER_AUDIT_ID={audit_id}\n",
        encoding="utf-8",
    )


def run_broker_smoke(
    spec_path: Path,
    *,
    lanes_path: Path | None = None,
    worker_url: str = DEFAULT_WORKER_URL,
    evidence_dir: Path | None = None,
    vault_path: Path | None = None,
) -> dict[str, Any]:
    """Smoke broker local (sin OpenClaw/Worker): valida, renderiza y simula collect.

    Deja ``final-metrics.json`` con el mismo esquema que el smoke v1
    (verdict/pit_id/lane_count/generated_at) para que
    ``check_broker_smoke_gate`` lo acepte antes de un spawn real.
    """
    spec_path = Path(spec_path)
    validation = validate_broker_file(spec_path)
    if validation["status"] != "pass":
        raise RunBlocked(f"broker spec invalid: {validation['errors']}")
    spec = load_broker_spec(spec_path)

    evidence = (evidence_dir or DRY_RUN_EVIDENCE_ROOT / spec.pit_id).expanduser()
    evidence.mkdir(parents=True, exist_ok=True)
    vault = (vault_path or evidence / "vault").expanduser()
    _bootstrap_scratch_vault(vault)

    batch_id = f"{spec.pit_id}-broker"
    enrichment = load_lane_enrichment(lanes_path)
    lanes = build_broker_lanes(spec, enrichment=enrichment, batch_id=batch_id)

    # Render de roles (prueba el template) — no se spawnea nada.
    for lane in lanes:
        lane["role"] = render_broker_role(spec, lane, worker_url=worker_url)
    build_broker_spawn_prompt(
        spec, lanes, worker_url=worker_url, vault=vault,
        lane_timeout_seconds=DEFAULT_LANE_TIMEOUT_SECONDS,
    )

    vault_check = core.check_pit_vault(vault, require_write_scope=False)

    # Simula el cierre broker de cada lane y corre el collect real (1 pasada).
    for lane in lanes:
        _seed_fake_broker_lane(vault, spec.pit_id, lane)
    lane_states = collect_broker_lanes(
        vault, spec.pit_id, lanes, timeout_seconds=0.0, poll_seconds=0.0
    )

    all_complete = bool(lane_states) and all(s["broker_complete"] for s in lane_states)
    ok = vault_check["status"] == "pass" and all_complete
    metrics = {
        "schema_version": 1,
        "kind": "pit_broker_dry_run_final_metrics",
        "generated_by": "scripts/pit/pit_broker_run.py --smoke (P10)",
        "generated_at": _utcnow().isoformat(),
        "dry_run": True,
        "pit_id": spec.pit_id,
        "spec_path": str(spec_path),
        "vault_path": str(vault),
        "lane_count": len(lanes),
        "vault_preflight": vault_check["status"],
        "lanes": [
            {
                "lane_id": s["lane_id"],
                "agent_id": s["agent_id"],
                "broker_complete": s["broker_complete"],
                "broker_audit_id": s["broker_audit_id"],
            }
            for s in lane_states
        ],
        "constraints": {"openclaw": False, "worker_post": False, "real_spawn": False},
        "verdict": DRY_RUN_PASS if ok else DRY_RUN_FAIL,
    }
    metrics_path = evidence / "final-metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metrics["final_metrics_path"] = str(metrics_path)
    _log(f"smoke final-metrics: {metrics_path}")
    _log(f"smoke verdict: {metrics['verdict']}")
    return metrics


# ---------------------------------------------------------------------------
# Run end-to-end (broker)
# ---------------------------------------------------------------------------


def run_broker_tournament(
    spec_path: Path,
    *,
    gate: str = "",
    worker_url: str = DEFAULT_WORKER_URL,
    lanes_path: Path | None = None,
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
    """Orquesta el torneo broker P10 y persiste run-metrics.json."""
    spec_path = Path(spec_path)
    started_at = _utcnow().isoformat()

    # Gate David — solo para spawn real. plan-only no registra ni spawnea.
    if not plan_only and gate != GATE_PHRASE:
        raise RunBlocked(
            f"gate phrase mismatch: broker spawn requires the literal phrase "
            f"{GATE_PHRASE!r} from David (got {gate!r}); use --plan-only to render "
            "without spawning"
        )

    validation = validate_broker_file(spec_path)
    if validation["status"] != "pass":
        raise RunBlocked(f"broker spec invalid: {validation['errors']}")
    spec = load_broker_spec(spec_path)
    if not core.PIT_ID_RE.match(spec.pit_id):
        raise RunBlocked(
            f"pit_id {spec.pit_id!r} must match {core.PIT_ID_RE.pattern} "
            "(vault path + kill-prefix safety)"
        )
    if spec.openclaw_orchestration is None or not spec.openclaw_orchestration.enabled:
        raise RunBlocked(
            "openclaw_orchestration.enabled must be true for a broker spawn run "
            "(P10); add the block to the spec or run another package"
        )

    batch_id = f"{spec.pit_id}-broker"
    enrichment = load_lane_enrichment(lanes_path)
    lanes = build_broker_lanes(spec, enrichment=enrichment, batch_id=batch_id)

    vault = (
        vault_path or Path(os.environ.get("PIT_VAULT_PATH") or DEFAULT_VAULT_PATH)
    ).expanduser()
    evidence = (evidence_dir or DEFAULT_EVIDENCE_ROOT / spec.pit_id).expanduser()
    evidence.mkdir(parents=True, exist_ok=True)
    config_path = (
        openclaw_config
        or Path(os.environ.get("OPENCLAW_CONFIG_PATH") or DEFAULT_OPENCLAW_CONFIG)
    ).expanduser()
    cli = cli or OpenClawCli(os.environ.get("OPENCLAW_BIN", "openclaw"))
    worker_url = worker_url or DEFAULT_WORKER_URL

    # 1. Smoke gate — PIT_DRY_RUN_PASS o no hay torneo.
    smoke = check_broker_smoke_gate(
        spec, smoke_metrics_path=smoke_metrics_path, max_age_hours=max_smoke_age_hours
    )
    _log(f"smoke gate: {smoke['verdict']} ({smoke['metrics_path']})")

    # 2. Preflight broker — vault read-only check (schema-agnostic, no producto).
    vault_check = core.check_pit_vault(vault, require_write_scope=False)
    _log(f"vault preflight: {vault_check['status']}")
    if vault_check["status"] != "pass":
        raise RunBlocked(f"vault preflight failed: {vault_check['errors']}")

    for lane in lanes:
        lane["role"] = render_broker_role(spec, lane, worker_url=worker_url)

    agents_doc = build_broker_agents_yaml(spec, lanes, created_at=started_at)
    spawn_prompt = build_broker_spawn_prompt(
        spec, lanes, worker_url=worker_url, vault=vault,
        lane_timeout_seconds=lane_timeout_seconds,
    )
    (evidence / "spawn-prompt.md").write_text(spawn_prompt, encoding="utf-8")

    oc = spec.openclaw_orchestration
    metrics: dict[str, Any] = {
        "schema_version": 1,
        "kind": "pit_broker_run_metrics",
        "generated_by": "scripts/pit/pit_broker_run.py (P10)",
        "started_at": started_at,
        "pit_id": spec.pit_id,
        "spec_path": str(spec_path),
        "lanes_path": str(lanes_path) if lanes_path else None,
        "vault_path": str(vault),
        "worker_url": worker_url,
        "lane_count": len(lanes),
        "budget_usd_total": spec.budget_usd_total,
        "smoke_gate": smoke,
        "vault_preflight": vault_check["status"],
        "gate_phrase_ok": plan_only or gate == GATE_PHRASE,
        "plan_only": plan_only,
        "openclaw_orchestration": {
            "enabled": oc.enabled,
            "spawn_from": oc.spawn_from,
            "collect_mode": oc.collect_mode,
        },
        "lanes": [
            {
                "lane_id": lane["lane_id"],
                "agent_id": lane["agent_id"],
                "model": lane["model"],
                "reasoning_effort": lane["reasoning_effort"],
                "mission": lane["mission"],
                "batch_id": lane["batch_id"],
            }
            for lane in lanes
        ],
        "constraints": {
            "broker_required_task": spec.broker_contract.required_task,
            "forbid_direct_llm_repo_analysis": spec.broker_contract.forbid_direct_llm_repo_analysis,
            "secrets_deny": spec.secrets_scope.deny,
            "one_post_per_lane_no_retries": True,
            "spawn_parent": "main (standalone, G-D1b)",
        },
    }

    if plan_only:
        v1.write_generated_artifacts(spec, lanes, agents_doc, vault=None, out_dir=evidence)
        metrics["verdict"] = BROKER_RUN_PLAN_ONLY
        _log(
            "plan-only: ROLE broker + agents.yaml + spawn-prompt renderizados; "
            "sin registro ni spawn"
        )
        v1._write_metrics(evidence, metrics)
        return metrics

    if not cli.available():
        raise RunBlocked(
            f"openclaw binary not found ({cli.bin_path}) — set OPENCLAW_BIN or run on the VPS"
        )

    artifact_paths = v1.write_generated_artifacts(
        spec, lanes, agents_doc, vault=vault, out_dir=evidence
    )
    metrics["artifacts"] = artifact_paths

    # 3. Registro de efímeros (reusa el ciclo de vida v1).
    registration = v1.register_ephemeral_agents(
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
        if not skip_gateway_restart:
            restart = cli.gateway_restart()
            metrics["registration"]["gateway_restart_rc"] = restart.returncode
            if restart.returncode != 0:
                raise RunBlocked(
                    "gateway restart failed after registration — config backup at "
                    f"{registration['backup_path']}"
                )

        # 4. Spawn vía main standalone (G-D1b): sessions_spawn × N + yield.
        _log(f"spawn: openclaw agent --agent main ({len(lanes)} broker lanes)")
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
            # 5. Collect contra el vault (broker_result.json + announce.md).
            lane_states = collect_broker_lanes(
                vault,
                spec.pit_id,
                lanes,
                timeout_seconds=collect_timeout_seconds,
                poll_seconds=collect_poll_seconds,
            )
    finally:
        # 6. Kill + desregistro SIEMPRE (aunque collect/spawn fallaran).
        killed_at = _utcnow().isoformat()
        metrics["kill"] = v1.kill_tournament_subagents(cli, spec.pit_id)
        try:
            dereg = v1.deregister_ephemeral_agents(
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
        v1.write_generated_artifacts(spec, lanes, agents_doc, vault=vault, out_dir=evidence)

    metrics["lane_results"] = lane_states
    metrics["lanes_completed"] = sum(1 for s in lane_states if s.get("broker_complete"))
    metrics["verdict"] = _broker_verdict_for(lane_states, spawn_ok)
    v1._write_metrics(evidence, metrics)
    return metrics


def exit_code_for(verdict: str) -> int:
    """Map a broker verdict to a process exit code."""
    if verdict in (BROKER_RUN_PASS, BROKER_RUN_PLAN_ONLY):
        return 0
    if verdict == BROKER_RUN_BLOCKED:
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P10 — OpenClaw broker-real tournament runner (pit_spec v2)."
    )
    parser.add_argument("spec_path", type=Path, help="Path al pit_spec v2 broker (YAML/JSON).")
    parser.add_argument(
        "lanes_path",
        type=Path,
        nargs="?",
        default=None,
        help="Lanes file opcional (lanes: [{lane_id, lane_focus}, ...]) para enriquecer el prompt.",
    )
    parser.add_argument(
        "--gate",
        default="",
        help=f"Frase literal del gate David ({GATE_PHRASE!r}). Requerida solo para spawn real.",
    )
    parser.add_argument("--worker-url", default=DEFAULT_WORKER_URL,
                        help=f"URL del Worker para el broker (default: {DEFAULT_WORKER_URL}).")
    parser.add_argument("--vault-path", type=Path, default=None,
                        help="pit-vault real (default: $PIT_VAULT_PATH o ~/umbral-pit-vault).")
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="Evidencia (default: ~/.coord-ag-evidence/pit-openclaw-broker/<pit_id>).")
    parser.add_argument("--smoke-metrics", type=Path, default=None,
                        help="final-metrics.json del broker dry-run (default: evidencia estándar).")
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
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke local (sin OpenClaw/Worker): simula announces broker y "
                             "deja final-metrics.json PIT_DRY_RUN_PASS para el smoke gate.")
    parser.add_argument("--skip-gateway-restart", action="store_true",
                        help="No reiniciar el gateway tras alta/baja (operador lo hace a mano).")
    args = parser.parse_args(argv)

    if args.smoke:
        try:
            metrics = run_broker_smoke(
                args.spec_path,
                lanes_path=args.lanes_path,
                worker_url=args.worker_url,
                evidence_dir=args.evidence_dir,
                vault_path=args.vault_path,
            )
        except RunBlocked as exc:
            _log(f"BLOCKED: {exc}")
            _log(f"smoke verdict: {DRY_RUN_FAIL}")
            return 1
        except Exception as exc:
            _log(f"ERROR: {exc}")
            _log(f"smoke verdict: {DRY_RUN_FAIL}")
            return 1
        return 0 if metrics["verdict"] == DRY_RUN_PASS else 1

    try:
        metrics = run_broker_tournament(
            args.spec_path,
            gate=args.gate,
            worker_url=args.worker_url,
            lanes_path=args.lanes_path,
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
        _log(f"verdict: {BROKER_RUN_BLOCKED}")
        return 2
    except Exception as exc:  # error inesperado — visible, sin medio-correr
        _log(f"ERROR: {exc}")
        _log(f"verdict: {BROKER_RUN_BLOCKED}")
        return 2

    return exit_code_for(metrics["verdict"])


if __name__ == "__main__":
    sys.exit(main())
