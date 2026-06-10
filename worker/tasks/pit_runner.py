"""PIT runner Worker tasks (PIT-2) — torneo de producto, capa repo-side.

Tasks: ``pit.preflight``, ``pit.lane_init``, ``pit.iteration_close``,
``pit.lane_announce``. Wrappers finos sobre ``scripts/pit/pit_runner_core``
(misma fuente que el smoke ``pit_tournament_dry_run.sh``).

Deliberadamente separado de ``worker.tasks.tournament_lane_github`` (D3 code,
PR_URL): PIT compite con PROTOTYPE_URL + KPI_PACK + FULFILLMENT sobre el
umbral-pit-vault, no con ramas/PRs. El protocolo D3 queda intacto.

El spawn real de agentes efímeros OpenClaw NO vive acá — es PIT-2b
(docs/ops/pit-2-runner-protocol.md).
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

try:
    from scripts.pit import pit_runner_core as core
except ImportError:  # worker desplegado fuera del repo root en sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_runner_core as core

logger = logging.getLogger("worker.tasks.pit_runner")


def _resolve_vault_path(input_data: Dict[str, Any]) -> str:
    raw = (input_data.get("vault_path") or os.environ.get("PIT_VAULT_PATH") or "").strip()
    if not raw:
        raise ValueError("vault_path is required (input or PIT_VAULT_PATH env)")
    return raw


def _require_str(input_data: Dict[str, Any], key: str) -> str:
    value = (input_data.get(key) or "").strip() if isinstance(input_data.get(key), str) else ""
    if not value:
        raise ValueError(f"{key} is required")
    return value


def handle_pit_preflight(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Valida pit_spec.yaml + budget (kill switch stub) + pit_vault_check."""
    try:
        spec_path = _require_str(input_data, "spec_path")
        vault_path = _resolve_vault_path(input_data)
        result = core.preflight(
            spec_path,
            vault_path,
            require_write_scope=bool(input_data.get("require_write_scope", False)),
        )
        if result["budget"]:
            logger.info(
                "pit.preflight budget_usd=%s max_cost_estimate_usd=%s kill_switch=%s%%"
                " (enforced=%s, enforcement=%s)",
                result["budget"]["budget_usd"],
                result["budget"]["max_cost_estimate_usd"],
                result["budget"]["kill_switch"]["threshold_pct"],
                result["budget"]["kill_switch"]["enforced"],
                result["budget"]["kill_switch"]["enforcement_milestone"],
            )
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_pit_lane_init(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea pit/<pit_id>/lanes/<lane_id>/ con kanban/board.md + iterations/1/."""
    try:
        result = core.lane_init(
            _resolve_vault_path(input_data),
            _require_str(input_data, "pit_id"),
            _require_str(input_data, "lane_id"),
            research_profile=input_data.get("research_profile") or "mixed",
        )
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_pit_iteration_close(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Escribe kpi_pack.json de la iteración y agrega la tarjeta al kanban."""
    try:
        result = core.iteration_close(
            _resolve_vault_path(input_data),
            _require_str(input_data, "pit_id"),
            _require_str(input_data, "lane_id"),
            input_data.get("iteration"),
            input_data.get("hypothesis"),
            input_data.get("kpis"),
            prototype_url=input_data.get("prototype_url"),
            kanban_column=input_data.get("kanban_column") or "Fulfillment",
            synthetic_personas=input_data.get("synthetic_personas"),
            notes=input_data.get("notes"),
        )
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def handle_pit_lane_announce(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Emite las 3 líneas literales de cierre y el veredicto lane_complete."""
    try:
        result = core.lane_announce(
            _resolve_vault_path(input_data),
            _require_str(input_data, "pit_id"),
            _require_str(input_data, "lane_id"),
            iteration=input_data.get("iteration"),
            prototype_url=input_data.get("prototype_url"),
        )
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
