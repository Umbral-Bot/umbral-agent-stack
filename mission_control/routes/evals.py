"""GET /evals - latest Core Eval Harness report, read-only."""
from __future__ import annotations

from fastapi import APIRouter

from mission_control import config
from mission_control.adapters.evals import read_latest_report

router = APIRouter()


@router.get("/evals")
async def evals_state() -> dict:
    return read_latest_report(config.EVAL_REPORT_PATH)
