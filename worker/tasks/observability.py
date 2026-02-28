"""
S6 — Tareas de observabilidad: reportes OODA y self-evaluation.

- system.ooda_report: genera reporte OODA con datos reales de Redis.
- system.self_eval: evalúa calidad de tareas completadas.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("worker.tasks.observability")

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def handle_ooda_report(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera reporte OODA con datos de Redis.

    Input:
        week_ago (int, optional): 0=esta semana (default).
        format (str, optional): "markdown" o "json" (default: "markdown").
    """
    sys.path.insert(0, str(_SCRIPTS_DIR.parent))
    try:
        from scripts.ooda_report import build_report, to_markdown
        import argparse

        week_ago = int(input_data.get("week_ago", 0))
        fmt = input_data.get("format", "markdown")

        args = argparse.Namespace(week_ago=week_ago, format=fmt)
        report = build_report(args)

        if fmt == "markdown":
            output = to_markdown(report)
        else:
            output = json.dumps(report, indent=2)

        return {"ok": True, "format": fmt, "report": output}
    except Exception as e:
        logger.exception("OODA report failed: %s", e)
        return {"ok": False, "error": str(e)}


def handle_self_eval(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa tareas completadas (Self-Evaluation).

    Input:
        limit (int, optional): máximo de tareas a evaluar (default: 20).
        format (str, optional): "markdown" o "json" (default: "markdown").
    """
    sys.path.insert(0, str(_SCRIPTS_DIR.parent))
    try:
        from scripts.evals_self_check import run_evals, to_markdown

        limit = int(input_data.get("limit", 20))
        fmt = input_data.get("format", "markdown")

        evals = run_evals(limit)

        if fmt == "markdown":
            output = to_markdown(evals)
        else:
            output = json.dumps(evals, indent=2)

        avg = 0.0
        valid = [e for e in evals if "overall" in e]
        if valid:
            avg = sum(e["overall"] for e in valid) / len(valid)

        return {
            "ok": True,
            "format": fmt,
            "tasks_evaluated": len(valid),
            "average_score": round(avg, 2),
            "report": output,
        }
    except Exception as e:
        logger.exception("Self-eval failed: %s", e)
        return {"ok": False, "error": str(e)}
