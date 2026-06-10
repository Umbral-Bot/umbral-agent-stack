#!/usr/bin/env python3
"""PIT-2 — smoke local de torneo PIT, SIN spawn OpenClaw.

Simula las N lanes del spec en secuencia (init → 1 iteración fake →
fulfillment → announce) sobre un pit-vault scratch local, y deja la evidencia
en ``~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json``.

Garantías del smoke (docs/ops/pit-2-runner-protocol.md):

- **NO internet** — las señales KPI son sintéticas deterministas (etiquetadas
  ``synthetic: true``) derivadas del propio spec.
- **NO Magnific** — sin visual_assets.
- **NO sessions_spawn** — ningún agente efímero; el spawn real es PIT-2b.
- **Budget kill switch (stub):** ``budget_usd`` del spec se loguea como
  estimación tope de costo (max cost estimate). El corte duro al 100 % queda
  documentado; su enforcement real es PIT-3.

Uso (directo o vía ``scripts/pit/pit_tournament_dry_run.sh``)::

    python scripts/pit/pit_dry_run.py examples/pit-salud-mental-pilot.yaml
    python scripts/pit/pit_dry_run.py <spec.yaml> --evidence-dir /tmp/evidencia
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.pit import pit_runner_core as core
    from scripts.pit.pit_spec_validate import PitSpec, load_spec
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_runner_core as core
    from scripts.pit.pit_spec_validate import PitSpec, load_spec

DRY_RUN_PASS = "PIT_DRY_RUN_PASS"
DRY_RUN_FAIL = "PIT_DRY_RUN_FAIL"

# Factores deterministas por lane (sin RNG): el fulfillment simulado de cada
# lane queda ≈ su factor, así el smoke es verificable a ojo y en tests.
LANE_FACTORS = (0.6, 0.8, 1.0, 0.7, 0.9)
LANE_SUFFIXES = ("a", "b", "c", "d", "e")

DEFAULT_EVIDENCE_ROOT = Path.home() / ".coord-ag-evidence" / "pit-dry-run"


def _log(message: str) -> None:
    print(f"[pit-dry-run] {message}")


def _bootstrap_scratch_vault(vault: Path) -> None:
    """Vault scratch mínimo (espejo python de pit_vault_init.sh, sin git)."""
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True, exist_ok=True)
    readme = vault / "README.md"
    if not readme.exists():
        readme.write_text(
            "# umbral-pit-vault (scratch dry-run)\n\n"
            "Vault efímero creado por scripts/pit/pit_dry_run.py para el smoke\n"
            "PIT-2. No es el pit-vault real de la VPS; puede borrarse.\n",
            encoding="utf-8",
        )
    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            ".obsidian/workspace.json\n.obsidian/workspaces.json\n", encoding="utf-8"
        )
    if core.TEMPLATES_DIR.is_dir():
        for template in core.TEMPLATES_DIR.iterdir():
            if template.is_file():
                target = vault / "templates" / template.name
                if not target.exists():
                    shutil.copyfile(template, target)


def _fake_kpis(spec: PitSpec, factor: float) -> list[dict[str, Any]]:
    """Señales KPI fake deterministas: score por KPI ≈ factor de la lane."""
    kpis: list[dict[str, Any]] = []
    for kd in spec.kpi_definitions:
        if kd.direction == "increase":
            achieved = round(kd.kpi_expected * factor, 2)
        else:
            achieved = round(kd.kpi_expected / factor, 2) if kd.kpi_expected > 0 else 0.0
        kpis.append(
            {
                "kpi_id": kd.kpi_id,
                "unit": kd.unit,
                "kpi_expected": kd.kpi_expected,
                "kpi_achieved": achieved,
                "direction": kd.direction,
                "weight": kd.weight,
                # Todas las señales del dry run son sintéticas — SIEMPRE etiquetadas.
                "synthetic": True,
            }
        )
    return kpis


def _fake_hypothesis(spec: PitSpec) -> dict[str, Any]:
    target = spec.kpi_definitions[0]
    return {
        "variable": "[dry-run] variable simulada (sin señal real)",
        "statement": (
            f"[dry-run] Si ajusto la variable simulada, espero mover {target.kpi_id} "
            f"hacia {target.direction}. Iteración fake del smoke PIT-2."
        ),
        "kpi_id": target.kpi_id,
        "validated": None,
    }


def run_dry_run(
    spec_path: Path,
    *,
    evidence_dir: Path | None = None,
    vault_path: Path | None = None,
) -> dict[str, Any]:
    """Corre el smoke completo y devuelve el final-metrics dict (ya persistido)."""
    spec = load_spec(spec_path)

    evidence = (evidence_dir or DEFAULT_EVIDENCE_ROOT / spec.pit_id).expanduser()
    evidence.mkdir(parents=True, exist_ok=True)
    vault = (vault_path or evidence / "vault").expanduser()
    _bootstrap_scratch_vault(vault)

    budget = {
        "budget_usd": spec.budget_usd,
        "budget_per_lane_usd": round(spec.budget_per_lane_usd, 2),
        "max_cost_estimate_usd": spec.budget_usd,
        # Smoke local sin LLM/Magnific/spawn ⇒ gasto estimado 0.
        "estimated_spend_usd": 0.0,
        "kill_switch": dict(core.BUDGET_KILL_SWITCH),
    }
    # Logs en ASCII puro: la consola Windows (cp1252) rompe con U+2192 et al.
    _log(
        f"budget_usd={spec.budget_usd} -> max_cost_estimate_usd={spec.budget_usd} | "
        f"kill switch @{budget['kill_switch']['threshold_pct']}% documentado "
        f"(stub PIT-2, enforcement real: {budget['kill_switch']['enforcement_milestone']})"
    )

    # El smoke declara el write scope canónico para ejercitar el gate real.
    previous_scope = os.environ.get("PIT_VAULT_WRITE_SCOPE")
    os.environ["PIT_VAULT_WRITE_SCOPE"] = "pit"
    try:
        preflight = core.preflight(spec_path, vault, require_write_scope=True)
        _log(f"preflight: {preflight['verdict']}")

        lanes: list[dict[str, Any]] = []
        if preflight["ok"]:
            for index in range(spec.lane_count):
                lane_id = f"lane-dry-{LANE_SUFFIXES[index]}"
                factor = LANE_FACTORS[index]
                core.lane_init(
                    vault, spec.pit_id, lane_id, research_profile=spec.research_profile
                )
                close = core.iteration_close(
                    vault,
                    spec.pit_id,
                    lane_id,
                    1,
                    _fake_hypothesis(spec),
                    _fake_kpis(spec, factor),
                    prototype_url=(
                        f"https://dry-run.invalid/mission-control/{spec.pit_id}/{lane_id}"
                    ),
                    kanban_column="Fulfillment",
                    synthetic_personas={"used": True, "count": 3},
                    notes=(
                        "Iteración fake del smoke PIT-2 (pit_tournament_dry_run): "
                        "sin internet, sin Magnific, sin sessions_spawn."
                    ),
                )
                announce = core.lane_announce(vault, spec.pit_id, lane_id, iteration=1)
                _log(
                    f"{lane_id}: fulfillment={announce['fulfillment']} "
                    f"lane_complete={announce['lane_complete']}"
                )
                lanes.append(
                    {
                        "lane_id": lane_id,
                        "iteration": 1,
                        "fulfillment": announce["fulfillment"],
                        "kpi_pack": announce["kpi_pack"],
                        "prototype_url": announce["prototype_url"],
                        "lane_complete": announce["lane_complete"],
                        "schema_validation": close["schema_validation"],
                        "announce": announce["announce"],
                    }
                )
    finally:
        if previous_scope is None:
            os.environ.pop("PIT_VAULT_WRITE_SCOPE", None)
        else:
            os.environ["PIT_VAULT_WRITE_SCOPE"] = previous_scope

    all_complete = bool(lanes) and all(lane["lane_complete"] for lane in lanes)
    ok = preflight["ok"] and all_complete
    winner_candidate = (
        max(lanes, key=lambda lane: lane["fulfillment"]) if lanes else None
    )

    metrics: dict[str, Any] = {
        "schema_version": 1,
        "kind": "pit_dry_run_final_metrics",
        "generated_by": "scripts/pit/pit_dry_run.py (PIT-2)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
        "pit_id": spec.pit_id,
        "spec_path": str(spec_path),
        "vault_path": str(vault),
        "lane_count": spec.lane_count,
        "iteration_count_spec": spec.iteration_count,
        "iterations_simulated": 1,
        "preflight_verdict": preflight["verdict"],
        "budget": budget,
        "lanes": lanes,
        # Informativo: el winner real sale del juez + gate David (fuera del smoke).
        "winner_candidate": (
            {
                "lane_id": winner_candidate["lane_id"],
                "fulfillment": winner_candidate["fulfillment"],
            }
            if winner_candidate
            else None
        ),
        "constraints": {
            "internet": False,
            "magnific": False,
            "sessions_spawn": False,
        },
        "verdict": DRY_RUN_PASS if ok else DRY_RUN_FAIL,
    }

    metrics_path = evidence / "final-metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metrics["final_metrics_path"] = str(metrics_path)
    _log(f"final-metrics: {metrics_path}")
    _log(f"verdict: {metrics['verdict']}")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PIT tournament dry run (smoke local, sin spawn OpenClaw)."
    )
    parser.add_argument("spec_path", type=Path, help="Path al pit_spec YAML/JSON.")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Directorio de evidencia (default: ~/.coord-ag-evidence/pit-dry-run/<pit_id>).",
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=None,
        help="Vault a usar (default: <evidence>/vault, scratch efímero).",
    )
    args = parser.parse_args(argv)

    try:
        metrics = run_dry_run(
            args.spec_path,
            evidence_dir=args.evidence_dir,
            vault_path=args.vault_path,
        )
    except Exception as exc:  # spec inválido, vault roto, etc.
        _log(f"ERROR: {exc}")
        _log(f"verdict: {DRY_RUN_FAIL}")
        return 1
    return 0 if metrics["verdict"] == DRY_RUN_PASS else 1


if __name__ == "__main__":
    sys.exit(main())
