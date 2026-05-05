"""Mission Control FastAPI app — dashboard read-only OpenClaw + Worker.

Arranque local:
    MISSION_CONTROL_TOKEN=devtoken python -m uvicorn mission_control.app:app \\
        --host 127.0.0.1 --port 8089

VPS (systemd user):
    Ver infra/systemd/mission-control.service.template.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import config
from .auth import require_token
from .routes import agents, health, queue, quotas, tournaments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mission_control %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mission_control")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    if not config.TOKEN:
        logger.warning(
            "MISSION_CONTROL_TOKEN no configurado — todas las rutas autenticadas "
            "responderán 503. Setear el env var antes de exponer el dashboard."
        )
    logger.info(
        "Mission Control v%s up — bind %s:%s, openclaw_json=%s",
        __import__("mission_control").__version__,
        config.HOST,
        config.PORT,
        config.OPENCLAW_JSON_PATH,
    )
    yield


app = FastAPI(
    title="Umbral Mission Control",
    version=__import__("mission_control").__version__,
    description="Dashboard read-only para OpenClaw + Worker. ADR-009.",
    lifespan=lifespan,
)

# /health: anónimo (ADR-009 D4).
app.include_router(health.router)

# Resto: bearer obligatorio.
_auth = [Depends(require_token)]
app.include_router(agents.router, dependencies=_auth)
app.include_router(quotas.router, dependencies=_auth)
app.include_router(tournaments.router, dependencies=_auth)
app.include_router(queue.router, dependencies=_auth)


_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/", response_class=HTMLResponse, dependencies=_auth)
async def index(request: Request) -> HTMLResponse:
    """Vista HTMX que pollea los endpoints JSON cada 10s."""
    return _templates.TemplateResponse("index.html", {"request": request})
