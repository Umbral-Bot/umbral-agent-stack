"""
Umbral Worker — Centralized Configuration

All environment variables are loaded here. Import from this module
instead of calling os.environ directly.
"""

import os


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
WORKER_TOKEN: str | None = os.environ.get("WORKER_TOKEN")
WORKER_PORT: int = int(os.environ.get("WORKER_PORT", "8088"))
WORKER_RATE_LIMIT_PER_MIN: int = int(os.environ.get("WORKER_RATE_LIMIT_PER_MIN", "120"))

# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------
NOTION_API_KEY: str | None = os.environ.get("NOTION_API_KEY")
NOTION_CONTROL_ROOM_PAGE_ID: str | None = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID")
NOTION_GRANOLA_DB_ID: str | None = os.environ.get("NOTION_GRANOLA_DB_ID")
NOTION_DASHBOARD_PAGE_ID: str | None = os.environ.get("NOTION_DASHBOARD_PAGE_ID")
NOTION_API_VERSION: str = os.environ.get("NOTION_API_VERSION", "2022-06-28")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def require_worker_token() -> str:
    """Raise if WORKER_TOKEN is not set."""
    if not WORKER_TOKEN:
        raise RuntimeError("WORKER_TOKEN not configured on server")
    return WORKER_TOKEN


def require_notion() -> tuple[str, str, str]:
    """Raise if any Notion env var is missing. Returns (api_key, control_room_id, granola_db_id)."""
    missing = []
    if not NOTION_API_KEY:
        missing.append("NOTION_API_KEY")
    if not NOTION_CONTROL_ROOM_PAGE_ID:
        missing.append("NOTION_CONTROL_ROOM_PAGE_ID")
    if not NOTION_GRANOLA_DB_ID:
        missing.append("NOTION_GRANOLA_DB_ID")
    if missing:
        raise RuntimeError(f"Missing Notion env vars: {', '.join(missing)}")
    return NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID, NOTION_GRANOLA_DB_ID  # type: ignore
