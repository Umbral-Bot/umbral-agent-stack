"""
Tests for Team Workflow Engine (R5 task 020).

Covers:
- YAML loading and team queries
- Template rendering with {prev_result}, {topic}, {team}
- Multi-step workflow execution (marketing 3-step)
- prev_result propagation between steps
- Team without workflow uses fallback
- Error in one step doesn't crash the whole workflow
- Result text extraction from various task response shapes
- Smart reply integration (workflow vs LLM-plan fallback)

Run with:
    python -m pytest tests/test_workflow_engine.py -v
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import yaml

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")
os.environ.setdefault("WORKER_URL", "http://localhost:8088")

from dispatcher.workflow_engine import (
    WorkflowEngine,
    WorkflowNotFoundError,
    _extract_result_text,
    _render_template,
)


# ======================================================================
# Fixtures
# ======================================================================

SAMPLE_CONFIG = {
    "marketing": {
        "default_workflow": "research_and_post",
        "workflows": {
            "research_and_post": {
                "description": "Research + post + notify",
                "steps": [
                    {
                        "task": "research.web",
                        "input_template": {
                            "query": "{topic} marketing digital",
                            "count": 5,
                        },
                    },
                    {
                        "task": "llm.generate",
                        "input_template": {
                            "prompt": "Genera un post sobre {topic}: {prev_result}",
                            "model": "gemini-2.5-flash",
                        },
                    },
                    {
                        "task": "notion.add_comment",
                        "input_template": {
                            "text": "Rick: [Marketing] Post para {topic}:\n{prev_result}",
                        },
                    },
                ],
            },
        },
    },
    "advisory": {
        "default_workflow": "financial_analysis",
        "workflows": {
            "financial_analysis": {
                "steps": [
                    {
                        "task": "research.web",
                        "input_template": {"query": "{topic} análisis financiero"},
                    },
                    {
                        "task": "llm.generate",
                        "input_template": {
                            "prompt": "Análisis financiero de {topic}: {prev_result}",
                        },
                    },
                ],
            },
        },
    },
    "system": {
        "default_workflow": "health_report",
        "workflows": {
            "health_report": {
                "steps": [
                    {"task": "ping"},
                ],
            },
        },
    },
}


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Write sample config to a temp YAML file."""
    p = tmp_path / "team_workflows.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(SAMPLE_CONFIG, f, allow_unicode=True)
    return p


@pytest.fixture
def mock_wc() -> MagicMock:
    """A mock WorkerClient."""
    wc = MagicMock()
    wc.base_url = "http://localhost:8088"
    wc.token = "test"
    wc.timeout = 30.0
    return wc


@pytest.fixture
def engine(config_file: Path, mock_wc: MagicMock) -> WorkflowEngine:
    """WorkflowEngine loaded with the sample config."""
    return WorkflowEngine(config_file, mock_wc)


# ======================================================================
# Template rendering
# ======================================================================


class TestRenderTemplate:
    def test_simple_string(self):
        assert _render_template("hello {name}", {"name": "world"}) == "hello world"

    def test_dict_recursive(self):
        tpl = {"query": "{topic} test", "count": 5}
        result = _render_template(tpl, {"topic": "AI"})
        assert result == {"query": "AI test", "count": 5}

    def test_list_recursive(self):
        tpl = ["{a}", "{b}"]
        result = _render_template(tpl, {"a": "x", "b": "y"})
        assert result == ["x", "y"]

    def test_passthrough_int(self):
        assert _render_template(42, {"x": "y"}) == 42

    def test_multiple_vars_in_string(self):
        result = _render_template(
            "{topic} for {team}",
            {"topic": "AI", "team": "marketing"},
        )
        assert result == "AI for marketing"

    def test_missing_var_left_as_is(self):
        result = _render_template("{unknown_var}", {"topic": "AI"})
        assert result == "{unknown_var}"


# ======================================================================
# Result text extraction
# ======================================================================


class TestExtractResultText:
    def test_llm_generate_shape(self):
        r = {"result": {"text": "Hello world"}}
        assert _extract_result_text(r) == "Hello world"

    def test_research_web_shape(self):
        r = {
            "result": {
                "results": [
                    {"title": "T1", "snippet": "S1", "url": "http://u1"},
                    {"title": "T2", "snippet": "S2", "url": "http://u2"},
                ]
            }
        }
        text = _extract_result_text(r)
        assert "T1" in text
        assert "T2" in text
        assert "S1" in text

    def test_composite_report_shape(self):
        r = {"result": {"report": "Full report text"}}
        assert _extract_result_text(r) == "Full report text"

    def test_string_result(self):
        r = {"result": "just a string"}
        assert _extract_result_text(r) == "just a string"

    def test_ping_shape(self):
        r = {"pong": True, "version": "0.4.0"}
        assert _extract_result_text(r) == "pong: ok"

    def test_empty_research(self):
        r = {"result": {"results": []}}
        assert "(no results)" in _extract_result_text(r)


# ======================================================================
# Config loading & queries
# ======================================================================


class TestConfigLoading:
    def test_loads_teams(self, engine: WorkflowEngine):
        teams = engine.get_teams()
        assert set(teams) == {"marketing", "advisory", "system"}

    def test_get_default_workflow(self, engine: WorkflowEngine):
        assert engine.get_default_workflow("marketing") == "research_and_post"
        assert engine.get_default_workflow("advisory") == "financial_analysis"
        assert engine.get_default_workflow("system") == "health_report"

    def test_get_default_workflow_unknown_team(self, engine: WorkflowEngine):
        assert engine.get_default_workflow("nonexistent") is None

    def test_get_workflow_names(self, engine: WorkflowEngine):
        assert "research_and_post" in engine.get_workflow_names("marketing")

    def test_has_workflow(self, engine: WorkflowEngine):
        assert engine.has_workflow("marketing") is True
        assert engine.has_workflow("marketing", "research_and_post") is True
        assert engine.has_workflow("marketing", "nonexistent") is False
        assert engine.has_workflow("nonexistent") is False

    def test_missing_config_file(self, mock_wc: MagicMock, tmp_path: Path):
        eng = WorkflowEngine(tmp_path / "missing.yaml", mock_wc)
        assert eng.get_teams() == []

    def test_reload(self, engine: WorkflowEngine, config_file: Path):
        # Modify config and reload
        new_config = {"new_team": {"default_workflow": "w1", "workflows": {"w1": {"steps": [{"task": "ping"}]}}}}
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f)
        engine.reload()
        assert "new_team" in engine.get_teams()
        assert "marketing" not in engine.get_teams()


# ======================================================================
# Workflow execution
# ======================================================================


class TestExecuteWorkflow:
    def test_marketing_3_steps(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """Marketing workflow executes all 3 steps and returns ok."""
        mock_wc.run.side_effect = [
            # Step 0: research.web
            {"result": {"results": [{"title": "T1", "snippet": "S1", "url": "http://u1"}]}},
            # Step 1: llm.generate
            {"result": {"text": "Generated LinkedIn post about AI"}},
            # Step 2: notion.add_comment
            {"result": "ok"},
        ]

        result = engine.execute_workflow("marketing", context={"topic": "IA generativa"})

        assert result["ok"] is True
        assert result["team"] == "marketing"
        assert result["workflow"] == "research_and_post"
        assert result["steps_completed"] == 3
        assert result["steps_total"] == 3
        assert len(result["results"]) == 3
        assert result["error"] is None

        # Verify all 3 tasks were called
        assert mock_wc.run.call_count == 3
        call_tasks = [c.args[0] for c in mock_wc.run.call_args_list]
        assert call_tasks == ["research.web", "llm.generate", "notion.add_comment"]

    def test_prev_result_passes_between_steps(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """Each step receives {prev_result} from the previous step."""
        mock_wc.run.side_effect = [
            {"result": {"results": [{"title": "Research Title", "snippet": "Research snippet", "url": "http://url"}]}},
            {"result": {"text": "LLM output text"}},
            {"result": "ok"},
        ]

        engine.execute_workflow("marketing", context={"topic": "test"})

        # Step 1 (llm.generate) should have received research results in prompt
        step1_input = mock_wc.run.call_args_list[1][1] if mock_wc.run.call_args_list[1][1] else mock_wc.run.call_args_list[1][0][1]
        prompt = step1_input.get("prompt", "")
        assert "Research Title" in prompt or "Research snippet" in prompt

        # Step 2 (notion.add_comment) should have LLM output in text
        step2_input = mock_wc.run.call_args_list[2][0][1]
        text = step2_input.get("text", "")
        assert "LLM output text" in text

    def test_team_without_workflow_returns_error(self, engine: WorkflowEngine):
        """Unknown team returns ok=False with error message."""
        result = engine.execute_workflow("nonexistent_team")
        assert result["ok"] is False
        assert "No workflow defined" in result["error"]
        assert result["steps_completed"] == 0

    def test_error_in_step_continues(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """An error in step 1 doesn't crash step 2."""
        mock_wc.run.side_effect = [
            RuntimeError("Research API down"),     # Step 0 fails
            {"result": {"text": "LLM generated anyway"}},  # Step 1 succeeds
            {"result": "ok"},                      # Step 2 succeeds
        ]

        result = engine.execute_workflow("marketing", context={"topic": "test"})

        assert result["ok"] is False  # not all steps ok
        assert result["steps_completed"] == 2  # 2 of 3 succeeded
        assert result["steps_total"] == 3
        assert result["results"][0]["ok"] is False
        assert "RuntimeError" in result["results"][0]["error"]
        assert result["results"][1]["ok"] is True
        assert result["results"][2]["ok"] is True

    def test_system_health_workflow(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """System health_report workflow runs ping."""
        mock_wc.run.return_value = {"pong": True, "version": "0.4.0"}
        result = engine.execute_workflow("system")
        assert result["ok"] is True
        assert result["workflow"] == "health_report"
        assert result["steps_completed"] == 1
        mock_wc.run.assert_called_once_with("ping", {})

    def test_explicit_workflow_name(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """Can specify workflow name explicitly instead of using default."""
        mock_wc.run.side_effect = [
            {"result": {"results": []}},
            {"result": {"text": "analysis"}},
        ]
        result = engine.execute_workflow("advisory", "financial_analysis", {"topic": "BIM"})
        assert result["ok"] is True
        assert result["workflow"] == "financial_analysis"

    def test_step_without_input_template(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """A step without input_template gets empty dict input."""
        mock_wc.run.return_value = {"pong": True}
        result = engine.execute_workflow("system", "health_report")
        mock_wc.run.assert_called_with("ping", {})

    def test_context_variables_in_template(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """Verify {topic} and {team} are replaced in templates."""
        mock_wc.run.side_effect = [
            {"result": {"results": []}},
            {"result": {"text": "post"}},
            {"result": "ok"},
        ]
        engine.execute_workflow("marketing", context={"topic": "crypto"})

        # Check first step's query has "crypto"
        step0_input = mock_wc.run.call_args_list[0][0][1]
        assert "crypto" in step0_input["query"]

    def test_all_steps_fail(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """All steps failing returns ok=False with 0 completed."""
        mock_wc.run.side_effect = RuntimeError("down")
        result = engine.execute_workflow("marketing", context={"topic": "x"})
        assert result["ok"] is False
        assert result["steps_completed"] == 0
        assert result["steps_total"] == 3

    def test_final_result_from_last_successful_step(self, engine: WorkflowEngine, mock_wc: MagicMock):
        """final_result comes from last successful step's output."""
        mock_wc.run.side_effect = [
            {"result": {"results": [{"title": "R", "snippet": "S", "url": "U"}]}},
            {"result": {"text": "Final answer from LLM"}},
            {"result": "ok"},
        ]
        result = engine.execute_workflow("marketing", context={"topic": "x"})
        # Last step is notion.add_comment which returns "ok" string
        assert result["final_result"] == "ok"


# ======================================================================
# Smart reply integration
# ======================================================================


class TestSmartReplyIntegration:
    """Test that smart_reply._handle_task uses workflow engine when available."""

    @patch("dispatcher.smart_reply._get_workflow_engine")
    @patch("dispatcher.smart_reply._post_comment")
    def test_task_with_workflow_calls_engine(
        self, mock_post, mock_get_engine
    ):
        """When team has a workflow, _handle_task executes it."""
        from dispatcher.smart_reply import _handle_task
        from dispatcher.queue import TaskQueue

        mock_engine = MagicMock()
        mock_engine.has_workflow.return_value = True
        mock_engine.get_default_workflow.return_value = "research_and_post"
        mock_engine.execute_workflow.return_value = {
            "ok": True,
            "team": "marketing",
            "workflow": "research_and_post",
            "steps_completed": 3,
            "steps_total": 3,
            "results": [],
            "final_result": "Generated post",
            "error": None,
        }
        mock_get_engine.return_value = mock_engine

        wc = MagicMock()
        queue = MagicMock()

        _handle_task("crea un post sobre IA", "comment-123", "marketing", wc, queue)

        mock_engine.has_workflow.assert_called_once_with("marketing")
        mock_engine.execute_workflow.assert_called_once()
        # Should NOT enqueue (workflow handled it)
        queue.enqueue.assert_not_called()

    @patch("dispatcher.smart_reply._get_workflow_engine")
    @patch("dispatcher.smart_reply._do_llm_generate")
    @patch("dispatcher.smart_reply._post_comment")
    def test_task_without_workflow_uses_llm_plan(
        self, mock_post, mock_llm, mock_get_engine
    ):
        """When team has no workflow, falls back to LLM plan + enqueue."""
        from dispatcher.smart_reply import _handle_task

        mock_engine = MagicMock()
        mock_engine.has_workflow.return_value = False
        mock_get_engine.return_value = mock_engine

        mock_llm.return_value = "1. Step one\n2. Step two"

        wc = MagicMock()
        queue = MagicMock()

        _handle_task("haz algo", "comment-456", "unknown_team", wc, queue)

        mock_engine.execute_workflow.assert_not_called()
        queue.enqueue.assert_called_once()

    @patch("dispatcher.smart_reply._get_workflow_engine")
    @patch("dispatcher.smart_reply._post_comment")
    def test_workflow_error_posts_error_message(
        self, mock_post, mock_get_engine
    ):
        """When workflow has errors, posts error summary."""
        from dispatcher.smart_reply import _handle_task

        mock_engine = MagicMock()
        mock_engine.has_workflow.return_value = True
        mock_engine.get_default_workflow.return_value = "research_and_post"
        mock_engine.execute_workflow.return_value = {
            "ok": False,
            "team": "marketing",
            "workflow": "research_and_post",
            "steps_completed": 1,
            "steps_total": 3,
            "results": [],
            "final_result": "",
            "error": "1/3 steps succeeded",
        }
        mock_get_engine.return_value = mock_engine

        wc = MagicMock()
        queue = MagicMock()

        _handle_task("crea post", "comment-789", "marketing", wc, queue)

        # Should post error message
        posted_text = mock_post.call_args_list[-1][0][1]
        assert "errores" in posted_text.lower() or "error" in posted_text.lower()
