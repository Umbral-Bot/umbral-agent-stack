"""
Umbral Worker MCP Server

Exposes 73 Worker task handlers as MCP tools.
Proxies tool calls to the Worker HTTP API (POST /run).

Transports:
    - stdio  (default) — for VS Code, Claude Desktop, local agents
    - sse    — for remote HTTP clients

Env vars:
    WORKER_URL    — Worker base URL (default: http://localhost:8088)
    WORKER_TOKEN  — Bearer token for Worker auth (required)

Usage:
    # stdio (default)
    python -m mcp_server.server

    # SSE on port 8090
    python -m mcp_server.server --transport sse --port 8090
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tool_registry import TOOL_DEFINITIONS, TOOL_NAME_TO_TASK

logger = logging.getLogger("mcp_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8088")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")


def _build_server() -> Server:
    """Create and configure the MCP server with all Worker tools."""
    server = Server("umbral-worker")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        task_name = TOOL_NAME_TO_TASK.get(name)
        if task_name is None:
            return [TextContent(type="text", text=json.dumps({
                "ok": False,
                "error": f"Unknown tool: {name}",
            }))]

        if not WORKER_TOKEN:
            return [TextContent(type="text", text=json.dumps({
                "ok": False,
                "error": "WORKER_TOKEN not set — cannot authenticate with Worker API.",
            }))]

        input_data = arguments.get("input", {})
        payload = {"task": task_name, "input": input_data}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{WORKER_URL}/run",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {WORKER_TOKEN}",
                        "X-Umbral-Caller": "mcp-server",
                    },
                )
                result = resp.json()
        except httpx.TimeoutException:
            result = {"ok": False, "error": f"Worker timeout after 120s for task '{task_name}'"}
        except httpx.ConnectError:
            result = {"ok": False, "error": f"Cannot connect to Worker at {WORKER_URL}"}
        except Exception as e:
            result = {"ok": False, "error": f"Request failed: {e}"}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    return server


async def _run_stdio() -> None:
    """Run MCP server over stdio transport."""
    server = _build_server()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Umbral MCP server started (stdio, %d tools)", len(TOOL_DEFINITIONS))
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def _run_sse(host: str, port: int) -> None:
    """Run MCP server over SSE transport."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    server = _build_server()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Any) -> Any:
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    import uvicorn
    logger.info("Umbral MCP server starting (SSE on %s:%d, %d tools)", host, port, len(TOOL_DEFINITIONS))
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Umbral Worker MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    if not WORKER_TOKEN:
        logger.warning("WORKER_TOKEN not set — tool calls will fail.")

    if args.transport == "sse":
        asyncio.run(_run_sse(args.host, args.port))
    else:
        asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
