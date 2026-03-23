"""
Carga variables de entorno canónicas para scripts operativos.

Orden de precedencia:
1. Variables ya definidas en el proceso.
2. ~/.config/openclaw/env (VPS/Linux)
3. .env en la raíz del repo (dev/local)

Así los scripts pueden ejecutarse tanto en la VPS como en clones locales sin
depender de una sola convención de entorno.

Uso: importar al inicio del script:
    import scripts.env_loader  # noqa: F401
o: from scripts import env_loader; env_loader.load()
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"
_OPENCLAW_ENV_FILE = Path(os.environ.get("HOME", "")) / ".config/openclaw/env"


def _iter_env_files() -> list[Path]:
    candidates: list[Path] = []
    if os.name != "nt":
        candidates.append(_OPENCLAW_ENV_FILE)
    candidates.append(_ENV_FILE)
    return candidates


def load() -> None:
    """Carga archivos de entorno sin sobrescribir variables ya definidas."""
    for env_file in _iter_env_files():
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k.startswith("export "):
                k = k[7:].strip()
            v = v.strip().strip('"').strip("'").replace("\x00", "")
            if k and "\x00" not in k and k not in os.environ:
                os.environ.setdefault(k, v)
