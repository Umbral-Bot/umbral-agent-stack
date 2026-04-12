"""
CLI runner for the Copilot Agent.

Usage:
    python -m copilot_agent "Listá las tareas pendientes en Linear"
    python -m copilot_agent --interactive
"""

import argparse
import asyncio
import logging
import sys

from .agent import UmbralCopilotAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("copilot_agent")


async def _run_once(prompt: str) -> None:
    """Run a single prompt and print the result."""
    async with UmbralCopilotAgent() as agent:
        result = await agent.run(prompt)
        if result.get("error"):
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        print(result["text"])


async def _run_interactive() -> None:
    """Interactive REPL mode."""
    async with UmbralCopilotAgent() as agent:
        print("Rick (Copilot Agent) — escribe 'salir' para terminar.")
        while True:
            try:
                prompt = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                break
            if prompt.strip().lower() in ("salir", "exit", "quit"):
                break
            if not prompt.strip():
                continue
            result = await agent.run(prompt)
            if result.get("error"):
                print(f"[Error: {result['error']}]")
            else:
                print(result["text"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Umbral Copilot Agent (BYOK)")
    parser.add_argument("prompt", nargs="?", help="Single prompt to execute")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--model", default="gpt-5.4", help="Model name (default: gpt-5.4)")
    args = parser.parse_args()

    if args.interactive:
        asyncio.run(_run_interactive())
    elif args.prompt:
        asyncio.run(_run_once(args.prompt))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
