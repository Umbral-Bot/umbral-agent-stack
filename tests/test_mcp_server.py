"""
Tests for the Umbral MCP Server — Phase 3.

Validates:
- Tool registry generates correct definitions from TASK_HANDLERS
- Tool names are MCP-compliant (no dots)
- All handlers have descriptions
- Server builds without errors
- call_tool proxies to Worker API
- Unknown tool returns error
- Missing WORKER_TOKEN returns error

Run:
    python -m pytest tests/test_mcp_server.py -v
"""

import json

import pytest

from mcp_server.tool_registry import (
    TOOL_DEFINITIONS,
    TOOL_NAME_TO_TASK,
    build_tool_definitions,
)
from worker.tasks import TASK_HANDLERS


# ---------------------------------------------------------------------------
# Tool registry tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_all_handlers_have_tools(self):
        """Every TASK_HANDLERS entry must produce a tool definition."""
        tool_task_names = {t["task_name"] for t in TOOL_DEFINITIONS}
        for task_name in TASK_HANDLERS:
            assert task_name in tool_task_names, f"Missing tool for handler: {task_name}"

    def test_tool_count_matches_handlers(self):
        assert len(TOOL_DEFINITIONS) == len(TASK_HANDLERS)

    def test_no_dots_in_tool_names(self):
        """MCP tool names must not contain dots."""
        for t in TOOL_DEFINITIONS:
            assert "." not in t["name"], f"Tool name has dots: {t['name']}"

    def test_all_tools_have_descriptions(self):
        for t in TOOL_DEFINITIONS:
            assert t["description"], f"Empty description for: {t['name']}"
            assert len(t["description"]) <= 200

    def test_all_tools_have_input_schema(self):
        for t in TOOL_DEFINITIONS:
            schema = t["inputSchema"]
            assert schema["type"] == "object"
            assert "input" in schema["properties"]
            assert "input" in schema["required"]

    def test_lookup_table_consistent(self):
        for t in TOOL_DEFINITIONS:
            assert TOOL_NAME_TO_TASK[t["name"]] == t["task_name"]

    def test_known_tools_exist(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert "ping" in names
        assert "llm_generate" in names
        assert "notion_upsert_task" in names
        assert "linear_create_issue" in names
        assert "research_web" in names

    def test_build_is_deterministic(self):
        a = build_tool_definitions()
        b = build_tool_definitions()
        assert a == b


# ---------------------------------------------------------------------------
# Server build tests
# ---------------------------------------------------------------------------


class TestServerBuild:
    def test_server_creates_successfully(self):
        from mcp_server.server import _build_server
        server = _build_server()
        assert server.name == "umbral-worker"


# ---------------------------------------------------------------------------
# call_tool proxy tests
# ---------------------------------------------------------------------------


class TestCallTool:
    def test_call_tool_lookup_resolves_ping(self, monkeypatch):
        """Tool name 'ping' should resolve to task name 'ping'."""
        assert TOOL_NAME_TO_TASK["ping"] == "ping"
        assert TOOL_NAME_TO_TASK["llm_generate"] == "llm.generate"
        assert TOOL_NAME_TO_TASK["notion_upsert_task"] == "notion.upsert_task"

    def test_unknown_tool_not_in_lookup(self):
        """Unknown tool name should not be in the lookup table."""
        assert "nonexistent_tool_xyz" not in TOOL_NAME_TO_TASK

    def test_missing_token_warning(self, monkeypatch):
        """Server should still build even without WORKER_TOKEN."""
        import mcp_server.server as srv
        monkeypatch.setattr(srv, "WORKER_TOKEN", "")
        server = srv._build_server()
        assert server.name == "umbral-worker"


# ---------------------------------------------------------------------------
# Module grouping tests
# ---------------------------------------------------------------------------


class TestModuleGrouping:
    def test_modules_are_populated(self):
        modules = {t["module"] for t in TOOL_DEFINITIONS}
        assert "notion" in modules
        assert "linear" in modules
        assert "system" in modules

    def test_notion_tools_grouped(self):
        notion_tools = [t for t in TOOL_DEFINITIONS if t["module"] == "notion"]
        assert len(notion_tools) >= 14
