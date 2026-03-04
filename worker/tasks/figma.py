"""
Tasks: Figma integration handlers.

- figma.get_file:      Leer metadata + estructura de un archivo Figma.
- figma.get_node:      Leer uno o varios nodos específicos (frame, component, etc.).
- figma.export_image:  Exportar frame/nodo como imagen (PNG, SVG, JPG, PDF).
- figma.add_comment:   Agregar un comentario en un archivo Figma.
- figma.list_comments: Listar comentarios de un archivo Figma.

Autenticación: Personal Access Token en FIGMA_API_KEY.
Docs: https://www.figma.com/developers/api
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .. import config

logger = logging.getLogger("worker.tasks.figma")

FIGMA_BASE_URL = "https://api.figma.com/v1"


def _headers() -> Dict[str, str]:
    return {"X-Figma-Token": config.FIGMA_API_KEY or ""}


def _get(path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    url = f"{FIGMA_BASE_URL}{path}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: Dict) -> Dict[str, Any]:
    url = f"{FIGMA_BASE_URL}{path}"
    resp = requests.post(url, headers=_headers(), json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_figma_get_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lee la metadata y estructura de un archivo Figma.

    Input:
        file_key (str, required): Clave del archivo (de la URL: figma.com/file/{file_key}/...).
        depth (int, optional): Profundidad de nodos a devolver (1–4). Default 2.

    Returns:
        {"ok": True, "name": "...", "last_modified": "...", "pages": [...], "raw": {...}}
    """
    if not config.FIGMA_API_KEY:
        return {"ok": False, "error": "FIGMA_API_KEY not configured"}

    file_key = (input_data.get("file_key") or "").strip()
    if not file_key:
        return {"ok": False, "error": "'file_key' is required"}

    depth = input_data.get("depth", 2)

    try:
        data = _get(f"/files/{file_key}", params={"depth": depth})
    except requests.HTTPError as e:
        return {"ok": False, "error": f"Figma API error: {e.response.status_code} {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    pages: List[Dict] = []
    document = data.get("document", {})
    for child in document.get("children", []):
        pages.append({
            "id": child.get("id"),
            "name": child.get("name"),
            "type": child.get("type"),
            "children_count": len(child.get("children", [])),
        })

    logger.info("[figma.get_file] file_key=%s name=%s pages=%d", file_key, data.get("name"), len(pages))

    return {
        "ok": True,
        "name": data.get("name"),
        "last_modified": data.get("lastModified"),
        "version": data.get("version"),
        "thumbnail_url": data.get("thumbnailUrl"),
        "pages": pages,
    }


def handle_figma_get_node(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lee uno o varios nodos específicos de un archivo Figma.

    Input:
        file_key (str, required): Clave del archivo.
        node_ids (str|list, required): ID o lista de IDs de nodos (ej. "1:2" o ["1:2", "3:4"]).
        depth (int, optional): Profundidad. Default 2.

    Returns:
        {"ok": True, "nodes": {"1:2": {...}, ...}}
    """
    if not config.FIGMA_API_KEY:
        return {"ok": False, "error": "FIGMA_API_KEY not configured"}

    file_key = (input_data.get("file_key") or "").strip()
    if not file_key:
        return {"ok": False, "error": "'file_key' is required"}

    node_ids = input_data.get("node_ids")
    if not node_ids:
        return {"ok": False, "error": "'node_ids' is required"}

    if isinstance(node_ids, list):
        ids_str = ",".join(node_ids)
    else:
        ids_str = str(node_ids)

    depth = input_data.get("depth", 2)

    try:
        data = _get(f"/files/{file_key}/nodes", params={"ids": ids_str, "depth": depth})
    except requests.HTTPError as e:
        return {"ok": False, "error": f"Figma API error: {e.response.status_code} {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    nodes = data.get("nodes", {})
    result = {}
    for node_id, node_data in nodes.items():
        doc = node_data.get("document", {}) if node_data else {}
        result[node_id] = {
            "id": doc.get("id"),
            "name": doc.get("name"),
            "type": doc.get("type"),
            "children_count": len(doc.get("children", [])),
        }

    logger.info("[figma.get_node] file_key=%s nodes=%s", file_key, list(result.keys()))

    return {"ok": True, "nodes": result}


def handle_figma_export_image(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exporta uno o varios frames/nodos de Figma como imagen.

    Input:
        file_key (str, required): Clave del archivo.
        node_ids (str|list, required): ID o lista de IDs de nodos a exportar.
        format (str, optional): "png" | "svg" | "jpg" | "pdf". Default "png".
        scale (float, optional): Escala 0.01–4. Default 1.

    Returns:
        {"ok": True, "images": {"1:2": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/..."}}
    """
    if not config.FIGMA_API_KEY:
        return {"ok": False, "error": "FIGMA_API_KEY not configured"}

    file_key = (input_data.get("file_key") or "").strip()
    if not file_key:
        return {"ok": False, "error": "'file_key' is required"}

    node_ids = input_data.get("node_ids")
    if not node_ids:
        return {"ok": False, "error": "'node_ids' is required"}

    if isinstance(node_ids, list):
        ids_str = ",".join(node_ids)
    else:
        ids_str = str(node_ids)

    fmt = input_data.get("format", "png").lower()
    if fmt not in {"png", "svg", "jpg", "pdf"}:
        return {"ok": False, "error": f"Invalid format '{fmt}'. Must be png, svg, jpg, or pdf."}

    scale = input_data.get("scale", 1)

    try:
        data = _get(
            f"/images/{file_key}",
            params={"ids": ids_str, "format": fmt, "scale": scale},
        )
    except requests.HTTPError as e:
        return {"ok": False, "error": f"Figma API error: {e.response.status_code} {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    images = data.get("images", {})
    logger.info("[figma.export_image] file_key=%s format=%s nodes=%d", file_key, fmt, len(images))

    return {"ok": True, "format": fmt, "images": images}


def handle_figma_add_comment(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agrega un comentario en un archivo Figma.

    Input:
        file_key (str, required): Clave del archivo.
        message (str, required): Texto del comentario.
        node_id (str, optional): ID del nodo al que adjuntar el comentario.
        client_meta (dict, optional): Posición {x, y} o {node_id, node_offset {x,y}}.

    Returns:
        {"ok": True, "id": "...", "message": "...", "created_at": "..."}
    """
    if not config.FIGMA_API_KEY:
        return {"ok": False, "error": "FIGMA_API_KEY not configured"}

    file_key = (input_data.get("file_key") or "").strip()
    if not file_key:
        return {"ok": False, "error": "'file_key' is required"}

    message = (input_data.get("message") or "").strip()
    if not message:
        return {"ok": False, "error": "'message' is required"}

    body: Dict[str, Any] = {"message": message}

    node_id = input_data.get("node_id")
    if node_id:
        body["client_meta"] = input_data.get("client_meta") or {"node_id": node_id, "node_offset": {"x": 0, "y": 0}}
    elif input_data.get("client_meta"):
        body["client_meta"] = input_data["client_meta"]

    try:
        data = _post(f"/files/{file_key}/comments", body)
    except requests.HTTPError as e:
        return {"ok": False, "error": f"Figma API error: {e.response.status_code} {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    logger.info("[figma.add_comment] file_key=%s comment_id=%s", file_key, data.get("id"))

    return {
        "ok": True,
        "id": data.get("id"),
        "message": data.get("message"),
        "created_at": data.get("created_at"),
        "user": data.get("user", {}).get("handle"),
    }


def handle_figma_list_comments(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista los comentarios de un archivo Figma.

    Input:
        file_key (str, required): Clave del archivo.

    Returns:
        {"ok": True, "count": N, "comments": [...]}
    """
    if not config.FIGMA_API_KEY:
        return {"ok": False, "error": "FIGMA_API_KEY not configured"}

    file_key = (input_data.get("file_key") or "").strip()
    if not file_key:
        return {"ok": False, "error": "'file_key' is required"}

    try:
        data = _get(f"/files/{file_key}/comments")
    except requests.HTTPError as e:
        return {"ok": False, "error": f"Figma API error: {e.response.status_code} {e.response.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    comments = data.get("comments", [])
    simplified = [
        {
            "id": c.get("id"),
            "message": c.get("message"),
            "created_at": c.get("created_at"),
            "user": c.get("user", {}).get("handle"),
            "resolved_at": c.get("resolved_at"),
        }
        for c in comments
    ]

    logger.info("[figma.list_comments] file_key=%s count=%d", file_key, len(simplified))

    return {"ok": True, "count": len(simplified), "comments": simplified}
