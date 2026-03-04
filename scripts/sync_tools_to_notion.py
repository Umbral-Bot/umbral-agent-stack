"""
sync_tools_to_notion.py — Sync Worker task inventory to Notion Dashboard

Reads TASK_HANDLERS from the Worker, checks env-var availability for each
task category, and posts a summary table to the Notion Dashboard page.

Usage:
    python scripts/sync_tools_to_notion.py --dry-run   # print without posting
    python scripts/sync_tools_to_notion.py              # post to Notion
"""

import argparse
import json
import logging
import os
import sys

# Ensure repo root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Env requirements per task category
# ---------------------------------------------------------------------------

_CATEGORY_ENV_REQUIREMENTS: dict[str, list[str]] = {
    "notion": ["NOTION_API_KEY"],
    "linear": ["LINEAR_API_KEY"],
    "figma": ["FIGMA_API_KEY"],
    "azure": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
    "ai": ["ANTHROPIC_API_KEY"],  # at least one LLM provider
    "integrations": [],  # make.post_webhook needs URL per call, no global env
    "windows": [],  # runs on the VM itself
    "system": [],  # always available
}


def _check_env(env_vars: list[str]) -> bool:
    """Return True if ALL env vars are set and non-empty."""
    return all(os.environ.get(v, "").strip() for v in env_vars)


def build_tools_table() -> list[dict]:
    """Build a table rows of tasks with module, category and status."""
    from worker.tasks import TASK_HANDLERS

    _CATEGORY_MAP = {
        "ping": "system", "notion": "notion", "windows": "windows",
        "system": "system", "linear": "linear", "research": "ai",
        "llm": "ai", "composite": "ai", "figma": "figma",
        "azure": "azure", "make": "integrations",
    }

    rows = []
    for task_name in sorted(TASK_HANDLERS.keys()):
        module = task_name.split(".")[0]
        category = _CATEGORY_MAP.get(module, module)
        env_vars = _CATEGORY_ENV_REQUIREMENTS.get(category, [])
        configured = _check_env(env_vars) if env_vars else True
        rows.append({
            "task": task_name,
            "module": module,
            "category": category,
            "status": "✅" if configured else "⚠️",
            "env_vars": env_vars,
        })
    return rows


def format_markdown_table(rows: list[dict]) -> str:
    """Format rows as Markdown table."""
    lines = ["| Task | Status | Module | Category |", "|------|--------|--------|----------|"]
    for r in rows:
        lines.append(f"| `{r['task']}` | {r['status']} | {r['module']} | {r['category']} |")
    return "\n".join(lines)


def post_to_notion(content: str) -> dict:
    """Post the tools table as a comment on the Notion Dashboard page."""
    import urllib.request

    api_key = os.environ.get("NOTION_API_KEY", "").strip()
    page_id = os.environ.get("NOTION_DASHBOARD_PAGE_ID", "").strip()
    if not api_key or not page_id:
        return {"ok": False, "error": "NOTION_API_KEY or NOTION_DASHBOARD_PAGE_ID not set"}

    # Notion comments have a 2000-char limit per rich_text block; split if needed
    chunks = [content[i:i + 1900] for i in range(0, len(content), 1900)]
    rich_text = [{"type": "text", "text": {"content": chunk}} for chunk in chunks]

    payload = {
        "parent": {"page_id": page_id},
        "rich_text": rich_text,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/comments",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return {"ok": True, "status": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Sync Worker tools inventory to Notion Dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Print table without posting to Notion")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of Markdown")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    rows = build_tools_table()
    total = len(rows)
    configured = sum(1 for r in rows if r["status"] == "✅")
    warning = total - configured

    header = f"🔧 Tools Inventory — {total} tasks ({configured} ✅ / {warning} ⚠️)\n\n"

    if args.json:
        print(json.dumps({"total": total, "configured": configured, "tasks": rows}, indent=2))
        return

    table = format_markdown_table(rows)
    output = header + table
    print(output)

    if args.dry_run:
        print(f"\n[dry-run] Would post {len(output)} chars to Notion Dashboard")
        return

    result = post_to_notion(output)
    if result.get("ok"):
        print(f"\n✅ Posted to Notion Dashboard (status {result.get('status', '?')})")
    else:
        print(f"\n❌ Failed to post: {result.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
