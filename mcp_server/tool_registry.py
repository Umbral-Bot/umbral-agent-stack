"""
Tool registry — builds MCP tool definitions from Worker task handlers.

Reads TASK_HANDLERS to auto-generate tool names, descriptions, and schemas.
Groups tools by module prefix (notion.*, linear.*, etc).
"""

import inspect
from typing import Any, Dict, List

from worker.tasks import TASK_HANDLERS


# Fallback descriptions for handlers without docstrings.
_FALLBACK_DESCRIPTIONS: Dict[str, str] = {
    "browser.click": "Click an element on the page by CSS selector.",
    "browser.navigate": "Navigate the browser to a URL.",
    "browser.press_key": "Press a keyboard key in the browser.",
    "browser.read_page": "Read the text content or HTML of the current page.",
    "browser.screenshot": "Take a screenshot of the current page.",
    "browser.type_text": "Type text into an element identified by CSS selector.",
    "gui.activate_window": "Activate/focus a window by title.",
    "gui.click": "Click at screen coordinates.",
    "gui.desktop_status": "Check desktop session status (resolution, active window).",
    "gui.hotkey": "Press a hotkey combination (e.g. ctrl+c).",
    "gui.list_windows": "List open windows on the desktop.",
    "gui.screenshot": "Take a desktop screenshot.",
    "gui.type_text": "Type text via keyboard.",
    "n8n.create_workflow": "Create a new n8n workflow.",
    "n8n.get_workflow": "Get details of an n8n workflow by ID.",
    "n8n.list_workflows": "List n8n workflows.",
    "n8n.post_webhook": "POST data to an n8n webhook URL.",
    "n8n.update_workflow": "Update an existing n8n workflow.",
    "windows.fs.ensure_dirs": "Ensure directories exist, creating them if needed.",
    "windows.fs.list": "List contents of a directory on the Worker VM.",
    "windows.fs.read_text": "Read a text file from the Worker VM filesystem.",
    "windows.fs.write_bytes_b64": "Write binary data (base64-encoded) to a file.",
    "windows.fs.write_text": "Write text to a file on the Worker VM filesystem.",
}


def _get_description(task_name: str) -> str:
    """Extract first paragraph of handler docstring, or use fallback."""
    handler = TASK_HANDLERS.get(task_name)
    if handler is None:
        return task_name
    doc = inspect.getdoc(handler) or ""
    # First paragraph (up to blank line)
    lines: List[str] = []
    for line in doc.split("\n"):
        if not line.strip() and lines:
            break
        lines.append(line.strip())
    desc = " ".join(lines).strip()
    if not desc:
        desc = _FALLBACK_DESCRIPTIONS.get(task_name, f"Execute Worker task: {task_name}")
    # Cap at 200 chars for MCP tool description
    if len(desc) > 200:
        desc = desc[:197] + "..."
    return desc


def _get_module(task_name: str) -> str:
    """Extract module prefix: 'notion.upsert_task' → 'notion'."""
    parts = task_name.split(".")
    return parts[0] if len(parts) > 1 else "system"


def build_tool_definitions() -> List[Dict[str, Any]]:
    """
    Build MCP-compatible tool definitions for all Worker tasks.

    Returns list of dicts with: name, description, module, inputSchema.
    """
    tools = []
    for task_name in sorted(TASK_HANDLERS.keys()):
        tool_name = task_name.replace(".", "_")  # MCP tool names can't have dots
        tools.append({
            "name": tool_name,
            "task_name": task_name,  # original name for Worker API
            "description": _get_description(task_name),
            "module": _get_module(task_name),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "object",
                        "description": f"Input parameters for '{task_name}'. Pass as a JSON object with the fields the handler expects.",
                    },
                },
                "required": ["input"],
            },
        })
    return tools


# Pre-built registry for import
TOOL_DEFINITIONS = build_tool_definitions()

# Lookup: mcp_tool_name → original task_name
TOOL_NAME_TO_TASK: Dict[str, str] = {t["name"]: t["task_name"] for t in TOOL_DEFINITIONS}
