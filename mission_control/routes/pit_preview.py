"""Preview seguro de prototipos PIT — PIT-5 P5.3, opción A del plan.

Tres routers (ver docs/ops/pit-5-mission-control-v2-implementation-plan.md §4):

- ``link_router`` (bearer, lo monta app.py con ``dependencies=_auth``):
  ``GET /pit/tournaments/{pit}/lanes/{lane}/iterations/{n}/preview-link`` —
  emite URL firmada HMAC-SHA256 (key = MISSION_CONTROL_TOKEN, TTL 15 min).
- ``preview_router`` (SIN bearer global — auth propia):
  ``GET /pit/preview/{pit}/{lane}/{n}/{path}`` — primer hit valida ``?t=``
  (firma + expiry), setea cookie ``HttpOnly; SameSite=Strict`` con ``Path``
  acotado al prefijo del preview y redirige a la entry; los hits siguientes
  (assets relativos css/js/img) validan la cookie. La cookie NO da acceso a
  las rutas JSON ``/pit/*`` ni al resto del dashboard (bearer-only).
- ``alias_router``: ``/pit-preview/*`` → redirect a la ruta canónica
  ``/pit/preview/...`` normalizando los 3 formatos de path observados en los
  announce del piloto (P5.0): ``iterations/<n>/prototype/<file>``,
  ``iter-<n>`` e ``iteration-<n>``. Rewrite puro: sin auth, sin filesystem.

Guards de seguridad (cada uno con test dedicado en test_pit_preview.py):

1. realpath + ``is_relative_to(<vault>/pit/<pit>/lanes/<lane>/iterations/<n>/prototype/)``
   — rechaza ``..``, ``%2e%2e`` y symlinks que escapen del vault → 403.
2. Regex de ids (mismos de P5.1 / kpi-pack.schema.json) ANTES de tocar
   filesystem → 422.
3. Allowlist de extensiones (config.PIT_PREVIEW_ALLOWED_EXTENSIONS) → resto
   403; Content-Type explícito por extensión + ``X-Content-Type-Options: nosniff``.
4. Sin directory listing; el root del prototype redirige a ``index.html``
   (o al primer ``.html`` si no hay index); subdirectorios sin archivo → 404.
5. HTML servido con CSP self-only (corta exfiltración a internet) +
   ``Referrer-Policy: no-referrer``.
6. Firma/cookie HMAC con TTL corto; vencida o inválida → 403; ausente → 401;
   MISSION_CONTROL_TOKEN sin configurar → 503 (fail-closed, igual que bearer).
7. Nada acá cambia el bind (config.HOST sigue 127.0.0.1) ni emite URL pública.

El archivo servido se resuelve SIEMPRE por filesystem
(``iterations/<n>/prototype/...``) — nunca se confía en el PROTOTYPE_URL del
announce. Solo se sirve el subtree activo ``pit/`` (archive/ no se publica).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import RedirectResponse

from mission_control import config
from mission_control.adapters import pit_vault
from mission_control.auth import make_preview_sig, verify_preview_sig

link_router = APIRouter(prefix="/pit/tournaments")
preview_router = APIRouter(prefix="/pit/preview")
alias_router = APIRouter(prefix="/pit-preview")

PREVIEW_COOKIE = "pit_preview"

# Content-Type explícito por extensión permitida (guard 3) — nunca sniffing.
CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}

# CSP del plan §P5.3: self-only, sin conexiones externas; inline css/js
# permitido (prototipos single-file generados por agentes).
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; connect-src 'self'"
)

# Formatos legacy del announce del piloto (evidencia P5.0).
_ALIAS_CANONICAL_RE = re.compile(r"^iterations/([0-9]{1,2})(?:/prototype(?:/(.*))?)?$")
_ALIAS_ITER_RE = re.compile(r"^iter(?:ation)?-([0-9]{1,2})$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_ids(pit_id: str, lane_id: str) -> None:
    """Guard 2: regex de ids (P5.1) antes de cualquier acceso a filesystem."""
    if not pit_vault.PIT_ID_RE.fullmatch(pit_id):
        raise HTTPException(status_code=422, detail="invalid pit_id")
    if not pit_vault.LANE_ID_RE.fullmatch(lane_id):
        raise HTTPException(status_code=422, detail="invalid lane_id")


def _scope(pit_id: str, lane_id: str, iteration: int) -> str:
    return f"{pit_id}/{lane_id}/{iteration}"


def _prefix(pit_id: str, lane_id: str, iteration: int) -> str:
    return f"/pit/preview/{pit_id}/{lane_id}/{iteration}/"


def _prototype_root(pit_id: str, lane_id: str, iteration: int) -> Path | None:
    """Root canónico del prototype bajo el subtree activo ``pit/`` del vault.

    Construido desde el vault YA resuelto (realpath) — los componentes
    pit/lane/iteration vienen regex-validados, así que el único riesgo de
    escape restante son symlinks, que ataja ``_resolve_inside`` (guard 1).
    """
    try:
        vault_real = config.PIT_VAULT_PATH.resolve()
    except OSError:
        return None
    root = (
        vault_real
        / "pit"
        / pit_id
        / "lanes"
        / lane_id
        / "iterations"
        / str(iteration)
        / "prototype"
    )
    return root if root.is_dir() else None


def _resolve_inside(root: Path, rest: str) -> Path:
    """Guard 1: realpath + containment. 403 ante traversal o symlink escape."""
    try:
        file_real = (root / rest).resolve()
    except (OSError, ValueError):
        raise HTTPException(status_code=403, detail="path inválido") from None
    # root viene construido sobre el vault resuelto SIN resolver los
    # componentes pit/lane/iter: si algún symlink (directorio o archivo)
    # saca el resolve fuera del prototype, el is_relative_to falla.
    if not file_real.is_relative_to(root):
        raise HTTPException(status_code=403, detail="path fuera del prototype")
    return file_real


def _default_entry(root: Path) -> str | None:
    """Entry por defecto: ``index.html`` o el primer ``.html`` ordenado."""
    try:
        html_files = sorted(
            p.name
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in (".html", ".htm")
        )
    except OSError:
        return None
    if "index.html" in html_files:
        return "index.html"
    return html_files[0] if html_files else None


def _check_preview_auth(request: Request, scope: str) -> str | None:
    """Auth propia del preview (guard 6).

    Devuelve el token a fijar como cookie si la auth vino por ``?t=``
    (primer hit), o None si vino por cookie. 503 fail-closed sin TOKEN,
    401 sin credenciales, 403 firma/cookie inválida o vencida.
    """
    if not config.TOKEN:
        raise HTTPException(
            status_code=503, detail="MISSION_CONTROL_TOKEN no configurado"
        )
    sig = request.query_params.get("t")
    if sig is not None:
        if not verify_preview_sig(scope, sig):
            raise HTTPException(
                status_code=403, detail="firma inválida o vencida"
            )
        return sig
    cookie = request.cookies.get(PREVIEW_COOKIE)
    if cookie is None:
        raise HTTPException(
            status_code=401, detail="preview requiere URL firmada (preview-link)"
        )
    if not verify_preview_sig(scope, cookie):
        raise HTTPException(status_code=403, detail="cookie inválida o vencida")
    return None


def _set_preview_cookie(response: Response, prefix: str, token_value: str) -> None:
    """Cookie HttpOnly, SameSite=Strict, Path acotado al prefijo del preview."""
    response.set_cookie(
        key=PREVIEW_COOKIE,
        value=token_value,
        max_age=config.PIT_PREVIEW_TTL_SECONDS,
        path=prefix,
        httponly=True,
        samesite="strict",
    )


# ---------------------------------------------------------------------------
# preview-link (bearer — app.py lo monta con dependencies=_auth)
# ---------------------------------------------------------------------------


@link_router.get("/{pit_id}/lanes/{lane_id}/iterations/{iteration}/preview-link")
async def preview_link(
    pit_id: str,
    lane_id: str,
    iteration: int = PathParam(
        ge=pit_vault.ITERATION_MIN, le=pit_vault.ITERATION_MAX
    ),
) -> dict:
    """Emite la URL firmada de preview (TTL config.PIT_PREVIEW_TTL_SECONDS)."""
    _validate_ids(pit_id, lane_id)
    if _prototype_root(pit_id, lane_id, iteration) is None:
        raise HTTPException(status_code=404, detail="prototype not found")
    token_value, expires_at = make_preview_sig(
        _scope(pit_id, lane_id, iteration), config.PIT_PREVIEW_TTL_SECONDS
    )
    return {
        "url": f"{_prefix(pit_id, lane_id, iteration)}?t={token_value}",
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Preview estático (auth propia firma/cookie — SIN bearer global)
# ---------------------------------------------------------------------------


@preview_router.get("/{pit_id}/{lane_id}/{iteration}/{rest:path}")
async def serve_preview(
    request: Request,
    pit_id: str,
    lane_id: str,
    iteration: int = PathParam(
        ge=pit_vault.ITERATION_MIN, le=pit_vault.ITERATION_MAX
    ),
    rest: str = "",
) -> Response:
    """Sirve un archivo del prototype/ con todos los guards del plan §P5.3."""
    _validate_ids(pit_id, lane_id)  # guard 2 — antes de tocar filesystem
    scope = _scope(pit_id, lane_id, iteration)
    fresh_sig = _check_preview_auth(request, scope)  # guard 6
    prefix = _prefix(pit_id, lane_id, iteration)

    root = _prototype_root(pit_id, lane_id, iteration)
    if root is None:
        raise HTTPException(status_code=404, detail="prototype not found")

    if rest == "":
        # Guard 4: el root NO lista; redirige a la entry (assets relativos
        # del HTML resuelven contra el mismo prefijo).
        entry = _default_entry(root)
        if entry is None:
            raise HTTPException(status_code=404, detail="prototype sin HTML")
        response: Response = RedirectResponse(
            url=f"{prefix}{entry}", status_code=302
        )
        if fresh_sig is not None:
            _set_preview_cookie(response, prefix, fresh_sig)
        return response

    # Guard 3: allowlist por extensión del path PEDIDO, antes de tocar disco.
    suffix = PurePosixPath(rest).suffix.lower()
    if suffix not in config.PIT_PREVIEW_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="extensión no permitida")

    file_real = _resolve_inside(root, rest)  # guard 1
    if file_real.is_dir():
        raise HTTPException(status_code=404, detail="not found")  # guard 4
    if not file_real.is_file():
        raise HTTPException(status_code=404, detail="not found")

    try:
        body = file_real.read_bytes()  # lee el path YA resuelto (no re-traversa)
    except OSError:
        raise HTTPException(status_code=404, detail="not found") from None

    headers = {
        "X-Content-Type-Options": "nosniff",  # guard 3
        "Referrer-Policy": "no-referrer",  # guard 5
        "Cache-Control": "no-store",
    }
    if suffix in (".html", ".htm"):
        headers["Content-Security-Policy"] = CSP  # guard 5
    response = Response(
        content=body, media_type=CONTENT_TYPES[suffix], headers=headers
    )
    if fresh_sig is not None:
        _set_preview_cookie(response, prefix, fresh_sig)
    return response


# ---------------------------------------------------------------------------
# Alias legacy /pit-preview/* → canónica (rewrite puro, sin auth ni FS)
# ---------------------------------------------------------------------------


@alias_router.get("/{pit_id}/{lane_id}/{rest:path}")
async def alias_redirect(
    request: Request, pit_id: str, lane_id: str, rest: str = ""
) -> RedirectResponse:
    """Normaliza los 3 formatos de announce del piloto (P5.0) a la canónica.

    Preserva el query string (``?t=`` firmado sigue funcionando). La auth la
    aplica la ruta canónica; acá no se toca filesystem ni se valida firma.
    """
    _validate_ids(pit_id, lane_id)
    rest = rest.strip("/")
    file_part = ""
    match = _ALIAS_CANONICAL_RE.fullmatch(rest)
    if match:
        iteration_raw, file_part = match.group(1), match.group(2) or ""
    else:
        match = _ALIAS_ITER_RE.fullmatch(rest)
        if not match:
            raise HTTPException(
                status_code=404, detail="formato de preview no reconocido"
            )
        iteration_raw = match.group(1)
    iteration = int(iteration_raw)
    if not (pit_vault.ITERATION_MIN <= iteration <= pit_vault.ITERATION_MAX):
        raise HTTPException(status_code=422, detail="invalid iteration")
    target = f"{_prefix(pit_id, lane_id, iteration)}{file_part}"
    if request.url.query:
        target += f"?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)
