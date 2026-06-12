"""GET /pit/* — PIT tournaments read-only (PIT-5 P5.1, ADR-009 addendum).

Namespace separado de /tournaments (D3, historia estática de torneos de
modelos): /pit/* lee el PIT vault real vía adapters.pit_vault. Solo GET,
sin launcher, sin escrituras. Los ids se validan contra los regexes del
kpi-pack.schema.json ANTES de tocar el filesystem (422 si no matchean).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from mission_control import config
from mission_control.adapters import pit_vault

router = APIRouter(prefix="/pit")


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
