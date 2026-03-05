"""
Umbral Worker — Centralized Configuration

All environment variables are loaded here. Import from this module
instead of calling os.environ directly.
On Linux, if vars are missing from os.environ, we try loading from
~/.config/openclaw/env (e.g. when Worker is started by cron with minimal env).
"""

import os
from pathlib import Path


def _load_openclaw_env() -> None:
    """Load ~/.config/openclaw/env into os.environ (Linux/VPS). Fills missing vars; for LINEAR_API_KEY also overwrites if empty (cron may pass empty env)."""
    if os.name == "nt":
        return
    env_file = Path(os.environ.get("HOME", "")) / ".config/openclaw/env"
    if not env_file.exists():
        return
    raw = env_file.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'").replace("\r", "")
        if k.startswith("export "):
            k = k[7:].strip()
        if not k:
            continue
        # Siempre aplicar desde archivo (última aparición gana, como en bash source)
        os.environ[k] = v


_load_openclaw_env()

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
NOTION_TASKS_DB_ID: str | None = os.environ.get("NOTION_TASKS_DB_ID")
NOTION_API_VERSION: str = os.environ.get("NOTION_API_VERSION", "2022-06-28")

# Granola pipeline
ENLACE_NOTION_USER_ID: str | None = os.environ.get("ENLACE_NOTION_USER_ID")

# ---------------------------------------------------------------------------
# Linear
# ---------------------------------------------------------------------------
LINEAR_API_KEY: str | None = os.environ.get("LINEAR_API_KEY")

# ---------------------------------------------------------------------------
# Figma
# ---------------------------------------------------------------------------
FIGMA_API_KEY: str | None = os.environ.get("FIGMA_API_KEY")

# ---------------------------------------------------------------------------
# VM / Windows (tarea windows.open_notepad)
# ---------------------------------------------------------------------------
# Para que el Bloc de notas se abra en la sesión del usuario al iniciar sesión,
# definir en la VM: OPENCLAW_NOTEPAD_RUN_AS_USER (ej. "pcrick\\rick") y
# OPENCLAW_NOTEPAD_RUN_AS_PASSWORD (contraseña del usuario).
OPENCLAW_NOTEPAD_RUN_AS_USER: str | None = os.environ.get("OPENCLAW_NOTEPAD_RUN_AS_USER")
OPENCLAW_NOTEPAD_RUN_AS_PASSWORD: str | None = os.environ.get("OPENCLAW_NOTEPAD_RUN_AS_PASSWORD")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def require_worker_token() -> str:
    """Raise if WORKER_TOKEN is not set."""
    if not WORKER_TOKEN:
        raise RuntimeError("WORKER_TOKEN not configured on server")
    return WORKER_TOKEN


def require_notion_core() -> tuple[str, str]:
    """Raise if NOTION_API_KEY or NOTION_CONTROL_ROOM_PAGE_ID are missing."""
    missing = []
    if not NOTION_API_KEY:
        missing.append("NOTION_API_KEY")
    if not NOTION_CONTROL_ROOM_PAGE_ID:
        missing.append("NOTION_CONTROL_ROOM_PAGE_ID")
    if missing:
        raise RuntimeError(f"Missing Notion env vars: {', '.join(missing)}")
    return NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID  # type: ignore


def require_notion() -> tuple[str, str, str]:
    """Raise if any Notion env var is missing. Returns (api_key, control_room_id, granola_db_id)."""
    api_key, control_room_id = require_notion_core()
    if not NOTION_GRANOLA_DB_ID:
        raise RuntimeError("Missing Notion env vars: NOTION_GRANOLA_DB_ID")
    return api_key, control_room_id, NOTION_GRANOLA_DB_ID  # type: ignore
