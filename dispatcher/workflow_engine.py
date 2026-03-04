"""
Team Workflow Engine — executes multi-step workflows per team.

Loads workflow definitions from config/team_workflows.yaml and runs them
sequentially, passing each step's result to the next via {prev_result}.

Usage:
    from dispatcher.workflow_engine import WorkflowEngine
    engine = WorkflowEngine("config/team_workflows.yaml", worker_client)
    result = engine.execute_workflow("marketing", "research_and_post", {"topic": "IA generativa"})
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from client.worker_client import WorkerClient

logger = logging.getLogger("dispatcher.workflow_engine")


# ── Exceptions ───────────────────────────────────────────────────

class WorkflowNotFoundError(Exception):
    """Raised when a workflow name doesn't exist for a team."""


class WorkflowStepError(Exception):
    """Raised when a workflow step fails (non-fatal — captured in results)."""

    def __init__(self, step_index: int, task: str, message: str):
        self.step_index = step_index
        self.task = task
        super().__init__(f"Step {step_index} ({task}): {message}")


# ── Template rendering ───────────────────────────────────────────

def _render_template(template: Any, context: Dict[str, str]) -> Any:
    """
    Recursively render {variable} placeholders in a template value.

    Supports str, dict (recursive), list (recursive), and passes through
    other types (int, float, bool) unchanged.
    """
    if isinstance(template, str):
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    if isinstance(template, dict):
        return {k: _render_template(v, context) for k, v in template.items()}
    if isinstance(template, list):
        return [_render_template(item, context) for item in template]
    return template


def _extract_result_text(result: Dict[str, Any]) -> str:
    """
    Extract a human-readable text from a worker task result dict.

    Handles common result shapes:
    - {"result": {"text": "..."}}         → llm.generate
    - {"result": {"results": [...]}}      → research.web
    - {"result": {"report": "..."}}       → composite.research_report
    - {"result": "string"}                → simple tasks
    - {"pong": true}                      → ping
    """
    if not isinstance(result, dict):
        return str(result)

    inner = result.get("result")

    # Nested dict with known fields
    if isinstance(inner, dict):
        # llm.generate → text
        if "text" in inner:
            return str(inner["text"])
        # composite → report
        if "report" in inner:
            return str(inner["report"])
        # research.web → formatted results
        if "results" in inner and isinstance(inner["results"], list):
            lines = []
            for i, r in enumerate(inner["results"], 1):
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                url = r.get("url", "")
                lines.append(f"{i}. {title}\n   {snippet}\n   {url}")
            return "\n\n".join(lines) if lines else "(no results)"
        # Generic dict
        return json.dumps(inner, ensure_ascii=False, default=str)[:2000]

    # Simple string result
    if isinstance(inner, str):
        return inner

    # ping-style response or other flat dicts
    if "pong" in result:
        return "pong: ok"

    return json.dumps(result, ensure_ascii=False, default=str)[:2000]


# ── WorkflowEngine ───────────────────────────────────────────────

class WorkflowEngine:
    """
    Loads and executes team workflows defined in YAML.

    Each workflow is a sequence of steps. Each step calls a registered
    worker task handler. The result of each step is available to the
    next step as {prev_result} in the input_template.
    """

    def __init__(
        self,
        config_path: str | Path,
        worker_client: WorkerClient,
    ):
        self.config_path = Path(config_path)
        self.wc = worker_client
        self.workflows: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load and validate the workflow YAML."""
        if not self.config_path.exists():
            logger.warning("Workflow config not found: %s", self.config_path)
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            logger.error("Workflow config is not a dict: %s", self.config_path)
            return {}

        logger.info(
            "Loaded workflows for %d teams from %s",
            len(data),
            self.config_path,
        )
        return data

    def reload(self) -> None:
        """Reload config from disk (useful for hot-reload)."""
        self.workflows = self._load_config()

    # ── Queries ──────────────────────────────────────────────────

    def get_teams(self) -> List[str]:
        """Return list of teams that have workflow definitions."""
        return list(self.workflows.keys())

    def get_default_workflow(self, team: str) -> Optional[str]:
        """Return the default workflow name for a team, or None."""
        team_cfg = self.workflows.get(team)
        if not team_cfg or not isinstance(team_cfg, dict):
            return None
        return team_cfg.get("default_workflow")

    def get_workflow_names(self, team: str) -> List[str]:
        """Return available workflow names for a team."""
        team_cfg = self.workflows.get(team)
        if not team_cfg or not isinstance(team_cfg, dict):
            return []
        wfs = team_cfg.get("workflows", {})
        return list(wfs.keys()) if isinstance(wfs, dict) else []

    def has_workflow(self, team: str, workflow_name: Optional[str] = None) -> bool:
        """Check if a team has a specific (or any default) workflow."""
        if workflow_name:
            return workflow_name in self.get_workflow_names(team)
        return self.get_default_workflow(team) is not None

    def _get_steps(self, team: str, workflow_name: str) -> List[Dict[str, Any]]:
        """Return the step list for a given team + workflow."""
        team_cfg = self.workflows.get(team, {})
        wfs = team_cfg.get("workflows", {})
        wf = wfs.get(workflow_name, {})
        steps = wf.get("steps", [])
        return steps if isinstance(steps, list) else []

    # ── Execution ────────────────────────────────────────────────

    def execute_workflow(
        self,
        team: str,
        workflow_name: Optional[str] = None,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow for a team.

        Args:
            team: Team name (must match a key in the YAML).
            workflow_name: Workflow to run. If None, uses the team's default.
            context: Template variables — typically {"topic": "...", "text": "..."}.

        Returns:
            {
                "ok": bool,
                "team": str,
                "workflow": str,
                "steps_completed": int,
                "steps_total": int,
                "results": [{"step": int, "task": str, "ok": bool, "result": ...}, ...],
                "final_result": str,
                "error": str | None,
            }
        """
        ctx = dict(context or {})
        ctx.setdefault("team", team)

        # Resolve workflow name
        if not workflow_name:
            workflow_name = self.get_default_workflow(team)

        if not workflow_name:
            return {
                "ok": False,
                "team": team,
                "workflow": None,
                "steps_completed": 0,
                "steps_total": 0,
                "results": [],
                "final_result": "",
                "error": f"No workflow defined for team '{team}'",
            }

        steps = self._get_steps(team, workflow_name)
        if not steps:
            return {
                "ok": False,
                "team": team,
                "workflow": workflow_name,
                "steps_completed": 0,
                "steps_total": 0,
                "results": [],
                "final_result": "",
                "error": f"Workflow '{workflow_name}' has no steps for team '{team}'",
            }

        logger.info(
            "Executing workflow '%s' for team '%s' (%d steps, context keys: %s)",
            workflow_name, team, len(steps), list(ctx.keys()),
        )

        step_results: List[Dict[str, Any]] = []
        prev_result_text = ""
        steps_completed = 0

        for i, step in enumerate(steps):
            task_name = step.get("task", "")
            if not task_name:
                logger.warning("Step %d has no 'task' field, skipping", i)
                step_results.append({
                    "step": i,
                    "task": "",
                    "ok": False,
                    "error": "Missing 'task' field",
                })
                continue

            # Build input from template
            input_template = step.get("input_template", {})
            render_ctx = {**ctx, "prev_result": prev_result_text}
            task_input = _render_template(input_template, render_ctx)

            logger.info(
                "  Step %d/%d: %s (input keys: %s)",
                i + 1, len(steps), task_name,
                list(task_input.keys()) if isinstance(task_input, dict) else "raw",
            )

            try:
                result = self.wc.run(task_name, task_input if isinstance(task_input, dict) else {})
                result_text = _extract_result_text(result)

                step_results.append({
                    "step": i,
                    "task": task_name,
                    "ok": True,
                    "result": result,
                })

                prev_result_text = result_text
                steps_completed += 1

                logger.info(
                    "  Step %d/%d: %s → OK (%d chars)",
                    i + 1, len(steps), task_name, len(result_text),
                )

            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "  Step %d/%d: %s → FAILED: %s",
                    i + 1, len(steps), task_name, error_msg,
                )
                step_results.append({
                    "step": i,
                    "task": task_name,
                    "ok": False,
                    "error": error_msg,
                })
                # Continue to next step — don't crash the whole workflow.
                # prev_result_text remains from the last successful step.

        all_ok = all(sr.get("ok") for sr in step_results)
        logger.info(
            "Workflow '%s' for '%s': %d/%d steps completed (ok=%s)",
            workflow_name, team, steps_completed, len(steps), all_ok,
        )

        return {
            "ok": all_ok,
            "team": team,
            "workflow": workflow_name,
            "steps_completed": steps_completed,
            "steps_total": len(steps),
            "results": step_results,
            "final_result": prev_result_text,
            "error": None if all_ok else f"{steps_completed}/{len(steps)} steps succeeded",
        }
