"""Mission Control FastAPI app — dashboard read-only OpenClaw + Worker.

Arranque local:
    MISSION_CONTROL_TOKEN=devtoken python -m uvicorn mission_control.app:app \\
        --host 127.0.0.1 --port 8089

VPS (systemd user):
    Ver infra/systemd/mission-control.service.template.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import config
from .adapters import pit_vault
from .auth import require_token
from .routes import agents, evals, gates, health, pit, queue, quotas, risks, tournaments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mission_control %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mission_control")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    if not config.TOKEN:
        logger.warning(
            "MISSION_CONTROL_TOKEN no configurado — todas las rutas autenticadas "
            "responderán 503. Setear el env var antes de exponer el dashboard."
        )
    logger.info(
        "Mission Control v%s up — bind %s:%s, openclaw_json=%s",
        __import__("mission_control").__version__,
        config.HOST,
        config.PORT,
        config.OPENCLAW_JSON_PATH,
    )
    yield


app = FastAPI(
    title="Umbral Mission Control",
    version=__import__("mission_control").__version__,
    description="Dashboard read-only para OpenClaw + Worker. ADR-009.",
    lifespan=lifespan,
)

# /health: anónimo (ADR-009 D4).
app.include_router(health.router)

# Resto: bearer obligatorio.
_auth = [Depends(require_token)]
app.include_router(agents.router, dependencies=_auth)
app.include_router(quotas.router, dependencies=_auth)
app.include_router(tournaments.router, dependencies=_auth)
app.include_router(queue.router, dependencies=_auth)
app.include_router(gates.router, dependencies=_auth)
app.include_router(risks.router, dependencies=_auth)
app.include_router(evals.router, dependencies=_auth)
app.include_router(pit.router, dependencies=_auth)


_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/", response_class=HTMLResponse, dependencies=_auth)
async def index(request: Request) -> HTMLResponse:
    """Vista HTMX que pollea los endpoints JSON cada 10s."""
    return _templates.TemplateResponse(request, "index.html")


def _pit_lane_iterations(
    pit_id: str, lane: dict[str, Any], kpi_defs: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Detalle KPI por iteración para el template — lee kpi_packs vía adapter.

    Junta unit/expected/direction del propio pack (schema v1) con fallback a
    ``kpi_definitions`` del spec por kpi_id; los packs legacy de fixtures usan
    ``value`` en vez de ``kpi_achieved``. Best-effort: iteraciones sin pack
    legible se omiten.
    """
    last = lane.get("last_iteration")
    if not isinstance(last, int) or last < pit_vault.ITERATION_MIN:
        return []
    iterations: list[dict[str, Any]] = []
    for n in range(pit_vault.ITERATION_MIN, min(last, pit_vault.ITERATION_MAX) + 1):
        try:
            payload = pit_vault.read_kpi_pack(
                config.PIT_VAULT_PATH, pit_id, lane["lane_id"], n
            )
        except ValueError:
            return []
        if payload is None or not isinstance(payload.get("kpi_pack"), dict):
            continue
        pack = payload["kpi_pack"]
        fulfillment = pack.get("fulfillment_score")
        if not isinstance(fulfillment, (int, float)) or isinstance(fulfillment, bool):
            fulfillment = None
        kpis: list[dict[str, Any]] = []
        raw_kpis = pack.get("kpis")
        if isinstance(raw_kpis, list):
            for raw in raw_kpis:
                if not isinstance(raw, dict):
                    continue
                kpi_id = raw.get("kpi_id")
                spec_def = kpi_defs.get(kpi_id, {}) if isinstance(kpi_id, str) else {}
                achieved = raw.get("kpi_achieved")
                if achieved is None:
                    achieved = raw.get("value")
                kpis.append(
                    {
                        "kpi_id": kpi_id,
                        "unit": raw.get("unit") or spec_def.get("unit"),
                        "expected": (
                            raw.get("kpi_expected")
                            if raw.get("kpi_expected") is not None
                            else spec_def.get("kpi_expected")
                        ),
                        "achieved": achieved,
                        "direction": raw.get("direction") or spec_def.get("direction"),
                        "synthetic": raw.get("synthetic") is True,
                    }
                )
        iterations.append({"n": n, "fulfillment": fulfillment, "kpis": kpis})
    return iterations


def _pit_tournament_context(summary: dict[str, Any]) -> dict[str, Any]:
    """Mergea summary (list_tournaments) + detail (read_tournament) para pit.html."""
    merged = dict(summary)
    merged["lane_total"] = summary.get("lane_count")
    merged["outcome"] = {"present": False, "winner_lane_id": None, "david_gate": None}
    merged["lanes"] = []
    pit_id = summary.get("pit_id")
    if not isinstance(pit_id, str):
        return merged
    try:
        detail = pit_vault.read_tournament(
            config.PIT_VAULT_PATH,
            config.PIT_EVIDENCE_DIR,
            pit_id,
            config.PIT_SPEC_FALLBACK_DIR,
        )
    except ValueError:
        detail = None
    if detail is None:
        return merged
    merged["outcome"] = detail["outcome"]
    kpi_defs: dict[str, dict[str, Any]] = {}
    spec = detail.get("spec")
    if isinstance(spec, dict):
        for kpi_def in spec.get("kpi_definitions") or []:
            if isinstance(kpi_def, dict) and isinstance(kpi_def.get("kpi_id"), str):
                kpi_defs[kpi_def["kpi_id"]] = kpi_def
    lanes: list[dict[str, Any]] = []
    for lane in detail["lanes"]:
        lane_ctx = dict(lane)
        lane_ctx["iterations"] = _pit_lane_iterations(pit_id, lane, kpi_defs)
        lanes.append(lane_ctx)
    merged["lanes"] = lanes
    return merged


@app.get("/pit", response_class=HTMLResponse, dependencies=_auth)
async def pit_dashboard(request: Request) -> HTMLResponse:
    """Dashboard judge PIT-5 P5.2 — server-rendered, read-only, sin polling."""
    listing = pit_vault.list_tournaments(
        config.PIT_VAULT_PATH,
        config.PIT_EVIDENCE_DIR,
        config.PIT_SPEC_FALLBACK_DIR,
    )
    return _templates.TemplateResponse(
        request,
        "pit.html",
        {
            "vault": listing["vault"],
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%SZ"
            ),
            "tournaments": [
                _pit_tournament_context(summary)
                for summary in listing["tournaments"]
            ],
        },
    )
