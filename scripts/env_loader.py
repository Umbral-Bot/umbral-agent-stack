"""
Carga .env de la raíz del repo en os.environ (solo si la variable no está ya definida).
Así los scripts pueden leer claves desde .env sin tenerlas en el repo.
Uso: importar al inicio del script:
    import scripts.env_loader  # noqa: F401
o: from scripts import env_loader; env_loader.load()
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


def load() -> None:
    """Carga .env en os.environ. No sobrescribe variables ya definidas."""
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'").replace("\x00", "")
        if k and "\x00" not in k and k not in os.environ:
            os.environ.setdefault(k, v)
