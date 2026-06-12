"""GET /pit/* — PIT tournaments read-only (PIT-5 P5.1, ADR-009 addendum).

Namespace separado de /tournaments (D3, historia estática de torneos de
modelos): /pit/* lee el PIT vault real vía adapters.pit_vault. Solo GET,
sin launcher, sin escrituras. Los ids se validan contra los regexes del
kpi-pack.schema.json ANTES de tocar el filesystem (422 si no matchean).

P5.2b — judge UX v2: ``pages_router`` sirve shells HTML **sin bearer**
(/pit/access, /pit/judge[/{pit_id}]). Los shells no renderizan NINGÚN dato
del vault server-side: son páginas estáticas cuyo JS hace fetch a las rutas
JSON de este módulo con ``Authorization: Bearer`` desde sessionStorage
(cargado en /pit/access). Fail-closed: sin token las APIs siguen 401/503.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from mission_control import config
from mission_control.adapters import pit_vault

router = APIRouter(prefix="/pit")

# HTML shells del judge (montado SIN dependencia de bearer en app.py — no
# exponen datos; solo markup + JS que pide token al usuario).
pages_router = APIRouter(prefix="/pit")

_templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def _validated_pit_id(pit_id: str) -> str:
    if not pit_vault.PIT_ID_RE.fullmatch(pit_id):
        raise HTTPException(status_code=422, detail="invalid pit_id")
    return pit_id


def _validated_lane_id(lane_id: str) -> str:
    if not pit_vault.LANE_ID_RE.fullmatch(lane_id):
        raise HTTPException(status_code=422, detail="invalid lane_id")
    return lane_id


@router.get("/tournaments")
async def pit_tournaments() -> dict:
    return pit_vault.list_tournaments(
        config.PIT_VAULT_PATH,
        config.PIT_EVIDENCE_DIR,
        config.PIT_SPEC_FALLBACK_DIR,
    )


@router.get("/tournaments/{pit_id}")
async def pit_tournament_detail(pit_id: str) -> dict:
    _validated_pit_id(pit_id)
    payload = pit_vault.read_tournament(
        config.PIT_VAULT_PATH,
        config.PIT_EVIDENCE_DIR,
        pit_id,
        config.PIT_SPEC_FALLBACK_DIR,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="tournament not found")
    return payload


@router.get("/tournaments/{pit_id}/lanes/{lane_id}/kpi/{iteration}")
async def pit_kpi_pack(
    pit_id: str,
    lane_id: str,
    iteration: int = PathParam(
        ge=pit_vault.ITERATION_MIN, le=pit_vault.ITERATION_MAX
    ),
) -> dict:
    _validated_pit_id(pit_id)
    _validated_lane_id(lane_id)
    payload = pit_vault.read_kpi_pack(
        config.PIT_VAULT_PATH, pit_id, lane_id, iteration
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="kpi_pack not found")
    return payload


# ---------------------------------------------------------------------------
# Judge HTML shells (P5.2b) — sin bearer, sin datos server-rendered
# ---------------------------------------------------------------------------


@pages_router.get("/access", response_class=HTMLResponse)
async def pit_access(request: Request) -> HTMLResponse:
    """Landing para pegar el token (→ sessionStorage). Shell estático."""
    return _templates.TemplateResponse(request, "pit_access.html")


@pages_router.get("/judge", response_class=HTMLResponse)
async def pit_judge_index(request: Request) -> HTMLResponse:
    """Picker de torneo: el JS lista /pit/tournaments con el bearer guardado."""
    return _templates.TemplateResponse(
        request, "pit_judge.html", {"pit_id": None}
    )


@pages_router.get("/judge/{pit_id}", response_class=HTMLResponse)
async def pit_judge_detail(request: Request, pit_id: str) -> HTMLResponse:
    """Vista judge de un torneo. Valida el id (422) pero NO toca el vault."""
    _validated_pit_id(pit_id)
    return _templates.TemplateResponse(
        request, "pit_judge.html", {"pit_id": pit_id}
    )
