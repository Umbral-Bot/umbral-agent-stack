"""
Granola Watcher — .env file loader (stdlib only).

Loads KEY=VALUE pairs from a .env file into os.environ.
Falls back gracefully if the file doesn't exist.
"""

import os
from pathlib import Path


def load_env(path: str = r"C:\Granola\.env") -> dict[str, str]:
    """Carga variables de entorno desde archivo .env simple (KEY=VALUE).

    Returns a dict of the loaded variables (for testing/inspection).
    If the file doesn't exist, returns an empty dict without raising.
    """
    loaded: dict[str, str] = {}
    env_path = Path(path)

    if not env_path.is_file():
        return loaded

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        # Strip surrounding quotes if present
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ.setdefault(key, value)
        loaded[key] = value

    return loaded
